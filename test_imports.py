#!/usr/bin/env python
"""
Minimal import test to verify core dependencies
"""
import sys
print(f"Python version: {sys.version}")
print("\n=== TESTING IMPORTS ===\n")

try:
    import fastapi
    print("✅ fastapi")
except ImportError as e:
    print(f"❌ fastapi: {e}")

try:
    import sqlalchemy
    print("✅ sqlalchemy")
except ImportError as e:
    print(f"❌ sqlalchemy: {e}")

try:
    import httpx
    print("✅ httpx")
except ImportError as e:
    print(f"❌ httpx: {e}")

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    print("✅ apscheduler")
except ImportError as e:
    print(f"❌ apscheduler: {e}")

try:
    from prometheus_client import Counter
    print("✅ prometheus_client")
except ImportError as e:
    print(f"❌ prometheus_client: {e}")

try:
    from slowapi import Limiter
    print("✅ slowapi")
except ImportError as e:
    print(f"❌ slowapi: {e}")

try:
    from pydantic import BaseModel
    print("✅ pydantic")
except ImportError as e:
    print(f"❌ pydantic: {e}")

try:
    from dotenv import load_dotenv
    print("✅ python-dotenv")
except ImportError as e:
    print(f"❌ python-dotenv: {e}")

try:
    import beautifulsoup4
    print("✅ beautifulsoup4")
except ImportError as e:
    print(f"❌ beautifulsoup4: {e}")

print("\n=== TESTING APP MODULES (without DB) ===\n")

# Test imports from app structure
import os
os.chdir('/app' if os.path.exists('/app') else '.')

try:
    from app.config import Settings
    print("✅ app.config")
except Exception as e:
    print(f"❌ app.config: {e}")

try:
    from app.schemas import JobResponse
    print("✅ app.schemas")
except Exception as e:
    print(f"❌ app.schemas: {e}")

try:
    # This might fail if database driver not installed
    from app.database.models import Job
    print("✅ app.database.models")
except Exception as e:
    print(f"⚠️  app.database.models: {e}")

print("\n=== DEPENDENCIES CHECK COMPLETE ===")
