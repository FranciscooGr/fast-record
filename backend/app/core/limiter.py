"""
Shared rate-limiter instance — used by main.py (middleware)
and individual routers (per-endpoint decorators).

The key function extracts the client IP from the request.
Behind a reverse proxy (ngrok, Vercel, etc.) it respects
X-Forwarded-For automatically via Starlette's `client.host`.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
