# Testing Strategy: [REPO_NAME]

## Test Philosophy

[APPROACH] (e.g., TDD, Testing Pyramid, Risk-Based)

## Test Types

### 1. Unit Tests

**Framework**: [FRAMEWORK]
**Location**: `[DIRECTORY]`
**Coverage Target**: [PERCENTAGE]%

**What to Test**:
- [ ] Pure functions
- [ ] Utility functions
- [ ] Component logic
- [ ] State transformations

**Running**:
```bash
[COMMAND]
```

### 2. Integration Tests

**Framework**: [FRAMEWORK]
**Location**: `[DIRECTORY]`
**Coverage Target**: [PERCENTAGE]%

**What to Test**:
- [ ] API endpoints
- [ ] Database operations
- [ ] Component interactions
- [ ] Service integrations

**Running**:
```bash
[COMMAND]
```

### 3. E2E Tests

**Framework**: [FRAMEWORK]
**Location**: `[DIRECTORY]`

**Critical User Flows**:
1. [FLOW_1]
2. [FLOW_2]
3. [FLOW_3]

**Running**:
```bash
[COMMAND]
```

## Test Structure

```
[TESTS_DIRECTORY]/
├── unit/              # Unit tests
│   ├── [CATEGORY_1]/
│   └── [CATEGORY_2]/
├── integration/       # Integration tests
│   ├── [API_TESTS]/
│   └── [DB_TESTS]/
└── e2e/              # End-to-end tests
    ├── [FLOW_1]/
    └── [FLOW_2]/
```

## Coverage Report

**Current Coverage**: [PERCENTAGE]%
**Target**: [PERCENTAGE]%

### Coverage by Module

| Module | Coverage | Status |
|--------|----------|--------|
| [MODULE_1] | [%] | [✅/⚠️] |
| [MODULE_2] | [%] | [✅/⚠️] |

## CI/CD Integration

Tests run automatically on:
- [ ] Pull request
- [ ] Push to main
- [ ] Manual trigger

**CI Config**: `[FILE]`

## Writing Tests

### Test Template

```[LANGUAGE]
// Test: [WHAT_IT_TESTS]
describe('[Feature/Component]', () => {
  // Given
  const input = [SETUP];

  it('should [EXPECTED_BEHAVIOR]', () => {
    // When
    const result = [ACTION];

    // Then
    expect(result).toBe([EXPECTED]);
  });
});
```

## Testing Best Practices

1. **Arrange, Act, Assert** - Clear test structure
2. **One assertion per test** - Focused tests
3. **Descriptive names** - Test names should read like requirements
4. **Test behavior, not implementation** - Black-box testing
5. **Mock external dependencies** - Isolate the unit under test

## Troubleshooting

### Flaky Tests

**Symptom**: Tests pass sometimes, fail sometimes

**Solutions**:
- Add explicit waits
- Mock async operations
- Increase timeouts
- Fix race conditions

### Timeout Issues

**Symptom**: Tests timeout after [TIME]ms

**Solutions**:
- Increase timeout: jest.setTimeout([TIME])
- Fix async operations
- Check for infinite loops
- Mock slow operations
