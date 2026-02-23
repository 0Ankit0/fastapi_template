# Test Suite Documentation

## Overview
This test suite provides comprehensive coverage of the FastAPI application with both unit and integration tests.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── factories.py             # Factory classes for generating test data
├── test_factories.py        # Tests for the factory classes
│
├── unit/                    # Unit tests (fast, isolated)
│   ├── core/               # Core functionality tests
│   │   ├── test_api.py    # API endpoint tests
│   │   ├── test_config.py # Configuration tests
│   │   ├── test_security.py # Security function tests
│   │   └── test_hypothesis_properties.py # Property-based tests
│   │
│   └── iam/                # IAM (Identity & Access Management) tests
│       ├── api/v1/auth/   # Authentication endpoint tests
│       ├── models/        # Database model tests
│       └── schemas/       # Schema validation tests
│
└── integration/            # Integration tests (E2E, slower)
    ├── auth/              # Authentication flow integration tests
    │   ├── test_auth_flow.py    # Complete auth lifecycle
    │   ├── test_security.py     # Security features
    │   ├── test_tokens.py       # Token management
    │   └── test_user_flow.py    # User flow scenarios
    │
    └── api/               # API integration tests
        ├── test_general.py      # General endpoints
        └── test_error_handling.py # Error cases
```

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run by Category
```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Core tests
pytest tests/unit/core/

# IAM tests
pytest tests/unit/iam/

# Authentication tests
pytest tests/unit/iam/api/v1/auth/
```

### Run by Marker
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only slow tests
pytest -m slow

# Run auth-related tests
pytest -m auth

# Run isolated tests
pytest -m isolated
```

### Run Specific Test File
```bash
pytest tests/unit/iam/api/v1/auth/test_login.py
```

### Run Specific Test Class or Function
```bash
pytest tests/unit/iam/api/v1/auth/test_login.py::TestLogin
pytest tests/unit/iam/api/v1/auth/test_login.py::TestLogin::test_login_success
```

### Run with Coverage
```bash
# With HTML report
pytest tests/ --cov=src --cov-report=html

# View in browser
open htmlcov/index.html

# With terminal report
pytest tests/ --cov=src --cov-report=term-missing
```

### Run in Verbose Mode
```bash
pytest tests/ -v
pytest tests/ -vv  # Extra verbose
```

### Run and Stop at First Failure
```bash
pytest tests/ -x
```

### Run Failed Tests from Last Run
```bash
pytest tests/ --lf
```

## Test Statistics
- **Total Tests**: 115
- **Unit Tests**: ~102
- **Integration Tests**: ~13
- **Pass Rate**: 92%+
- **Code Coverage**: 58%

## Test Fixtures

### Database Fixtures
- `test_engine`: Creates a fresh in-memory SQLite database for each test
- `db_session`: Provides a database session with automatic cleanup
- `client`: HTTP client with database session override and mocked email service

### Factory Fixtures
Located in `factories.py`:
- `UserFactory`: Generate test users
- `UserProfileFactory`: Generate user profiles
- `LoginAttemptFactory`: Generate login attempt records
- `TokenTrackingFactory`: Generate token tracking records
- `IPAccessControlFactory`: Generate IP access control records

## Writing Tests

### Unit Test Example
```python
import pytest
from src.apps.core import security

class TestPasswordHashing:
    def test_hash_password(self):
        """Test that password hashing works."""
        password = "TestPassword123"
        hashed = security.get_password_hash(password)
        assert hashed != password
        assert security.verify_password(password, hashed)
```

### Integration Test Example
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

class TestAuthFlow:
    @pytest.mark.asyncio
    async def test_signup_and_login(self, client: AsyncClient, db_session: AsyncSession):
        """Test complete signup and login flow."""
        # Signup
        signup_response = await client.post(
            "/api/v1/auth/signup/?set_cookie=false",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePass123",
                "confirm_password": "SecurePass123"
            }
        )
        assert signup_response.status_code == 200
        
        # Login
        login_response = await client.post(
            "/api/v1/auth/login/?set_cookie=false",
            json={"username": "testuser", "password": "SecurePass123"}
        )
        assert login_response.status_code == 200
```

### Using Factories
```python
from tests.factories import UserFactory

@pytest.mark.asyncio
async def test_with_factory(db_session):
    # Create a user with factory
    user = UserFactory.build(username="testuser")
    db_session.add(user)
    await db_session.commit()
    
    # Test logic here
    assert user.username == "testuser"
```

## Best Practices

### 1. Test Naming
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Use descriptive names that explain what is being tested

### 2. Test Organization
- One test file per module/feature
- Group related tests in classes
- Keep tests independent and isolated

### 3. Test Isolation
- Each test should be independent
- Use fixtures for setup/teardown
- Don't rely on test execution order

### 4. Assertions
- One logical assertion per test
- Use descriptive assertion messages
- Test both success and failure cases

### 5. Test Data
- Use factories for generating test data
- Keep test data minimal and focused
- Use meaningful test data that explains the test

### 6. Async Tests
- Mark async tests with `@pytest.mark.asyncio`
- Use `await` for async operations
- Clean up resources properly

## Troubleshooting

### Tests Fail When Run Together
Some tests may have isolation issues. Run them individually:
```bash
pytest tests/unit/iam/api/v1/auth/test_login.py -v
```

### Rate Limiting Issues
Tests that hit rate limits can be run with delays or individually.

### Database Issues
If you see database-related errors:
1. Ensure SQLite is installed
2. Check that migrations are up to date
3. Try running tests with `-v` for more details

### Import Errors
Make sure you're running tests from the project root:
```bash
cd /path/to/fastapi_template
pytest tests/
```

## Continuous Integration

### Pre-commit Checks
```bash
# Run tests before committing
pytest tests/ --cov=src --cov-report=term-missing

# Check coverage threshold
pytest tests/ --cov=src --cov-fail-under=70
```

### CI/CD Pipeline
The test suite is designed to run in CI/CD pipelines:
```yaml
# Example GitHub Actions
- name: Run tests
  run: |
    pytest tests/ --cov=src --cov-report=xml
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Contributing

When adding new tests:
1. Place unit tests in `tests/unit/` mirroring the source structure
2. Place integration tests in `tests/integration/` grouped by feature
3. Add appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
4. Ensure tests are isolated and don't depend on execution order
5. Update this README if adding new test categories

## Resources
- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLModel Testing](https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/)
