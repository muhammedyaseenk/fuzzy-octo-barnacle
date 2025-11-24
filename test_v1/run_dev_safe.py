#!/usr/bin/env python3
"""
Safe development server runner that handles missing services
"""
import uvicorn
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
os.chdir(project_root)

if __name__ == "__main__":
    print("🚀 Starting Aurum Matrimony API (Development Mode)")
    print("This version will start even if PostgreSQL/Redis/MinIO are not available")
    print("Visit http://localhost:8000/setup-guide for setup instructions")
    print("Visit http://localhost:8000/docs for API documentation")
    print()
    
    uvicorn.run(
        "app.main_dev:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        log_level="info"
    )