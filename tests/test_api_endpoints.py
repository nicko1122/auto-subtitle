import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from src.api.server import app

def test_api():
    client = TestClient(app)
    
    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    print("✔ /api/health passed:", res.json())
    
    # 2. Index HTML
    res_html = client.get("/")
    assert res_html.status_code == 200
    assert "select-llm-engine" in res_html.text
    print("✔ / (HTML) passed: select-llm-engine is present in UI!")

    # 3. Assets check
    res_assets = client.get("/api/assets")
    assert res_assets.status_code == 200
    print("✔ /api/assets passed:", f"{len(res_assets.json().get('assets', []))} assets found")

if __name__ == "__main__":
    test_api()
    print("All API integration tests passed!")
