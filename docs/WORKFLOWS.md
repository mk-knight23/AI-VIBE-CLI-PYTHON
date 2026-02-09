# Friday AI - Workflows
## Common Usage Patterns

---

## Table of Contents

1. [Code Analysis Workflow](#code-analysis-workflow)
2. [Refactoring Workflow](#refactoring-workflow)
3. [Debugging Workflow](#debugging-workflow)
4. [Documentation Workflow](#documentation-workflow)
5. [Testing Workflow](#testing-workflow)
6. [Learning Workflow](#learning-workflow)

---

## Code Analysis Workflow

### Understanding a New Codebase

```bash
# Start Friday in the project directory
friday -c /path/to/project
```

```
[user]> Analyze this codebase structure. What are the main components?

# Friday will:
# 1. List the directory structure
# 2. Read key files (README, pyproject.toml, etc.)
# 3. Analyze the source code organization
# 4. Provide a summary of architecture
```

### Deep Dive into Specific Areas

```
[user]> Find all functions that handle user authentication

# Follow-up questions:
[user]> Show me the login function implementation
[user]> What files import this authentication module?
[user]> Are there any tests for the auth functionality?
```

### Code Review Pattern

```
[user]> Review the src/auth.py file for security issues

# Friday will:
# 1. Read the file
# 2. Analyze for common security patterns
# 3. Suggest improvements
# 4. Identify potential vulnerabilities
```

---

## Refactoring Workflow

### Step-by-Step Refactoring

```
[user]> I want to refactor the utils.py file to improve readability

# Create a checkpoint first
[user]> /checkpoint
[success] Checkpoint created: refactor-utils-1

# Proceed with refactoring
[user]> Read utils.py and identify functions that can be split
[user]> Extract the validation functions into a separate validators.py file
[user]> Update imports in files that use these functions
[user]> Run tests to ensure nothing broke

# If something goes wrong:
[user]> /restore refactor-utils-1
```

### Adding Type Hints

```
[user]> Add type hints to all functions in the models.py file

# Friday will:
# 1. Read the file
# 2. Analyze function signatures
# 3. Add appropriate type hints
# 4. Import necessary types
```

### Improving Error Handling

```
[user]> Find all try/except blocks that catch generic Exception
[user]> For each one, suggest more specific exception handling

# Review suggestions and apply selectively
```

---

## Debugging Workflow

### Investigating an Issue

```
[user]> I'm getting an error when running the tests. Help me debug.

[user]> Run the tests and capture the error output
[user]> Read the relevant source files mentioned in the traceback
[user]> Search for similar error patterns in the codebase
[user]> Suggest a fix for the issue
```

### Log Analysis

```
[user]> Search for all log.error calls in the codebase
[user]> Are there any error patterns that aren't being handled properly?

# Friday can:
# 1. Find error handling patterns
# 2. Identify missing error cases
# 3. Suggest improvements
```

### Performance Investigation

```
[user]> Find all database queries in the users.py file
[user]> Are there any N+1 query patterns?

# Friday will analyze the code for common performance issues
```

---

## Documentation Workflow

### Generating Documentation

```
[user]> Generate a README.md for this project based on the code

# Friday will:
# 1. Analyze project structure
# 2. Read existing files
# 3. Generate comprehensive README with:
#    - Description
#    - Installation instructions
#    - Usage examples
#    - API documentation
```

### Adding Docstrings

```
[user]> Add docstrings to all public functions in api/routes.py

# Friday will:
# 1. Read the file
# 2. Identify public functions
# 3. Add Google-style docstrings
# 4. Include Args, Returns, Raises sections
```

### Creating API Documentation

```
[user]> Document all the API endpoints in the app

# Friday will:
# 1. Find all route definitions
# 2. Extract endpoint information
# 3. Document request/response formats
# 4. Create OpenAPI/Swagger compatible docs
```

---

## Testing Workflow

### Generating Tests

```
[user]> Generate tests for the auth.py module

# Friday will:
# 1. Read the module
# 2. Identify functions that need testing
# 3. Create pytest test cases
# 4. Include success and failure cases
```

### Improving Test Coverage

```
[user]> What parts of the codebase have the least test coverage?

# Friday can help:
# 1. Analyze test files
# 2. Compare with source files
# 3. Identify untested functions
# 4. Generate test templates
```

### Debugging Failing Tests

```
[user]> The test_user_login test is failing. Help me fix it.

[user]> Read the test file and identify the failing test
[user]> Read the implementation being tested
[user]> Identify the mismatch between test and implementation
[user]> Fix either the test or the implementation
```

---

## Learning Workflow

### Understanding a New Technology

```
[user]> Search for best practices for Python asyncio
[user]> Show me examples of proper async/await patterns in this codebase

# Friday will:
# 1. Search the web for best practices
# 2. Find examples in your codebase
# 3. Compare with recommended patterns
# 4. Suggest improvements
```

### Exploring Language Features

```
[user]> Find examples of context managers in this codebase
[user]> Explain how they're being used

# Friday will:
# 1. Search for context manager patterns
# 2. Explain each usage
# 3. Suggest where context managers could be added
```

### Code Review Learning

```
[user]> Review my recent changes and teach me better patterns

# Save your work first
[user]> /checkpoint

# Ask for detailed review
[user]> What are some Python patterns I could use to improve this code?
```

---

## Advanced Workflows

### Multi-File Refactoring

```
[user]> I need to rename the User class to Customer across the entire codebase

# Create a checkpoint
[user]> /checkpoint

# Find all occurrences
[user]> Grep for all files that reference the User class

# Plan the changes
[user]> Show me all the files that need to be modified

# Execute changes
[user]> Rename User to Customer in each file
[user]> Update all imports
[user]> Run tests to verify
```

### Code Generation

```
[user]> Create a new FastAPI endpoint for user management

# Friday will:
# 1. Look at existing endpoints for patterns
# 2. Generate the new endpoint code
# 3. Add necessary imports
# 4. Suggest tests for the new endpoint
```

### Migration Workflow

```
[user]> Help me migrate from requests to httpx for async support

# Create checkpoint
[user]> /checkpoint

# Find all usage
[user]> Find all files that import requests
[user]> For each file, show me what needs to change

# Execute migration
[user]> Update imports and code to use httpx
[user]> Ensure async/await is used correctly
```

---

## Session Management Tips

### Long-Running Tasks

```
# For complex multi-step tasks:

[user]> /checkpoint  # Save state before major changes

# Do work...

[user]> /checkpoint  # Save progress

# More work...

[user]> /save  # Save the entire session for later
```

### Collaborative Sessions

```
# Share session state with teammates:

[user]> /save
[success] Session saved: session-abc-123

# Teammate can resume:
$ friday
[user]> /resume session-abc-123
```

### Context Management

```
# When context gets too long:
[user]> /stats
Session Statistics
   turn_count: 45  # Getting high!

[user]> /clear  # Clear and start fresh

# Or checkpoint and start new focused task:
[user]> /checkpoint focused-task-1
```

---

## Productivity Tips

### 1. Use Memory for Context

```
[user]> Remember that the main config is in app/core/config.py
# Later...
[user]> Where is the main config file?
# Friday recalls from memory
```

### 2. Use Todos for Multi-Step Tasks

```
[user]> Add a todo: Refactor auth module
[user]> Add a todo: Update tests
[user]> Add a todo: Update documentation
[user]> Show my todos
```

### 3. Combine Tools Effectively

```
[user]> Search for "TODO" comments in the codebase
[user]> For each TODO, create a todo item
[user]> Save the session so I can work on these later
```

### 4. Web Research + Code

```
[user]> Search for Python dataclass best practices
[user]> Show me how dataclasses are used in this codebase
[user]> Suggest improvements based on best practices
```

---

*Workflows Guide v1.0 - Friday AI Teammate*
