import email
import imaplib
import smtplib
import time
import uuid
from email.mime.text import MIMEText
from typing import Optional

from agent.config import CONFIG
from agent.logger import LOGGER


class ApprovalGate:
    """Human-in-the-loop gate for any real-world action taken under the
    operator's identity. Sends an email describing the proposed action and
    polls the inbox for a reply containing APPROVE/REJECT + the token.

    Fails closed: if SMTP/IMAP aren't configured, requests silently can't be
    sent and replies can never be found, so gated actions never fire."""

    ACTION_DESCRIPTIONS = {
        "service_arbitrage": "post an offer/reply under your identity on a real listing",
        "micro_saas": "deploy a real, live product page and create a real payable Stripe product",
        "content_farm": "publish a real, live article under your identity",
    }

    def send_request(self, opportunity: dict, strategy: str = "service_arbitrage") -> Optional[dict]:
        token = uuid.uuid4().hex[:8]
        action = self.ACTION_DESCRIPTIONS.get(strategy, "take a real-world action under your identity")
        subject = f"[Survival Agent] Approve: {strategy} ({token})"
        body = (
            f"The agent wants to {action}. It will NOT act until you reply.\n\n"
            f"Strategy: {strategy}\n"
            f"Niche: {opportunity.get('niche')}\n"
            f"Problem: {opportunity.get('problem')}\n"
            f"Proposed action: {opportunity.get('solution')}\n"
            f"Price point: ${opportunity.get('price_point')}\n"
            f"Source: {opportunity.get('source_url') or 'n/a (agent-originated, not sourced from a listing)'}\n\n"
            f"Reply to this email with the words APPROVE {token} to let it proceed, "
            f"or REJECT {token} to skip it.\n"
            f"No reply within {CONFIG.APPROVAL_TIMEOUT_HOURS}h is treated as a rejection."
        )
        if not self._send(subject, body):
            return None
        return {
            "token": token,
            "opportunity": opportunity,
            "strategy": strategy,
            "subject": subject,
            "sent_at": time.time(),
        }

    def _send(self, subject: str, body: str) -> bool:
        if not (CONFIG.EMAIL_SMTP_HOST and CONFIG.EMAIL_SMTP_USER and CONFIG.APPROVAL_EMAIL_TO):
            LOGGER.warning("Approval email not configured (EMAIL_SMTP_HOST/USER/APPROVAL_EMAIL_TO); skipping send")
            return False

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = CONFIG.EMAIL_FROM or CONFIG.EMAIL_SMTP_USER
        msg["To"] = CONFIG.APPROVAL_EMAIL_TO

        try:
            with smtplib.SMTP(CONFIG.EMAIL_SMTP_HOST, CONFIG.EMAIL_SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(CONFIG.EMAIL_SMTP_USER, CONFIG.EMAIL_SMTP_PASSWORD)
                server.sendmail(msg["From"], [CONFIG.APPROVAL_EMAIL_TO], msg.as_string())
            LOGGER.info(f"Approval email sent: {subject}")
            return True
        except (smtplib.SMTPException, OSError) as e:
            LOGGER.error(f"Approval email send failed: {e}")
            return False

    def check_reply(self, token: str) -> Optional[bool]:
        """Returns True (approved), False (explicitly rejected), or None (no
        matching reply yet — caller decides what to do, e.g. keep waiting)."""
        if not (CONFIG.EMAIL_IMAP_HOST and CONFIG.EMAIL_IMAP_USER):
            return None

        try:
            with imaplib.IMAP4_SSL(CONFIG.EMAIL_IMAP_HOST, CONFIG.EMAIL_IMAP_PORT) as imap:
                imap.login(CONFIG.EMAIL_IMAP_USER, CONFIG.EMAIL_IMAP_PASSWORD)
                imap.select("INBOX")
                status, data = imap.search(None, "UNSEEN")
                if status != "OK" or not data or not data[0]:
                    return None

                for num in data[0].split():
                    status, msg_data = imap.fetch(num, "(RFC822)")
                    if status != "OK" or not msg_data or not msg_data[0]:
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    body = self._extract_body(msg)
                    haystack = f"{msg.get('Subject', '')}\n{body}"
                    if token not in haystack:
                        continue
                    upper = haystack.upper()
                    if "APPROVE" in upper:
                        return True
                    if "REJECT" in upper:
                        return False
            return None
        except (imaplib.IMAP4.error, OSError) as e:
            LOGGER.warning(f"Approval inbox check failed: {e}")
            return None

    @staticmethod
    def _extract_body(msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    return payload.decode(errors="ignore") if payload else ""
            return ""
        payload = msg.get_payload(decode=True)
        return payload.decode(errors="ignore") if payload else ""


APPROVAL = ApprovalGate()
