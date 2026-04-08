# Performance Tests

## Purpose

Performance and load testing for system reliability:

- **Baseline** (`test_baseline.py`) - Response time baselines
- **Load** (`test_load.py`) - Load testing with ramp-up
- **Stress** (`test_stress.py`) - Breaking point identification
- **Spike** (`test_spike.py`) - Sudden traffic spikes
- **Endurance** (`test_endurance.py`) - Long-running stability
- **Volume** (`test_volume.py`) - Large dataset processing
- **Resource Utilization** (`test_resource_utilization.py`) - CPU/memory/disk monitoring
- **Database Performance** (`test_database_performance.py`) - Query optimization
- **Cache Efficiency** (`test_cache_efficiency.py`) - Cache hit/miss ratios
- **Third-party** (`test_third_party.py`) - External API performance

## Running Tests

```bash
# Run all performance tests
pytest tests/performance/ -v

# Run baseline tests only
pytest tests/performance/test_baseline.py -v

# Run with timing
pytest tests/performance/ -v --durations=10
```

## Markers

- `-m performance` - All performance tests

## Notes

- Performance tests may take longer to run
- Use `--timeout=120` for endurance tests
- Some tests require `psutil` for resource monitoring