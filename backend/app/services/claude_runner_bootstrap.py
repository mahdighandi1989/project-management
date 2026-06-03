# -*- coding: utf-8 -*-
"""
🤖 Claude Code Auto-Runner Bootstrapper

این سرویس برای هر پروژهٔ watched فایل workflow گیت‌هاب اکشن می‌سازد و
secret های مورد نیاز را روی ریپو نصب می‌کند. وقتی تسکی به فولدر
`prompt/` آن ریپو push شود (توسط backend sync)، GitHub Actions این
workflow را trigger می‌کند، Claude Code در حالت headless بالا می‌آید،
از API خود همین backend (`/api/external/prompts/*`) تسک‌های pending را
می‌گیرد، یکی یکی اجرا می‌کند و مستقیماً به main commit + push می‌کند.

**مزایای استفاده از API خود backend:**
- وضعیت تسک‌ها همان‌جا که هست (oversight service) به‌روز می‌شود
- workflow بعد از انجام تسک، آن را از index حذف می‌کند (job complete)
- اگر verifier تسکی را needs_rework کرد، backend دوباره آن را به index
  اضافه می‌کند و push بعدی workflow را triggers می‌کند
- هیچ مسیر دوگانه‌ای برای state management وجود ندارد

**سه secret که روی هر ریپو نصب می‌شود:**
- `CLAUDE_CODE_OAUTH_TOKEN` — توکن Claude Code برای headless execution
- `OVERSIGHT_EXTERNAL_TOKEN` — همان EXTERNAL_TOOL_TOKEN backend
- `OVERSIGHT_BACKEND_URL` — آدرس public backend (مثلاً Render URL)

**فایل workflow که نصب می‌شود:**
مسیر: `.github/workflows/claude-auto-task.yml`
trigger: تغییر در `prompt/_index.json` یا `prompt/**.md`
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Any, Dict, Optional, Tuple

from .github_pr_service import get_github_pr_service
from .prompt_github_sync import _resolve_repo_and_branch, _commit_message

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

WORKFLOW_PATH = ".github/workflows/claude-auto-task.yml"

SECRET_OAUTH = "CLAUDE_CODE_OAUTH_TOKEN"
SECRET_EXTERNAL = "OVERSIGHT_EXTERNAL_TOKEN"
SECRET_BACKEND_URL = "OVERSIGHT_BACKEND_URL"

# Master prompt که Claude در هر run می‌بیند — این جای پرامپت تک‌خطی است
# که قبلاً کاربر دستی کپی می‌کرد. شامل ضد-فرار TO-DO، اجبار به push به
# main، عدم batching، و قاعدهٔ iteration کامل per-task.
# Master prompt که Claude در هر run می‌بیند. **یک تسک per run** strategy:
# هر workflow run یک تسک را برمی‌دارد، اجرا می‌کند، complete می‌کند، و exit
# می‌کند. backend بعد از /complete دوباره workflow_dispatch می‌زند اگر تسک
# pending دیگری باقی مانده. این جلوی hitting max-turns را می‌گیرد و هزینهٔ
# هر run را قابل‌پیش‌بینی می‌کند ($0.30-0.80 بسته به اندازهٔ تسک).
MASTER_PROMPT = (
    "وظیفه‌ات: **فقط یک تسک** را اجرا کن سپس exit کن.\n"
    "\n"
    "## نکتهٔ بسیار مهم درباره curl ها\n"
    "\n"
    "**همهٔ** فراخوانی‌های backend (claim/complete/fail) باید این flags داشته باشند:\n"
    "  `-fsS --max-time 180 --retry 5 --retry-delay 8 --retry-all-errors -w \"\\nHTTP:%{http_code}\\n\"`\n"
    "بعد از هر curl، **حتماً** HTTP status را چک کن. اگر 2xx نبود، با /fail\n"
    "گزارش بده و سپس **`exit 1`** بزن. هرگز با curl ناموفق exit موفق نکن.\n"
    "(دلیل: backend ممکن است روی Render free tier از sleep بیدار شود — تا\n"
    "۶۰ ثانیه طول می‌کشد. --max-time و --retry برای این طراحی شده.)\n"
    "\n"
    "## مرحله ۱ — تعیین task_id\n"
    "\n"
    "**اگر $TARGET_TASK_ID خالی نیست** (یعنی backend در حال retry روی یک تسک\n"
    "خاص است): همان task_id را استفاده کن. برو مستقیم به مرحله ۲ (هنوز باید\n"
    "/claim بزنی).\n"
    "\n"
    "**اگر $TARGET_TASK_ID خالی است** (chain-next نرمال): لیست را بگیر:\n"
    "\n"
    "```bash\n"
    "curl -fsS --max-time 180 --retry 5 --retry-delay 8 --retry-all-errors \\\n"
    "  -H \"X-External-Token: $OVERSIGHT_EXTERNAL_TOKEN\" \\\n"
    "  -w \"\\nHTTP:%{http_code}\\n\" \\\n"
    "  \"$OVERSIGHT_BACKEND_URL/api/external/prompts/next?watched_id=$WATCHED_ID&limit=1\" \\\n"
    "  -o /tmp/next.json || { echo 'next failed'; exit 1; }\n"
    "```\n"
    "\n"
    "اولین task_id را از /tmp/next.json بردار. اگر لیست خالی است → \n"
    "`echo 'no pending tasks'` و **موفق exit** کن (exit 0).\n"
    "\n"
    "## مرحله ۲ — claim کن (الزامی — حتی با TARGET_TASK_ID)\n"
    "\n"
    "```bash\n"
    "HTTP_CODE=$(curl -fsS --max-time 180 --retry 5 --retry-delay 8 --retry-all-errors \\\n"
    "  -X POST -H \"X-External-Token: $OVERSIGHT_EXTERNAL_TOKEN\" \\\n"
    "  -H \"Content-Type: application/json\" \\\n"
    "  -d '{\"agent_id\":\"claude-code-action\"}' \\\n"
    "  -w \"%{http_code}\" -o /tmp/claim.json \\\n"
    "  \"$OVERSIGHT_BACKEND_URL/api/external/prompts/<task_id>/claim\") || \\\n"
    "  { echo 'claim curl failed'; exit 1; }\n"
    "if [ \"$HTTP_CODE\" = \"409\" ]; then echo 'already claimed — exit'; exit 0; fi\n"
    "if [ \"$HTTP_CODE\" != \"200\" ]; then echo \"claim failed HTTP=$HTTP_CODE\"; cat /tmp/claim.json; exit 1; fi\n"
    "```\n"
    "\n"
    "## مرحله ۳ — فایل تسک را کامل بخوان\n"
    "\n"
    "`cat prompt/<task_id>.md` (نه head/tail/sed). محتوا = پرامپت + AC + Steps.\n"
    "\n"
    "## مرحله ۴ — کار را انجام بده\n"
    "\n"
    "هر AC را پیاده‌سازی کن. کد را با Edit/Write بنویس، تست کن.\n"
    "\n"
    "## مرحله ۵ — commit و push مستقیم به main\n"
    "\n"
    "```bash\n"
    "git add -A\n"
    "git commit -m \"[<task_id>] <خلاصهٔ کوتاه>\" || echo 'no changes'\n"
    "git push origin main || { git pull --rebase origin main && git push origin main; } || exit 1\n"
    "```\n"
    "\n"
    "هرگز PR نزن. هرگز branch جدا نساز. مستقیم به main.\n"
    "\n"
    "## مرحله ۶ — complete اعلام کن (حیاتی — اگر اینجا fail شود، تسک معلق می‌ماند)\n"
    "\n"
    "```bash\n"
    "HTTP_CODE=$(curl -fsS --max-time 180 --retry 5 --retry-delay 8 --retry-all-errors \\\n"
    "  -X POST -H \"X-External-Token: $OVERSIGHT_EXTERNAL_TOKEN\" \\\n"
    "  -H \"Content-Type: application/json\" \\\n"
    "  -d '{\"agent_id\":\"claude-code-action\",\"summary\":\"<چه کاری شد>\"}' \\\n"
    "  -w \"%{http_code}\" -o /tmp/complete.json \\\n"
    "  \"$OVERSIGHT_BACKEND_URL/api/external/prompts/<task_id>/complete\") || \\\n"
    "  { echo 'complete curl FAILED — task will be stuck'; exit 1; }\n"
    "if [ \"$HTTP_CODE\" != \"200\" ]; then\n"
    "  echo \"complete returned HTTP=$HTTP_CODE\"; cat /tmp/complete.json\n"
    "  # backend ممکن است claim mismatch داشته باشد — قبل از exit، fail بزن\n"
    "  curl -fsS --max-time 60 --retry 3 -X POST \\\n"
    "    -H \"X-External-Token: $OVERSIGHT_EXTERNAL_TOKEN\" \\\n"
    "    -H \"Content-Type: application/json\" \\\n"
    "    -d \"{\\\"agent_id\\\":\\\"claude-code-action\\\",\\\"error\\\":\\\"complete returned HTTP=$HTTP_CODE\\\"}\" \\\n"
    "    \"$OVERSIGHT_BACKEND_URL/api/external/prompts/<task_id>/fail\" || true\n"
    "  exit 1\n"
    "fi\n"
    "echo 'complete OK — exit'\n"
    "```\n"
    "\n"
    "سپس exit 0. (backend پس از /complete موفق، verify-after-complete را اجرا\n"
    "می‌کند و سپس برای تسک بعدی workflow را دوباره trigger می‌کند.)\n"
    "\n"
    "## در صورت شکست در هر مرحلهٔ کار\n"
    "\n"
    "```bash\n"
    "curl -fsS --max-time 180 --retry 5 --retry-delay 8 --retry-all-errors \\\n"
    "  -X POST -H \"X-External-Token: $OVERSIGHT_EXTERNAL_TOKEN\" \\\n"
    "  -H \"Content-Type: application/json\" \\\n"
    "  -d '{\"agent_id\":\"claude-code-action\",\"error\":\"<reason>\"}' \\\n"
    "  \"$OVERSIGHT_BACKEND_URL/api/external/prompts/<task_id>/fail\" || true\n"
    "exit 1\n"
    "```\n"
    "\n"
    "## قواعد کلیدی\n"
    "\n"
    "- TO-DO فقط برای: credential کاربر، تصمیم سلیقه‌ای کاربر، account/billing\n"
    "  سرویس خارجی. هرگز برای UI، endpoint، migration، test، integration\n"
    "  (با stub بساز).\n"
    "- اگر تسک نیاز به credential دارد → /fail با reason \"needs user credential\".\n"
    "- مستقیم به main commit و push (no PR، no branch).\n"
    "- فقط **یک تسک** را در این run اجرا کن، سپس exit. هرگز loop نکن.\n"
    "- **هرگز exit 0 بدون /complete موفق نکن.** اگر /complete fail شد → exit 1.\n"
    "\n"
    "## ⏰ بودجهٔ turn\n"
    "\n"
    "max-turns = **250** (فضای کافی برای بزرگترین تسک‌ها). از تمام بودجه\n"
    "استفاده کن تا تسک را **کامل و درست** تمام کنی. هرگز عجله نکن، هرگز\n"
    "AC را skip نکن.\n"
    "\n"
    "**فقط در حالت اضطراری** (اگر بعد از ~220 turn هنوز کار تمام نشده،\n"
    "یعنی تسک واقعاً غیرعادی بزرگ است):\n"
    "1. commit + push آنچه تا الان انجام شده\n"
    "2. POST /fail با reason \"task too large: completed N of M ACs\"\n"
    "3. exit 1\n"
    "\n"
    "این فقط emergency است. برای تسک عادی، از همه بودجه استفاده کن تا\n"
    "complete واقعی بزنی.\n"
)


# ----------------------------------------------------------------------
# Workflow YAML builder
# ----------------------------------------------------------------------

def build_workflow_yaml(
    *,
    watched_id: str,
    repo_full_name: str,
    branch: str = "main",
    claude_args: str = (
        # 🆕 (dynamic model selection) — مدل به‌صورت ${{ inputs.claude_model }}
        # در workflow ذکر می‌شود تا backend در زمان dispatch، آخرین Opus/Sonnet/
        # Haiku را بر اساس نوع تسک بفرستد. اگر input ندهد (مثل trigger دستی از
        # GitHub UI)، fallback به alias `sonnet` که خود Claude Code CLI آن را
        # به آخرین Sonnet موجود route می‌کند — هیچ model id ثابتی هاردکد نیست.
        "--max-turns 250 --model "
        "${{ github.event.inputs.claude_model || 'sonnet' }} "
        "--dangerously-skip-permissions"
    ),
) -> str:
    """ساخت محتوای فایل YAML برای workflow.

    `watched_id` در workflow embed می‌شود تا backend بداند تسک‌های کدام
    watched را برگرداند (در صورت چند ریپو متصل به یک backend).
    """
    # YAML literal block scalar (`|`) برای master prompt — newlineها حفظ
    # می‌شوند. هر خط با ۱۲ فاصله indent (دو سطح زیر `prompt:`).
    master_prompt_lines = MASTER_PROMPT.splitlines()
    indented_prompt = "\n".join(f"            {line}" for line in master_prompt_lines)

    yaml = f"""# 🤖 Claude Auto Task Runner (auto-generated by oversight backend)
