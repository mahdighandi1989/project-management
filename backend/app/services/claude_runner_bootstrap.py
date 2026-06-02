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
MASTER_PROMPT = (
    "این پرامپت را کامل بخوان (نه skim). به شاخه main برو. از endpoint "
    "$OVERSIGHT_BACKEND_URL/api/external/prompts/next?watched_id=$WATCHED_ID "
    "(header X-External-Token: $OVERSIGHT_EXTERNAL_TOKEN) لیست تسک‌های pending "
    "را به ترتیب اولویت بگیر.\n"
    "\n"
    "اگر لیست خالی برگشت یا API در دسترس نبود: یک خط log بنویس "
    "'no pending tasks — exiting cleanly' و کار را با success تمام کن. "
    "هیچ تسک خیالی نساز، هیچ commit نزن.\n"
    "\n"
    "برای هر تسک:\n"
    "\n"
    "1) endpoint POST /api/external/prompts/{task_id}/claim با body "
    "{\"agent\":\"claude-code-action\"} لاک تسک را بگیر. اگر 409 خوردی، "
    "تسک قبلاً توسط دیگری claim شده — رد شو به تسک بعدی.\n"
    "\n"
    "2) فایل prompt/<task_id>.md را cat کامل (نه head/tail/--lines/sed) "
    "بخوان. wc -l + grep -c '^##' بزن آمار خط/section بنویس. لیست همه "
    "section header ها را نشان بده. اگر > 500 خط، warning بنویس. Prompt + "
    "همه AC + همه Step را عیناً quote کن (بدون '...' یا 'etc'). AC_count "
    "اعلام = paste شده.\n"
    "\n"
    "3) iteration کامل: بررسی → پیاده‌سازی → commit → push origin main فوری "
    "(rejected → pull --rebase → push دوباره). هرگز batch نکن، هرگز branch "
    "جدا نکن، هرگز push تأخیری.\n"
    "\n"
    "4) برای هر AC: پیاده‌سازی، تست، diff (اگر خالی برگرد)، self-verify per "
    "AC، re-read + coverage report per section (✓/✗) — اگر < 100% برگرد. "
    "commit message: task_id + Prompt stats + Coverage.\n"
    "\n"
    "5) endpoint POST /api/external/prompts/{task_id}/complete با body "
    "{\"summary\":\"<خلاصه کار انجام‌شده>\",\"commit_sha\":\"<sha>\"} تسک "
    "را به‌عنوان done اعلام کن. اگر شکست خوردی، POST /fail با reason.\n"
    "\n"
    "🚨 قاعدهٔ ضد-فرار TO-DO: TO-DO فقط برای موارد واقعاً غیرممکن انسانی — "
    "credential کاربر، account/billing روی سرویس خارجی، داده‌ی خصوصی کاربر، "
    "تصمیم سلیقه‌ای/حقوقی/کسب‌وکار. هرگز TO-DO برای: UI component (.tsx/.jsx)، "
    "endpoint، model، migration، test، docs، Celery، scheduler، integration "
    "با Google/Stripe (با stub بساز)، 'feature بزرگه'، '.tsx بود ولی repo "
    ".jsx است' (از .jsx استفاده کن)، 'نیازمند فیلد X' (اضافه کن). قبل از "
    "TO-DO ۴ سؤال بپرس: می‌تونم stub بسازم؟ test بنویسم؟ abstraction تعریف "
    "کنم؟ فقط یه decision کاربر مونده؟ اگه بله → بساز و TO-DO نکن. اگه > "
    "20% تسک‌ها TO-DO شد، خودت در گزارش پایانی اعلام کن 'من فرار کردم، "
    "کاربر بازبینی کند'.\n"
    "\n"
    "هرگز batching commit، هرگز skim section های وسط، هرگز 'section مشابه "
    "قبلی' فرض کن، هرگز '...' در quote، هرگز 'already done' بدون اثبات، "
    "هرگز defer/skip، هرگز 'no-op تأییدی' برای تسک‌های آخر؛ گزارش نهایی "
    "شامل commits == pushes، Coverage کلی، لیست TO-DO ها با اعلام نسبت "
    "آن. هیچ‌گاه merge یا PR نزن — مستقیم به main commit و push کن."
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
        "--max-turns 30 --model claude-opus-4-8 "
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
  workflow_dispatch: {{}}

# 🛡 (workflow trigger leak fix) — strategy جدید: cancel-in-progress: true
# قبلاً cancel-in-progress: false بود → یعنی runی که در حال اجرا بود
# نگه‌داری می‌شد ولی runهای صف از سوی GitHub خودکار cancel می‌شدند
# (هر بار یک trigger جدید بیاید). نتیجه: runها ۷-۸ دقیقه setup می‌کردند
# سپس cancel می‌شدند بدون اینکه کاری کنند → سهمیه ماهانه را در یک
# روز می‌سوزاند.
#
# با cancel-in-progress: true، run قبلی فوراً (در چند ثانیه) cancel
# می‌شود وقتی triger جدیدی بیاید → setup time هدر نمی‌رود → فقط آخرین
# run کامل اجرا می‌شود. این هم‌خوان با master prompt است که می‌گوید
# Claude **همهٔ** تسک‌های pending را در یک run می‌گیرد، نه فقط آخرین.
concurrency:
  group: claude-auto-task-{watched_id}
  cancel-in-progress: true

jobs:
  run-task:
    runs-on: ubuntu-latest
    timeout-minutes: 60
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

async def trigger_workflow_dispatch(
    watched: Any, *, gh_token: str, ref: str = "main",
) -> Dict[str, Any]:
    """trigger دستی workflow Claude Auto-Runner از طریق GitHub API.

    این تابع از سوی backend بعد از push موفق `prompt/_index.json` صدا
    زده می‌شود تا workflow اجرا شود (چون trigger روی push کار نمی‌کند).

    Returns:
      {"success": bool, "error": str, "skipped": bool}
      skipped=True اگر runner enabled نباشد یا workflow نصب نشده باشد.
    """
    # فقط اگر runner برای این watched نصب شده، trigger بزن
    if not getattr(watched, "claude_runner_enabled", False):
        return {"success": True, "skipped": True, "reason": "runner_not_enabled"}

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
    body = {"ref": use_ref}
    res = await pr._gh_request("POST", url, headers=headers, json_body=body)  # noqa: SLF001
    status = res.get("status")
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
    return {
        "success": False,
        "error": (
            f"dispatch_failed status={status} "
            f"body={(res.get('body_text') or '')[:200]}"
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
    claude_args: str = "--max-turns 30 --model claude-opus-4-8",
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
    yaml_content = build_workflow_yaml(
        watched_id=watched.id,
        repo_full_name=watched.repo_full_name,
        branch=branch,
        claude_args=claude_args,
    )
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

