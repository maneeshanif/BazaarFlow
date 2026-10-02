"""Start the real stack for the web auth end-to-end test (task 20), run it, and tear everything down.

    uv run python scripts/e2e_auth_stack.py

Postgres 16 in Docker (roles provisioned like Supabase, migrations applied), three users (owner, manager,
staff) in one shop, the FastAPI backend on :8000 with 1-minute access tokens, then Playwright (which starts the
Next.js server on :3100). Needs Docker and `npm run build` in frontend/ to have been run.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
NAME = "bf-e2e-pg"
PORT = 55440
PW = {"postgres": "admin-pw", "migrator": "mig-pw", "app": "app-pw", "report": "rep-pw"}
USER_PASSWORD = "e2e-password-1"


def sh(args: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=kw.pop("cwd", ROOT), check=True, **kw)


def wait_for_postgres() -> None:
    for _ in range(60):
        probe = subprocess.run(
            ["docker", "exec", NAME, "psql", "-U", "postgres", "-d", "bazaarflow", "-Atc", "select 1"],
            capture_output=True,
        )
        if probe.returncode == 0:
            time.sleep(3)  # the image restarts once after init
            return
        time.sleep(1)
    raise SystemExit("postgres did not become ready")


def url(user: str, scheme: str = "postgresql+asyncpg") -> str:
    pw = {"postgres": PW["postgres"], "migrator": PW["migrator"], "app_user": PW["app"]}[user]
    return f"{scheme}://{user}:{pw}@localhost:{PORT}/bazaarflow"


async def seed_users() -> None:
    import asyncpg

    from app.core.security import hash_password

    conn = await asyncpg.connect(url("postgres", "postgresql"))  # superuser: bypasses RLS for seeding
    try:
        tenant = uuid.uuid4()
        await conn.execute(
            "INSERT INTO tenants (id, name, slug, plan, status, onboarding_state, timezone, currency, created_at, updated_at) "
            "VALUES ($1, 'E2E Mart', 'e2e-mart', 'demo', 'active', 'created', 'Asia/Karachi', 'PKR', now(), now())",
            tenant,
        )
        for role in ("owner", "manager", "staff"):
            user = uuid.uuid4()
            await conn.execute(
                "INSERT INTO users (id, email, hashed_password, is_platform_admin, is_active, created_at, updated_at) "
                "VALUES ($1, $2, $3, false, true, now(), now())",
                user,
                f"{role}@example.com",
                hash_password(USER_PASSWORD),
            )
            await conn.execute(
                "INSERT INTO memberships (id, tenant_id, user_id, role, created_at, updated_at) "
                "VALUES (gen_random_uuid(), $1, $2, $3, now(), now())",
                tenant,
                user,
                role,
            )
    finally:
        await conn.close()


def main() -> int:
    sh(["docker", "rm", "-f", NAME], capture_output=True) if False else subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
    sh(["docker", "run", "-d", "--rm", "--name", NAME, "-p", f"{PORT}:5432", "-e", f"POSTGRES_PASSWORD={PW['postgres']}", "-e", "POSTGRES_DB=bazaarflow", "postgres:16"], capture_output=True)
    api: subprocess.Popen | None = None
    code = 1
    try:
        wait_for_postgres()
        env = {**os.environ, "APP_ENV": "development", "SECRET_KEY": "e2e-secret-key-not-for-anything-else-0123456789"}
        sh(
            ["uv", "run", "python", "-m", "app.cli.provision_db", "--admin-url", url("postgres", "postgresql"), "--database", "bazaarflow"],
            env={**env, "MIGRATOR_PASSWORD": PW["migrator"], "APP_USER_PASSWORD": PW["app"], "REPORT_RO_PASSWORD": PW["report"]},
        )
        sh(["uv", "run", "alembic", "upgrade", "head"], env={**env, "DATABASE_URL_MIGRATIONS": url("migrator")})
        sys.path.insert(0, str(ROOT))
        os.environ.update(env)
        asyncio.run(seed_users())

        api_env = {
            **env,
            "DATABASE_URL": url("app_user"),
            "FRONTEND_ORIGIN": "http://localhost:3100",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "1",
            "MARKETING_SCHEDULER_ENABLED": "false",
            "LEGACY_V1_ROUTES": "true",
        }
        api = subprocess.Popen(["uv", "run", "uvicorn", "app.main:app", "--port", "8000"], cwd=ROOT, env=api_env)
        for _ in range(60):
            try:
                import urllib.request

                urllib.request.urlopen("http://localhost:8000/health", timeout=2)
                break
            except Exception:
                time.sleep(1)
        else:
            raise SystemExit("API did not start")

        result = subprocess.run(
            ["npx", "playwright", "test", *(sys.argv[1:] or ["e2e/auth.spec.ts"])],
            cwd=FRONTEND,
            env={**os.environ, "E2E_AUTH": "1", "API_INTERNAL_URL": "http://localhost:8000"},
            shell=os.name == "nt",
        )
        code = result.returncode
    finally:
        if api is not None:
            api.terminate()
            try:
                api.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api.kill()
        subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
