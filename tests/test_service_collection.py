"""
Unit tests for Component 1 platform-neutral service collection and health-check logic.
Covers:
- Multi-platform URLs (Azure, Render, Oracle Cloud) handled by generic collector
- /health success acceptance
- /ping fallback when /health is unavailable (e.g. 404)
- Safe failure when both /health and /ping fail (no crash, allows background retry)
- /metrics is the only telemetry endpoint used by the collector
- Platform-neutral names & backward compatibility aliases
- Component 3 feed regression test (/api/component3/feed remains available)
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import requests
from fastapi.testclient import TestClient

import pipeline
import app


class TestServiceCollectionRefactor(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app.app)

    def test_multi_platform_service_discovery(self):
        """A configured Azure-style, Render-style, and Oracle-style URL all use the same generic collector."""
        mock_services = {
            "services": [
                {
                    "name": "azure-microservice",
                    "base_url": "https://microservice-22.canadacentral.azurecontainerapps.io",
                    "enabled": True,
                },
                {
                    "name": "render-microservice",
                    "base_url": "https://microservice-20.onrender.com",
                    "enabled": True,
                },
                {
                    "name": "oracle-microservice",
                    "base_url": "https://oracle-service.oraclecloud.com",
                    "enabled": True,
                },
            ]
        }

        with patch("json.load", return_value=mock_services), \
             patch("os.path.exists", return_value=True), \
             patch.dict(os.environ, {
                 "MONITORED_SERVICE_PAYMENT": "https://payment.internal.net",
                 "AZURE_SERVICE_ORDER": "https://order.azurewebsites.net"
             }):
            services = pipeline.load_monitored_services()
            # Backward compatibility alias
            legacy_services = pipeline.load_azure_services()

            self.assertEqual(services, legacy_services)
            self.assertIn("azure-microservice", services)
            self.assertIn("render-microservice", services)
            self.assertIn("oracle-microservice", services)
            self.assertIn("payment", services)
            self.assertIn("order-azure", services)

    def test_health_success_accepted(self):
        """When /health returns 2xx, it is accepted as healthy and /ping is not queried."""
        calls = []

        def mock_get(url, timeout=3.0):
            calls.append(url)
            resp = MagicMock()
            if url.endswith("/health"):
                resp.status_code = 200
                return resp
            resp.status_code = 404
            return resp

        with patch("requests.get", side_effect=mock_get):
            is_healthy, detail = pipeline._check_service_health("http://oracle-service:8080")
            self.assertTrue(is_healthy)
            self.assertIn("/health OK", detail)
            self.assertEqual(calls, ["http://oracle-service:8080/health"])

    def test_ping_fallback_when_health_unavailable(self):
        """When /health returns 404 or raises RequestException, /ping fallback is accepted when 2xx."""
        calls = []

        def mock_get(url, timeout=3.0):
            calls.append(url)
            resp = MagicMock()
            if url.endswith("/health"):
                resp.status_code = 404
                return resp
            if url.endswith("/ping"):
                resp.status_code = 200
                return resp
            resp.status_code = 500
            return resp

        with patch("requests.get", side_effect=mock_get):
            is_healthy, detail = pipeline._check_service_health("http://legacy-sidecar:8080")
            self.assertTrue(is_healthy)
            self.assertIn("/ping OK", detail)
            self.assertEqual(calls, [
                "http://legacy-sidecar:8080/health",
                "http://legacy-sidecar:8080/ping",
            ])

    def test_both_health_endpoints_failing_does_not_crash_discovery(self):
        """Both /health and /ping failing does not crash discovery or prevent background retry."""
        def mock_get(url, timeout=3.0):
            raise requests.ConnectionError("Connection refused")

        with patch("requests.get", side_effect=mock_get):
            is_healthy, detail = pipeline._check_service_health("http://offline-service:8080")
            self.assertFalse(is_healthy)
            self.assertIn("unreachable", detail)

    def test_metrics_is_only_telemetry_endpoint(self):
        """/metrics remains the only telemetry endpoint used by the collector (no /control during normal collection)."""
        calls = []

        def mock_get(url, timeout=(5.0, 15.0)):
            calls.append(url)
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "cpu_percent": 15.0,
                "memory_percent": 45.0,
                "memory_used_mb": 512.0,
                "gc_count": 2,
                "log_message": "healthy heartbeat",
            }
            return resp

        results_list = []
        lock = MagicMock()
        service_status = {"test-svc": True}

        # Mock time.sleep to immediately clear service_status so loop exits after first iteration
        def mock_sleep(secs):
            service_status["test-svc"] = False

        with patch("requests.get", side_effect=mock_get), \
             patch("time.sleep", side_effect=mock_sleep):
            pipeline._collect_service_metrics(
                service_name="test-svc",
                base_url="http://any-platform-service:8080",
                duration_seconds=10,
                interval_seconds=1,
                results_list=results_list,
                results_lock=lock,
                error_counter=[0],
                warning_counter=[0],
                service_status=service_status,
            )

        self.assertTrue(len(calls) > 0)
        for url in calls:
            self.assertTrue(url.endswith("/metrics"), f"Non-/metrics call detected: {url}")
            self.assertNotIn("/control", url)
            self.assertNotIn("/ping", url)
            self.assertNotIn("/health", url)

    def test_backward_compatibility_aliases_and_signatures(self):
        """Check all legacy aliases exist and point to the platform-neutral implementations."""
        # pipeline aliases
        self.assertIs(pipeline.load_azure_services, pipeline.load_monitored_services)
        self.assertIs(pipeline._collect_azure_sidecar, pipeline._collect_service_metrics)
        self.assertIs(pipeline.stage1_collect_azure_sidecar, pipeline.stage1_collect_monitored_services)
        self.assertIs(pipeline._detect_azure_stack, pipeline._detect_service_stack)

        # app aliases
        self.assertIs(app.AzureServiceInput, app.MonitoredServiceInput)
        self.assertIs(app.api_azure_services, app.api_monitored_services)
        self.assertIs(app.api_add_azure_service, app.api_add_monitored_service)
        self.assertIs(app.api_delete_azure_service, app.api_delete_monitored_service)

    def test_component3_feed_regression(self):
        """Regression test confirming /api/component3/feed remains available and returns HTTP 200."""
        resp = self.client.get("/api/component3/feed")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("windows", data)
        self.assertIn("new_windows_count", data)

        # Also confirm dual endpoints /api/monitored-services and /api/azure-services
        resp_mon = self.client.get("/api/monitored-services")
        resp_az = self.client.get("/api/azure-services")
        self.assertEqual(resp_mon.status_code, 200)
        self.assertEqual(resp_az.status_code, 200)
        self.assertEqual(resp_mon.json(), resp_az.json())


if __name__ == "__main__":
    unittest.main()
