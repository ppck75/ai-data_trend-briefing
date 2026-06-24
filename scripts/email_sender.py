from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv


def send_email_if_configured(subject: str, body: str) -> bool:
    load_dotenv()

    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_to = os.getenv("EMAIL_TO")

    if not all([email_user, email_password, email_to]):
        print("ℹ️ 이메일 환경변수가 없어 이메일 발송을 건너뜁니다.")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_user
    msg["To"] = email_to
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(email_user, email_password)
            smtp.send_message(msg)
        print("  ✓ 이메일 발송 완료")
        return True
    except Exception as exc:
        print(f"  ✗ 이메일 발송 실패: {exc}")
        return False
