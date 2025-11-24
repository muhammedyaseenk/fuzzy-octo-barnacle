#!/usr/bin/env python3
"""
Development server runner for Aurum Matrimony API
"""
import uvicorn
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
os.chdir(project_root)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        log_level="info"
    )