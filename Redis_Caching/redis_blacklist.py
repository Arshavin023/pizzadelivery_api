# redis_blacklist.py

import os
import asyncio
from redis.asyncio import Redis
from dotenv import load_dotenv

load_dotenv()

redis = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True
)

async def add_token_to_blocklist(jti: str, expires_in: int = 1800):
    await redis.setex(f"blocklist:{jti}", expires_in, "true")

async def is_token_blocklisted(jti: str) -> bool:
    return await redis.exists(f"blocklist:{jti}") == 1
