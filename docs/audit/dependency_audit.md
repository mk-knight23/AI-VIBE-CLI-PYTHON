# Dependency Audit Report - Friday AI Teammate

**Date:** 2026-02-13
**Version:** 2.1.0
**Audit Tooling:** `uv`, `pip-audit`, `deptry`, `pip-licenses`

---

## 📊 Executive Summary

The dependency health of **Friday AI Teammate** is generally excellent. No known security vulnerabilities were detected, and the project uses modern dependency management with `uv` and a lock file (`uv.lock`).

**Key Findings:**
- **Vulnerabilities:** 0 detected.
- **Outdated Packages:** 3 minor/patch updates available.
- **Missing Dependencies:** 1 package used but not defined (`aiosqlite`).
- **Version Integrity:** Discrepancy between `pyproject.toml` constraints and currently installed versions.

---

## 🛠️ Dependency Management Files

| File | Status | Role |
|------|--------|------|
| `pyproject.toml` | Active | Primary source of truth; defines ranges and optional extras. |
| `uv.lock` | Active | Strict version locking for deterministic builds. |
| `requirements.txt` | Legacy/Mirror | Manual mirror of core dependencies; potentially redundant. |

---

## ⚠️ Outdated Dependencies

Found **3** packages with available updates in the current environment:

| Package | Current | Latest | Type | Status |
|---------|---------|--------|------|--------|
| `click` | 8.1.8 | 8.3.1 | Minor | Safe to update |
| `py-key-value-aio` | 0.3.0 | 0.4.0 | Minor | Safe to update |
| `referencing` | 0.36.2 | 0.37.0 | Patch | Safe to update |

**Note on Version Constraints:**
There is a significant discrepancy between `pyproject.toml` and the installed environment. For example:
- `ddgs`: Constraint `<7.0.0`, Installed `9.10.0`.
- `openai`: Constraint `<2.0.0`, Installed `2.20.0`.
- `httpx`: Constraint `<0.28.0`, Installed `0.28.1`.

**Recommendation:** Update `pyproject.toml` constraints to reflect tested and working versions to avoid resolution failures in fresh environments.

---

## 🔒 Security Audit

A full vulnerability scan was performed using `pip-audit`.

**Results:**
- ✅ **No known vulnerabilities found.**

---

## 🔍 Unused & Missing Dependencies

Audited using `deptry`.

### 🚨 Missing Dependencies (Imported but not defined)
- `aiosqlite`: Used in `friday_ai/database/pool.py` but missing from `pyproject.toml`.

### ℹ️ Naming Discrepancies (False Positives)
The following are correctly defined but flagged due to module name differences:
- `pyyaml` (imported as `yaml`)
- `python-dotenv` (imported as `dotenv`)
- `SpeechRecognition` (imported as `speech_recognition`)

### 🧹 Potential Unused
- `python-dotenv`, `pyyaml`, `pytest`, etc. were flagged as unused in the main source code, but are utilized in specific modules or tests. No immediate action required.

---

## 📜 License Compliance

**Project License:** MIT

**Dependency Licenses:**
All direct dependencies use permissive, MIT-compatible licenses.

| Dependency Type | Licenses | Compatibility |
|-----------------|----------|---------------|
| Core | MIT, BSD-3-Clause, Apache 2.0 | ✅ High |
| Storage/DB | MIT, Apache 2.0 | ✅ High |
| Optional/Voice | MIT, BSD, MPL-2.0 | ✅ Compatible |

*Note: `pyttsx3` is MPL-2.0, which is a weak copyleft license. It is compatible with MIT as long as the library itself remains unmodified or changes are shared under MPL.*

---

## 🔐 Version Locking Strategy

1. **Development/Libraries:** `pyproject.toml` uses range pinning (`>=X.Y.Z, <A.B.C`), which is best practice for avoiding breaking changes while allowing security patches.
2. **Production/CLI:** `uv.lock` ensures every developer and deployment uses the exact same versions of all transitive dependencies.
3. **Redundancy:** `requirements.txt` should be either automated or removed to prevent desynchronization.

---

## ✅ Recommendations

1. **Immediate:** Add `aiosqlite` to `pyproject.toml`.
2. **Maintenance:** Sync `pyproject.toml` version ranges with actual installed versions (especially `ddgs` and `openai`).
3. **Refactor:** Remove `requirements.txt` and use `uv export` if a requirements format is needed for CI/CD.
4. **Automation:** Integrate `uv pip audit` (or `pip-audit`) into CI/CD pipeline.
