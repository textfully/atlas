from starlette.applications import Starlette
from starlette.routing import Mount
import uvicorn
from config.settings import API_HOST, API_PORT
from api.app import app as fastapi_app
from utils.logger import logger

app = Starlette(
    routes=[
        Mount("/v1", app=fastapi_app),
    ]
)


def start_server():
    """
    Run the FastAPI server that handles API requests
    """
    try:
        logger.info(f"Starting FastAPI server on port {API_PORT}")
        uvicorn.run("api_server:app", host=API_HOST, port=API_PORT, reload=True)
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        raise


if __name__ == "__main__":
    start_server()
