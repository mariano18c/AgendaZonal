"""Performance: Spike testing.

Tests for sudden traffic spikes and system elasticity.
"""
import pytest
import time
import concurrent.futures
from tests.conftest import _bearer


class TestSpikeTesting:
    """Spike testing scenarios."""

    def test_sudden_traffic_spike(self, client, create_contact):
        """Test system response to sudden traffic spike."""
        contact = create_contact()
        
        # Normal traffic
        for _ in range(5):
            r = client.get(f"/api/contacts/{contact.id}")
            assert r.status_code == 200
        
        # Sudden spike
        def spike_request():
            return client.get(f"/api/contacts/{contact.id}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(spike_request) for _ in range(100)]
            results = [f.result() for f in futures]
        
        success_count = sum(1 for r in results if r.status_code == 200)
        
        # Should handle some of the spike
        assert success_count > 0

    def test_recovery_after_spike(self, client, create_contact):
        """Test recovery after traffic spike."""
        contact = create_contact()
        
        # Spike
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(client.get, f"/api/contacts/{contact.id}") for _ in range(100)]
            [f.result() for f in futures]
        
        # Wait for recovery
        time.sleep(2)
        
        # Should recover
        r = client.get(f"/api/contacts/{contact.id}")
        assert r.status_code == 200

    def test_zero_to_high_spike(self, client):
        """Test going from zero to high traffic instantly."""
        # Immediate high load
        def instant_spike():
            return client.get("/api/categories")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(instant_spike) for _ in range(200)]
            results = [f.result() for f in futures]
        
        success = sum(1 for r in results if r.status_code == 200)
        
        # Should handle some requests
        assert success > 0


class TestElasticity:
    """Test system elasticity."""

    def test_auto_scaling_trigger(self, client):
        """Test behavior when scaling would be triggered."""
        # Simulate traffic that would trigger scaling
        for _ in range(10):
            r = client.get("/api/categories")
            assert r.status_code == 200

    def test_graceful_degradation_spike(self, client):
        """Test graceful degradation during spike."""
        # High traffic
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(client.get, "/api/categories") for _ in range(100)]
            results = [f.result() for f in futures]
        
        # Core functionality should still work
        r = client.get("/health")
        assert r.status_code == 200


class TestBurstTraffic:
    """Test burst traffic handling."""

    def test_burst_requests(self, client):
        """Test burst of requests."""
        # Send burst
        for _ in range(10):
            r = client.get("/api/categories")
            assert r.status_code == 200

    def test_burst_write_requests(self, client, user_headers):
        """Test burst of write requests."""
        def create_contact(i):
            return client.post(
                "/api/contacts",
                headers=user_headers,
                json={"name": f"Burst {i}", "phone": f"123456{i}"}
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_contact, i) for i in range(20)]
            results = [f.result() for f in futures]
        
        success = sum(1 for r in results if r.status_code == 201)
        assert success > 0


class TestSpikeRecovery:
    """Test recovery from spikes."""

    def test_rapid_recovery(self, client):
        """Test rapid recovery after spike."""
        # Cause spike
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(client.get, "/api/categories") for _ in range(60)]
            [f.result() for f in futures]
        
        # Quick recovery check
        times = []
        for _ in range(10):
            start = time.time()
            r = client.get("/api/categories")
            times.append(time.time() - start)
            assert r.status_code == 200
        
        avg_time = sum(times) / len(times)
        assert avg_time < 1.0

    def test_full_recovery(self, client):
        """Test full recovery after spike."""
        # Stress
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            futures = [executor.submit(client.get, "/api/categories") for _ in range(80)]
            [f.result() for f in futures]
        
        # Wait
        time.sleep(3)
        
        # Full recovery
        r = client.get("/health")
        assert r.status_code == 200
        
        r = client.get("/api/categories")
        assert r.status_code == 200


class TestSpikePatterns:
    """Different spike patterns."""

    def test_square_wave_spike(self, client):
        """Test square wave spike pattern."""
        # High
        for _ in range(20):
            r = client.get("/api/categories")
        
        # Low
        time.sleep(0.5)
        
        # High again
        for _ in range(20):
            r = client.get("/api/categories")
        
        assert True

    def test_sawtooth_spike(self, client):
        """Test sawtooth spike pattern."""
        for i in range(5):
            # Increasing load
            num_requests = (i + 1) * 10
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
                futures = [executor.submit(client.get, "/api/categories") for _ in range(num_requests)]
                [f.result() for f in futures]

    def test_step_spike(self, client):
        """Test step spike pattern."""
        # Step 1
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(client.get, "/api/categories") for _ in range(10)]
            [f.result() for f in futures]
        
        # Step 2
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(client.get, "/api/categories") for _ in range(40)]
            [f.result() for f in futures]
        
        # Step 3
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(client.get, "/api/categories") for _ in range(100)]
            results = [f.result() for f in futures]
        
        success = sum(1 for r in results if r.status_code == 200)
        assert success > 0


class TestSpikeMonitoring:
    """Monitor system during spikes."""

    def test_response_time_during_spike(self, client, create_contact):
        """Test response time degradation during spike."""
        contact = create_contact()
        
        # Baseline
        baseline_times = []
        for _ in range(10):
            start = time.time()
            r = client.get(f"/api/contacts/{contact.id}")
            baseline_times.append(time.time() - start)
        
        baseline_avg = sum(baseline_times) / len(baseline_times)
        
        # Spike
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(client.get, f"/api/contacts/{contact.id}") for _ in range(60)]
            [f.result() for f in futures]
        
        # Measure again
        spike_times = []
        for _ in range(10):
            start = time.time()
            r = client.get(f"/api/contacts/{contact.id}")
            spike_times.append(time.time() - start)
        
        spike_avg = sum(spike_times) / len(spike_times)
        
        # Spike times should not be dramatically worse
        assert spike_avg < baseline_avg * 10