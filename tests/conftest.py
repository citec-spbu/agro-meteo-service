import os
import sys
from pathlib import Path


os.environ.setdefault("APP_TITLE", "meteo-service-test")
os.environ.setdefault("APP_VERSION", "0.0.0-test")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
