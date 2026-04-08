# OWASP Top 10 Test Suite

## Purpose

This directory contains tests for OWASP Top 10 security vulnerabilities:

- **A01**: Broken Access Control (`test_access_control.py`)
- **A02**: Cryptographic Failures (`test_cryptographic_failures.py`)
- **A03**: Injection (`test_injection.py`)
- **A04**: Insecure Design (`test_insecure_design.py`)
- **A05**: Security Misconfiguration (`test_security_misconfiguration.py`)
- **A06**: Vulnerable Components (`test_vulnerable_components.py`)
- **A07**: Identification and Authentication Failures (`test_auth_failures.py`)
- **A08**: Software and Data Integrity Failures (`test_software_integrity.py`)
- **A09**: Security Logging and Monitoring Failures (`test_logging_monitoring.py`)
- **A10**: Server-Side Request Forgery (`test_ssrf.py`)

## Running Tests

```bash
# Run all OWASP tests
pytest tests/owasp/ -v

# Run specific vulnerability class
pytest tests/owasp/test_injection.py -v

# Run with coverage
pytest tests/owasp/ -v --cov=app --cov-report=html
```

## Markers

Use pytest markers to filter tests:
- `-m owasp` - All OWASP tests
- `-m security` - All security tests

## Notes

- Tests use fixtures from `tests/conftest.py`
- Some tests require specific infrastructure (e.g., TLS testing)
- Placeholder tests exist for scenarios requiring specialized tools