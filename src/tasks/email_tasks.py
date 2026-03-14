import asyncio

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from core.celery import celery_app
from core.settings import settings


conf = ConnectionConfig(
    MAIL_USERNAME="",
    MAIL_PASSWORD="",
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.SMTP_PORT,
    MAIL_SERVER=settings.SMTP_HOST,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=False,
    VALIDATE_CERTS=False,
    TEMPLATE_FOLDER="templates",
)

TEMPLATES = {
    "activation": "account_activation.html",
    "reset_pass": "reset_password.html",
    "reset_pass_success": "reset_password_success.html"
}

@celery_app.task(name="tasks.email_tasks.send_email")
def send_email(email: str, body_data: dict, msg_type: str):
    subjects = {
        "activation": "Welcome! Please activate your account",
        "reset_pass": "Reset your password",
        "reset_pass_success": "Your password has been changed"
    }
    message = MessageSchema(
        subject=subjects[msg_type],
        recipients=[email],
        template_body=body_data,
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    try:
        asyncio.run(fm.send_message(message, template_name=TEMPLATES[msg_type]))
        return f"Sent to {email}"
    except Exception as e:
        return f"Failed: {str(e)}"
