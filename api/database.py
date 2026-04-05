"""
Database setup — SQLAlchemy instance.
Uses PostgreSQL in production (DATABASE_URL env var) or SQLite locally.
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
