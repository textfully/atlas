import json
from utils.logger import logger
from server.services import atlas


def process_message(sender, is_from_atlas, message_text, attachments):
    """
    Processes a message.

    Args:
        sender (str): The sender of the message
        is_from_atlas (bool): Whether the message is from Atlas
        message_text (str): The text of the message
        attachments (list): List of attachment dictionaries
    """
    if not is_from_atlas and sender != "Unknown":
        if sender.startswith("+"):
            sender_phone = sender
            sender_email = None
        else:
            sender_phone = None
            sender_email = sender
    else:
        sender_phone = None
        sender_email = None

    # Ignore messages sent from Atlas
    if is_from_atlas:
        return

    # TODO: Handle new messages
    if is_from_atlas:
        print(f'New message from Atlas: "{message_text}"')
    else:
        if sender_phone:
            print(f'New message from {sender_phone}: "{message_text}"')
        elif sender_email:
            print(f'New message from {sender_email}: "{message_text}"')
        else:
            print(f'New message from Unknown: "{message_text}"')

        process_attachments(attachments)


def process_attachments(attachments):
    """
    Processes attachments.

    Args:
        attachments (list): List of attachment dictionaries
    """
    for attachment in attachments:
        attachment_type = attachment.get("mimeType", None)

        if attachment_type is None:
            # TODO: Handle unknown attachment types
            logger.error(f"Unknown attachment type: {json.dumps(attachment, indent=4)}")
        elif attachment_type.startswith("image/"):
            attachment_path = atlas.download_attachment(attachment)
            if attachment_path:
                with open(attachment_path, "rb") as file:
                    # TODO: Handle image
                    print("Image downloaded to ", attachment_path)
            else:
                logger.error(
                    f"Failed to download image attachment: {attachment.get('guid')}"
                )

        elif attachment_type.startswith("video/"):
            # TODO: handle video attachments
            print(f"Video attachment: {json.dumps(attachment, indent=4)}")
        else:
            # TODO: Handle other attachment types
            logger.error(
                f"Other attachment type: {attachment_type} for attachment: {json.dumps(attachment, indent=4)}"
            )
