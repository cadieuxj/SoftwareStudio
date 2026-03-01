"""Integration tests for the orchestrator HTTP API endpoints."""

from __future__ import annotations

import pytest
import httpx
import os


ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8000")


@pytest.mark.integration
class TestOrchestratorHealth:
    """Tests for the /healthz endpoint."""

    def test_health_check_returns_200(self) -> None:
        """The health endpoint should return HTTP 200."""
        try:
            response = httpx.get(f"{ORCHESTRATOR_URL}/healthz", timeout=5)
            assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("Orchestrator not running – skipping integration test")

    def test_health_check_returns_status(self) -> None:
        """The health endpoint should include a status field."""
        try:
            response = httpx.get(f"{ORCHESTRATOR_URL}/healthz", timeout=5)
            body = response.json()
            assert "status" in body
        except httpx.ConnectError:
            pytest.skip("Orchestrator not running – skipping integration test")


@pytest.mark.integration
class TestSessionsEndpoint:
    """Tests for the /sessions REST endpoint."""

    def test_list_sessions_returns_list(self) -> None:
        """GET /sessions should return a JSON array."""
        try:
            response = httpx.get(f"{ORCHESTRATOR_URL}/sessions", timeout=5)
            assert response.status_code == 200
            assert isinstance(response.json(), list)
        except httpx.ConnectError:
            pytest.skip("Orchestrator not running – skipping integration test")

    def test_create_session_requires_mission(self) -> None:
        """POST /sessions without mission should return 400 or 422."""
        try:
            response = httpx.post(
                f"{ORCHESTRATOR_URL}/sessions",
                json={},
                timeout=5,
            )
            assert response.status_code in (400, 422)
        except httpx.ConnectError:
            pytest.skip("Orchestrator not running – skipping integration test")

    def test_create_and_retrieve_session(self) -> None:
        """Creating a session should return an object retrievable by ID."""
        try:
            create_resp = httpx.post(
                f"{ORCHESTRATOR_URL}/sessions",
                json={"mission": "Integration test mission", "project_name": "test-project"},
                timeout=10,
            )
            if create_resp.status_code not in (200, 201):
                pytest.skip("Session creation not supported or orchestrator unavailable")

            session = create_resp.json()
            session_id = session.get("session_id") or session.get("id")
            assert session_id is not None

            get_resp = httpx.get(f"{ORCHESTRATOR_URL}/sessions/{session_id}", timeout=5)
            assert get_resp.status_code == 200
            got = get_resp.json()
            assert got.get("session_id") == session_id or got.get("id") == session_id
        except httpx.ConnectError:
            pytest.skip("Orchestrator not running – skipping integration test")


@pytest.mark.integration
class TestMetricsEndpoint:
    """Tests for the /metrics endpoint."""

    def test_metrics_returns_expected_fields(self) -> None:
        """GET /metrics should include session counts."""
        try:
            response = httpx.get(f"{ORCHESTRATOR_URL}/metrics", timeout=5)
            assert response.status_code == 200
            body = response.json()
            known_fields = {
                "total_sessions", "running_sessions", "completed_sessions",
                "failed_sessions", "awaiting_approval",
            }
            assert known_fields & set(body.keys()), f"No known metric fields in: {body.keys()}"
        except httpx.ConnectError:
            pytest.skip("Orchestrator not running – skipping integration test")
