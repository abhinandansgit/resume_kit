import re
import random
import string
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders


def generate_resume_id():
    year = datetime.utcnow().year
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"RES-{year}-{suffix}"


def generate_password(name: str, dob: str) -> str:
    first = name.strip().split()[0] if name.strip() else "user"
    return f"{first}-{dob}"


def utc_now() -> str:
    return datetime.utcnow().isoformat()


def expiry_from_now(hours: int = 24) -> str:
    return (datetime.utcnow() + timedelta(hours=hours)).isoformat()


def is_expired(expires_at: str) -> bool:
    try:
        return datetime.utcnow() > datetime.fromisoformat(expires_at)
    except Exception:
        return True


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))


def validate_phone(phone: str) -> bool:
    if not phone:
        return True
    cleaned = re.sub(r"[\s\-\(\)\+]", "", phone)
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15


def auto_capitalize(text: str) -> str:
    stop_words = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
                  "for", "of", "with", "by", "from", "as", "is", "was", "are"}
    words = text.strip().split()
    return " ".join(
        w.capitalize() if i == 0 or w.lower() not in stop_words else w.lower()
        for i, w in enumerate(words)
    )


def simulate_email(to: str, resume_id: str, password: str, pdf_bytes: bytes = None):
    print(f"[EMAIL SIM] To: {to}")
    print(f"[EMAIL SIM] Subject: Your Resume {resume_id}")
    print(f"[EMAIL SIM] Body: Resume attached. Password: {password}")
    if pdf_bytes:
        print(f"[EMAIL SIM] Attachment: {resume_id}.pdf ({len(pdf_bytes)} bytes)")


def whatsapp_link(resume_id: str, password: str, base_url: str) -> str:
    link = f"{base_url}/resume/{resume_id}/download"
    text = f"Here is my resume. Link: {link} | Password: {password}"
    return f"https://wa.me/?text={text.replace(' ', '%20').replace('|', '%7C').replace(':', '%3A')}"


def format_display_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%-d %B %Y – %-I:%M %p")
    except Exception:
        return iso
