import sys
import asyncio
import time
sys.path.insert(0, '.')

from swarm.enterprise.core.gateway import RateLimiter

async def test_limiter():
    limiter = RateLimiter(default_rate=5, default_burst=5)
    
    for i in range(7):
        print(f"\n--- Request {i+1} ---")
        bucket_before = limiter._buckets.get("test-key")
        if bucket_before:
            print(f"  Before: tokens={bucket_before['tokens']}, check={bucket_before['tokens'] >= 1000}")
        
        allowed = await limiter.check_limit("test-key")
        
        bucket_after = limiter._buckets.get("test-key")
        if bucket_after:
            tokens = bucket_after.get("tokens", 0)
            check = bucket_after["tokens"] >= 1000
            print(f"Request {i+1}: allowed={allowed}, tokens={bucket_after['tokens']}, check={bucket_after['tokens'] >= 1000}")
        else:
            print(f"Request {i+1}: allowed={allowed}, bucket not found")

asyncio.run(test_limiter())
