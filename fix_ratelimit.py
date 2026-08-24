with open('/home/kali/swarm-agent/swarm/enterprise/core/gateway/server.py', 'r') as f:
    content = f.read()

old = '''    async def check_limit(self, key: str, rate: Optional[int] = None, burst: Optional[int] = None) -> bool:
        async with self._lock:
            rate = rate or self.default_rate
            burst = burst or self.default_burst

            now = time.time()
            bucket = self._buckets.get(key)

            if not bucket:
                self._buckets[key] = {
                    "tokens": burst,
                    "last_refill": time.time(),
                    "rate": rate,
                    "burst": burst,
                }
                return True

            bucket = self._buckets[key]
            elapsed = time.time() - bucket["last_refill"]
            bucket["tokens"] = min(bucket["burst"], bucket["tokens"] + elapsed * bucket["rate"])
            bucket["last_refill"] = time.time()

            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True

            return False'''

new = '''    async def check_limit(self, key: str, rate: Optional[int] = None, burst: Optional[int] = None) -> bool:
        async with self._lock:
            rate = rate or self.default_rate
            burst = burst or self.default_burst

            now = time.time()
            bucket = self._buckets.get(key)

            if not bucket:
                self._buckets[key] = {
                    "tokens": burst * 1000,  # Use integer tokens (millitokens)
                    "last_refill": time.time(),
                    "rate": rate * 1000,  # millitokens per second
                    "burst": burst * 1000,
                }
                return True

            bucket = self._buckets[key]
            elapsed = time.time() - bucket["last_refill"]
            # Refill tokens (rate is in tokens per second, we use millitokens)
            bucket["tokens"] = min(bucket["burst"], bucket["tokens"] + int(elapsed * bucket["rate"]))
            bucket["last_refill"] = time.time()

            if bucket["tokens"] >= 1000:  # 1000 millitokens = 1 token
                bucket["tokens"] -= 1000
                return True

            return False'''

with open('/home/kali/swarm-agent/swarm/enterprise/core/gateway/server.py', 'w') as f:
    f.write(content.replace(old, new))

print("Fixed RateLimiter to use integer tokens")
