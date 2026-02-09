# Friday AI - Security Guide
## Security Features and Guidelines

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Approval Policies](#approval-policies)
3. [Dangerous Command Detection](#dangerous-command-detection)
4. [Secret Scrubbing](#secret-scrubbing)
5. [Path Validation](#path-validation)
6. [Configuration Security](#configuration-security)
7. [Best Practices](#best-practices)

---

## Security Overview

Friday AI includes multiple layers of security:

| Layer | Feature | Description |
|-------|---------|-------------|
| **Execution Control** | Approval Policies | Configure when user confirmation is required |
| **Command Safety** | Dangerous Pattern Detection | Automatic detection of harmful commands |
| **Data Protection** | Secret Scrubbing | Automatic redaction of sensitive data |
| **Access Control** | Path Validation | Restrict operations to allowed directories |
| **Environment Safety** | Shell Environment Controls | Filter environment variables |

---

## Approval Policies

### Available Policies

| Policy | Confirmation Required | Use Case |
|--------|----------------------|----------|
| `yolo` | Never | ⚠️ Dangerous - only for safe environments |
| `auto` | Dangerous commands only | ✅ Recommended default |
| `auto-edit` | Writes only, reads auto-approved | ✅ Balanced approach |
| `on-request` | Every tool call | 🔒 Maximum safety |
| `on-failure` | Only when tools fail | 🔄 Debug mode |
| `never` | Always deny (tools disabled) | 🔒 Disabled mode |

### Configuration

```toml
# config.toml
approval = "auto"  # Set default policy
```

Change during session:
```
[user]> /approval auto-edit
[success] Approval policy changed to: auto-edit
```

---

## Dangerous Command Detection

### Detected Patterns

Friday automatically detects these dangerous patterns:

#### File System Destruction
```bash
rm -rf /          # Recursive deletion
rm -rf /*         # Root deletion
rm -rf ~          # Home directory deletion
rmdir -p /        # Directory removal
```

#### Database Destruction
```bash
drop database     # SQL database drop
dropdb            # PostgreSQL drop
```

#### Redirect Overwrites
```bash
command > /etc/passwd       # System file overwrite
command > ~/.bashrc         # Config file overwrite
command >> /etc/hosts       # System file append
```

#### Remote Code Execution
```bash
curl ... | bash             # Pipe from internet
curl ... | sh               # Pipe to shell
wget ... | bash             # Wget pipe
fetch ... | sh              # Fetch pipe
```

#### Privilege Escalation
```bash
sudo ...                    # Superuser commands
su -                        # Switch user
```

#### Disk Operations
```bash
mkfs                        # Format filesystem
dd if=... of=/dev/sda       # Direct disk write
fdisk                       # Partition manipulation
```

### Shell Command Filtering

```python
# Shell environment configuration
[shell_environment]
ignore_default_excludes = false
exclude_patterns = [
    "*KEY*",
    "*TOKEN*",
    "*SECRET*",
    "*PASSWORD*",
    "*API_KEY*"
]
```

---

## Secret Scrubbing

### Automatically Redacted Patterns

Friday automatically scrubs these patterns from output:

- API keys (various formats)
- Passwords
- Bearer tokens
- Private keys
- Environment variables matching patterns

### Configuration

```toml
[shell_environment]
exclude_patterns = [
    "*KEY*",
    "*TOKEN*",
    "*SECRET*",
    "AWS_*",
    "GITHUB_*"
]
```

### Example

```
Before scrubbing:
  API_KEY=sk-abc123xyz789

After scrubbing:
  API_KEY=***REDACTED***
```

---

## Path Validation

### Working Directory Restriction

By default, Friday operates within:
1. The configured `cwd` directory
2. Temp directories (for temporary operations)
3. Home directory (for configuration)

### Path Safety Checks

```python
# These are validated:
- Absolute paths must be within allowed directories
- Relative paths are resolved against cwd
- Symlinks are followed but checked
- Parent directory traversal (../) is restricted
```

### Configuration

```toml
# Allow specific additional paths
cwd = "/home/user/projects"
```

---

## Configuration Security

### Safe Configuration Practices

#### 1. Environment Variables for Secrets

```bash
# ✅ Good - use environment variables
export API_KEY="your-key"
export BASE_URL="https://api.provider.com"
```

```toml
# ✅ Good - config file without secrets
[model]
name = "GLM-4.7"
temperature = 1.0
```

#### 2. File Permissions

```bash
# Set restrictive permissions on config
chmod 600 ~/.config/ai-agent/config.toml

# Set permissions on .env
chmod 600 .env
```

#### 3. .gitignore

```gitignore
# Never commit secrets
.env
*.key
*.pem
config.toml  # If it contains secrets
```

### MCP Server Security

When configuring MCP servers:

```toml
# ✅ Good - explicit arguments
[mcp_servers.filesystem]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
enabled = true

# ❌ Avoid - broad permissions
args = ["-y", "@modelcontextprotocol/server-filesystem", "/"]  # Root access!
```

---

## Best Practices

### For Users

1. **Start with restrictive policy**
   ```toml
   approval = "on-request"  # Most safe
   ```

2. **Review before approving**
   - Always read the command before approving
   - Check paths in file operations
   - Verify shell commands are safe

3. **Use checkpoints for risky operations**
   ```
   [user]> /checkpoint
   [success] Checkpoint created: cp-123
   # Do risky work...
   [user]> /restore cp-123  # If something goes wrong
   ```

4. **Regular session cleanup**
   ```
   [user]> /clear  # Clear sensitive context
   ```

### For Developers

1. **Validate all inputs**
   ```python
   async def execute(self, path: str) -> str:
       # Validate path is within allowed directory
       if not is_path_allowed(path):
           return "Error: Path not allowed"
   ```

2. **Sanitize output**
   ```python
   # Scrub secrets from tool output
   return scrub_secrets(result)
   ```

3. **Use least privilege**
   ```python
   # Don't use sudo/root unless absolutely necessary
   ```

4. **Audit logging**
   ```toml
   [[hooks]]
   name = "audit-log"
   trigger = "after_tool"
   command = "echo '{{timestamp}} {{tool_name}}' >> /var/log/friday-audit.log"
   ```

---

## Security Checklist

### Before Running Friday

- [ ] API key stored securely (environment variable)
- [ ] Configuration file has safe permissions (600)
- [ ] Approval policy set appropriately
- [ ] Working directory configured correctly
- [ ] Shell environment excludes sensitive patterns

### During Use

- [ ] Review dangerous commands before approving
- [ ] Use `/checkpoint` before major changes
- [ ] Clear context with `/clear` when done
- [ ] Save sessions only if they don't contain secrets

### In Projects

- [ ] `.env` in `.gitignore`
- [ ] No hardcoded secrets in code
- [ ] MCP servers restricted to safe paths
- [ ] Custom tools validate inputs

---

## Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** open a public issue
2. Email: security@example.com
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

---

*Security Guide v1.0 - Friday AI Teammate*
