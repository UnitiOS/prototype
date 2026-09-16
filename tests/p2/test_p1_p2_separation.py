"""tests/p2/test_p1_p2_separation.py

Verifies the strict separation between Prototype 1 (port 8000, Sorella Demo)
and Prototype 2 (port 8100, Modular Metamodel & Studio Workbench).
"""

import io

import pytest

from components.web import render, serve


def test_p1_rendering_isolation():
    """Verify that Prototype 1 does NOT contain Studio link or P2 references."""
    render.set_mode("p1", show_studio=False, brand_sub="Sorella Gelato Enterprise Demo")

    html = render.page(
        "Overview",
        "<p>Operational Data</p>",
        valid_at="2026-06-16",
        as_of="2026-06-16",
        path="/",
    )

    assert "Sorella Gelato Enterprise Demo" in html
    assert "Uniti Studio 2.0" not in html
    assert 'href="/studio' not in html

    # Also verify that home stages do not show Studio card in P1
    p1_stages = [s for s in serve.STAGES if s[2] != "/studio"]
    home_html = render.home_html(p1_stages, valid_at="2026-06-16", as_of="2026-06-16")
    assert "/studio" not in home_html
    assert "The Ontologist Workbench" not in home_html


def test_p2_rendering_features():
    """Verify that Prototype 2 displays Studio link and P2 branding."""
    render.set_mode("p2", show_studio=True, brand_sub="Prototype 2: Modular Metamodel & Studio")

    html = render.page(
        "Overview",
        "<p>Modular Metamodel</p>",
        valid_at="2026-06-16",
        as_of="2026-06-16",
        path="/",
    )

    assert "Prototype 2: Modular Metamodel" in html
    assert "Uniti Studio 2.0" in html
    assert 'href="/studio' in html

    # Verify home stages include Studio card in P2
    p2_stages = serve.STAGES
    home_html = render.home_html(p2_stages, valid_at="2026-06-16", as_of="2026-06-16")
    assert "/studio" in home_html
    assert "The Ontologist Workbench" in home_html


class DummyP1Handler(serve.Handler):
    """Dummy handler configured in P1 or P2 mode."""
    def __init__(self, path, method="GET", body=b""):
        self.path = path
        self.command = method
        self.headers = {"Content-Length": str(len(body))}
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()
        self.status = None
        self.response_headers = {}

    def send_response(self, code):
        self.status = code

    def send_header(self, k, v):
        self.response_headers[k] = v

    def end_headers(self):
        pass


def test_p1_handler_blocks_studio():
    """Verify that accessing /studio or /api/studio in P1 mode is refused."""
    render.set_mode("p1", show_studio=False, brand_sub="Sorella Gelato Enterprise Demo")

    handler = DummyP1Handler("/studio")
    handler.do_GET()
    out = handler.wfile.getvalue().decode("utf-8")
    assert handler.status == 404
    assert "Prototype 1 Isolation" in out
    assert "port 8100" in out

    # Test POST to /api/studio/patch
    post_handler = DummyP1Handler("/api/studio/patch", method="POST", body=b'{"pkg":"foo"}')
    post_handler.do_POST()
    post_out = post_handler.wfile.getvalue().decode("utf-8")
    assert post_handler.status == 403
    assert "Prototype 1 Isolation" in post_out


def test_p2_handler_allows_studio():
    """Verify that accessing /studio in P2 mode renders successfully."""
    render.set_mode("p2", show_studio=True, brand_sub="Prototype 2: Modular Metamodel & Studio")

    handler = DummyP1Handler("/studio?pkg=packages/@uniti/core")
    handler.do_GET()
    out = handler.wfile.getvalue().decode("utf-8")
    assert handler.status == 200
    assert "Socratic Ontologist Workbench" in out
    assert "packages/@uniti/core" in out
