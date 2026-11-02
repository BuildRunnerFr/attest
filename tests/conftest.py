import os
import sys
from pathlib import Path

os.environ["ATTEST_BACKEND"] = "mock"
os.environ.setdefault("NO_PROXY", "127.0.0.1,localhost")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