#
# این فایل خودکار توسط پنل oversight روی این ریپو نصب شده است.
# هرگاه تسکی به فولدر prompt/ این ریپو push شود (توسط backend sync یا
# دستی)، GitHub Actions این workflow را trigger می‌کند و Claude Code
# تسک‌های pending را به ترتیب اولویت اجرا می‌کند.
#
# برای غیرفعال کردن: از پنل oversight روی این پروژه، toggle «اجرای
# خودکار با Claude Code» را خاموش کنید — این فایل خودکار حذف می‌شود.
# (یا این فایل را manually delete کنید.)

name: Claude Auto Task Runner

# 'on' را به‌صورت string quote می‌کنیم چون در YAML 1.1، on/off/yes/no
# مقدار boolean هستند. GitHub Actions هر دو فرم را می‌پذیرد ولی این
# فرم با همهٔ YAML parserها سازگار است.
"on":
  # claude-code-action@v1 روی push event کار نمی‌کند
  # ("Unsupported event type: push"). فقط workflow_dispatch پشتیبانی
  # می‌شود. backend پس از push شدن تسک به prompt/_index.json، خودکار
  # workflow را با GitHub API trigger می‌زند (dispatches endpoint).
  #
  # 🆕 (target_task_id) — اگر backend در حال retry روی یک تسک خاص است
  # (بعد از verify=partial)، task_id را در inputs می‌گذارد تا Claude
  # **همان** تسک را بگیرد، نه /next.
  workflow_dispatch:
    inputs:
      target_task_id:
        description: 'task_id خاص برای اجرا (اختیاری). اگر خالی، از /next گرفته می‌شود.'
        required: false
        type: string
      # 🆕 (dynamic model) — backend در زمان dispatch، آخرین مدل Opus/Sonnet/
      # Haiku را بر اساس tier تشخیص داده‌شده از prompt تسک می‌فرستد. این
      # یعنی هرگاه Anthropic مدل جدید بدهد (مثلاً claude-opus-5-0-...)، حداکثر
      # ۱ ساعت بعد (cache /v1/models) خودکار استفاده می‌شود — بدون redeploy و
      # بدون refresh YAML. اگر input خالی باشد (مثل dispatch دستی از GitHub
      # UI بدون پر کردن این فیلد)، fallback به alias `sonnet` که Claude Code
      # CLI خودش به آخرین Sonnet route می‌کند.
      claude_model:
        description: 'model id کامل یا alias (opus/sonnet/haiku). اگر خالی → sonnet.'
        required: false
        type: string
        default: ''

