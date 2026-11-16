"""PM-INS-0009 — the inspector bridges name icon-only controls (no more «کلیک کردی روی  (pointerdown)»)."""

from pathlib import Path

from app.api.routes import render_logs as RL

ROOT = Path(__file__).resolve().parents[2]


def _sources():
    return {
        "INSPECTOR_BRIDGE_SCRIPT": RL.INSPECTOR_BRIDGE_SCRIPT,
        "INSPECTOR_BRIDGE_SCRIPT_JS": RL.INSPECTOR_BRIDGE_SCRIPT_JS,
        "INSPECTOR_BRIDGE_CLIENT_COMPONENT": RL.INSPECTOR_BRIDGE_CLIENT_COMPONENT,
        "InspectorBridge.tsx": (ROOT / "frontend/src/app/InspectorBridge.tsx").read_text(encoding="utf-8"),
    }


def test_every_bridge_climbs_from_icon_and_reads_accessible_name():
    for name, src in _sources().items():
        assert ".closest(" in src and "aria-label" in src and "svg title" in src, name
        assert "'عنصر ناشناخته'" not in src.split("function getElementInfo")[-1][:200], name


def test_tsx_bridge_accepts_svg_targets_and_skips_window_focus():
    src = _sources()["InspectorBridge.tsx"]
    assert "!(el instanceof HTMLElement)) return" not in src  # an SVG icon is an Element, not an HTMLElement
    assert "e.target instanceof Element" in src


def test_layout_menu_buttons_have_names():
    src = (ROOT / "frontend/src/components/Layout.tsx").read_text(encoding="utf-8")
    assert 'aria-label="بازکردنِ منو"' in src and 'aria-label="بستنِ منو"' in src
