# Healthcare Staffing Bridge - Testing Infrastructure

## Overview

This document describes the comprehensive test suite for the Healthcare Staffing Bridge backend API, implemented as part of Track 5: Testing Infrastructure.

## Test Statistics

- **Total Test Count**: 108 tests
- **Test Framework**: pytest with async support
- **Coverage Tool**: pytest-cov
- **Test Database**: SQLite (in-memory for speed)

## Test Suite Structure

### 1. Authentication Tests (`test_auth.py`)
**Total: 19 tests**

#### Test Classes:
- **TestAuthToken** (5 tests)
  - Login with valid credentials
  - Login with invalid username
  - Login with invalid password
  - Login with inactive user account
  - Case-insensitive username login

- **TestAuthRefresh** (4 tests)
  - Successful token refresh
  - Refresh with access token (should fail)
  - Refresh with invalid token
  - Refresh for inactive user

- **TestAuthMe** (4 tests)
  - Get current user with valid token
  - Access without token
  - Access with invalid token
  - Access for different user roles

- **TestUserRegistration** (4 tests)
  - Successful user registration
  - Duplicate username prevention
  - Password length validation
  - Registration without company (platform admin)

- **TestPasswordHashing** (2 tests)
  - Password hash verification
  - Hash uniqueness (salting)

### 2. Shift Management Tests (`test_shifts.py`)
**Total: 25 tests**

#### Test Classes:
- **TestCreateShift** (5 tests)
  - Successful shift creation
  - Unauthorized user prevention
  - Tiered visibility with auto-release
  - Unauthenticated access prevention
  - Premium shift creation

- **TestListShifts** (4 tests)
  - List shifts as facility admin
  - Visibility filtering (internal vs agency)
  - Filter by date range
  - Filter by status

- **TestGetShift** (3 tests)
  - Get specific shift
  - Non-existent shift (404)
  - Forbidden visibility enforcement

- **TestUpdateShift** (2 tests)
  - Successful shift update
  - Unauthorized update prevention

- **TestCancelShift** (2 tests)
  - Successful shift cancellation
  - Cancel with pending claims (auto-deny)

- **TestShiftConflictDetection** (2 tests)
  - No conflict for different dates
  - Conflict detection for overlapping times

### 3. Claim Management Tests (`test_claims.py`)
**Total: 22 tests**

#### Test Classes:
- **TestClaimShift** (6 tests)
  - Successful shift claim
  - Duplicate claim prevention
  - Visibility-based access control
  - Cannot claim cancelled shift
  - Cannot claim approved shift
  - Shift status update on claim

- **TestListShiftClaims** (3 tests)
  - List claims as facility admin
  - Unauthorized access prevention
  - Include user names in response

- **TestApproveClaim** (4 tests)
  - Successful claim approval
  - Auto-deny other pending claims
  - Unauthorized approval prevention
  - Non-existent claim (404)

- **TestDenyClaim** (5 tests)
  - Successful claim denial
  - Shift status back to open
  - Maintain pending status with other claims
  - Unauthorized denial prevention
  - Optional denial reason

- **TestListMyClaims** (4 tests)
  - List own claims
  - Include shift details
  - Empty list for new user
  - Only show user's own claims

### 4. Notification Tests (`test_notifications.py`)
**Total: 22 tests**

#### Test Classes:
- **TestListNotifications** (4 tests)
  - List notifications for user
  - Filter unread only
  - Only show user's own notifications
  - Authentication requirement

- **TestMarkNotificationRead** (4 tests)
  - Mark as read
  - Mark as unread
  - Non-existent notification (404)
  - Cannot mark other user's notification

- **TestMarkAllRead** (2 tests)
  - Mark all notifications as read
  - Only affects current user

- **TestNotificationCreationOnEvents** (4 tests)
  - Notification on shift claim
  - Notification on claim approval
  - Notification on claim denial
  - Notification on shift cancellation

- **TestNotificationService** (4 tests)
  - Create notification via service
  - List notifications via service
  - Mark read via service
  - Mark all read via service

### 5. Admin Functionality Tests (`test_admin.py`)
**Total: 31 tests**

#### Test Classes:
- **TestListRelationships** (4 tests)
  - List as platform admin
  - Forbidden for facility admin
  - Forbidden for agency admin
  - Authentication requirement

- **TestCreateRelationship** (4 tests)
  - Successful creation
  - Duplicate prevention
  - Invalid facility ID
  - Forbidden for facility admin

- **TestUpdateRelationship** (4 tests)
  - Update status
  - Revoke relationship
  - Non-existent relationship (404)
  - Forbidden for facility admin

- **TestDeleteRelationship** (3 tests)
  - Successful deletion
  - Non-existent relationship (404)
  - Forbidden for facility admin

- **TestListPendingClaims** (4 tests)
  - List as platform admin
  - List as facility admin
  - Only pending status
  - Forbidden for agency admin

- **TestGetCompanyStats** (4 tests)
  - Get facility statistics
  - Get agency statistics
  - Non-existent company (404)
  - Forbidden for facility admin

- **TestLockCompany** (4 tests)
  - Lock company
  - Unlock company
  - Non-existent company (404)
  - Forbidden for facility admin

- **TestResetAdminPassword** (4 tests)
  - Reset facility admin password
  - Reset agency admin password
  - Non-existent company (404)
  - Forbidden for facility admin

## Test Fixtures

Located in `/home/user/Connected/backend/tests/conftest.py`:

### Database Fixtures
- `test_db()` - In-memory SQLite database (function scope)
- `client()` - FastAPI TestClient with dependency overrides

