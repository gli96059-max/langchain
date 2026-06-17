"""
Backward-compatibility shim for PostgreSQL migration.

All user-related functions have moved to app.db.
This module re-exports them so existing imports in auth.py and chef.py
continue to work without modification.
"""
from app.db import create_user, verify_user, get_user_by_id, init_db as init_master_db
