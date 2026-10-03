"""Task 65: personal data never reaches an agent trace."""

from __future__ import annotations

from app.agent_runtime.redact import Redactor


def test_phone_numbers_and_emails_are_masked_by_pattern() -> None:
    r = Redactor()
    out = r.text("Call +92 300 1234567 or 0300-1234567, mail zainab@example.com about 2 shirts")
    assert "1234567" not in out and "zainab@example.com" not in out
    assert "[phone]" in out and "[email]" in out and "2 shirts" in out


def test_a_name_no_pattern_could_find_is_removed_once_a_tool_touched_it() -> None:
    r = Redactor()
    assert "Zainab" in r.text("Zainab wants 2 shirts")  # not known yet
    r.learn("Zainab Bibi", "customer")
    out = r.text("zainab wants 2 shirts, ZAINAB BIBI owes Rs 500")
    assert "zainab" not in out.lower() and "bibi" not in out.lower()
    assert out.count("[customer]") == 2 and "2 shirts" in out


def test_longer_values_are_replaced_before_their_parts() -> None:
    r = Redactor()
    r.learn("Ali Raza", "customer")
    assert r.text("Ali Raza and Ali") == "[customer] and [customer]"


def test_nested_data_is_redacted_and_secret_keys_are_blanked() -> None:
    r = Redactor()
    r.learn("+923001234567", "phone")
    data = {"customer": "x", "contact": ["+923001234567", {"note": "ring 0300 1234567"}], "api_key": "sk-123", "qty": 2}
    out = r.data(data)
    assert out["api_key"] == "***" and out["qty"] == 2
    assert "1234567" not in str(out)


def test_one_letter_values_are_ignored_so_ordinary_words_survive() -> None:
    r = Redactor()
    r.learn("A", "customer")
    assert r.text("a shirt and a hat") == "a shirt and a hat"
