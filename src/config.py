import os
from pathlib import Path

from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent


class Config:
    # Load environment variables from .env file
    load_dotenv()
    # Swagger service config
    swagger_urls = os.getenv("SWAGGER_URLS", None)
    swagger_api_servers = os.getenv("SWAGGER_API_SERVERS", None)
    swagger_timeout = float(os.getenv("SWAGGER_TIMEOUT", "30.0"))
    swagger_headers = os.getenv("SWAGGER_HEADERS", "{}")
    swagger_tool_prefix = os.getenv("SWAGGER_TOOL_PREFIX", "swagger_")


config = Config()
