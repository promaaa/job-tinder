import logging
import os
import mimetypes
import aiosmtplib
from email.message import EmailMessage
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class EmailSender:
    """Handles sending real emails via SMTP."""
    
    def __init__(self):
        self.host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.user = os.getenv("SMTP_USER")
        self.password = os.getenv("SMTP_PASSWORD")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
    async def send(self, message: Dict[str, Any], to_email: str, attachments: Optional[List[str]] = None) -> bool:
        """
        Send a real email message via SMTP with optional attachments.
        
        Args:
            message: Dict with 'subject' and 'body'
            to_email: Recipient email
            attachments: List of file paths to attach
        """
        if not self.user or not self.password:
            logger.warning("SMTP credentials not set (SMTP_USER/SMTP_PASSWORD). simulating send.")
            # Simulation fallback
            logger.info(f"🚀 [SIMULATION] SENDING EMAIL TO: {to_email}")
            if attachments:
                logger.info(f"📎 [SIMULATION] WITH ATTACHMENTS: {attachments}")
            return True

        msg = EmailMessage()
        msg["From"] = self.user
        msg["To"] = to_email
        msg["Subject"] = message.get("subject", "No Subject")
        msg.set_content(message.get("body", ""))

        # Process attachments
        if attachments:
            for file_path in attachments:
                path = Path(file_path)
                if not path.exists():
                    logger.warning(f"Attachment not found: {path}")
                    continue
                
                # Guess mime type or default
                ctype, encoding = mimetypes.guess_type(path)
                if ctype is None or encoding is not None:
                    # No guess could be made, or the file is encoded (compressed), so
                    # use a generic bag-of-bits type.
                    ctype = "application/octet-stream"
                
                maintype, subtype = ctype.split("/", 1)
                
                try:
                    file_data = path.read_bytes()
                    msg.add_attachment(
                        file_data,
                        maintype=maintype,
                        subtype=subtype,
                        filename=path.name
                    )
                    logger.info(f"Attached file: {path.name}")
                except Exception as e:
                    logger.error(f"Failed to attach {path}: {e}")

        try:
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=self.use_tls
            )
            logger.info(f"✅ Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            return False
