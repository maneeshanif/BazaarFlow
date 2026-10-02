"""The signing key fails closed: no key means no start, unless the environment is `test` or dev mode is explicit."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.settings import Settings


def _settings(**kwargs: object) -> Settings:
    return Settings(_env_file=None, **kwargs)  # type: ignore[call-arg]


@pytest.mark.parametrize("env", ["development", "production", "staging", "prod", "Production", "", "anything"])
def test_a_missing_secret_key_refuses_to_start(env: str) -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _settings(APP_ENV=env, SECRET_KEY="")


def test_a_real_secret_key_is_accepted_everywhere() -> None:
    assert _settings(APP_ENV="production", SECRET_KEY="x" * 40).SECRET_KEY == "x" * 40


def test_the_test_environment_gets_a_throwaway_key() -> None:
    assert _settings(APP_ENV="test", SECRET_KEY="").SECRET_KEY


def test_dev_mode_must_be_opted_into_explicitly() -> None:
    assert _settings(APP_ENV="development", SECRET_KEY="", ALLOW_INSECURE_DEV_SECRET=True).SECRET_KEY


def test_the_insecure_dev_opt_in_is_ignored_in_production() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        _settings(APP_ENV="production", SECRET_KEY="", ALLOW_INSECURE_DEV_SECRET=True)
