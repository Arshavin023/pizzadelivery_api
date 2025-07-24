from typing import Set

blocklisted_tokens: Set[str] = set()

def add_token_to_blocklist(token: str):
    blocklisted_tokens.add(token)

def is_token_blocklisted(token: str) -> bool:
    return token in blocklisted_tokens