"""Password policy for new accounts (PRD F-002: at least 8 characters and not in a common-password list).

The list holds the passwords people choose most often that are at least 8 characters long (shorter ones already fail
the length rule). It is deliberately small and offline: it stops the obvious guesses without calling an outside service.
"""

from __future__ import annotations

COMMON_PASSWORDS: frozenset[str] = frozenset(
    {
        "12345678", "123456789", "1234567890", "12345678910", "11111111", "00000000", "87654321", "98765432",
        "123123123", "112233445", "1q2w3e4r", "1q2w3e4r5t", "1qaz2wsx", "qwertyui", "qwertyuiop", "qwerty123",
        "qwerty1234", "qwerty12345", "asdfghjk", "asdfghjkl", "zxcvbnm1", "zxcvbnm123", "q1w2e3r4", "q1w2e3r4t5",
        "password", "password1", "password12", "password123", "password1234", "passw0rd", "p@ssw0rd", "p@ssword",
        "pass1234", "pass12345", "admin123", "admin1234", "administrator", "welcome1", "welcome123", "letmein1",
        "letmein123", "iloveyou", "iloveyou1", "iloveyou123", "princess1", "sunshine1", "football1", "baseball1",
        "superman1", "monkey123", "dragon123", "master123", "shadow123", "michael123", "jordan123", "abc12345",
        "abcd1234", "abcd12345", "abcdefgh", "abcdefg1", "aaaaaaaa", "bbbbbbbb", "zzzzzzzz", "changeme",
        "changeme123", "default123", "test1234", "test12345", "testtest", "testing123", "login123", "user1234",
        "internet", "computer", "trustno1", "whatever", "freedom1", "starwars", "pakistan", "pakistan1",
        "pakistan123", "bazaarflow", "bazaarflow1", "bazaarflow123", "karachi123", "lahore123", "islamabad1",
        "muhammad", "muhammad1", "muhammad123", "allahallah", "mohammed1", "bismillah", "bismillah1", "03001234567",
        "923001234567", "1234qwer", "qwer1234", "asdf1234", "zxcv1234", "1234abcd", "12341234", "12121212",
        "11223344", "55555555", "66666666", "77777777", "88888888", "99999999", "123456aa", "123456ab", "a1234567",
        "a12345678", "aa123456", "aa1234567", "abc123456", "qazwsxedc", "qazwsx123", "1qazxsw2", "zaq12wsx",
        "passwort", "motdepasse", "contrasena", "master12", "hello123", "hello1234", "secret123", "secret12",
        "mypassword", "mypass123", "newpass123", "password!", "password@1", "password#1", "pa55word", "pa55w0rd",
    }
)


def is_common_password(password: str) -> bool:
    """True for a listed password, any capitalisation of one, or a single character repeated."""
    lowered = password.strip().lower()
    return lowered in COMMON_PASSWORDS or len(set(lowered)) == 1
