# cache.py
import os
import json
import time
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def cache_get(key):
    val = r.get(key)
    if val is None:
        return None
    try:
        return json.loads(val)
    except json.JSONDecodeError:
        return val

def cache_set(key, value, ttl=600):
    r.setex(key, ttl, json.dumps(value))

def cache_delete_prefix(prefix):
    # careful with KEYS in production; for small keyspace it’s fine
    for k in r.scan_iter(f"{prefix}*"):
        r.delete(k)
