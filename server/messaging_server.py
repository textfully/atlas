from handlers.webhook import PostHandler
from handlers.server import ThreadedHTTPServer
from config.settings import SERVER_HOST, SERVER_PORT
from utils.logger import logger


def start_server():
    """
    Run the messaging server that handles Atlas requests
    """
    try:
        server = ThreadedHTTPServer((SERVER_HOST, SERVER_PORT), PostHandler)
        logger.info(f"Messaging server started on port {SERVER_PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Failed to start messaging server: {e}")
        raise


if __name__ == "__main__":
    start_server()
