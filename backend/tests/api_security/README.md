# API Security Tests

## Purpose

Advanced API security tests beyond OWASP Top 10:

- **Rate Limiting** (`test_rate_limiting.py`) - Rate limiting bypass techniques
- **Token Security** (`test_token_security.py`) - JWT algorithm confusion, token attacks
- **Business Logic** (`test_business_logic.py`) - Workflow manipulation, race conditions
- **Documentation** (`test_documentation.py`) - API documentation exposure
- **Content-Type** (`test_content_type.py`) - Parser differentials, content-type confusion
- **HTTP Method Override** (`test_http_method_override.py`) - Method override attacks

## Running Tests

```bash
# Run all API security tests
pytest tests/api_security/ -v

# Run specific test
pytest tests/api_security/test_token_security.py -v
```

## Markers

- `-m api_security` - All API security tests

## Notes

- Tests validate proper API security configurations
- Some tests check for information disclosure
- Business logic tests verify workflow integrity