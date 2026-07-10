"""Reads environment variables to decide how the app talks to its data.

BACKEND=memory (default) -> MemoryRepository, no network, great for dev/demo.
BACKEND=supabase          -> SupabaseRepository, needs SUPABASE_URL + SUPABASE_KEY.

Nothing above this file (services, pages, app.py) needs to know which one
is active -- they only ever see the Repository interface.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set by the OS/host instead

BACKEND = os.getenv("BACKEND", "supabase").strip().lower()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()


def build_repository():
    if BACKEND == "supabase" and SUPABASE_URL and SUPABASE_KEY:
        from backend.supabase_repository import SupabaseRepository
        return SupabaseRepository(SUPABASE_URL, SUPABASE_KEY)

    from backend.memory_repository import MemoryRepository
    return MemoryRepository()
