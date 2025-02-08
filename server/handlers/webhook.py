import json
from http.server import BaseHTTPRequestHandler
from services import message
from utils.logger import logger


class PostHandler(BaseHTTPRequestHandler):
    def return_bad_request(self, error="Bad Request"):
        """
        A function to return a 400 error.

        Args:
            error (str): The error message to return
        """
        self.send_response(400)
        self.end_headers()
        self.wfile.write(error.encode("utf-8"))

    def return_ok(self, message="OK"):
        """
        A function to return a 200 response.

        Args:
            message (str): The message to return
        """
        self.send_response(200)
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))

    def do_POST(self):
        """
        A POST request handler. This is called when a POST request is received.
        This function does some validation around "valid" requests relative to
        what the Atlas server will emit via Webhooks.
        """
        # Ignore any request that isn't JSON
        if self.headers["Content-Type"] != "application/json":
            return self.return_bad_request()

        # Read the data
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)

        try:
            # Convert the data to a JSON object and pass it to the handler
            data = json.loads(post_data)
            self.handle_json(data)
        except ValueError as ex:
            return self.return_bad_request(ex.message or "Invalid JSON received")

        self.return_ok()

    def handle_json(self, data):
        """
        Handles a generic JSON object. This function will check the type of the
        event and handle it accordingly.

        Args:
            data (dict): The JSON data
        """
        print("📩 Received JSON data: ", data)

        event_type = data.get("type")

        match event_type:
            case "new-message":
                self.handle_message(data)
            case "updated-message":
                self.handle_message(data, updated=True)
            case "typing-indicator":
                self.handle_typing_indicator(data)
            case "chat-read-status-changed":
                self.handle_chat_read_status_changed(data)
            case _:
                print("❓ Unhandled event type: ", data.get("type"))

    def handle_message(self, data, updated=False):
        """
        Handles a new-message event.

        Args:
            data (dict): The JSON data
        """
        if not isinstance(data.get("data"), dict):
            return

        chats = data.get("data").get("chats", [])
        if not updated and not chats:
            logger.error("No chats found in data")
            return

        if not updated:
            chat_guid = chats[0].get("guid")
            is_group_chat = chat_guid.startswith("iMessage;+;") or chat_guid.startswith(
                "SMS;+;"
            )

        message_text = data.get("data").get("text", "")
        date_created = data.get("data").get("dateCreated")
        date_read = data.get("data").get("dateRead")
        date_delivered = data.get("data").get("dateDelivered")
        is_from_atlas = data.get("data").get("isFromMe", False)

        attachments = data.get("data").get("attachments", [])

        sender = data.get("data").get("handle", {}).get("address", "Unknown")
        service = data.get("data").get("handle", {}).get("service", "Unknown")
        country_code = (
            data.get("data").get("handle", {}).get("country", "Unknown")
        )  # ISO 3166-1 alpha-2

        message_guid = data.get("data", {}).get("guid")
        thread_originator_guid = data.get("data", {}).get("threadOriginatorGuid")
        is_reply = thread_originator_guid is not None

        # TODO: use message_guid to update message dateDelivered and dateRead in database

        message.process_message(sender, is_from_atlas, message_text, attachments)

    def handle_typing_indicator(self, data):
        """
        Handles a typing-indicator event.

        Args:
            data (dict): The JSON data
        """
        message_guid = data.get("data", {}).get("guid")
        is_typing = data.get("data", {}).get("display", False)

        # TODO: Handle typing indicators
        if is_typing:
            print(f"{message_guid} is typing...")
        else:
            print(f"{message_guid} stopped typing.")

    def handle_chat_read_status_changed(self, data):
        """
        Handles a chat-read-status-changed event.

        Args:
            data (dict): The JSON data
        """

        message_guid = data.get("data", {}).get("chatGuid")
        is_read = data.get("data", {}).get("read", False)

        # TODO: Handle chat read status changed
        if is_read:
            print(f"{message_guid} read the message.")
