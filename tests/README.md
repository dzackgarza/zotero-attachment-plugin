# Test Suite Documentation

This directory contains three types of tests for the Fulltext Attachment API:

## Test Files

### 1. `test_tdd_integration.py` - General TDD Tests
- **Purpose**: Fail-first TDD tests that work on any Zotero installation
- **Dependencies**: None - dynamically discovers test items
- **Use Case**: General development and CI/CD testing
- **Features**:
  - Tests endpoint existence before/after installation
  - Tests error handling (missing files, invalid items)
  - Tests successful attachment
  - Dynamically finds test items in any library

### 2. `test_real_library.py` - Real Library Tests
- **Purpose**: Tests using REAL hardcoded items from developer's library
- **Dependencies**: Specific Zotero items (e.g., BXXECN89 for Alexeev paper)
- **Use Case**: Developer-specific validation with known data
- **Features**:
  - Tests with actual paper content ("Γrhas 19 roots")
  - Tests search functionality
  - Tests large file handling (textbook simulation)
  - Uses real item keys that only exist in developer's library

### 3. `test_api_endpoint.py` - API Unit Tests
- **Purpose**: Detailed API endpoint testing
- **Dependencies**: None - creates test data as needed
- **Use Case**: Comprehensive API validation
- **Features**:
  - Tests all API methods and parameters
  - Tests concurrent requests
  - Tests edge cases

## Running Tests

### For General Testing (Anyone)
```bash
# Run general TDD tests
python test_tdd_integration.py

# Run API unit tests
python test_api_endpoint.py
```

### For Developer Testing (With Real Library)
```bash
# Run tests with real library items
python test_real_library.py
```

### For Complete Testing
```bash
# Run all tests
python -m pytest tests/

# Or manually run each
python test_tdd_integration.py
python test_api_endpoint.py
python test_real_library.py  # Only works on developer's system
```

## Key Differences

| Test Type | Hardcoded Values | Works Anywhere | Use Case |
|-----------|------------------|----------------|----------|
| TDD Integration | No | Yes | General development |
| Real Library | Yes (BXXECN89, etc) | No | Developer validation |
| API Endpoint | No | Yes | API testing |

## Adding Your Own Real Library Tests

To add your own hardcoded tests in `test_real_library.py`:

1. Find item keys from your library:
   ```python
   # Add your own constants at the top
   MY_FAVORITE_PAPER = "XYZ789"
   TEXTBOOK_ITEM = "ABC123"
   ```

2. Create specific tests:
   ```python
   def test_my_specific_item(self):
       """Test with my specific library item."""
       # Your test code here
   ```

This separation ensures:
- General tests remain portable
- Real library tests can validate actual known content
- Developers can test with their specific data without breaking general tests
