import os
import resend

resend.api_key = os.environ["RESEND_API_KEY"]


def send_email(to: str, subject: str, body: str):
    params: resend.Emails.SendParams = {
        "from": "Textfully <noreply@textfully.dev>",
        "to": [to],
        "subject": subject,
        "html": body,
    }

    email = resend.Emails.send(params)
    return email
