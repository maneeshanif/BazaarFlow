"""Provision the Supabase roles and write the connection strings into .env, without the passwords ever being
printed, typed on a command line, or pasted into a chat.

Put these three lines in your local .env (it is gitignored), then run the command:

    SUPABASE_PROJECT_REF=<the part after "postgres." in the pooler user name>
    SUPABASE_POOLER_HOST=<aws-0-<region>.pooler.supabase.com from Connect -> Session pooler>
    SUPABASE_ADMIN_PASSWORD=<the database password you set when creating the project>

    uv run python -m app.cli.provision_supabase

It generates strong passwords for ``migrator``, ``app_user`` and ``report_ro``, creates the roles (safe to re-run:
it re-sets them), writes DATABASE_URL_MIGRATIONS and DATABASE_URL plus the three role passwords into .env, and
blanks SUPABASE_ADMIN_PASSWORD afterwards. See docs/operations/supabase-setup.md.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import sys
from pathlib import Path
from urllib.parse import quote

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


def build_urls(ref: str, host: str, *, migrator_pw: str, app_pw: str, admin_pw: str) -> dict[str, str]:
    return {
        # migrations need DDL and session semantics: the session pooler (port 5432)
        "DATABASE_URL_MIGRATIONS": (
            f"postgresql+asyncpg://migrator.{ref}:{quote(migrator_pw, safe='')}@{host}:5432/postgres"
        ),
        # the running API uses the transaction pooler (port 6543)
        "DATABASE_URL": f"postgresql+asyncpg://app_user.{ref}:{quote(app_pw, safe='')}@{host}:6543/postgres",
        "ADMIN_URL": f"postgresql://postgres.{ref}:{quote(admin_pw, safe='')}@{host}:5432/postgres",
    }


def update_env_file(path: Path, values: dict[str, str], *, blank: tuple[str, ...]) -> None:
    """Set ``values`` in a .env file (replacing existing keys, appending new ones) and empty the ``blank`` keys."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    out: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in remaining:
            out.append(f"{key}={remaining.pop(key)}")
        elif key in blank:
            out.append(f"{key}=")
        else:
            out.append(line)
    out += [f"{key}={value}" for key, value in remaining.items()]
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH, override=True)
    ref = os.environ.get("SUPABASE_PROJECT_REF", "")
    host = os.environ.get("SUPABASE_POOLER_HOST", "")
    admin_pw = os.environ.get("SUPABASE_ADMIN_PASSWORD", "")
    wanted = (("SUPABASE_PROJECT_REF", ref), ("SUPABASE_POOLER_HOST", host), ("SUPABASE_ADMIN_PASSWORD", admin_pw))
    missing = [name for name, value in wanted if not value]
    if missing:
        print(f"error: set {', '.join(missing)} in {ENV_PATH.name} first (see this file's docstring)", file=sys.stderr)
        return 1

    from app.cli.provision_db import ProvisionError, provision

    migrator_pw, app_pw, report_pw = (secrets.token_urlsafe(32) for _ in range(3))
    urls = build_urls(ref, host, migrator_pw=migrator_pw, app_pw=app_pw, admin_pw=admin_pw)
    try:
        asyncio.run(provision(urls["ADMIN_URL"], "postgres", migrator_pw, app_pw, report_pw))
    except ProvisionError as exc:  # names the failing step and the server's reason; contains no password
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - name the failure class only: the message can echo connection details
        print(
            f"error: could not provision the roles ({type(exc).__name__}). Check the project ref, host and password.",
            file=sys.stderr,
        )
        return 1
    update_env_file(
        ENV_PATH,
        {
            "DATABASE_URL_MIGRATIONS": urls["DATABASE_URL_MIGRATIONS"],
            "DATABASE_URL": urls["DATABASE_URL"],
            "MIGRATOR_PASSWORD": migrator_pw,
            "APP_USER_PASSWORD": app_pw,
            "REPORT_RO_PASSWORD": report_pw,
        },
        blank=("SUPABASE_ADMIN_PASSWORD",),
    )
    print("roles migrator, app_user and report_ro are ready on the Supabase project")
    print(f"wrote DATABASE_URL_MIGRATIONS and DATABASE_URL to {ENV_PATH.name}; SUPABASE_ADMIN_PASSWORD was cleared")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
