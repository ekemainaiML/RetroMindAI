import logging
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import aiosmtplib
import jinja2

from core.config import settings

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_JINJA_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


@dataclass
class EmailMessage:
    to: str
    subject: str
    template_name: str
    context: dict = field(default_factory=dict)
    cc: list[str] | None = None
    bcc: list[str] | None = None
    reply_to: str | None = None


class EmailSender:
    def __init__(self) -> None:
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password
        self._use_tls = settings.smtp_use_tls
        self._from_addr = settings.email_from
        self._from_name = settings.email_from_name
        self._enabled = settings.email_enabled

    async def send(self, message: EmailMessage) -> bool:
        if not self._enabled:
            logger.info("Email disabled; skipping send to %s", message.to)
            return False
        try:
            html = _JINJA_ENV.get_template(message.template_name).render(**message.context)
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self._from_name} <{self._from_addr}>"
            msg["To"] = message.to
            msg["Subject"] = message.subject
            if message.reply_to:
                msg["Reply-To"] = message.reply_to
            msg.attach(MIMEText(html, "html"))
            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._user or None,
                password=self._password or None,
                use_tls=self._use_tls,
            )
            logger.info("Email sent to %s — %s", message.to, message.subject)
            return True
        except Exception:
            logger.exception("Failed to send email to %s — %s", message.to, message.subject)
            return False

    async def send_assessment_complete(self, to: str, workshop_name: str, job_id: str, report_url: str) -> bool:
        return await self.send(EmailMessage(
            to=to,
            subject=f"Assessment Complete — {workshop_name}",
            template_name="assessment_complete.html",
            context={
                "workshop_name": workshop_name,
                "job_id": job_id,
                "report_url": report_url,
                "brand_name": self._from_name,
            },
        ))

    async def send_assessment_failed(self, to: str, workshop_name: str, job_id: str, error: str) -> bool:
        return await self.send(EmailMessage(
            to=to,
            subject=f"Assessment Failed — {workshop_name}",
            template_name="assessment_failed.html",
            context={
                "workshop_name": workshop_name,
                "job_id": job_id,
                "error": error,
                "brand_name": self._from_name,
            },
        ))

    async def send_key_expiring(self, to: str, workshop_name: str, days_left: int) -> bool:
        return await self.send(EmailMessage(
            to=to,
            subject=f"API Key Expiring Soon — {workshop_name}",
            template_name="key_expiring.html",
            context={
                "workshop_name": workshop_name,
                "days_left": days_left,
                "brand_name": self._from_name,
            },
        ))

    async def send_team_invite(self, to: str, invited_by: str, workshop_name: str, invite_url: str) -> bool:
        return await self.send(EmailMessage(
            to=to,
            subject=f"You've been invited to {workshop_name}",
            template_name="team_invite.html",
            context={
                "invited_by": invited_by,
                "workshop_name": workshop_name,
                "invite_url": invite_url,
                "brand_name": self._from_name,
            },
        ))

    async def send_portal_invite(self, to: str, workshop_name: str, portal_url: str, expires_hours: int) -> bool:
        return await self.send(EmailMessage(
            to=to,
            subject=f"Assessment Report Ready — {workshop_name}",
            template_name="portal_invite.html",
            context={
                "workshop_name": workshop_name,
                "portal_url": portal_url,
                "expires_hours": expires_hours,
                "brand_name": self._from_name,
            },
        ))

    async def send_payment_receipt(self, to: str, workshop_name: str, amount: str, plan_name: str) -> bool:
        return await self.send(EmailMessage(
            to=to,
            subject=f"Payment Receipt — {plan_name}",
            template_name="payment_receipt.html",
            context={
                "workshop_name": workshop_name,
                "amount": amount,
                "plan_name": plan_name,
                "brand_name": self._from_name,
            },
        ))

    async def send_daily_digest(self, to: str, workshop_name: str, assessments_count: int, failed_count: int) -> bool:
        return await self.send(EmailMessage(
            to=to,
            subject=f"Daily Digest — {workshop_name}",
            template_name="daily_digest.html",
            context={
                "workshop_name": workshop_name,
                "assessments_count": assessments_count,
                "failed_count": failed_count,
                "brand_name": self._from_name,
            },
        ))


_sender: EmailSender | None = None


def get_email_sender() -> EmailSender:
    global _sender
    if _sender is None:
        _sender = EmailSender()
    return _sender
