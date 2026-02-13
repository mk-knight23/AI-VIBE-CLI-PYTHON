# Friday AI - Comprehensive Bug Audit Report

**Date:** Fri Feb 13 2026
**Status:** Critical Issues Identified
**Audit Scope:** Core Agent Logic, Tool System, Resource Management, Concurrency, and Error Handling.

---

## Executive Summary

The audit revealed several critical and moderate issues, primarily stemming from recent refactoring and inconsistent resource management. Most notably, a regression in the `Agent` cleanup logic will cause errors during session termination, and multiple resource leaks exist in the HTTP and MCP integration layers.

---

## 1. Critical Regressions (Refactoring Bugs)

### 1.1 `Agent` Logic Broken by Refactoring
- **File:** `friday_ai/agent/agent.py`
- **Issue:** The `Agent` class still attempts to access attributes directly on `self.session` (e.g., `self.session.tool_registry`, `self.session.hook_system`, `self.session.mcp_manager`) that were moved to subcomponents like `tool_orchestrator` during the refactoring.
- **LSP Evidence:** 50+ errors in `agent.py` regarding unknown attributes of `Session`.
- **Impact:** The agent will crash almost immediately upon running any task or during initialization/cleanup.

### 1.2 `ToolOrchestrator.get_tools_info` Logic Error
- **File:** `friday_ai/agent/tool_orchestrator.py`
- **Issue:** In `get_tools_info`, the code tries to call `.keys()` on `mcp_servers`, which is a `list[Tool]`.
- **LSP Evidence:** `ERROR [89:49] Cannot access attribute "keys" for class "list[Tool]"`
- **Impact:** Crashes when attempting to view tool/MCP status.

### 1.3 `Agent.__aexit__` Broken Attribute Access
- **File:** `friday_ai/agent/agent.py`
- **Issue:** The `__aexit__` method attempts to call `self.session.mcp_manager.shutdown()`. However, the `Session` class was refactored, and `mcp_manager` was moved to `self.session.tool_orchestrator.mcp_manager`.
- **Impact:** Calling `__aexit__` (which happens automatically when using `async with Agent(...)`) will likely raise an `AttributeError` or skip MCP shutdown, leaving orphan processes/connections.
- **Recommendation:** Update `Agent.__aexit__` to use `self.session.tool_orchestrator.mcp_manager.shutdown()` or call a consolidated `self.session.cleanup()`.

## 2. Resource & Memory Leaks


### 2.1 `HttpClient` Singleton Leak
- **File:** `friday_ai/tools/builtin/http_client.py`, `friday_ai/agent/session.py`
- **Issue:** The `HttpClient` provides a global singleton with connection pooling. While a `shutdown_http_client` function exists, it is called in `Session.cleanup()` but NOT in `Agent.__aexit__`.
- **Impact:** Connections in the pool may remain open until the process terminates, potentially leading to port exhaustion in long-running environments (e.g., API server mode).

### 2.2 `ToolOrchestrator` Shutdown Incomplete
- **File:** `friday_ai/agent/tool_orchestrator.py`
- **Issue:** `ToolOrchestrator.shutdown()` logs a shutdown message but fails to call `self.mcp_manager.shutdown()`.
- **Impact:** MCP server processes (node/python subprocesses) are not explicitly killed, leading to zombie processes.

### 2.3 `DatabaseTool` Connection Spawning
- **File:** `friday_ai/tools/builtin/database.py`
- **Issue:** The tool creates a fresh connection for every single query/execute action instead of using the `ConnectionPool` implemented in `friday_ai/database/pool.py`.
- **Impact:** Extreme inefficiency and high risk of "Too many connections" errors on the database server.

---

## 3. Concurrency & Race Conditions

### 3.1 `Scheduler` Premature Exit
- **File:** `friday_ai/scheduler/scheduler.py`
- **Issue:** The `start()` loop condition is `while self.running and self.tasks:`. If the scheduler is started without any initial tasks, it terminates immediately.
- **Impact:** Subsequent calls to `schedule()` will add tasks to the list, but they will never be executed as the loop has already finished.
- **Recommendation:** Change loop condition to `while self.running:`.

### 3.2 `ConnectionPool.acquire` Race Condition
- **File:** `friday_ai/database/pool.py`
- **Issue:** There is a gap between failing to get a connection via `get_nowait()` and waiting on the semaphore. If a connection is released in that millisecond, the acquirer might still block on the semaphore.
- **Impact:** Minor performance degradation or unnecessary timeouts under extreme load.

---

## 4. Logic & Edge Case Errors

### 4.1 Broken Imports and Type Safety
- **File:** `friday_ai/main.py`, `friday_ai/agent/safety_manager.py`
- **Issue:** Several imports are broken. For example, `VoiceStatus` is missing from `friday_ai.ui.voice`, and `friday_ai.safety.validators` is missing.
- **LSP Evidence:** Multiple "could not be resolved" and "unknown import symbol" errors.
- **Impact:** System-wide instability; specific features like Voice or Safety validation will fail at runtime.

### 4.2 Hardcoded Tool CWD
- **File:** `friday_ai/api/routers/tools.py`
- **Issue:** Line 67 contains `# TODO: Get from session or config`. The `cwd` is currently hardcoded to `"/tmp"`.
- **Impact:** Tools executed via the API will not see the project files unless they are in `/tmp`.

### 4.2 File Encoding & Size (Edit/Write Tools)
- **File:** `friday_ai/tools/builtin/edit_file.py`
- **Issue:** Hardcoded `utf-8` encoding and `read_text()` which loads the entire file into memory.
- **Impact:** Failure on non-UTF-8 files and OOM crashes on large log/data files.

### 4.3 Timezone Inconsistency
- **Files:** `friday_ai/scheduler/scheduler.py` vs `friday_ai/agent/autonomous_loop.py`
- **Issue:** `scheduler.py` uses `datetime.now()` (local time), while `autonomous_loop.py` correctly uses `datetime.now(timezone.utc)`.
- **Impact:** Tasks scheduled in one part of the system might be compared against times from another part with different offsets, leading to missed or premature executions.

---

## 5. Existing Code Tags (TODO/FIXME/BUG)

| File | Line | Tag | Description |
|------|------|-----|-------------|
| `friday_ai/api/routers/tools.py` | 67 | TODO | Get CWD from session/config instead of `/tmp` |
| `friday_ai/database/pool.py` | 93 | FIX | Lock for thread-safe stats updates (Implemented) |
| `friday_ai/database/pool.py` | 133 | FIX | Batch health check (Implemented) |
| `friday_ai/database/pool.py` | 219 | FIX | Try to acquire without blocking (Partial) |
| `friday_ai/database/pool.py` | 312 | FIX | Protect stats update with lock (Implemented) |
| `friday_ai/agent/autonomous_loop.py` | 80 | FIX | Limit file list to prevent unbounded growth (Implemented) |

---

## 6. Recommendations

1.  **Immediate Fix:** Repair `Agent.__aexit__` to correctly navigate the refactored `Session` structure and call `Session.cleanup()`.
2.  **Resource Management:** Ensure `HttpClient.shutdown()` and `DatabasePool.close()` are called during application/agent teardown.
3.  **Refactor `DatabaseTool`:** Update it to utilize the existing `ConnectionPool` for all backends.
4.  **Standardize Time:** Enforce `timezone-aware UTC datetimes` across the entire codebase.
5.  **Robust File I/O:** Update file tools to detect encoding and use streaming for large files.
