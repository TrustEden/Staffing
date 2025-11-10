"""External notification service for sending SMS and email notifications."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger(__name__)


class NotificationSender:
    """Service for sending external notifications via SMS (Twilio) and Email (SendGrid)."""

    def __init__(self):
        # SendGrid configuration
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.sendgrid_from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@healthcarebridge.com")

        # Twilio configuration
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from_number = os.getenv("TWILIO_FROM_NUMBER")

        # Initialize clients lazily
        self._sendgrid_client = None
        self._twilio_client = None

        # Setup Jinja2 for email templates
        template_dir = Path(__file__).parent.parent / "templates" / "emails"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=True
        )

        # Log configuration status
        if self.sendgrid_api_key:
            logger.info("SendGrid email notifications enabled")
        else:
            logger.info("SendGrid not configured - email notifications disabled")

        if self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number:
            logger.info("Twilio SMS notifications enabled")
        else:
            logger.info("Twilio not configured - SMS notifications disabled")

    @property
    def sendgrid_client(self):
        """Lazy initialization of SendGrid client."""
        if self._sendgrid_client is None and self.sendgrid_api_key:
            try:
                from sendgrid import SendGridAPIClient
                self._sendgrid_client = SendGridAPIClient(self.sendgrid_api_key)
            except ImportError:
                logger.error("SendGrid package not installed. Install with: pip install sendgrid")
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid client: {e}")
        return self._sendgrid_client

    @property
    def twilio_client(self):
        """Lazy initialization of Twilio client."""
        if self._twilio_client is None and all([self.twilio_account_sid, self.twilio_auth_token]):
            try:
                from twilio.rest import Client
                self._twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
            except ImportError:
                logger.error("Twilio package not installed. Install with: pip install twilio")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")
        return self._twilio_client

    def render_email_template(self, template_name: str, context: dict) -> str:
        """
        Render an email template with the given context.

        Args:
            template_name: Name of the template file (e.g., 'shift_claimed.html')
            context: Dictionary of variables to render in the template

        Returns:
            Rendered HTML string

        Raises:
            TemplateNotFound: If the template doesn't exist
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound:
            logger.error(f"Email template not found: {template_name}")
            raise
        except Exception as e:
            logger.error(f"Error rendering email template {template_name}: {e}")
            raise

    def send_email(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: dict
    ) -> bool:
        """
        Send an email using SendGrid with an HTML template.

        Args:
            to: Recipient email address
            subject: Email subject line
            template_name: Name of the email template to use
            context: Dictionary of variables for the template

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not to:
            logger.debug("No email address provided, skipping email notification")
            return False

        if not self.sendgrid_client:
            logger.debug("SendGrid not configured, skipping email notification")
            return False

        try:
            # Render the HTML template
            html_content = self.render_email_template(template_name, context)

            # Create the email message
            from sendgrid.helpers.mail import Mail

            message = Mail(
                from_email=self.sendgrid_from_email,
                to_emails=to,
                subject=subject,
                html_content=html_content
            )

            # Send the email
            response = self.sendgrid_client.send(message)

            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Email sent successfully to {to} with subject: {subject}")
                return True
            else:
                logger.error(f"Failed to send email to {to}. Status: {response.status_code}")
                return False

        except TemplateNotFound:
            logger.error(f"Email template not found: {template_name}")
            return False
        except Exception as e:
            logger.error(f"Error sending email to {to}: {e}")
            return False

    def send_sms(self, to: str, message: str) -> bool:
        """
        Send an SMS using Twilio.

        Args:
            to: Recipient phone number (E.164 format recommended, e.g., +1234567890)
            message: SMS message content (max 160 characters recommended)

        Returns:
            True if SMS was sent successfully, False otherwise
        """
        if not to:
            logger.debug("No phone number provided, skipping SMS notification")
            return False

        if not self.twilio_client or not self.twilio_from_number:
            logger.debug("Twilio not configured, skipping SMS notification")
            return False

        try:
            # Send the SMS
            sms = self.twilio_client.messages.create(
                body=message,
                from_=self.twilio_from_number,
                to=to
            )

            logger.info(f"SMS sent successfully to {to}. SID: {sms.sid}")
            return True

        except Exception as e:
            logger.error(f"Error sending SMS to {to}: {e}")
            return False


# Create a singleton instance
_notification_sender = None


def get_notification_sender() -> NotificationSender:
    """Get the singleton NotificationSender instance."""
    global _notification_sender
    if _notification_sender is None:
        _notification_sender = NotificationSender()
    return _notification_sender
