"""The Supabase provisioning helper: builds the right connection strings and edits .env without leaking secrets."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.cli import provision_supabase
from app.cli.provision_supabase import build_urls, update_env_file

REF, HOST = "llwinbumuaqvypgnickd", "aws-0-ap-south-1.pooler.supabase.com"


def test_urls_use_the_session_pooler_for_migrations_and_the_transaction_pooler_for_the_app() -> None:
    urls = build_urls(REF, HOST, migrator_pw="m-pw", app_pw="a-pw", admin_pw="adm in/pw@")
    assert urls["DATABASE_URL_MIGRATIONS"] == f"postgresql+asyncpg://migrator.{REF}:m-pw@{HOST}:5432/postgres"
    assert urls["DATABASE_URL"] == f"postgresql+asyncpg://app_user.{REF}:a-pw@{HOST}:6543/postgres"
    assert urls["ADMIN_URL"] == f"postgresql://postgres.{REF}:adm%20in%2Fpw%40@{HOST}:5432/postgres"


def test_special_characters_in_the_admin_password_are_percent_encoded() -> None:
    urls = build_urls(REF, HOST, migrator_pw="x", app_pw="x", admin_pw="p@ss:w/ord#1")
    assert urls["ADMIN_URL"].endswith(f"p%40ss%3Aw%2Ford%231@{HOST}:5432/postgres")


def test_env_update_replaces_existing_keys_keeps_the_rest_and_appends_new_ones(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("KEEP=1\nDATABASE_URL=old\n# comment\nSUPABASE_ADMIN_PASSWORD=secret\n", encoding="utf-8")
    update_env_file(env, {"DATABASE_URL": "new", "MIGRATOR_PASSWORD": "mp"}, blank=("SUPABASE_ADMIN_PASSWORD",))
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "KEEP=1" and "# comment" in lines
    assert "DATABASE_URL=new" in lines and "DATABASE_URL=old" not in lines
    assert "MIGRATOR_PASSWORD=mp" in lines
    assert "SUPABASE_ADMIN_PASSWORD=" in lines, "the admin password must not stay on disk"
    assert "secret" not in env.read_text(encoding="utf-8")


def test_a_missing_env_file_is_created(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    update_env_file(env, {"A": "1"}, blank=())
    assert env.read_text(encoding="utf-8").strip() == "A=1"


def test_main_refuses_to_run_without_the_inputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in ("SUPABASE_PROJECT_REF", "SUPABASE_POOLER_HOST", "SUPABASE_ADMIN_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(provision_supabase, "ENV_PATH", tmp_path / ".env")
    assert provision_supabase.main([]) == 1


def test_a_failed_connection_reports_the_class_only_and_leaves_env_untouched(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    env = tmp_path / ".env"
    env.write_text(
        f"SUPABASE_PROJECT_REF={REF}\nSUPABASE_POOLER_HOST={HOST}\nSUPABASE_ADMIN_PASSWORD=very-secret-pw\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(provision_supabase, "ENV_PATH", env)

    async def failing(*_: object) -> None:
        raise ConnectionError("password authentication failed for user postgres.x using very-secret-pw")

    monkeypatch.setattr("app.cli.provision_db.provision", failing)
    assert provision_supabase.main([]) == 1
    captured = capsys.readouterr()
    assert "very-secret-pw" not in captured.out + captured.err
    assert "ConnectionError" in captured.err
    assert "DATABASE_URL" not in env.read_text(encoding="utf-8"), "nothing is written when provisioning failed"


def test_a_failed_step_is_named_without_leaking_the_password() -> None:
    from app.cli.provision_db import _label, _statements

    statements = _statements("postgres", "mig-secret-pw", "app-secret-pw", "rep-secret-pw")
    alter = next(s for s in statements if s.startswith("ALTER ROLE migrator"))
    assert _label(alter) == "ALTER ROLE migrator WITH LOGIN"
    assert not any("secret" in _label(s) for s in statements)
