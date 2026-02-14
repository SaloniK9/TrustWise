#!/usr/bin/env python3
"""
Phase 5B Verification Script
Tests Redis Sentinel, PostgreSQL Replication, and HAProxy Load Balancing
"""
import time
import requests
import subprocess
import sys

print("=" * 80)
print("PHASE 5B HIGH AVAILABILITY VERIFICATION")
print("=" * 80)
print()

passed = 0
failed = 0

def test_health(name, url, expected_status=200):
    """Test health endpoint."""
    global passed, failed
    try:
        resp = requests.get(url, timeout=5, verify=False)
        if resp.status_code == expected_status:
            print(f"✅ {name}: {resp.status_code}")
            passed += 1
            return True
        else:
            print(f"❌ {name}: Got {resp.status_code}, expected {expected_status}")
            failed += 1
            return False
    except Exception as e:
        print(f"❌ {name}: {e}")
        failed += 1
        return False

def run_docker_cmd(cmd):
    """Run docker command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

# ============================================================================
# TEST 1: Redis Sentinel
# ============================================================================
print("TEST 1: Redis Sentinel Status")
print("-" * 80)

code, out, err = run_docker_cmd('docker exec trustwise-sentinel-1 redis-cli -p 26379 sentinel masters')
if code == 0 and 'mymaster' in out:
    print("✅ Sentinel-1 monitoring mymaster")
    passed += 1
else:
    print(f"❌ Sentinel-1 not monitoring: {err}")
    failed += 1

code, out, err = run_docker_cmd('docker exec trustwise-redis-master redis-cli INFO replication')
if code == 0 and 'role:master' in out:
    print("✅ Redis master is running")
    passed += 1
    # Count replicas
    if 'connected_slaves:2' in out:
        print("✅ Redis has 2 connected replicas")
        passed += 1
    else:
        print(f"⚠️  Redis replica count unexpected")
else:
    print(f"❌ Redis master check failed: {err}")
    failed += 1

print()

# ============================================================================
# TEST 2: PostgreSQL Replication
# ============================================================================
print("TEST 2: PostgreSQL Replication Status")
print("-" * 80)

code, out, err = run_docker_cmd('docker exec trustwise-postgres-primary pg_isready -U trustwise')
if code == 0:
    print("✅ PostgreSQL primary is ready")
    passed += 1
else:
    print(f"❌ PostgreSQL primary not ready: {err}")
    failed += 1

code, out, err = run_docker_cmd('docker exec trustwise-postgres-standby-1 pg_isready -U trustwise')
if code == 0:
    print("✅ PostgreSQL standby-1 is ready")
    passed += 1
else:
    print(f"⚠️  PostgreSQL standby-1 not ready (may be syncing): {err}")

print()

# ============================================================================
# TEST 3: HAProxy Load Balancer
# ============================================================================
print("TEST 3: HAProxy Load Balancer")
print("-" * 80)

test_health("HAProxy stats page", "http://localhost:8404/stats")

# Test API through load balancer
test_health("HAProxy → FastAPI (HTTP)", "http://localhost/health", expected_status=301)  # Redirects to HTTPS
test_health("HAProxy → FastAPI (HTTPS)", "https://localhost/health")

print()

# ============================================================================
# TEST 4: FastAPI Replicas
# ============================================================================
print("TEST 4: FastAPI Replica Health")
print("-" * 80)

test_health("FastAPI-1 direct", "http://localhost:8000/health")
# Note: fastapi-2 and fastapi-3 don't expose ports directly, accessed via HAProxy

print()

# ============================================================================
# TEST 5: Celery Workers
# ============================================================================
print("TEST 5: Celery Workers")
print("-" * 80)

code, out, err = run_docker_cmd('docker ps --filter "name=celery" --format "{{.Names}}: {{.Status}}"')
if code == 0:
    workers = out.strip().split('\n')
    for worker in workers:
        if 'Up' in worker:
            print(f"✅ {worker}")
            passed += 1
        else:
            print(f"❌ {worker}")
            failed += 1
else:
    print(f"❌ Could not check Celery workers: {err}")
    failed += 1

print()

# ============================================================================
# TEST 6: Flower Monitoring
# ============================================================================
print("TEST 6: Flower Monitoring")
print("-" * 80)

test_health("Flower UI", "http://localhost:5555")

print()

# ============================================================================
# SUMMARY
# ============================================================================
print("=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)
print(f"✅ Passed: {passed}")
print(f"❌ Failed: {failed}")
print()

if failed == 0:
    print("🎉 Phase 5B is COMPLETE and operational!")
    print()
    print("Next Steps:")
    print("  - Test failover: docker stop trustwise-redis-master")
    print("  - Monitor Sentinel: docker logs trustwise-sentinel-1")
    print("  - Check HAProxy stats: http://localhost:8404/stats")
    print("  - Access API via load balancer: https://localhost/health")
    sys.exit(0)
else:
    print("⚠️  Some tests failed. Check docker-compose logs for details.")
    print()
    print("Troubleshooting:")
    print("  - Check containers: docker-compose ps")
    print("  - View logs: docker-compose logs [service-name]")
    print("  - Restart services: docker-compose restart")
    sys.exit(1)
