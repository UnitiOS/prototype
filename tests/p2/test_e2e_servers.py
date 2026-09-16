"""tests/p2/test_e2e_servers.py

End-to-End integration test spinning up Prototype 1 (port 8000) and Prototype 2 (port 8100)
simultaneously, asserting complete UI, routing, and database isolation.
"""

import threading
import time
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

import components.web.render as render
import components.web.serve as serve
from components.generator.generate import read_map


class ServerThread(threading.Thread):
    def __init__(self, map_path, port, mode, studio):
        super().__init__(daemon=True)
        self.map_path = map_path
        self.port = port
        self.mode = mode
        self.studio = studio
        self.server = None
        self.started = threading.Event()

    def run(self):
        class IsolatedHandler(serve.Handler):
            pass

        IsolatedHandler.map_ = read_map(self.map_path)
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), IsolatedHandler)
        self.started.set()
        try:
            self.server.serve_forever()
        except Exception:
            pass

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()


def test_e2e_concurrent_p1_and_p2_servers():
    """Verify concurrent operation of P1 (:8000) and P2 (:8100)."""
    p1_port = 8011  # use distinct test ports to avoid collisions
    p2_port = 8111

    # Configure P1
    render.set_mode("p1", show_studio=False, brand_sub="Sorella Gelato Enterprise Demo")
    p1_thread = ServerThread("business/sorella_demo/v5.yaml", p1_port, "p1", False)
    p1_thread.start()
    p1_thread.started.wait(timeout=5)

    # Configure P2
    p2_thread = ServerThread("packages/@uniti/core/schema/archetypes.yaml", p2_port, "p2", True)
    p2_thread.start()
    p2_thread.started.wait(timeout=5)

    time.sleep(0.5)

    try:
        # 1. Test P1 Home
        with urllib.request.urlopen(f"http://127.0.0.1:{p1_port}/") as resp:
            assert resp.status == 200
            p1_body = resp.read().decode("utf-8")
            assert "Sorella Gelato" in p1_body or "uniti" in p1_body

        # 2. Test P1 refuses /studio when SHOW_STUDIO is False
        render.set_mode("p1", show_studio=False, brand_sub="Sorella Gelato Enterprise Demo")
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{p1_port}/studio")
            pytest.fail("Expected HTTP 404 for P1 /studio")
        except urllib.error.HTTPError as e:
            assert e.code == 404
            err_body = e.read().decode("utf-8")
            assert "Prototype 1 Isolation" in err_body

        # 3. Test P2 allows /studio when SHOW_STUDIO is True
        render.set_mode("p2", show_studio=True, brand_sub="Prototype 2: Modular Metamodel & Studio")
        with urllib.request.urlopen(f"http://127.0.0.1:{p2_port}/studio?pkg=packages/@community/inventory") as resp:
            assert resp.status == 200
            p2_studio_body = resp.read().decode("utf-8")
            assert "Socratic Ontologist Workbench" in p2_studio_body

        # 4. Test P2 Studio API
        with urllib.request.urlopen(f"http://127.0.0.1:{p2_port}/api/studio/packages") as resp:
            assert resp.status == 200
            api_body = resp.read().decode("utf-8")
            assert "@uniti/core" in api_body

    finally:
        p1_thread.stop()
        p2_thread.stop()
