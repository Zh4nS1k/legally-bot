import logging
import re
import random
import string
import aiosmtplib
from email.message import EmailMessage
from legally_bot.config import settings

class EmailService:
    @staticmethod
    def is_valid_email(email: str) -> bool:
        # Basic regex for email validation
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return re.match(pattern, email) is not None

    @staticmethod
    def is_valid_name(name: str) -> bool:
        # Min 2 characters, mostly letters (allowing spaces and basic punctuation like hyphens)
        if len(name) < 2:
            return False
        # Remove spaces and check if remaining are alpha
        clean_name = name.replace(" ", "").replace("-", "")
        return clean_name.isalpha()

    @staticmethod
    def generate_code(length=6) -> str:
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    async def send_verification_code(to_email: str, code: str):
        if not settings.SMTP_USER or not settings.SMTP_PASS:
            logging.warning("⚠️ SMTP credentials not set. Code not sent.")
            return False

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM
        message["To"] = to_email
        message["Subject"] = "Legally Bot - Verification Code"
        message.set_content(f"Hello,\n\nYour verification code for Legally Bot is: {code}\n\nPlease enter this code in the bot to complete your registration.\n\nBest regards,\nLegally Bot Team")

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASS,
                use_tls=False,
                start_tls=True 
            )
            logging.info(f"📧 Verification code sent to {to_email}")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to send email to {to_email}: {e}")
            return False
