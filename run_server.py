"""Entry point for PyInstaller-compiled VoWERP3 Backend."""
import uvicorn
import sys
import os

# When running as compiled exe, set the working directory to the exe location
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

from src.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)
