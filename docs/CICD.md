# Friday AI - CI/CD Guide
## Continuous Integration and Deployment

---

## Table of Contents

1. [GitHub Actions Workflow](#github-actions-workflow)
2. [Testing Pipeline](#testing-pipeline)
3. [Release Process](#release-process)
4. [PyPI Publishing](#pypi-publishing)

---

## GitHub Actions Workflow

### Example CI Configuration

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12', '3.14']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run tests
        run: pytest tests/ -v --cov=friday_ai --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install ruff mypy

      - name: Run ruff
        run: ruff check friday_ai/

      - name: Run mypy
        run: mypy friday_ai/
```

---

## Testing Pipeline

### Local Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=friday_ai --cov-report=html

# Run specific test file
pytest tests/test_security.py -v
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
```

---

## Release Process

### Version Bump Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create git tag
- [ ] Push to PyPI

### Automated Release Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install build twine

      - name: Build package
        run: python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

---

## PyPI Publishing

### Manual Publishing

```bash
# Clean build
rm -rf dist/ build/

# Build package
python -m build

# Check package
twine check dist/*

# Upload to PyPI
twine upload dist/*
```

### Test PyPI

```bash
# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Test install
pip install --index-url https://test.pypi.org/simple/ friday-ai-teammate
```

---

*CI/CD Guide v1.0 - Friday AI Teammate*
