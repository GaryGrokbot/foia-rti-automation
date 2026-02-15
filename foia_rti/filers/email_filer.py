"""
Email filer — formats and sends FOIA/RTI requests via email.

Produces MIME-compliant messages with proper headers, optional
attachments, and delivery confirmation tracking.
"""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Optional

from foia_rti.generators.generator_base import GeneratedRequest


@dataclass
class EmailConfig:
    """SMTP configuration for sending request emails."""

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""
    from_address: str = ""
    from_name: str = "Open Paws FOIA"
    reply_to: str = ""
    bcc: str = ""


@dataclass
class EmailMessage:
    """A fully formed email ready to send."""

    to: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    from_address: str = ""
    from_name: str = ""
    reply_to: str = ""
    bcc: str = ""
    attachments: list[Path] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)

    def to_mime(self) -> MIMEMultipart:
        msg = MIMEMultipart("mixed")
        msg["To"] = self.to
        msg["From"] = (
            f"{self.from_name} <{self.from_address}>"
            if self.from_name
            else self.from_address
        )
        msg["Subject"] = self.subject
        if self.reply_to:
            msg["Reply-To"] = self.reply_to
        if self.bcc:
            msg["Bcc"] = self.bcc
        for key, val in self.headers.items():
            msg[key] = val

        # Prefer multipart/alternative for text + html
        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(self.body_text, "plain", "utf-8"))
        if self.body_html:
            alt.attach(MIMEText(self.body_html, "html", "utf-8"))
        msg.attach(alt)

        # Attachments
        for filepath in self.attachments:
            if filepath.exists():
                with open(filepath, "rb") as f:
                    part = MIMEApplication(f.read(), Name=filepath.name)
                part["Content-Disposition"] = f'attachment; filename="{filepath.name}"'
                msg.attach(part)

        return msg


class EmailFiler:
    """
    Format and send FOIA/RTI requests via email.

    Usage:
        config = EmailConfig(smtp_host="smtp.gmail.com", username="...", password="...")
        filer = EmailFiler(config)
        msg = filer.format_request(generated_request)
        filer.send(msg)
    """

    # Subject line templates per jurisdiction
    SUBJECT_TEMPLATES = {
        "US-Federal": "FOIA Request — {topic} — {agency}",
        "India": "RTI Application under Section 6(1) — {topic}",
        "UK": "Freedom of Information Request — {topic}",
        "EU": "Application for Access to Documents (Reg. 1049/2001) — {topic}",
    }

    def __init__(self, config: Optional[EmailConfig] = None) -> None:
        self.config = config or EmailConfig()

    def format_request(
        self,
        request: GeneratedRequest,
        attachments: Optional[list[Path]] = None,
    ) -> EmailMessage:
        """
        Convert a GeneratedRequest into an EmailMessage ready for sending.
        """
        to_address = request.metadata.get("agency_email", "")
        if not to_address:
            raise ValueError(
                f"No email address found for {request.agency}. "
                "Please provide the agency's FOIA email."
            )

        subject = self._build_subject(request)

        return EmailMessage(
            to=to_address,
            subject=subject,
            body_text=request.text,
            body_html=self._text_to_html(request.text),
            from_address=self.config.from_address,
            from_name=self.config.from_name,
            reply_to=self.config.reply_to or self.config.from_address,
            bcc=self.config.bcc,
            attachments=attachments or [],
            headers={
                "X-FOIA-Jurisdiction": request.jurisdiction,
                "X-FOIA-Agency": request.agency,
            },
        )

    def send(self, message: EmailMessage, dry_run: bool = False) -> dict[str, str]:
        """
        Send the email via SMTP.

        Returns a dict with 'status' and 'message_id' or 'error'.
        In dry_run mode, returns the formatted message without sending.
        """
        if dry_run:
            mime = message.to_mime()
            return {
                "status": "dry_run",
                "to": message.to,
                "subject": message.subject,
                "body_preview": message.body_text[:200],
                "mime_size": str(len(mime.as_string())),
            }

        if not self.config.username or not self.config.password:
            raise ValueError(
                "SMTP credentials not configured. Set EmailConfig.username and password."
            )

        mime = message.to_mime()

        try:
            if self.config.use_tls:
                context = ssl.create_default_context()
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(self.config.username, self.config.password)
                    recipients = [message.to]
                    if message.bcc:
                        recipients.append(message.bcc)
                    server.sendmail(
                        self.config.from_address,
                        recipients,
                        mime.as_string(),
                    )
            else:
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    server.login(self.config.username, self.config.password)
                    server.sendmail(
                        self.config.from_address,
                        [message.to],
                        mime.as_string(),
                    )

            return {"status": "sent", "to": message.to, "subject": message.subject}

        except smtplib.SMTPException as e:
            return {"status": "error", "error": str(e)}

    def format_for_portal(self, request: GeneratedRequest) -> dict[str, str]:
        """
        Format a request for manual copy-paste into a web portal.

        Returns a dict with 'subject', 'body', and 'agency_portal' fields.
        """
        return {
            "subject": self._build_subject(request),
            "body": request.text,
            "agency_portal": request.metadata.get("agency_portal", ""),
            "instructions": (
                f"1. Go to {request.metadata.get('agency_portal', 'the agency portal')}\n"
                f"2. Copy the subject line into the subject field\n"
                f"3. Paste the body text into the request description field\n"
                f"4. Attach any supporting documents\n"
                f"5. Submit and note the confirmation number"
            ),
        }

    def _build_subject(self, request: GeneratedRequest) -> str:
        jurisdiction = request.jurisdiction
        # Match prefix for state-level
        if jurisdiction.startswith("US-State"):
            jurisdiction = "US-Federal"

        template = self.SUBJECT_TEMPLATES.get(jurisdiction, "Public Records Request — {topic}")
        return template.format(
            topic=request.context.topic[:80],
            agency=request.agency[:60],
        )

    @staticmethod
    def _text_to_html(text: str) -> str:
        """Basic text-to-HTML conversion preserving paragraphs."""
        import html as html_mod
        escaped = html_mod.escape(text)
        paragraphs = escaped.split("\n\n")
        html_parts = []
        for para in paragraphs:
            lines = para.split("\n")
            html_parts.append("<p>" + "<br>\n".join(lines) + "</p>")
        body = "\n".join(html_parts)
        return (
            "<!DOCTYPE html><html><head>"
            '<meta charset="utf-8">'
            "<style>body{font-family:Georgia,serif;font-size:12pt;"
            "line-height:1.6;max-width:700px;margin:40px auto;}</style>"
            f"</head><body>{body}</body></html>"
        )
