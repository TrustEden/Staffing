"""Utility functions for generating unique display IDs for companies."""

from sqlalchemy.orm import Session
from backend.app.utils.constants import CompanyType


def generate_company_display_id(db: Session, company_type: CompanyType) -> str:
    """
    Generate a unique display ID for a company.

    Format:
    - AGY-XXXXX for agencies
    - FAC-XXXXX for facilities

    Where XXXXX is a 5-digit sequential number (00001, 00002, etc.).

    Args:
        db: Database session for checking uniqueness
        company_type: The type of company (agency or facility)

    Returns:
        A unique display ID string
    """
    from backend.app.models import Company

    prefix = "AGY" if company_type == CompanyType.AGENCY else "FAC"

    # Find the highest existing ID for this company type
    existing_ids = db.query(Company.display_id).filter(
        Company.type == company_type,
        Company.display_id.like(f"{prefix}-%")
    ).all()

    # Extract numbers from existing IDs and find the max
    max_number = 0
    for (display_id,) in existing_ids:
        try:
            # Extract the number part after the prefix and hyphen
            number_part = display_id.split("-")[1]
            number = int(number_part)
            max_number = max(max_number, number)
        except (IndexError, ValueError):
            # Skip malformed IDs
            continue

    # Generate the next sequential number
    next_number = max_number + 1
    display_id = f"{prefix}-{next_number:05d}"

    return display_id
