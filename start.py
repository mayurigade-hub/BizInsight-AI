import os
import sys

# Ensure backend directory is at head of sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Switch working directory to backend
os.chdir(BACKEND_DIR)

if __name__ == "__main__":
    import uvicorn
    from bizinsight_api.main import app

    port = int(os.getenv("PORT", 8001))
    print(f"Starting BizInsight AI API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
