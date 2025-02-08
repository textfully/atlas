import requests
import tempfile
from typing import Optional, Dict
from utils.logger import logger
from config.settings import ATLAS_SERVER_ADDRESS, ATLAS_SERVER_PASSWORD


def check_imessage_availability(chat_guid: str) -> bool:
    """
    Checks if the chat can be reached via iMessage.

    Args:
        chat_guid (str): The chat guid to check

    Returns:
        bool: True if the chat can be reached via iMessage, False otherwise
    """
    params = {"password": ATLAS_SERVER_PASSWORD, "address": chat_guid}

    try:
        response = requests.get(
            f"{ATLAS_SERVER_ADDRESS}/api/v1/handle/availability/imessage",
            params=params,
        )
        response.raise_for_status()

        response_data = response.json()
        return response_data.get("data", {}).get("available", False)
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to check iMessage availability: {str(e)}")
        return False


def create_chat(recipient: str, message: str) -> Optional[str]:
    """
    Creates a chat with the given recipient.

    Args:
        recipient (str): The recipient to add to the chat

    Returns:
        Optional[str]: The chat guid of the created chat, or None if an error occurred
    """
    params = {"password": ATLAS_SERVER_PASSWORD}
    data = {"addresses": [recipient], "message": message}

    try:
        response = requests.post(
            f"{ATLAS_SERVER_ADDRESS}/api/v1/chat/new",
            json=data,
            params=params,
        )
        response.raise_for_status()

        response_data = response.json()
        return response_data.get("data", {}).get("messages", [{}])[0].get("guid")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create chat: {str(e)}")
        return None


def get_chat(chat_guid: str) -> Optional[str]:
    """
    Gets a chat by its guid.

    Args:
        chat_guid (str): The chat guid to get

    Returns:
        Optional[str]: The chat guid of the chat, or None if an error occurred
    """
    params = {"password": ATLAS_SERVER_PASSWORD}

    try:
        response = requests.get(
            f"{ATLAS_SERVER_ADDRESS}/api/v1/chat/{chat_guid}",
            params=params,
        )
        response.raise_for_status()

        response_data = response.json()
        return response_data.get("data", {}).get("guid")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get chat: {str(e)}")
        return None


def send_text(
    chat_guid: str, message: str, method: str = "private-api"
) -> Optional[str]:
    """
    Sends a text message to a chat.

    Args:
        chat_guid (str): The chat guid to send the message to
        message (str): The text to send
        method (str): The method to use to send the message. Defaults to "private-api"

    Returns:
        Optional[str]: The message_guid of the sent message, or None if an error occurred
    """
    params = {"password": ATLAS_SERVER_PASSWORD}
    data = {"chatGuid": chat_guid, "message": message, "method": method}

    try:
        response = requests.post(
            f"{ATLAS_SERVER_ADDRESS}/api/v1/message/text",
            json=data,
            params=params,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        response_data = response.json()
        return response_data.get("data", {}).get("guid")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send message to chat {chat_guid}: {str(e)}")
        return None


def download_attachment(attachment: Dict) -> Optional[str]:
    """
    Downloads an attachment.

    Args:
        attachment (Dict): Attachment dictionary containing metadata

    Returns:
        Optional[str]: Path to the downloaded temporary file, or None if an error occurred
    """
    try:
        params = {
            "password": ATLAS_SERVER_PASSWORD,
            "width": attachment.get("width", 800),
            "height": attachment.get("height", 800),
            "quality": "better",
        }
        response = requests.get(
            f"{ATLAS_SERVER_ADDRESS}/api/v1/attachment/{attachment['guid']}/download",
            params=params,
        )
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name

        return temp_file_path

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download attachment: {str(e)}")
        return None

    except Exception as e:
        logger.error(f"Unknown error while processing attachment: {str(e)}")
        return None
