#!/usr/bin/env python3
"""Generate bcrypt hash"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password = "Test@1234"
hashed = pwd_context.hash(password)
print(f"Password: {password}")
print(f"Hash: {hashed}")
