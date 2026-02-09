# Deployment Guide: [REPO_NAME]

## Deployment Platform

**Primary**: [PLATFORM] (e.g., Vercel, Netlify, Render, GitHub Pages)
**Backup**: [PLATFORM]

## Prerequisites

1. [REQUIREMENT_1]
2. [REQUIREMENT_2]
3. [REQUIREMENT_3]

## Environment Variables

Required for production:

```bash
# [CATEGORY]
VAR_NAME=description
# Example: VAR_NAME=value

# [CATEGORY]
ANOTHER_VAR=description
```

### Local Development

Create `.env` or `.env.local`:

```bash
# Copy from .env.example
cp .env.example .env.local

# Edit values
nano .env.local
```

## Build Configuration

### Production Build

```bash
# Run the build script
bash .claude/scripts/build.sh
```

**Output**: [OUTPUT_DIRECTORY]

**Build Artifacts**:
- [ARTIFACT_1]
- [ARTIFACT_2]

## Deployment Steps

### Automatic Deploy (Recommended)

[PLATFORM] handles deployment automatically when:
- [TRIGGER_1]
- [TRIGGER_2]

### Manual Deploy

```bash
# Run the deploy script
bash .claude/scripts/deploy.sh
```

## Platform-Specific Notes

### [PLATFORM_NAME]

**Configuration File**: `[CONFIG_FILE]`

**Key Settings**:
- [SETTING_1]: [VALUE]
- [SETTING_2]: [VALUE]

**Build Command**: `[COMMAND]`
**Output Directory**: `[DIRECTORY]`
**Node Version**: `[VERSION]`

## Post-Deploy Checklist

- [ ] Build successful
- [ ] All pages/routes accessible
- [ ] Environment variables loaded
- [ ] API endpoints working (if applicable)
- [ ] Analytics configured (if applicable)
- [ ] Custom domain configured (if applicable)

## Monitoring

**Live URL**: [URL]
**Deploy Logs**: [URL]
**Analytics**: [URL]

## Rollback Procedure

If deployment fails:

1. [STEP_1]
2. [STEP_2]
3. [STEP_3]

## Troubleshooting

### Issue: [PROBLEM]

**Symptom**: [DESCRIPTION]

**Solution**:
```bash
[COMMAND]
```

### Issue: [PROBLEM]

**Symptom**: [DESCRIPTION]

**Solution**:
```bash
[COMMAND]
```
