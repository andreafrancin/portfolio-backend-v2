import base64
import json
import logging
from email.mime.image import MIMEImage
from pathlib import Path
import urllib.error
import urllib.request

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

RESEND_URL = "https://api.resend.com/emails"

# The logo travels inside each email (referenced as cid:...), so it shows whether or not the website is up.
HEADER_IMAGE_PATH = Path(__file__).resolve().parent / "email_assets" / "header.png"
HEADER_CONTENT_ID = "andrea-francin-header"

logger = logging.getLogger(__name__)


class ContactMailError(Exception):
    pass


def _header_image() -> bytes | None:
    try:
        return HEADER_IMAGE_PATH.read_bytes()
    except OSError:
        return None


def header_image_data_uri() -> str:
    """The logo as a data URI, for previews in the browser (email clients get it as an attachment)."""
    image = _header_image()
    return f"data:image/png;base64,{base64.b64encode(image).decode()}" if image else ""


def send_mail(to: str, subject: str, text: str, reply_to: str, html: str | None = None) -> None:
    """Send one email through Resend when it is configured, or Django's email backend otherwise."""
    image = _header_image() if html and f"cid:{HEADER_CONTENT_ID}" in html else None
    if settings.RESEND_API_KEY:
        _send_with_resend(to, subject, text, reply_to, html, image)
        return
    try:
        message = EmailMultiAlternatives(
            subject=subject,
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to],
            reply_to=[reply_to],
        )
        if html:
            message.attach_alternative(html, "text/html")
        if image:
            message.mixed_subtype = "related"
            inline = MIMEImage(image, "png")
            inline.add_header("Content-ID", f"<{HEADER_CONTENT_ID}>")
            inline.add_header("Content-Disposition", "inline", filename="andrea-francin.png")
            message.attach(inline)
        message.send(fail_silently=False)
    except Exception as exc:
        raise ContactMailError(str(exc)) from exc


def confirmation_enabled() -> bool:
    """Resend's test sender only reaches the account owner, so visitors are only written to from a real domain."""
    if not settings.CONTACT_SEND_CONFIRMATION:
        return False
    sender = settings.CONTACT_FROM_EMAIL if settings.RESEND_API_KEY else settings.DEFAULT_FROM_EMAIL
    return "@resend.dev" not in sender


def send_confirmation(to: str, subject: str, text: str, html: str) -> None:
    """The visitor's copy is a courtesy: if it fails, the message has still reached the owner."""
    try:
        send_mail(to, subject, text, reply_to=settings.CONTACT_REPLY_TO, html=html)
    except ContactMailError as exc:
        logger.warning("Contact confirmation not sent: %s", exc)


def _send_with_resend(
    to: str, subject: str, text: str, reply_to: str, html: str | None, image: bytes | None
) -> None:
    body = {
        "from": settings.CONTACT_FROM_EMAIL,
        "to": [to],
        "reply_to": reply_to,
        "subject": subject,
        "text": text,
    }
    if html:
        body["html"] = html
    if image:
        body["attachments"] = [{
            "content": base64.b64encode(image).decode(),
            "filename": "andrea-francin.png",
            "content_id": HEADER_CONTENT_ID,
        }]
    request = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "portfolio-contact-form",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            if response.status >= 300:
                raise ContactMailError(f"Resend answered {response.status}")
    except urllib.error.HTTPError as exc:
        raise ContactMailError(f"Resend answered {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ContactMailError(str(exc.reason)) from exc
