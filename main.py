import os

from src.config import BASE_DIR
from src.server import app

if __name__ == "__main__":
    import uvicorn

    """just for debug"""

    LOGGING_CONFIG_PATH = os.path.join(BASE_DIR, "logging.ini")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=LOGGING_CONFIG_PATH)