# 🛡 (concurrency strategy) — cancel-in-progress: false
# قبلاً true بود ولی یافتیم که runهای در حال اجرا را مید-اجرا cancel
# می‌کرد (Run #10 بعد از ۳ دقیقه اجرای واقعی، توسط Run #11 قطع شد).
#
# با false:
#   - in-progress run ادامه می‌دهد تا کاملاً تمام شود (Claude زمان دارد)
#   - queued runs اگر newer بیاید، جایگزین می‌شوند (فقط آخرین queued می‌ماند)
#
# combined با debounce 60s در backend و content-diff check، تعداد trigger
# های بی‌فایده به حداقل می‌رسد، پس setup-then-cancel نخواهیم داشت.
concurrency:
  group: claude-auto-task-{watched_id}
  cancel-in-progress: false

jobs:
  run-task:
    runs-on: ubuntu-latest
    # ⏰ کافی برای بزرگ‌ترین تسک‌ها (max-turns 250 × ~5 sec/turn = ~21 min
    # + setup + overhead). 90 دقیقه buffer امن دارد.
    timeout-minutes: 90
    permissions:
      contents: write       # برای commit + push به main
      pull-requests: write  # ذخیره برای آینده (الان استفاده نمی‌کنیم)
      id-token: write       # احیاناً برای OIDC در آینده
    steps:
      - name: Checkout (full history برای push کردن)
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          # token پیش‌فرض ACTIONS_GITHUB_TOKEN است — برای push کفایت می‌کند.
          # برای جلوگیری از infinite loop، commit messages ما حاوی
          # [skip ci] خواهد بود تا re-trigger نشوند.

      - name: Run Claude Code (headless)
        uses: anthropics/claude-code-action@v1
        with:
          claude_code_oauth_token: ${{{{ secrets.{SECRET_OAUTH} }}}}
          claude_args: "{claude_args}"
          prompt: |
{indented_prompt}
        env:
          OVERSIGHT_BACKEND_URL: ${{{{ secrets.{SECRET_BACKEND_URL} }}}}
          OVERSIGHT_EXTERNAL_TOKEN: ${{{{ secrets.{SECRET_EXTERNAL} }}}}
          WATCHED_ID: "{watched_id}"
          REPO_FULL_NAME: "{repo_full_name}"
          # 🆕 (target_task_id) — اگر backend در حال retry روی یک تسک خاص است
          # (بعد از verify=partial)، این مقدار task_id را به master prompt
          # می‌رساند تا Claude همان تسک را بگیرد به‌جای صدا زدن /next.
          # وقتی خالی است (chain-next نرمال)، Claude از /next استفاده می‌کند.
          TARGET_TASK_ID: ${{{{ github.event.inputs.target_task_id }}}}
