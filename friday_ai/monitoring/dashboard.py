"""Monitoring dashboard for Friday AI.

Web-based dashboard for real-time monitoring of:
- Autonomous loop status
- Session activity
- Resource usage
- Workflow executions
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiohttp import web

logger = logging.getLogger(__name__)


class MonitoringDashboard:
    """Web-based monitoring dashboard."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
    ):
        """Initialize the monitoring dashboard.

        Args:
            host: Host to bind to.
            port: Port to bind to.
        """
        self.host = host
        self.port = port
        self.app = web.Application()
        self._setup_routes()
        self._metrics: dict[str, Any] = {}

    def _setup_routes(self) -> None:
        """Setup HTTP routes."""
        self.app.router.add_get("/", self._index)
        self.app.router.add_get("/api/metrics", self._get_metrics)
        self.app.router.add_get("/api/loops", self._get_loops)
        self.app.router.add_get("/api/sessions", self._get_sessions)
        self.app.router.add_get("/api/workflows", self._get_workflows)
        self.app.router.add_post("/api/loops/{loop_id}/stop", self._stop_loop)

    async def _index(self, request: web.Request) -> web.Response:
        """Serve the dashboard HTML.

        Args:
            request: HTTP request.

        Returns:
            HTML page.
        """
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Friday AI - Monitoring Dashboard</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: #e0e0e0;
        }
        h1 {
            color: #4CAF50;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .section {
            background: #2a2a2a;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .section h2 {
            margin-top: 0;
            color: #4CAF50;
        }
        .metric {
            display: inline-block;
            margin: 10px 20px 10px 0;
        }
        .metric-label {
            font-size: 12px;
            color: #888;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        .status-active {
            background: #4CAF50;
            color: white;
        }
        .status-idle {
            background: #FFC107;
            color: black;
        }
        .status-error {
            background: #F44336;
            color: white;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #3a3a3a;
        }
        th {
            color: #888;
            font-weight: normal;
        }
        button {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Friday AI - Monitoring Dashboard</h1>

        <div class="section">
            <h2>System Status</h2>
            <div class="metric">
                <div class="metric-label">Status</div>
                <div class="metric-value" id="system-status">
                    <span class="status-badge status-active">Active</span>
                </div>
            </div>
            <div class="metric">
                <div class="metric-label">Active Sessions</div>
                <div class="metric-value" id="active-sessions">0</div>
            </div>
            <div class="metric">
                <div class="metric-label">Loops Running</div>
                <div class="metric-value" id="loops-running">0</div>
            </div>
            <div class="metric">
                <div class="metric-label">API Calls (This Hour)</div>
                <div class="metric-value" id="api-calls">0/100</div>
            </div>
        </div>

        <div class="section">
            <h2>Autonomous Loops</h2>
            <table id="loops-table">
                <thead>
                    <tr>
                        <th>Loop ID</th>
                        <th>Status</th>
                        <th>Iteration</th>
                        <th>Progress</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="loops-body">
                    <tr>
                        <td colspan="5" style="text-align: center; color: #888;">No active loops</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Sessions</h2>
            <table id="sessions-table">
                <thead>
                    <tr>
                        <th>Session ID</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Events</th>
                    </tr>
                </thead>
                <tbody id="sessions-body">
                    <tr>
                        <td colspan="4" style="text-align: center; color: #888;">No active sessions</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Workflow Executions</h2>
            <table id="workflows-table">
                <thead>
                    <tr>
                        <th>Workflow</th>
                        <th>Status</th>
                        <th>Steps</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody id="workflows-body">
                    <tr>
                        <td colspan="4" style="text-align: center; color: #888;">No active workflows</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // FIX-014: HTML escaping function to prevent XSS
        function htmlEscape(str) {
            if (str === null || str === undefined) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        // Auto-refresh every 2 seconds
        setInterval(refreshData, 2000);

        async function refreshData() {
            try {
                await Promise.all([
                    fetchMetrics(),
                    fetchLoops(),
                    fetchSessions(),
                    fetchWorkflows(),
                ]);
            } catch (error) {
                console.error('Error refreshing data:', error);
            }
        }

        async function fetchMetrics() {
            const response = await fetch('/api/metrics');
            const data = await response.json();

            document.getElementById('active-sessions').textContent = data.active_sessions || 0;
            document.getElementById('loops-running').textContent = data.loops_running || 0;
            document.getElementById('api-calls').textContent = `${data.api_calls || 0}/100`;
        }

        async function fetchLoops() {
            const response = await fetch('/api/loops');
            const loops = await response.json();

            const tbody = document.getElementById('loops-body');
            if (loops.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: #888;">No active loops</td></tr>';
                return;
            }

            // FIX-014: Use htmlEscape for all dynamic content
            tbody.innerHTML = loops.map(loop => `
                <tr>
                    <td>${htmlEscape(loop.id)}</td>
                    <td><span class="status-badge ${loop.status === 'running' ? 'status-active' : 'status-idle'}">${htmlEscape(loop.status)}</span></td>
                    <td>${htmlEscape(loop.iteration)}</td>
                    <td>${htmlEscape(loop.progress || 0)}%</td>
                    <td>
                        ${loop.status === 'running' ? `<button onclick="stopLoop('${htmlEscape(loop.id)}')">Stop</button>` : ''}
                    </td>
                </tr>
            `).join('');
        }

        async function fetchSessions() {
            const response = await fetch('/api/sessions');
            const sessions = await response.json();

            const tbody = document.getElementById('sessions-body');
            if (sessions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #888;">No active sessions</td></tr>';
                return;
            }

            // FIX-014: Use htmlEscape for all dynamic content
            tbody.innerHTML = sessions.map(session => `
                <tr>
                    <td>${htmlEscape(session.id)}</td>
                    <td>${htmlEscape(session.status)}</td>
                    <td>${htmlEscape(session.duration)}</td>
                    <td>${htmlEscape(session.events)}</td>
                </tr>
            `).join('');
        }

        async function fetchWorkflows() {
            const response = await fetch('/api/workflows');
            const workflows = await response.json();

            const tbody = document.getElementById('workflows-body');
            if (workflows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #888;">No active workflows</td></tr>';
                return;
            }

            // FIX-014: Use htmlEscape for all dynamic content
            tbody.innerHTML = workflows.map(wf => `
                <tr>
                    <td>${htmlEscape(wf.name)}</td>
                    <td>${htmlEscape(wf.status)}</td>
                    <td>${htmlEscape(wf.steps_completed)}/${htmlEscape(wf.total_steps)}</td>
                    <td>${htmlEscape(wf.duration)}</td>
                </tr>
            `).join('');
        }

        // FIX-014: Use htmlEscape in confirm dialog to prevent XSS
        async function stopLoop(loopId) {
            if (!confirm(`Stop loop ${htmlEscape(loopId)}?`)) return;

            try {
                await fetch(`/api/loops/${encodeURIComponent(loopId)}/stop`, { method: 'POST' });
                refreshData();
            } catch (error) {
                console.error('Error stopping loop:', error);
                alert('Failed to stop loop');
            }
        }

        // Initial load
        refreshData();
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type="text/html")

    async def _get_metrics(self, request: web.Request) -> web.Response:
        """Get system metrics.

        Args:
            request: HTTP request.

        Returns:
            JSON metrics.
        """
        # In a full implementation, this would gather real metrics
        metrics = {
            "active_sessions": len(self._metrics.get("sessions", [])),
            "loops_running": len(self._metrics.get("loops", [])),
            "api_calls": self._metrics.get("api_calls", 0),
            "uptime_seconds": self._metrics.get("uptime", 0),
        }

        return web.json_response(metrics)

    async def _get_loops(self, request: web.Request) -> web.Response:
        """Get active autonomous loops.

        Args:
            request: HTTP request.

        Returns:
            JSON loop data.
        """
        loops = self._metrics.get("loops", [])
        return web.json_response(loops)

    async def _get_sessions(self, request: web.Request) -> web.Response:
        """Get active sessions.

        Args:
            request: HTTP request.

        Returns:
            JSON session data.
        """
        sessions = self._metrics.get("sessions", [])
        return web.json_response(sessions)

    async def _get_workflows(self, request: web.Request) -> web.Response:
        """Get workflow executions.

        Args:
            request: HTTP request.

        Returns:
            JSON workflow data.
        """
        workflows = self._metrics.get("workflows", [])
        return web.json_response(workflows)

    async def _stop_loop(self, request: web.Request) -> web.Response:
        """Stop an autonomous loop.

        Args:
            request: HTTP request.

        Returns:
            JSON response.
        """
        loop_id = request.match_info["loop_id"]

        # In a full implementation, this would signal the loop to stop
        return web.json_response({"success": True, "loop_id": loop_id})

    def update_metrics(self, metrics: dict[str, Any]) -> None:
        """Update system metrics.

        Args:
            metrics: Metrics to update.
        """
        self._metrics.update(metrics)

    async def start(self) -> None:
        """Start the monitoring dashboard."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"Monitoring dashboard running on http://{self.host}:{self.port}")

        try:
            # Run forever
            await asyncio.Future()
        except asyncio.CancelledError:
            logger.info("Monitoring dashboard shutting down")
        finally:
            await runner.cleanup()


async def start_monitoring_dashboard(
    host: str = "localhost",
    port: int = 8080,
) -> MonitoringDashboard:
    """Start the monitoring dashboard in the background.

    Args:
        host: Host to bind to.
        port: Port to bind to.

    Returns:
        MonitoringDashboard instance.
    """
    dashboard = MonitoringDashboard(host, port)

    # Start in background
    asyncio.create_task(dashboard.start())

    return dashboard
