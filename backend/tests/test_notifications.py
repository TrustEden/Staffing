"""Tests for notification endpoints."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.services.notification_service import NotificationService
from backend.app.utils.constants import NotificationType


class TestListNotifications:
    """Tests for GET /api/notifications/."""

    def test_list_notifications_success(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        facility_admin_user: models.User,
    ):
        """Test listing notifications for current user."""
        # Create some notifications
        notif1 = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Your shift was claimed",
            read=False,
        )
        notif2 = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_APPROVED.value,
            content="Shift approved",
            read=True,
        )
        test_db.add_all([notif1, notif2])
        test_db.commit()

        response = client.get(
            "/api/notifications/",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        notification_ids = [n["id"] for n in data]
        assert str(notif1.id) in notification_ids
        assert str(notif2.id) in notification_ids

    def test_list_notifications_unread_only(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        facility_admin_user: models.User,
    ):
        """Test filtering notifications to show only unread."""
        # Create read and unread notifications
        read_notif = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Read notification",
            read=True,
            read_at=datetime.now(timezone.utc),
        )
        unread_notif = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_APPROVED.value,
            content="Unread notification",
            read=False,
        )
        test_db.add_all([read_notif, unread_notif])
        test_db.commit()

        response = client.get(
            "/api/notifications/?unread_only=true",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        notification_ids = [n["id"] for n in data]
        assert str(unread_notif.id) in notification_ids
        assert str(read_notif.id) not in notification_ids

    def test_list_notifications_only_shows_own(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        facility_admin_user: models.User,
        agency_admin_user: models.User,
    ):
        """Test that user only sees their own notifications."""
        # Create notification for facility admin
        own_notif = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Your notification",
            read=False,
        )
        # Create notification for agency admin
        other_notif = models.Notification(
            recipient_id=agency_admin_user.id,
            type=NotificationType.SHIFT_APPROVED.value,
            content="Other user notification",
            read=False,
        )
        test_db.add_all([own_notif, other_notif])
        test_db.commit()

        response = client.get(
            "/api/notifications/",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        notification_ids = [n["id"] for n in data]
        assert str(own_notif.id) in notification_ids
        assert str(other_notif.id) not in notification_ids

    def test_list_notifications_no_auth(self, client: TestClient):
        """Test that listing notifications requires authentication."""
        response = client.get("/api/notifications/")
        assert response.status_code == 401


class TestMarkNotificationRead:
    """Tests for POST /api/notifications/{notification_id}/read."""

    def test_mark_notification_read_success(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        facility_admin_user: models.User,
    ):
        """Test marking a notification as read."""
        notification = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Test notification",
            read=False,
        )
        test_db.add(notification)
        test_db.commit()

        response = client.post(
            f"/api/notifications/{notification.id}/read",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"read": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["read"] is True
        assert data["read_at"] is not None

    def test_mark_notification_unread(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        facility_admin_user: models.User,
    ):
        """Test marking a notification as unread."""
        notification = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Test notification",
            read=True,
            read_at=datetime.now(timezone.utc),
        )
        test_db.add(notification)
        test_db.commit()

        response = client.post(
            f"/api/notifications/{notification.id}/read",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"read": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["read"] is False
        assert data["read_at"] is None

    def test_mark_notification_read_not_found(
        self, client: TestClient, facility_admin_token: str
    ):
        """Test marking non-existent notification returns 404."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.post(
            f"/api/notifications/{fake_id}/read",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"read": True},
        )
        assert response.status_code == 404

    def test_mark_notification_read_wrong_user(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        agency_admin_user: models.User,
    ):
        """Test that user cannot mark another user's notification."""
        # Create notification for agency admin
        notification = models.Notification(
            recipient_id=agency_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Agency notification",
            read=False,
        )
        test_db.add(notification)
        test_db.commit()

        # Try to mark it as read using facility admin token
        response = client.post(
            f"/api/notifications/{notification.id}/read",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"read": True},
        )
        assert response.status_code == 404