"""
    return yaml


# ----------------------------------------------------------------------
# GitHub Secrets API (encrypted with libsodium sealed-box)
# ----------------------------------------------------------------------

async def _get_repo_public_key(
    owner: str, repo: str, *, gh_token: str,
) -> Optional[Dict[str, str]]:
    """گرفتن public key ریپو برای رمزگذاری secrets.

    Returns: {"key": str, "key_id": str} یا None در صورت خطا.
    """
    pr = get_github_pr_service()
    session = await pr._get_session()  # noqa: SLF001 (intentional reuse)
    url = f"{pr.GITHUB_API}/repos/{owner}/{repo}/actions/secrets/public-key"
    headers = pr._get_headers(token=gh_token)  # noqa: SLF001
    res = await pr._gh_request("GET", url, headers=headers)  # noqa: SLF001
    if not res.get("ok"):
        logger.warning(
            f"get_repo_public_key: {owner}/{repo} status={res.get('status')} "
            f"body={(res.get('body_text') or '')[:200]}"
        )
        return None
    body = res.get("body_json") or {}
    if not body.get("key") or not body.get("key_id"):
        return None
    return {"key": body["key"], "key_id": body["key_id"]}


def _encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    """رمزگذاری secret با sealed-box libsodium.

    GitHub Secrets API دقیقاً همین فرمت را می‌خواهد (base64-encoded
    sealed_box encryption of UTF-8 bytes با public key ریپو).
    """
    from nacl.public import PublicKey, SealedBox
    from nacl.encoding import Base64Encoder

    pk = PublicKey(public_key_b64.encode("utf-8"), encoder=Base64Encoder)
    sealed = SealedBox(pk).encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(sealed).decode("utf-8")


async def set_repo_secret(
    owner: str, repo: str, name: str, value: str, *, gh_token: str,
) -> Dict[str, Any]:
    """ست/آپدیت یک Actions secret روی ریپو.

    Returns: {"success": bool, "error": str}
    """
    pk = await _get_repo_public_key(owner, repo, gh_token=gh_token)
    if not pk:
        return {"success": False, "error": "could_not_fetch_public_key"}
    try:
        encrypted = _encrypt_secret(pk["key"], value)
    except Exception as e:
        return {"success": False, "error": f"encryption_failed: {e}"}

    pr = get_github_pr_service()
    url = f"{pr.GITHUB_API}/repos/{owner}/{repo}/actions/secrets/{name}"
    headers = pr._get_headers(token=gh_token)  # noqa: SLF001
    body = {"encrypted_value": encrypted, "key_id": pk["key_id"]}
    res = await pr._gh_request("PUT", url, headers=headers, json_body=body)  # noqa: SLF001
    if not res.get("ok"):
        return {
            "success": False,
            "error": (
                f"secret_put_failed status={res.get('status')} "
                f"body={(res.get('body_text') or '')[:200]}"
            ),
        }
    return {"success": True}


async def delete_repo_secret(
    owner: str, repo: str, name: str, *, gh_token: str,
) -> Dict[str, Any]:
    """حذف یک Actions secret. اگر وجود نداشته باشد، موفق محسوب می‌شود."""
    pr = get_github_pr_service()
    url = f"{pr.GITHUB_API}/repos/{owner}/{repo}/actions/secrets/{name}"
    headers = pr._get_headers(token=gh_token)  # noqa: SLF001
    res = await pr._gh_request("DELETE", url, headers=headers)  # noqa: SLF001
    status = res.get("status")
    if status in (204, 404):
        return {"success": True}
    return {
        "success": False,
        "error": (
            f"secret_delete_failed status={status} "
            f"body={(res.get('body_text') or '')[:200]}"
        ),
    }


# ----------------------------------------------------------------------
# workflow_dispatch trigger — backend از این برای آغاز run استفاده می‌کند
# ----------------------------------------------------------------------

async def pick_model_for_task(task: Any) -> Optional[str]:
    """انتخاب آخرین مدل Claude متناسب با محتوای تسک.

    منطق: prompt تسک + raw_idea + title را به‌عنوان "پیام کاربر" به
    cloud_code_service.pick_best_model می‌دهیم. همان classifier ای که برای
    چت بازرس ویژه (Cloud Code engine) ساخته‌ایم: کلمات سنگین (refactor /
    architecture / security / معماری / بازنویسی / ...) → آخرین Opus،
    پرامپت‌های ساده/کوتاه → Haiku، بقیه → Sonnet. در هر tier جدیدترین
    revision از /v1/models (cache یک‌ساعته) برنده است، پس اگر Anthropic
    فردا Opus 5 بدهد، حداکثر ۱ ساعت بعد خودکار استفاده می‌شود.

    Returns: model id (e.g., "claude-opus-4-5-20251101") یا None اگر
    OAuth token نباشد. None یعنی workflow از default خودش (alias `sonnet`)
    استفاده می‌کند که Claude Code CLI آن را به آخرین Sonnet route می‌کند.
    """
    try:
        from .cloud_code_service import cloud_code_is_configured, pick_best_model
    except Exception as e:
        logger.debug(f"pick_model_for_task: cloud_code import failed: {e}")
        return None
    if not cloud_code_is_configured():
        return None
    parts = []
    title = (getattr(task, "title", "") or "").strip()
    raw_idea = (getattr(task, "raw_idea", "") or "").strip()
    prompt_text = (getattr(task, "prompt", "") or "").strip()
    if title:
        parts.append(title)
    if raw_idea and raw_idea != title:
        parts.append(raw_idea)
    if prompt_text:
        parts.append(prompt_text[:6000])  # cap classifier input
    combined = "\n\n".join(parts).strip()
    if not combined:
        return None
    try:
        model_id, tier, reason = await pick_best_model(
            [{"role": "user", "content": combined}],
        )
        logger.info(
            f"pick_model_for_task: task={getattr(task, 'id', '?')} → "
            f"{tier}/{model_id} ({reason})"
        )
        return model_id
    except Exception as e:
        logger.warning(f"pick_model_for_task failed for {getattr(task, 'id', '?')}: {e}")
        return None


async def trigger_workflow_dispatch(
    watched: Any,
    *,
    gh_token: str,
    ref: str = "main",
    target_task_id: Optional[str] = None,
    force: bool = False,
    claude_model: Optional[str] = None,
) -> Dict[str, Any]:
    """trigger دستی workflow Claude Auto-Runner از طریق GitHub API.

    این تابع از سوی backend بعد از push موفق `prompt/_index.json` صدا
    زده می‌شود تا workflow اجرا شود (چون trigger روی push کار نمی‌کند).

    target_task_id: اگر داده شود، در workflow inputs پاس داده می‌شود تا
    Claude همان task_id را اجرا کند (به‌جای /next). برای retry بعد از
    verify=partial و trigger دستی تک‌تسک استفاده می‌شود.

    force: اگر True باشد، چک claude_runner_enabled رد می‌شود.
    برای trigger دستی تک‌تسک از UI/Telegram استفاده می‌شود — کاربر می‌خواهد
    فقط همین یک تسک اجرا شود حتی اگر auto-runner برای پروژه روشن نباشد.
    در این حالت workflow YAML باید قبلاً در repo نصب شده باشد (وگرنه 404).

    Returns:
      {"success": bool, "error": str, "skipped": bool}
      skipped=True اگر runner enabled نباشد یا workflow نصب نشده باشد.
    """
    # فقط اگر runner برای این watched نصب شده، trigger بزن
    # (مگر force=True که برای trigger دستی تک‌تسک استفاده می‌شود)
    if not force and not getattr(watched, "claude_runner_enabled", False):
        return {"success": True, "skipped": True, "reason": "runner_not_enabled"}
    # برای force trigger، حداقل workflow_path باید ست باشد (نصب قبلی)
    if force and not getattr(watched, "claude_runner_workflow_path", None):
        return {
            "success": False,
            "error": "workflow_not_installed — ابتدا runner را روی پروژه نصب کنید",
        }

    # 🔒 (verify-after-complete lock) — اگر یک تسک در حال verify است،
    # نباید workflow جدید trigger کنیم. این focus را روی تسک فعلی نگه
    # می‌دارد حتی اگر فولدر prompt/ تغییر کند (تسک جدید، sync، …).
    try:
        from .oversight_service import get_oversight_service
        _ovs = get_oversight_service()
        if _ovs.is_watched_verify_locked(getattr(watched, "id", "")):
            locked_task = getattr(watched, "claude_runner_verifying_task_id", "?")
            logger.info(
                f"trigger_workflow_dispatch: skipping for {getattr(watched, 'repo_full_name', '?')} "
                f"— verify-after-complete lock active (task {locked_task})"
            )
            return {
                "success": True,
                "skipped": True,
                "reason": "verify_in_progress",
                "locked_task_id": locked_task,
            }
    except Exception as _lock_e:
        logger.debug(f"verify-lock check failed (proceeding): {_lock_e}")

    resolved = _resolve_repo_and_branch(watched)
    if not resolved:
        return {"success": False, "error": "repo_not_resolvable"}
    owner, repo, branch = resolved
    use_ref = ref or branch or "main"

    pr = get_github_pr_service()
    workflow_filename = WORKFLOW_PATH.split("/")[-1]
    url = (
        f"{pr.GITHUB_API}/repos/{owner}/{repo}/actions/workflows/"
        f"{workflow_filename}/dispatches"
    )
    headers = pr._get_headers(token=gh_token)  # noqa: SLF001
    body: Dict[str, Any] = {"ref": use_ref}
    inputs: Dict[str, str] = {}
    if target_task_id:
        inputs["target_task_id"] = str(target_task_id)
    if claude_model:
        inputs["claude_model"] = str(claude_model)
    if inputs:
        body["inputs"] = inputs
    res = await pr._gh_request("POST", url, headers=headers, json_body=body)  # noqa: SLF001
    status = res.get("status")
    body_text = (res.get("body_text") or "")
    # 204 No Content = موفقیت. 404 = workflow هنوز روی GitHub index نشده
    # (تازه نصب شد و چند ثانیه طول می‌کشد قابل dispatch شود).
    if status == 204:
        return {"success": True}
    if status == 404:
        return {
            "success": False,
            "error": "workflow_not_indexed_yet (try again in a few seconds)",
            "transient": True,
        }
    # 422 با پیام "Unexpected inputs" یعنی YAML قدیمی است و input تازه‌ای
    # (target_task_id یا claude_model) را declare نکرده. retry با حذف input
    # ناشناخته. اگر فقط claude_model مشکل‌ساز است، با target_task_id بمانیم.
    has_unexpected = (
        status == 422
        and inputs
        and ("unexpected inputs" in body_text.lower() or "no input" in body_text.lower())
    )
    if has_unexpected:
        # تشخیص دقیق: کدام input ناشناخته است؟
        body_lower = body_text.lower()
        cm_unknown = "claude_model" in body_lower
        tt_unknown = "target_task_id" in body_lower

        # تلاش با حذف input ناشناخته (نه همه)
        retry_inputs: Dict[str, str] = {}
        if not tt_unknown and target_task_id:
            retry_inputs["target_task_id"] = str(target_task_id)
        if not cm_unknown and claude_model:
            retry_inputs["claude_model"] = str(claude_model)

        body2: Dict[str, Any] = {"ref": use_ref}
        if retry_inputs:
            body2["inputs"] = retry_inputs

        logger.warning(
            f"trigger_workflow_dispatch: workflow YAML قدیمی برای {owner}/{repo} "
            f"— retry با حذف unknown inputs "
            f"(cm_unknown={cm_unknown}, tt_unknown={tt_unknown})"
        )
        res2 = await pr._gh_request("POST", url, headers=headers, json_body=body2)  # noqa: SLF001
        status2 = res2.get("status")
        if status2 == 204:
            warnings = []
            if cm_unknown and claude_model:
                warnings.append(
                    "workflow YAML قدیمی است و claude_model input ندارد — "
                    "Claude مدل YAML را استفاده می‌کند (نه آنچه backend انتخاب کرد). "
                    "برای رفع، runner را refresh کنید."
                )
            if tt_unknown and target_task_id:
                warnings.append(
                    "workflow YAML قدیمی است و target_task_id input ندارد — "
                    "Claude /next می‌زند نه تسک خاص. برای رفع، runner را refresh کنید."
                )
            return {
                "success": True,
                "outdated_workflow": True,
                "warning": " | ".join(warnings) if warnings else (
                    "workflow YAML قدیمی است — لطفاً refresh کنید."
                ),
            }
        # حتی retry هم شکست خورد — همان خطای اولیه را برگردانیم
    return {
        "success": False,
        "error": (
            f"dispatch_failed status={status} "
            f"body={body_text[:200]}"
        ),
    }


# ----------------------------------------------------------------------
# GitHub Actions repo-level permissions (workflow can write to repo)
# ----------------------------------------------------------------------

async def set_workflow_permissions_write(
    owner: str, repo: str, *, gh_token: str,
) -> Dict[str, Any]:
    """تنظیم default workflow permissions روی «Read and write».

    بدون این تنظیم، GitHub جوب‌های workflow که در YAML
    `permissions: contents: write` می‌خواهند را روی وضعیت Pending قفل
    می‌کند و هرگز شروع نمی‌شوند (چون سطح permission ای که می‌خواهند از
    سقف repo بالاتر است).

    پیش‌فرض GitHub برای repo های جدید (از Feb 2023) «Read only» است،
    پس هر repo که توگل runner را روشن می‌کند باید این تنظیم را به
    write تغییر دهیم. این endpoint با همان GitHub PAT کلاسیک با scope
    `repo` کار می‌کند (admin روی repo شخصی خودکار).

    همچنین `can_approve_pull_request_reviews=true` تنظیم می‌شود تا
    Claude در صورت نیاز بتواند PR را approve کند (تأثیر مستقیم روی push
    به main ندارد ولی برای completeness).
    """
    pr = get_github_pr_service()
    url = (
        f"{pr.GITHUB_API}/repos/{owner}/{repo}/actions/permissions/workflow"
    )
    headers = pr._get_headers(token=gh_token)  # noqa: SLF001
    body = {
        "default_workflow_permissions": "write",
        "can_approve_pull_request_reviews": True,
    }
    res = await pr._gh_request("PUT", url, headers=headers, json_body=body)  # noqa: SLF001
    if not res.get("ok"):
        return {
            "success": False,
            "error": (
                f"workflow_permissions_failed status={res.get('status')} "
                f"body={(res.get('body_text') or '')[:200]}"
            ),
        }
    return {"success": True}


# ----------------------------------------------------------------------
# High-level: install / uninstall runner
# ----------------------------------------------------------------------

async def install_runner(
    watched: Any,
    *,
    gh_token: str,
    oauth_token: str,
    external_token: str,
    backend_url: str,
    claude_args: Optional[str] = None,
) -> Dict[str, Any]:
    """نصب workflow + سه secret روی ریپوی watched.

    Args:
      watched: WatchedProject instance
      gh_token: توکن GitHub با scope `repo` + `workflow` + `secrets`
      oauth_token: CLAUDE_CODE_OAUTH_TOKEN از خود کاربر (یا env سرور)
      external_token: مقدار EXTERNAL_TOOL_TOKEN که backend می‌پذیرد
      backend_url: آدرس public backend (مثل https://api.example.com)
      claude_args: آرگومان‌های CLI به Claude Code action

    Returns:
      {
        "success": bool,
        "workflow_path": str,
        "errors": [str, ...],  # اگر بخش‌هایی fail شده
      }
    """
    resolved = _resolve_repo_and_branch(watched)
    if not resolved:
        return {
            "success": False,
            "errors": ["repo_not_resolvable_or_sync_disabled"],
        }
    owner, repo, branch = resolved
    errors: list = []

    # 0) Workflow permissions repo را روی «Read and write» بگذار.
    # بدون این، GitHub جوب‌هایی که permissions: contents: write می‌خواهند را
    # روی Pending قفل می‌کند و هرگز شروع نمی‌شوند. این تنظیم پیش‌فرض
    # GitHub برای repo های جدید Read only است، پس برای هر repo که
    # runner را نصب می‌کنیم باید این را به write تغییر دهیم. اگر شکست
    # خورد، ادامه می‌دهیم (کاربر می‌تواند دستی هم تنظیم کند) ولی هشدار
    # واضح در errors می‌گذاریم.
    perm_res = await set_workflow_permissions_write(
        owner, repo, gh_token=gh_token,
    )
    if not perm_res.get("success"):
        errors.append(f"workflow_permissions: {perm_res.get('error')}")

    # 1) سه secret را نصب کن
    for secret_name, secret_value in (
        (SECRET_OAUTH, oauth_token),
        (SECRET_EXTERNAL, external_token),
        (SECRET_BACKEND_URL, backend_url),
    ):
        if not secret_value:
            errors.append(f"{secret_name}: empty value, skipped")
            continue
        res = await set_repo_secret(
            owner, repo, secret_name, secret_value, gh_token=gh_token,
        )
        if not res.get("success"):
            errors.append(f"{secret_name}: {res.get('error')}")

    # 2) workflow file را push کن (حتی اگر secret ها fail شدند، تا کاربر
    # ببیند چه خبر است. اگر workflow بدون secret اجرا شود، fail می‌کند
    # ولی این بهتر از نصب نکردن است.)
    # claude_args=None → از default داینامیک build_workflow_yaml استفاده می‌کند
    # (--model ${{ inputs.claude_model || 'sonnet' }}). هیچ model id ثابتی
    # هاردکد نمی‌شود — backend در زمان dispatch، آخرین مدل tier درست را
    # می‌فرستد. caller می‌تواند با پاس‌دادن claude_args دستی، override کند.
    _build_kwargs: Dict[str, Any] = {
        "watched_id": watched.id,
        "repo_full_name": watched.repo_full_name,
        "branch": branch,
    }
    if claude_args is not None:
        _build_kwargs["claude_args"] = claude_args
    yaml_content = build_workflow_yaml(**_build_kwargs)
    pr = get_github_pr_service()
    upsert = await pr.create_or_update_file(
        owner=owner,
        repo=repo,
        path=WORKFLOW_PATH,
        content=yaml_content,
        message=_commit_message(
            "install Claude auto-runner",
            details=f"watched={watched.id}",
        ),
        branch=branch,
        token=gh_token,
    )
    if not upsert.get("success"):
        # 🛡 تشخیص دقیق علت 403/422 برای راهنمایی کاربر
        err_text = str(upsert.get("error") or "")
        if (
            "refusing to allow" in err_text.lower()
            or "workflow" in err_text.lower()
            or "without `workflow`" in err_text
            or "403" in err_text
        ):
            errors.append(
                "workflow_push_failed: GitHub توکن شما اجازهٔ نوشتن در "
                ".github/workflows/ ندارد. توکن باید scope `workflow` "
                "داشته باشد (یا fine-grained PAT با اجازهٔ 'Workflows: "
                "write'). توکن را تنظیم مجدد کنید و دوباره تلاش کنید."
            )
        else:
            errors.append(f"workflow_push_failed: {err_text}")

    return {
        "success": len(errors) == 0,
        "workflow_path": WORKFLOW_PATH,
        "errors": errors,
    }


async def uninstall_runner(
    watched: Any, *, gh_token: str,
) -> Dict[str, Any]:
    """حذف workflow file + سه secret از ریپو.

    Returns: {"success": bool, "errors": [str, ...]}
    """
    resolved = _resolve_repo_and_branch(watched)
    if not resolved:
        return {"success": False, "errors": ["repo_not_resolvable"]}
    owner, repo, branch = resolved
    errors: list = []

    # 1) حذف workflow file (اگر موجود نباشد، not_found OK)
    pr = get_github_pr_service()
    # get sha اول
    file_info = await pr.get_file_content(
        owner=owner, repo=repo, path=WORKFLOW_PATH,
        branch=branch, token=gh_token,
    )
    if file_info.get("success") and file_info.get("sha"):
        del_res = await pr.delete_file(
            owner=owner,
            repo=repo,
            path=WORKFLOW_PATH,
            message=_commit_message(
                "uninstall Claude auto-runner",
                details=f"watched={watched.id}",
            ),
            branch=branch,
            token=gh_token,
            sha=file_info["sha"],
        )
        if not del_res.get("success") and not del_res.get("not_found"):
            errors.append(f"workflow_delete_failed: {del_res.get('error')}")

    # 2) حذف هر سه secret
    for secret_name in (SECRET_OAUTH, SECRET_EXTERNAL, SECRET_BACKEND_URL):
        res = await delete_repo_secret(
            owner, repo, secret_name, gh_token=gh_token,
        )
        if not res.get("success"):
            errors.append(f"{secret_name}: {res.get('error')}")

    return {
        "success": len(errors) == 0,
        "errors": errors,
    }


# ----------------------------------------------------------------------
# Recent runs viewer (Phase 4)
# ----------------------------------------------------------------------

async def list_workflow_runs(
    watched: Any, *, gh_token: str, limit: int = 10,
) -> Dict[str, Any]:
    """فهرست اجراهای اخیر workflow Claude Auto-Runner برای یک ریپو.

    از GitHub Actions API استفاده می‌کند:
      GET /repos/{owner}/{repo}/actions/workflows/{workflow_file}/runs

    Returns:
      {
        "success": bool,
        "runs": [
          {
            "id": int,
            "run_number": int,
            "status": str,          # queued | in_progress | completed
            "conclusion": str|null, # success | failure | cancelled | ... | null
            "created_at": str,
            "updated_at": str,
            "html_url": str,        # لینک به صفحهٔ run در GitHub
            "head_sha": str,
            "head_commit_message": str,
            "duration_seconds": int|null,
          },
          ...
        ],
        "html_url_workflow": str,  # لینک به صفحهٔ workflow در tab Actions
        "total_count": int,
      }
    """
    resolved = _resolve_repo_and_branch(watched)
    if not resolved:
        return {"success": False, "error": "repo_not_resolvable"}
    if not gh_token:
        return {"success": False, "error": "no_github_token"}
    owner, repo, _branch = resolved

    pr = get_github_pr_service()
    # workflow file path (همان WORKFLOW_PATH ولی فقط نام فایل)
    workflow_filename = WORKFLOW_PATH.split("/")[-1]
    url = (
        f"{pr.GITHUB_API}/repos/{owner}/{repo}/actions/workflows/"
        f"{workflow_filename}/runs"
    )
    headers = pr._get_headers(token=gh_token)  # noqa: SLF001
    params = {"per_page": max(1, min(int(limit or 10), 50))}
    res = await pr._gh_request("GET", url, headers=headers, params=params)  # noqa: SLF001
    if not res.get("ok"):
        status = res.get("status")
        # 404 یعنی workflow هرگز نصب نشده یا اجرا نشده — این خطا نیست
        if status == 404:
            return {
                "success": True,
                "runs": [],
                "total_count": 0,
                "html_url_workflow": (
                    f"https://github.com/{owner}/{repo}/actions"
                ),
                "note": "workflow_not_found_or_no_runs_yet",
            }
        return {
            "success": False,
            "error": (
                f"runs_list_failed status={status} "
                f"body={(res.get('body_text') or '')[:200]}"
            ),
        }

    body = res.get("body_json") or {}
    raw_runs = body.get("workflow_runs") or []

    def _duration_seconds(r: Dict[str, Any]) -> Optional[int]:
        try:
            from datetime import datetime as _dt
            ca = r.get("run_started_at") or r.get("created_at")
            ua = r.get("updated_at")
            if ca and ua and (r.get("status") == "completed"):
                t0 = _dt.fromisoformat(ca.replace("Z", "+00:00"))
                t1 = _dt.fromisoformat(ua.replace("Z", "+00:00"))
                return int((t1 - t0).total_seconds())
        except Exception:
            pass
        return None

    runs: list = []
    for r in raw_runs:
        head_commit = r.get("head_commit") or {}
        runs.append({
            "id": r.get("id"),
            "run_number": r.get("run_number"),
            "status": r.get("status"),
            "conclusion": r.get("conclusion"),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
            "html_url": r.get("html_url"),
            "head_sha": (r.get("head_sha") or "")[:8],
            "head_commit_message": (
                (head_commit.get("message") or "").splitlines()[0][:120]
                if head_commit else ""
            ),
            "duration_seconds": _duration_seconds(r),
        })

    return {
        "success": True,
        "runs": runs,
        "total_count": body.get("total_count") or len(runs),
        "html_url_workflow": (
            f"https://github.com/{owner}/{repo}/actions/workflows/"
            f"{workflow_filename}"
        ),
    }

