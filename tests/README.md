# Test Suite

## Overview
This directory contains all automated tests for the Eco Buddy AI platform. By separating test code from application code, we maintain a clean root directory and simplify deployment and packaging pipelines.

## Structure
The test directory is organized into several subdirectories based on the type of test:
- **`unit/`**: Fast, isolated tests for individual functions and classes.
- **`integration/`**: Tests that verify the interaction between multiple components or the database.
- **`api/`**: Tests that validate external API contracts and error handling.
- **`services/`**: Tests focusing on the core business logic and background services.
- **`performance/`**: Load and performance testing scripts.
- **`fixtures/`**: Shared pytest fixtures and mock data setups.

*(Note: Currently, many tests are located at the root of `tests/` as part of the Phase 2 migration (Issue #1205). They will gradually be sorted into these appropriate subdirectories.)*

## Running Tests
To run the entire test suite, ensure you are in the project root directory and execute:
```bash
pytest
```

To run a specific test file:
```bash
pytest tests/test_filename.py
```

## Adding New Tests
- All test files must be prefixed with `test_`.
- Place new tests in the appropriate subdirectory based on their scope.
- Use `pytest` fixtures for setup and teardown instead of raw `setUp` and `tearDown` methods where possible.