class TestMarkAllRead:
    """Tests for POST /api/notifications/mark-all-read."""

    def test_mark_all_read_success(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        facility_admin_user: models.User,
    ):
        """Test marking all notifications as read."""
        # Create multiple unread notifications
        notif1 = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Notification 1",
            read=False,
        )
        notif2 = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_APPROVED.value,
            content="Notification 2",
            read=False,
        )
        test_db.add_all([notif1, notif2])
        test_db.commit()

        response = client.post(
            "/api/notifications/mark-all-read",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 204

        # Verify all notifications are marked as read
        test_db.refresh(notif1)
        test_db.refresh(notif2)
        assert notif1.read is True
        assert notif2.read is True

    def test_mark_all_read_only_affects_own_notifications(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        facility_admin_user: models.User,
        agency_admin_user: models.User,
    ):
        """Test mark all read only affects current user's notifications."""
        # Create notification for facility admin
        own_notif = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Own notification",
            read=False,
        )
        # Create notification for agency admin
        other_notif = models.Notification(
            recipient_id=agency_admin_user.id,
            type=NotificationType.SHIFT_APPROVED.value,
            content="Other notification",
            read=False,
        )
        test_db.add_all([own_notif, other_notif])
        test_db.commit()

        response = client.post(
            "/api/notifications/mark-all-read",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 204

        # Verify only own notification is marked as read
        test_db.refresh(own_notif)
        test_db.refresh(other_notif)
        assert own_notif.read is True
        assert other_notif.read is False


class TestNotificationCreationOnEvents:
    """Tests for automatic notification creation on claim events."""

    def test_notification_created_on_claim(
        self,
        client: TestClient,
        test_db: Session,
        agency_staff_token: str,
        sample_shift: models.Shift,
        facility_admin_user: models.User,
        active_relationship: models.Relationship,
    ):
        """Test that notification is created when shift is claimed."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims",
            headers={"Authorization": f"Bearer {agency_staff_token}"},
        )
        assert response.status_code == 201

        # Check that facility admin received notification
        notifications = (
            test_db.query(models.Notification)
            .filter(models.Notification.recipient_id == facility_admin_user.id)
            .all()
        )
        assert len(notifications) >= 1
        claim_notifications = [
            n for n in notifications if n.type == NotificationType.SHIFT_CLAIMED.value
        ]
        assert len(claim_notifications) >= 1

    def test_notification_created_on_approval(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
        agency_staff_user: models.User,
    ):
        """Test that notification is created when claim is approved."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{sample_claim.id}/approve",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200

        # Check that agency staff received approval notification
        notifications = (
            test_db.query(models.Notification)
            .filter(models.Notification.recipient_id == agency_staff_user.id)
            .all()
        )
        assert len(notifications) >= 1
        approval_notifications = [
            n for n in notifications if n.type == NotificationType.SHIFT_APPROVED.value
        ]
        assert len(approval_notifications) >= 1

    def test_notification_created_on_denial(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
        agency_staff_user: models.User,
    ):
        """Test that notification is created when claim is denied."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/claims/{sample_claim.id}/deny",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
            json={"reason": "Insufficient experience"},
        )
        assert response.status_code == 200

        # Check that agency staff received denial notification
        notifications = (
            test_db.query(models.Notification)
            .filter(models.Notification.recipient_id == agency_staff_user.id)
            .all()
        )
        assert len(notifications) >= 1
        denial_notifications = [
            n for n in notifications if n.type == NotificationType.SHIFT_DENIED.value
        ]
        assert len(denial_notifications) >= 1

    def test_notification_created_on_shift_cancellation(
        self,
        client: TestClient,
        test_db: Session,
        facility_admin_token: str,
        sample_shift: models.Shift,
        sample_claim: models.Claim,
        agency_staff_user: models.User,
    ):
        """Test that notification is created when shift is cancelled."""
        response = client.post(
            f"/api/shifts/{sample_shift.id}/cancel",
            headers={"Authorization": f"Bearer {facility_admin_token}"},
        )
        assert response.status_code == 200

        # Check that agency staff received cancellation notification
        notifications = (
            test_db.query(models.Notification)
            .filter(models.Notification.recipient_id == agency_staff_user.id)
            .all()
        )
        assert len(notifications) >= 1
        cancel_notifications = [
            n
            for n in notifications
            if n.type == NotificationType.SHIFT_CANCELLED.value
        ]
        assert len(cancel_notifications) >= 1


class TestNotificationService:
    """Tests for NotificationService helper methods."""

    def test_create_notification(
        self, test_db: Session, facility_admin_user: models.User
    ):
        """Test creating notification via service."""
        service = NotificationService(test_db)
        notification = service.create_notification(
            facility_admin_user.id,
            NotificationType.SHIFT_CLAIMED.value,
            "Test notification content",
        )
        assert notification.recipient_id == facility_admin_user.id
        assert notification.type == NotificationType.SHIFT_CLAIMED.value
        assert notification.content == "Test notification content"
        assert notification.read is False

    def test_list_notifications_service(
        self, test_db: Session, facility_admin_user: models.User
    ):
        """Test listing notifications via service."""
        service = NotificationService(test_db)

        # Create notifications
        notif1 = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Notification 1",
            read=False,
        )
        notif2 = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_APPROVED.value,
            content="Notification 2",
            read=True,
        )
        test_db.add_all([notif1, notif2])
        test_db.commit()

        # List all
        all_notifs = service.list_notifications(facility_admin_user.id)
        assert len(all_notifs) >= 2

        # List unread only
        unread_notifs = service.list_notifications(
            facility_admin_user.id, unread_only=True
        )
        unread_ids = [n.id for n in unread_notifs]
        assert notif1.id in unread_ids
        assert notif2.id not in unread_ids

    def test_mark_read_service(
        self, test_db: Session, facility_admin_user: models.User
    ):
        """Test marking notification as read via service."""
        service = NotificationService(test_db)
        notification = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Test",
            read=False,
        )
        test_db.add(notification)
        test_db.commit()

        updated = service.mark_read(notification.id, read=True)
        assert updated.read is True
        assert updated.read_at is not None

    def test_mark_all_read_service(
        self, test_db: Session, facility_admin_user: models.User
    ):
        """Test marking all notifications as read via service."""
        service = NotificationService(test_db)

        # Create multiple notifications
        notif1 = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_CLAIMED.value,
            content="Notification 1",
            read=False,
        )
        notif2 = models.Notification(
            recipient_id=facility_admin_user.id,
            type=NotificationType.SHIFT_APPROVED.value,
            content="Notification 2",
            read=False,
        )
        test_db.add_all([notif1, notif2])
        test_db.commit()

        service.mark_all_read(facility_admin_user.id)

        test_db.refresh(notif1)
        test_db.refresh(notif2)
        assert notif1.read is True
        assert notif2.read is True
