# Chaos Engineering Tests

## Purpose

Resilience and fault tolerance testing:

- **Infrastructure Failure** (`test_infrastructure_failure.py`) - Node/network failures
- **Dependency Failure** (`test_dependency_failure.py`) - External service unavailability
- **Resource Exhaustion** (`test_resource_exhaustion.py`) - CPU/memory/disk exhaustion
- **Network Issues** (`test_network_issues.py`) - Latency, packet loss, DNS
- **Time-based Chaos** (`test_time_based_chaos.py`) - Clock skew, timezones
- **Data Corruption** (`test_data_corruption.py`) - DB corruption, backup restore
- **Security Chaos** (`test_security_chaos.py`) - Attack simulation
- **Recovery Validation** (`test_recovery_validation.py`) - RTO/RPO measurement
- **GameDays** (`test_game_days.py`) - Chaos engineering exercises
- **Blast Radius** (`test_blast_radius.py`) - Failure containment

## Running Tests

```bash
# Run all chaos tests
pytest tests/chaos/ -v

# Run specific chaos type
pytest tests/chaos/test_network_issues.py -v
```

## Markers

- `-m chaos` - All chaos engineering tests

## Notes

- Most tests are placeholders requiring infrastructure access
- Some tests work with existing fixtures (timeout handling, graceful degradation)
- True chaos engineering requires specialized tools (Chaos Mesh, Gremlin, etc.)