### Authentication Fixtures
- `auth_service()` - AuthService instance for testing
- `superadmin_token()` - Platform admin JWT token
- `facility_admin_token()` - Facility admin JWT token
- `agency_admin_token()` - Agency admin JWT token
- `agency_staff_token()` - Agency staff JWT token

### Data Fixtures
- `superadmin_user()` - Platform admin user (no company)
- `sample_facility()` - Test facility company
- `facility_admin_user()` - Facility admin user
- `sample_agency()` - Test agency company
- `agency_admin_user()` - Agency admin user
- `agency_staff_user()` - Agency staff member
- `sample_shift()` - Test shift
- `active_relationship()` - Active facility-agency relationship
- `sample_claim()` - Test claim

## Running Tests

### Run All Tests
```bash
cd backend
export PYTHONPATH=/home/user/Connected:$PYTHONPATH
python -m pytest tests/ -v
```

### Run Specific Test File
```bash
python -m pytest tests/test_auth.py -v
```

### Run Specific Test Class
```bash
python -m pytest tests/test_auth.py::TestAuthToken -v
```

### Run Specific Test
```bash
python -m pytest tests/test_auth.py::TestAuthToken::test_login_success -v
```

### Run with Coverage
```bash
python -m pytest tests/ --cov=backend/app --cov-report=term-missing --cov-report=html
```

### Using the Test Runner Script
```bash
./run_tests.sh
```

## Test Coverage Goals

The test suite aims for **>80% code coverage** across the following modules:

### Core Modules
- ✓ `backend/app/routes/auth_routes.py` - Authentication endpoints
- ✓ `backend/app/routes/shift_routes.py` - Shift management endpoints
- ✓ `backend/app/routes/claim_routes.py` - Claim management endpoints
- ✓ `backend/app/routes/notification_routes.py` - Notification endpoints
- ✓ `backend/app/routes/admin_routes.py` - Admin functionality endpoints

### Services
- ✓ `backend/app/services/auth_service.py` - Authentication service
- ✓ `backend/app/services/notification_service.py` - Notification service
- ✓ `backend/app/services/shift_conflict_checker.py` - Conflict detection

### Models & Schemas
- ✓ `backend/app/models.py` - Database models
- ✓ `backend/app/schemas.py` - Pydantic schemas

## Test Design Principles

1. **Independence**: Each test is independent and can run in isolation
2. **Fixtures**: Extensive use of fixtures for setup/teardown
3. **AAA Pattern**: Arrange-Act-Assert pattern for clarity
4. **Error Cases**: Tests cover both success and error scenarios
5. **Authorization**: Comprehensive authorization checks
6. **Realistic Data**: Uses realistic test data via fixtures
7. **Fast Execution**: In-memory SQLite for speed
8. **Type Safety**: Full type hints in test code

## Test Categories

Tests are organized to cover:

### Functional Testing
- ✓ User authentication and authorization
- ✓ Shift creation and management
- ✓ Claim lifecycle (create, approve, deny)
- ✓ Notification generation and delivery
- ✓ Admin operations

### Security Testing
- ✓ JWT token validation
- ✓ Role-based access control (RBAC)
- ✓ Password hashing
- ✓ Unauthorized access prevention
- ✓ Data isolation between users/companies

### Business Logic Testing
- ✓ Shift visibility rules (internal, agency, tiered)
- ✓ Shift conflict detection
- ✓ Duplicate claim prevention
- ✓ Auto-denial of competing claims
- ✓ Notification triggers

### Edge Cases
- ✓ Non-existent resources (404 errors)
- ✓ Duplicate operations (409 conflicts)
- ✓ Invalid inputs (422 validation errors)
- ✓ Inactive users
- ✓ Locked companies

## Dependencies

Test dependencies are defined in `/home/user/Connected/backend/requirements.txt`:

```
pytest>=7.4              # Test framework
pytest-asyncio>=0.21     # Async test support
httpx>=0.25              # HTTP client for TestClient
faker>=20.0              # Fake data generation
pytest-cov>=4.1          # Coverage reporting
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

- Fast execution (in-memory database)
- No external dependencies required
- Clear pass/fail status
- Coverage reporting
- Detailed error messages

## Future Enhancements

Potential additions to the test suite:

1. **Performance Tests**: Load testing with locust or pytest-benchmark
2. **Integration Tests**: End-to-end workflow tests
3. **API Contract Tests**: OpenAPI schema validation
4. **Mutation Testing**: Using mutmut for test quality
5. **Property-Based Tests**: Using hypothesis for edge cases
6. **Database Tests**: PostgreSQL-specific tests (transactions, constraints)

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Ensure PYTHONPATH is set correctly
   ```bash
   export PYTHONPATH=/home/user/Connected:$PYTHONPATH
   ```

2. **Import Errors**: Install all dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Errors**: Ensure SQLite support is available
   ```bash
   python -c "import sqlite3; print('SQLite OK')"
   ```

4. **Fixture Issues**: Run with verbose output
   ```bash
   pytest tests/ -vv --tb=long
   ```

## Summary

This comprehensive test suite provides:

- ✓ **108 tests** covering all major functionality
- ✓ **5 test modules** organized by feature
- ✓ **Authentication, Authorization, and Business Logic** coverage
- ✓ **Reusable fixtures** for efficient test setup
- ✓ **Error handling** and edge case testing
- ✓ **Fast execution** with in-memory database
- ✓ **CI/CD ready** with clear pass/fail status

The test infrastructure ensures high code quality, prevents regressions, and provides confidence in the Healthcare Staffing Bridge backend API.
