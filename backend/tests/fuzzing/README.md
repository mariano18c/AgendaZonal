# Fuzzing Tests

## Purpose

Comprehensive fuzzing tests for discovering edge cases and vulnerabilities:

- **Protocol Fuzzing** (`test_protocol_fuzzing.py`) - AFL++/libFuzzer integration
- **API Fuzzing** (`test_api_fuzzing.py`) - Schemathesis/Pact integration
- **Web Fuzzing** (`test_web_fuzzing.py`) - OWASP ZAP web fuzzing
- **Database Fuzzing** (`test_database_fuzzing.py`) - SQL injection fuzzing
- **File Upload Fuzzing** (`test_file_upload_fuzzing.py`) - File upload fuzzing
- **Memory Safety** (`test_memory_safety.py`) - ASan/UBSan integration
- **Configuration Fuzzing** (`test_configuration_fuzzing.py`) - Config file parsing
- **Distributed Fuzzing** (`test_distributed_fuzzing.py`) - Cluster fuzzing

## Running Tests

```bash
# Run all fuzzing tests
pytest tests/fuzzing/ -v

# Run specific fuzzing type
pytest tests/fuzzing/test_database_fuzzing.py -v
```

## Markers

- `-m fuzzing` - All fuzzing tests

## Notes

- Most tests are placeholders requiring specialized fuzzing tools
- Database fuzzing tests work with existing fixtures
- Web fuzzing provides basic input validation testing