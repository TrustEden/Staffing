"""Script to create the superadmin user."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.services.auth_service import AuthService
from app.schemas import UserCreate
from app.utils.constants import UserRole

def create_superadmin():
    db = SessionLocal()
    auth_service = AuthService(db)

    try:
        # Import User model
        from app.models import User

        # Check if superadmin already exists
        existing = db.query(User).filter(User.username == "superadmin").first()
        if existing:
            print("Superadmin user already exists!")
            return

        # Create superadmin
        user_data = UserCreate(
            username="superadmin",
            email="superadmin@example.com",
            password="ChangeMe123!",
            name="Super Admin",
            role=UserRole.ADMIN,
            company_id=None
        )

        user = auth_service.create_user(user_data)
        print(f"✓ Created superadmin user: {user.username} ({user.email})")
        print(f"  Login with username: superadmin")
        print(f"  Password: ChangeMe123!")

    except Exception as e:
        print(f"Error creating superadmin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_superadmin()
