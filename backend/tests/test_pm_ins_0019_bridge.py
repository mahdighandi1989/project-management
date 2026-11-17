"""PM-INS-0019 — Bridge never connected, version mismatch, request storm, model identity, agent false-positive."""
import re

from app.api.routes import render_logs as rl
from app.services import browser_agent as ba
from app.services.cloud_code_service import _build_system_blocks

URL = "wss://ai-creator-backend.onrender.com/api/render/ws/bridge/p1"


def test_injected_templates_keep_a_real_guard():
    # str.replace() at injection used to turn the guard into `WS_URL === '<url>'` (always true ⇒ never connects)
    for tpl_name in [n for n in dir(rl) if n.startswith("INSPECTOR_BRIDGE") and isinstance(getattr(rl, n), str)]:
        injected = getattr(rl, tpl_name).replace("__BRIDGE_WS_URL__", URL)
        assert not re.search(r"""WS_URL\s*===\s*['"]wss?://""", injected), tpl_name


def test_proxy_heals_old_self_guard_in_html_and_minified_js():
    html = f"const WS_URL = '{URL}'; if (!WS_URL || WS_URL === '{URL}') return;"
    out = rl._heal_bridge_self_guard(html)
    assert f"const WS_URL = '{URL}'" in out and "=== '__unset__'" in out
    js = f'const e="{URL}";if(!e||"{URL}"===e)return'
    out = rl._heal_bridge_self_guard(js)
    assert f'const e="{URL}"' in out and '"__unset__"===e' in out
    assert rl._heal_bridge_self_guard("nothing here") == "nothing here"


def test_html_bridge_version_is_read_from_html_comment():
    content = "<!-- Version: 2.5 -->\n<script>/* Inspector Bridge Script */</script>"
    m = re.search(r'(?://|<!--)\s*Version:\s*([\d.]+)', content)
    assert m and m.group(1) == rl.INSPECTOR_BRIDGE_VERSION


def test_nav_button_outside_form_is_not_a_submit():
    assert "e.type === 'submit' && (e.form || e.closest('form'))" in ba.OBSERVE_JS
    el = {"role": "button", "name": "جستجو"}
    assert ba.needs_confirmation({"type": "click", "element": el}) is None
    assert ba.needs_confirmation({"type": "click", "element": {"name": "حذف حساب"}})
    assert "Persian" in ba.SYSTEM


def test_system_blocks_carry_the_real_model_id():
    blocks = _build_system_blocks("be helpful", "claude-haiku-4-5")
    assert blocks[0]["text"].startswith("You are Claude Code")
    assert any("claude-haiku-4-5" in b["text"] for b in blocks)
    assert len(_build_system_blocks("x", "auto")) == 2
