from __future__ import annotations

import pytest

from assistant.policy.detector import detect_sensitive

# ---- Positive cases (should be detected as sensitive) ----

@pytest.mark.parametrize("text", [
    "api_key=sk-abc123xyz789abc123xyz789",
    "API_KEY: my-super-secret-key-value",
    "bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig",
    "AKIAIOSFODNN7EXAMPLE",                           # AWS access key
    "aws_secret_access_key=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "sk-abc123XYZabc123XYZabc1234",                   # OpenAI key
    "password=mysecretpassword",
    "passwd: hunter2",
    "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA",
    "Server=myserver;Database=mydb;Password=mypassword",
    "mongodb://user:mysecret@cluster.mongodb.net/mydb",
    "ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456",
    "xoxb-token-value-here",
    "secret_key=abcdefghij12345678",
])
def test_positive_detection(text: str):
    matches = detect_sensitive(text)
    assert len(matches) > 0, f"Expected sensitive detection for: {text!r}"


# ---- Negative cases (should NOT be detected as sensitive) ----

@pytest.mark.parametrize("text", [
    "The meeting is scheduled for tomorrow at 3pm",
    "def my_function(x): return x + 1",
    "Please review the attached document",
    "I need to update the API documentation",
    "The server is running on port 8080",
    "import os\nimport sys",
    "SELECT * FROM users WHERE id = 1",
    "The password for the project is explained in the README",  # no actual value
])
def test_negative_no_detection(text: str):
    matches = detect_sensitive(text)
    assert len(matches) == 0, f"Unexpected detection in: {text!r}, got {[m.label for m in matches]}"


def test_match_is_redacted():
    matches = detect_sensitive("password=mysecret123")
    assert matches[0].matched_text == "[REDACTED]"


def test_multiple_patterns_in_one_text():
    text = "api_key=abc123 and password=mypwd and ghp_aBcDeFgHiJkLmNoPqRsTuVwXyZ123456"
    matches = detect_sensitive(text)
    assert len(matches) >= 2
