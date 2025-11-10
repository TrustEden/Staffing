# Test Suite Quick Reference

## Quick Start

```bash
# Run all tests
cd /home/user/Connected/backend
export PYTHONPATH=/home/user/Connected:$PYTHONPATH
python -m pytest tests/ -v

# Or use the test runner script
./run_tests.sh
```

## Test Files

- `conftest.py` - Test fixtures and configuration
- `test_auth.py` - Authentication tests (19 tests)
- `test_shifts.py` - Shift management tests (25 tests)
- `test_claims.py` - Claim management tests (22 tests)
- `test_notifications.py` - Notification tests (22 tests)
- `test_admin.py` - Admin functionality tests (31 tests)

**Total: 108 tests**

## Common Commands

```bash
# Run specific test file
pytest tests/test_auth.py -v

# Run specific test class
pytest tests/test_auth.py::TestAuthToken -v

# Run specific test
pytest tests/test_auth.py::TestAuthToken::test_login_success -v

# Run with coverage
pytest tests/ --cov=backend/app --cov-report=term-missing

# Run with detailed output
pytest tests/ -vv --tb=long

# Stop on first failure
pytest tests/ -x

# Run tests matching pattern
pytest tests/ -k "test_login" -v
```

## Test Structure

Each test file follows this pattern:

```python
class TestFeatureName:
    """Tests for specific feature."""

    def test_success_case(self, client, token, fixture):
        """Test successful operation."""
        response = client.post(
            "/api/endpoint",
            headers={"Authorization": f"Bearer {token}"},
            json={"data": "value"}
        )
        assert response.status_code == 200

    def test_error_case(self, client):
        """Test error handling."""
        response = client.post("/api/endpoint")
        assert response.status_code == 401
```

## Available Fixtures

### Authentication
- `superadmin_token` - Platform admin token
- `facility_admin_token` - Facility admin token
- `agency_admin_token` - Agency admin token
- `agency_staff_token` - Agency staff token

### Data
- `sample_facility` - Test facility
- `sample_agency` - Test agency
- `sample_shift` - Test shift
- `sample_claim` - Test claim
- `active_relationship` - Active facility-agency relationship

### Infrastructure
- `test_db` - In-memory test database
- `client` - FastAPI TestClient
- `auth_service` - Authentication service

## Writing New Tests

1. Add test to appropriate file
2. Use descriptive test names
3. Follow AAA pattern (Arrange, Act, Assert)
4. Use fixtures for setup
5. Test both success and error cases
6. Include docstrings

Example:

```python
def test_new_feature_success(
    self,
    client: TestClient,
    facility_admin_token: str,
    sample_facility: models.Company,
):
    """Test that new feature works correctly."""
    # Arrange
    data = {"field": "value"}

    # Act
    response = client.post(
        "/api/new-endpoint",
        headers={"Authorization": f"Bearer {facility_admin_token}"},
        json=data,
    )

    # Assert
    assert response.status_code == 201
    assert response.json()["field"] == "value"
```

## Test Coverage

View coverage report:

```bash
# Generate and view HTML report
pytest tests/ --cov=backend/app --cov-report=html
open htmlcov/index.html  # Or browse to htmlcov/index.html
```

## Debugging Tests

```bash
# Show print statements
pytest tests/ -s

# More verbose
pytest tests/ -vv

# Show local variables on failure
pytest tests/ -l

# Drop into debugger on failure
pytest tests/ --pdb

# Stop on first failure
pytest tests/ -x
```

## CI/CD Integration

For CI/CD pipelines:

```bash
# Run with coverage and fail if below threshold
pytest tests/ --cov=backend/app --cov-fail-under=80

# Generate XML report for CI
pytest tests/ --cov=backend/app --cov-report=xml --junitxml=test-results.xml
```

## Tips

1. **Run tests frequently** during development
2. **Use `-k` flag** to run subset of tests
3. **Check coverage** to find untested code
4. **Use fixtures** to avoid code duplication
5. **Keep tests independent** - no shared state
6. **Test authorization** for all protected endpoints
7. **Test error cases** not just happy paths
8. **Use descriptive names** for clarity

## Getting Help

- See `/home/user/Connected/backend/TESTING.md` for full documentation
- Run `pytest --help` for all options
- Check test output for detailed error messages
