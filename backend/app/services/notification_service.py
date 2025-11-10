from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app import models
from backend.app.services.notification_sender import get_notification_sender

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, session: Session):
        self.session = session
        self.notification_sender = get_notification_sender()

    def create_notification(self, recipient_id: UUID, type_: str, content: str) -> models.Notification:
        # Create in-app notification
        notification = models.Notification(
            recipient_id=recipient_id,
            type=type_,
            content=content,
            read=False,
        )
        self.session.add(notification)
        self.session.commit()
        self.session.refresh(notification)

        # Send external notifications (email/SMS) if user has contact info
        self._send_external_notifications(recipient_id, type_, content)

        return notification

    def _send_external_notifications(self, recipient_id: UUID, type_: str, content: str) -> None:
        """Send external email and SMS notifications based on notification type."""
        # Get the recipient user
        recipient = self.session.get(models.User, recipient_id)
        if not recipient:
            logger.warning(f"Recipient user not found: {recipient_id}")
            return

        # Map notification types to email templates and context
        email_config = self._get_email_config(type_, content, recipient)
        sms_message = self._get_sms_message(type_, content)

        # Send email if user has email address
        if recipient.email and email_config:
            try:
                self.notification_sender.send_email(
                    to=recipient.email,
                    subject=email_config["subject"],
                    template_name=email_config["template"],
                    context=email_config["context"]
                )
            except Exception as e:
                logger.error(f"Failed to send email notification to {recipient.email}: {e}")

        # Send SMS if user has phone number
        if recipient.phone and sms_message:
            try:
                self.notification_sender.send_sms(
                    to=recipient.phone,
                    message=sms_message
                )
            except Exception as e:
                logger.error(f"Failed to send SMS notification to {recipient.phone}: {e}")

    def _get_email_config(self, type_: str, content: str, recipient: models.User) -> dict | None:
        """Get email template and context based on notification type."""
        # Parse the content to extract shift details
        # Content format examples:
        # "Shift on 2024-01-15 was claimed by John Doe."
        # "Your claim for the shift on 2024-01-15 has been approved."
        # "Shift on 2024-01-15 was cancelled."

        if type_ == "shift_claimed":
            # Extract shift details from content
            # Format: "Shift on {date} was claimed by {name}."
            # or "Your staff member {name} claimed a shift on {date}."
            shift_info = self._extract_shift_info(content)
            claimer_name = self._extract_claimer_name(content)

            return {
                "subject": "Shift Claimed - Action Required",
                "template": "shift_claimed.html",
                "context": {
                    "shift_title": shift_info.get("title", "Healthcare Shift"),
                    "shift_date": shift_info.get("date", "Unknown"),
                    "claimer_name": claimer_name or "Unknown"
                }
            }

        elif type_ == "shift_approved":
            # Format: "Your claim for the shift on {date} has been approved."
            shift_info = self._extract_shift_info(content)
            facility_name = self._get_facility_name_from_recipient(recipient)

            return {
                "subject": "Shift Approved - Congratulations!",
                "template": "claim_approved.html",
                "context": {
                    "shift_title": shift_info.get("title", "Healthcare Shift"),
                    "shift_date": shift_info.get("date", "Unknown"),
                    "facility_name": facility_name or "Unknown Facility"
                }
            }

        elif type_ == "shift_denied":
            # Format: "Your claim for the shift on {date} was denied."
            # or "{reason}" or "Shift on {date} was assigned to another clinician."
            shift_info = self._extract_shift_info(content)
            reason = self._extract_denial_reason(content)

            return {
                "subject": "Shift Claim Update",
                "template": "claim_denied.html",
                "context": {
                    "shift_title": shift_info.get("title", "Healthcare Shift"),
                    "shift_date": shift_info.get("date", "Unknown"),
                    "reason": reason
                }
            }

        elif type_ == "shift_cancelled":
            # Format: "Shift on {date} was cancelled."
            shift_info = self._extract_shift_info(content)

            return {
                "subject": "Shift Cancelled - Important Notice",
                "template": "shift_cancelled.html",
                "context": {
                    "shift_title": shift_info.get("title", "Healthcare Shift"),
                    "shift_date": shift_info.get("date", "Unknown")
                }
            }

        return None

    def _get_sms_message(self, type_: str, content: str) -> str | None:
        """Get SMS message based on notification type."""
        # SMS messages should be concise (160 characters recommended)
        if type_ == "shift_claimed":
            return f"Healthcare Staffing Bridge: {content}"
        elif type_ == "shift_approved":
            return f"Healthcare Staffing Bridge: {content}"
        elif type_ == "shift_denied":
            return f"Healthcare Staffing Bridge: {content}"
        elif type_ == "shift_cancelled":
            return f"Healthcare Staffing Bridge: {content}"
        return None

    def _extract_shift_info(self, content: str) -> dict:
        """Extract shift date from notification content."""
        # Simple parsing - look for date pattern
        import re
        date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', content)
        date_str = date_match.group(1) if date_match else "Unknown"

        return {
            "title": "Healthcare Shift",
            "date": date_str
        }

    def _extract_claimer_name(self, content: str) -> str | None:
        """Extract claimer name from notification content."""
        # Format: "Shift on {date} was claimed by {name}."
        # or "Your staff member {name} claimed a shift on {date}."
        import re

        # Try pattern 1: "claimed by NAME"
        match = re.search(r'claimed by (.+?)\.', content)
        if match:
            return match.group(1)

        # Try pattern 2: "staff member NAME claimed"
        match = re.search(r'staff member (.+?) claimed', content)
        if match:
            return match.group(1)

        return None

    def _extract_denial_reason(self, content: str) -> str:
        """Extract denial reason from notification content."""
        # If content doesn't follow standard patterns, use it as the reason
        if "was denied" in content or "assigned to another" in content:
            return content
        return content

    def _get_facility_name_from_recipient(self, recipient: models.User) -> str | None:
        """Get facility name from the recipient's company or related shift."""
        if recipient.company:
            return recipient.company.name
        return None

    def mark_read(self, notification_id: UUID, *, read: bool = True) -> models.Notification:
        notification = self.session.get(models.Notification, notification_id)
        if not notification:
            raise ValueError("Notification not found")
        notification.read = read
        notification.read_at = datetime.now(timezone.utc) if read else None
        self.session.commit()
        self.session.refresh(notification)
        return notification

    def mark_all_read(self, recipient_id: UUID) -> int:
        notifications: Iterable[models.Notification] = (
            self.session.query(models.Notification)
            .filter(models.Notification.recipient_id == recipient_id, models.Notification.read.is_(False))
            .all()
        )
        count = 0
        for notification in notifications:
            notification.read = True
            notification.read_at = datetime.now(timezone.utc)
            count += 1
        self.session.commit()
        return count

    def list_notifications(self, recipient_id: UUID, *, unread_only: bool = False) -> list[models.Notification]:
        query = self.session.query(models.Notification).filter(
            models.Notification.recipient_id == recipient_id
        )
        if unread_only:
            query = query.filter(models.Notification.read.is_(False))
        return query.order_by(models.Notification.created_at.desc()).all()
