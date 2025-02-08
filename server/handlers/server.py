from http.server import HTTPServer
import socketserver
from typing import Tuple, Type
from http.server import BaseHTTPRequestHandler


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """
    Handle requests in a separate thread.
    This allows the server to handle multiple requests concurrently.
    """

    def __init__(
        self,
        server_address: Tuple[str, int],
        RequestHandlerClass: Type[BaseHTTPRequestHandler],
    ):
        """
        Initialize the threaded HTTP server.

        Args:
            server_address: Tuple of (host, port)
            RequestHandlerClass: The request handler class to use
        """
        super().__init__(server_address, RequestHandlerClass)
        self.daemon_threads = True  # Set daemon_threads to True for clean shutdown
