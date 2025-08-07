# Testing Guide for Kizuna Restaurant Analytics

This directory contains comprehensive tests for the Kizuna Restaurant Analytics project, focusing on the data processing pipeline and related components.

## Test Structure

```
tests/
├── unit/                          # Unit tests
│   └── test_initial_load_pipeline.py
├── integration/                   # Integration tests
│   └── test_pipeline_integration.py
├── fixtures/                      # Test fixtures and data
│   └── test_data.py
├── e2e/                          # End-to-end tests (future)
└── README.md                     # This file
```

## Test Categories

### Unit Tests (`tests/unit/`)
- Test individual components in isolation
- Use mocks to isolate dependencies
- Fast execution
- Focus on specific functionality

### Integration Tests (`tests/integration/`)
- Test component interactions
- Use real file operations and data
- Test complete workflows
- More comprehensive coverage

### Test Fixtures (`tests/fixtures/`)
- Reusable test data
- Mock objects for testing
- Sample Excel files
- Common setup utilities

## Running Tests

### Prerequisites
Make sure you have the required packages installed:
```bash
pip install pytest pytest-django pandas openpyxl
```

### Using the Test Runner Script
The easiest way to run tests is using the provided test runner script:

```bash
# Run all tests
python scripts/run_tests.py

# Run only unit tests
python scripts/run_tests.py --unit

# Run only integration tests
python scripts/run_tests.py --integration

# Run tests with coverage report
python scripts/run_tests.py --coverage

# Run a specific test file
python scripts/run_tests.py --test tests/unit/test_initial_load_pipeline.py

# Check test environment
python scripts/run_tests.py --check
```

### Using pytest directly
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_initial_load_pipeline.py

# Run tests with verbose output
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=data_engineering --cov=apps --cov-report=html

# Run tests with specific markers
pytest tests/ -m unit
pytest tests/ -m integration
```

## Test Coverage

The tests cover the following areas:

### DataProcessingPipeline
- ✅ Pipeline initialization
- ✅ Successful pipeline execution
- ✅ Error handling at each stage (extract, transform, load)
- ✅ Status updates throughout processing
- ✅ Processing statistics tracking
- ✅ Error logging and reporting
- ✅ Different file types (Odoo export, recipes data)
- ✅ Concurrent processing
- ✅ Exception handling

### File Processing
- ✅ Valid Excel file processing
- ✅ Invalid file handling
- ✅ Empty file handling
- ✅ Large dataset processing
- ✅ Different file formats

### Error Handling
- ✅ Extraction errors
- ✅ Transformation errors
- ✅ Loading errors
- ✅ Database constraint violations
- ✅ File format errors
- ✅ Missing data errors

## Test Data

The test fixtures provide:

### Sample Data
- **Odoo Export Data**: Products, sales, and purchases data
- **Recipes Data**: Recipe information with ingredients and instructions
- **Large Datasets**: For performance testing

### File Types
- **Valid Excel Files**: Properly formatted data files
- **Invalid Files**: Files with wrong format or content
- **Empty Files**: Files with no data

### Mock Objects
- **MockExtractor**: Simulates data extraction
- **MockTransformer**: Simulates data transformation
- **MockLoader**: Simulates data loading

## Writing New Tests

### Unit Test Example
```python
def test_specific_functionality(self):
    """Test description"""
    # Arrange
    pipeline = DataProcessingPipeline(self.upload)
    
    # Act
    result = pipeline.some_method()
    
    # Assert
    self.assertTrue(result)
    self.assertEqual(pipeline.upload.status, "completed")
```

### Integration Test Example
```python
def test_full_workflow(self):
    """Test complete workflow with real data"""
    # Arrange
    upload = self.create_upload_instance(self.excel_file_path)
    
    # Act
    pipeline = DataProcessingPipeline(upload)
    result = pipeline.process()
    
    # Assert
    self.assertTrue(result)
    self.assertEqual(upload.status, "completed")
```

### Using Fixtures
```python
def test_with_fixture(self, sample_user, sample_excel_file):
    """Test using pytest fixtures"""
    upload = DataUpload.objects.create(
        file=sample_excel_file,
        uploaded_by=sample_user,
        file_type="odoo_export"
    )
    # ... rest of test
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Descriptive Names**: Use clear, descriptive test names
3. **Arrange-Act-Assert**: Structure tests in this pattern
4. **Mock External Dependencies**: Use mocks for external services
5. **Test Edge Cases**: Include error conditions and edge cases
6. **Clean Up**: Always clean up test data and files
7. **Use Fixtures**: Reuse common test data and setup

## Continuous Integration

The tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Tests
  run: |
    python scripts/run_tests.py --coverage
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure Django settings are properly configured
2. **Database Issues**: Tests use a test database, ensure migrations are applied
3. **File Permission Errors**: Ensure test directories are writable
4. **Memory Issues**: Large dataset tests may require more memory

### Debug Mode
Run tests with debug output:
```bash
pytest tests/ -v -s --tb=long
```

### Test Environment Check
```bash
python scripts/run_tests.py --check
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain test coverage above 80%
4. Update this README if adding new test categories
5. Add appropriate test markers for categorization

## Test Configuration

The test configuration is in `pytest.ini`:
- Django settings module: `config.settings.testing`
- Test discovery patterns
- Output formatting options
- Markers for test categorization 