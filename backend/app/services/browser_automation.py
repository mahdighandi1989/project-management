# -*- coding: utf-8 -*-
"""
🤖 Browser Automation Service با Playwright و AI

این سرویس امکان کنترل مرورگر توسط مدل‌های AI را فراهم می‌کند:
- گرفتن screenshot و تحلیل با AI Vision
- اجرای اکشن‌ها (کلیک، تایپ، اسکرول)
- بازگشت موقعیت cursor برای انیمیشن در فرانت‌اند
"""

import asyncio
import base64
import json
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from ..core.logging_utils import StructuredLogger

slog = StructuredLogger(__name__, "BROWSER-AUTO")

# Playwright رو optional می‌کنیم - در صورت نصب نبودن، خطای واضح می‌دهیم
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    slog.warning("Playwright not installed. Install with: pip install playwright && playwright install chromium")
    async_playwright = None
    Browser = None
    Page = None
    BrowserContext = None


def check_playwright_available():
    """بررسی نصب بودن Playwright"""
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright is not installed. Please install it:\n"
            "1. pip install playwright\n"
            "2. playwright install chromium\n"
            "Or on Render.com, add to requirements.txt and set PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright"
        )


class BrowserSession:
    """یک سشن مرورگر فعال"""

    def __init__(self, session_id: str, url: str):
        self.session_id = session_id
        self.url = url
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.created_at = datetime.utcnow()
        self.last_screenshot: Optional[str] = None  # base64
        self.viewport = {"width": 1280, "height": 720}
        self.action_log: List[Dict] = []

    async def start(self):
        """شروع مرورگر و باز کردن صفحه"""
        check_playwright_available()
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        self.context = await self.browser.new_context(
            viewport=self.viewport,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = await self.context.new_page()

        try:
            await self.page.goto(self.url, wait_until='networkidle', timeout=30000)
            slog.info(f"Browser session started", session_id=self.session_id, url=self.url)
        except Exception as e:
            slog.warning(f"Page load timeout, continuing anyway", error=str(e))

        return self

    async def take_screenshot(self) -> str:
        """گرفتن screenshot و بازگشت base64"""
        if not self.page:
            raise Exception("Browser session not started")

        screenshot_bytes = await self.page.screenshot(full_page=False)
        self.last_screenshot = base64.b64encode(screenshot_bytes).decode('utf-8')
        return self.last_screenshot

    async def get_page_info(self) -> Dict:
        """دریافت اطلاعات صفحه"""
        if not self.page:
            return {}

        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "viewport": self.viewport
        }

    async def find_elements(self, selector: str) -> List[Dict]:
        """پیدا کردن المان‌ها با selector"""
        if not self.page:
            return []

        elements = await self.page.query_selector_all(selector)
        result = []

        for el in elements[:10]:  # حداکثر 10 المان
            try:
                box = await el.bounding_box()
                if box:
                    result.append({
                        "x": box["x"] + box["width"] / 2,
                        "y": box["y"] + box["height"] / 2,
                        "width": box["width"],
                        "height": box["height"],
                        "text": await el.inner_text() if await el.inner_text() else "",
                        "tag": await el.evaluate("el => el.tagName.toLowerCase()")
                    })
            except:
                pass

        return result

    async def analyze_page_for_login(self) -> Dict:
        """تحلیل صفحه برای پیدا کردن فرم لاگین"""
        if not self.page:
            return {"found": False}

        # پیدا کردن فیلدهای ورودی
        inputs = []

        # Username/Email fields
        username_selectors = [
            'input[type="text"][name*="user"]',
            'input[type="text"][name*="email"]',
            'input[type="email"]',
            'input[name="username"]',
            'input[name="email"]',
            'input[id*="user"]',
            'input[id*="email"]',
            'input[placeholder*="user" i]',
            'input[placeholder*="email" i]',
            'input[placeholder*="نام کاربری" i]',
            'input[placeholder*="ایمیل" i]',
        ]

        for selector in username_selectors:
            try:
                el = await self.page.query_selector(selector)
                if el:
                    box = await el.bounding_box()
                    if box:
                        inputs.append({
                            "type": "username",
                            "selector": selector,
                            "x": box["x"] + box["width"] / 2,
                            "y": box["y"] + box["height"] / 2,
                            "width": box["width"],
                            "height": box["height"]
                        })
                        break
            except:
                pass

        # Password field
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[name="pass"]',
            'input[id*="password"]',
        ]

        for selector in password_selectors:
            try:
                el = await self.page.query_selector(selector)
                if el:
                    box = await el.bounding_box()
                    if box:
                        inputs.append({
                            "type": "password",
                            "selector": selector,
                            "x": box["x"] + box["width"] / 2,
                            "y": box["y"] + box["height"] / 2,
                            "width": box["width"],
                            "height": box["height"]
                        })
                        break
            except:
                pass

        # Login button
        button_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("login")',
            'button:has-text("Login")',
            'button:has-text("ورود")',
            'button:has-text("Sign in")',
            'button:has-text("log in")',
            '[role="button"]:has-text("login")',
            'a:has-text("ورود")',
        ]

        button = None
        for selector in button_selectors:
            try:
                el = await self.page.query_selector(selector)
                if el:
                    box = await el.bounding_box()
                    if box:
                        button = {
                            "type": "submit",
                            "selector": selector,
                            "x": box["x"] + box["width"] / 2,
                            "y": box["y"] + box["height"] / 2,
                            "width": box["width"],
                            "height": box["height"]
                        }
                        break
            except:
                pass

        return {
            "found": len(inputs) > 0,
            "inputs": inputs,
            "button": button,
            "page_title": await self.page.title(),
            "url": self.page.url
        }

    async def click(self, x: float, y: float) -> Dict:
        """کلیک در موقعیت مشخص"""
        if not self.page:
            return {"success": False, "error": "No page"}

        await self.page.mouse.click(x, y)
        self.action_log.append({
            "action": "click",
            "x": x,
            "y": y,
            "timestamp": datetime.utcnow().isoformat()
        })

        return {"success": True, "x": x, "y": y}

    async def click_selector(self, selector: str) -> Dict:
        """کلیک روی المان با selector"""
        if not self.page:
            return {"success": False, "error": "No page"}

        try:
            el = await self.page.query_selector(selector)
            if el:
                box = await el.bounding_box()
                if box:
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2
                    await el.click()
                    self.action_log.append({
                        "action": "click",
                        "selector": selector,
                        "x": x,
                        "y": y,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    return {"success": True, "x": x, "y": y}
            return {"success": False, "error": "Element not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def type_text(self, selector: str, text: str, delay: int = 50) -> Dict:
        """تایپ متن در المان"""
        if not self.page:
            return {"success": False, "error": "No page"}

        try:
            el = await self.page.query_selector(selector)
            if el:
                box = await el.bounding_box()
                x, y = 0, 0
                if box:
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2

                await el.click()
                await el.fill("")  # پاک کردن محتوای قبلی
                await el.type(text, delay=delay)

                self.action_log.append({
                    "action": "type",
                    "selector": selector,
                    "text": text[:20] + "..." if len(text) > 20 else text,
                    "x": x,
                    "y": y,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return {"success": True, "x": x, "y": y}
            return {"success": False, "error": "Element not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scroll(self, delta_y: int = 300) -> Dict:
        """اسکرول صفحه"""
        if not self.page:
            return {"success": False, "error": "No page"}

        await self.page.mouse.wheel(0, delta_y)
        self.action_log.append({
            "action": "scroll",
            "delta_y": delta_y,
            "timestamp": datetime.utcnow().isoformat()
        })
        return {"success": True}

    async def wait(self, ms: int = 1000):
        """صبر کردن"""
        await asyncio.sleep(ms / 1000)

    async def close(self):
        """بستن مرورگر"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        slog.info(f"Browser session closed", session_id=self.session_id)


# ذخیره سشن‌های فعال
active_sessions: Dict[str, BrowserSession] = {}


async def create_session(session_id: str, url: str) -> BrowserSession:
    """ایجاد یک سشن جدید"""
    if session_id in active_sessions:
        await active_sessions[session_id].close()

    session = BrowserSession(session_id, url)
    await session.start()
    active_sessions[session_id] = session
    return session


async def get_session(session_id: str) -> Optional[BrowserSession]:
    """دریافت سشن موجود"""
    return active_sessions.get(session_id)


async def close_session(session_id: str):
    """بستن سشن"""
    if session_id in active_sessions:
        await active_sessions[session_id].close()
        del active_sessions[session_id]


async def execute_ai_action(
    session: BrowserSession,
    action_type: str,
    params: Dict
) -> Dict:
    """
    اجرای یک اکشن بر اساس دستور AI

    action_types:
    - analyze: تحلیل صفحه
    - click: کلیک
    - type: تایپ
    - scroll: اسکرول
    - screenshot: گرفتن screenshot
    - find_login: پیدا کردن فرم لاگین
    - login: انجام لاگین کامل
    """

    result = {
        "action": action_type,
        "success": False,
        "cursor_position": None,
        "message": ""
    }

    try:
        if action_type == "analyze":
            info = await session.get_page_info()
            screenshot = await session.take_screenshot()
            result["success"] = True
            result["page_info"] = info
            result["screenshot"] = screenshot[:100] + "..."  # فقط برای لاگ
            result["message"] = f"صفحه تحلیل شد: {info.get('title', 'Unknown')}"

        elif action_type == "find_login":
            login_info = await session.analyze_page_for_login()
            result["success"] = login_info["found"]
            result["login_info"] = login_info
            if login_info["found"]:
                result["message"] = f"فرم لاگین پیدا شد با {len(login_info['inputs'])} فیلد"
                if login_info["inputs"]:
                    first_input = login_info["inputs"][0]
                    result["cursor_position"] = {
                        "x": (first_input["x"] / session.viewport["width"]) * 100,
                        "y": (first_input["y"] / session.viewport["height"]) * 100
                    }
            else:
                result["message"] = "فرم لاگین پیدا نشد"

        elif action_type == "click":
            if "selector" in params:
                click_result = await session.click_selector(params["selector"])
            else:
                click_result = await session.click(params.get("x", 0), params.get("y", 0))

            result["success"] = click_result["success"]
            if click_result.get("x"):
                result["cursor_position"] = {
                    "x": (click_result["x"] / session.viewport["width"]) * 100,
                    "y": (click_result["y"] / session.viewport["height"]) * 100
                }
            result["message"] = "کلیک انجام شد" if result["success"] else f"خطا: {click_result.get('error')}"

        elif action_type == "type":
            type_result = await session.type_text(
                params.get("selector", ""),
                params.get("text", ""),
                params.get("delay", 50)
            )
            result["success"] = type_result["success"]
            if type_result.get("x"):
                result["cursor_position"] = {
                    "x": (type_result["x"] / session.viewport["width"]) * 100,
                    "y": (type_result["y"] / session.viewport["height"]) * 100
                }
            result["message"] = f"تایپ انجام شد" if result["success"] else f"خطا: {type_result.get('error')}"

        elif action_type == "login":
            # انجام لاگین کامل
            login_info = await session.analyze_page_for_login()

            if not login_info["found"]:
                result["message"] = "فرم لاگین پیدا نشد"
                return result

            actions_done = []

            # تایپ username
            username = params.get("username", "admin")
            for inp in login_info["inputs"]:
                if inp["type"] == "username":
                    await session.wait(500)
                    type_result = await session.type_text(inp["selector"], username, delay=80)
                    if type_result["success"]:
                        actions_done.append({
                            "action": "type_username",
                            "cursor_position": {
                                "x": (type_result["x"] / session.viewport["width"]) * 100,
                                "y": (type_result["y"] / session.viewport["height"]) * 100
                            }
                        })
                    break

            # تایپ password
            password = params.get("password", "password")
            for inp in login_info["inputs"]:
                if inp["type"] == "password":
                    await session.wait(500)
                    type_result = await session.type_text(inp["selector"], password, delay=80)
                    if type_result["success"]:
                        actions_done.append({
                            "action": "type_password",
                            "cursor_position": {
                                "x": (type_result["x"] / session.viewport["width"]) * 100,
                                "y": (type_result["y"] / session.viewport["height"]) * 100
                            }
                        })
                    break

            # کلیک روی دکمه
            if login_info["button"]:
                await session.wait(500)
                click_result = await session.click_selector(login_info["button"]["selector"])
                if click_result["success"]:
                    actions_done.append({
                        "action": "click_login",
                        "cursor_position": {
                            "x": (click_result["x"] / session.viewport["width"]) * 100,
                            "y": (click_result["y"] / session.viewport["height"]) * 100
                        }
                    })

            # صبر برای لود صفحه
            await session.wait(2000)

            result["success"] = len(actions_done) > 0
            result["actions"] = actions_done
            result["message"] = f"لاگین انجام شد ({len(actions_done)} اکشن)"

            # screenshot نهایی
            result["final_screenshot"] = await session.take_screenshot()

        elif action_type == "screenshot":
            screenshot = await session.take_screenshot()
            result["success"] = True
            result["screenshot"] = screenshot
            result["message"] = "Screenshot گرفته شد"

        elif action_type == "scroll":
            scroll_result = await session.scroll(params.get("delta_y", 300))
            result["success"] = scroll_result["success"]
            result["message"] = "اسکرول انجام شد"

    except Exception as e:
        slog.error(f"Action failed: {action_type}", exception=e)
        result["error"] = str(e)
        result["message"] = f"خطا: {str(e)}"

    return result


async def analyze_with_vision_ai(
    ai_manager,
    model_id: str,
    screenshot_base64: str,
    task: str,
    previous_actions: List[Dict] = None
) -> Dict:
    """
    تحلیل screenshot با AI Vision و تصمیم‌گیری برای اقدام بعدی

    این تابع از مدل‌های vision مثل GPT-4V استفاده می‌کند
    """
    from ..services.ai_base import Message

    previous_context = ""
    if previous_actions:
        previous_context = "\n\n## اقدامات قبلی:\n" + "\n".join([
            f"- {a.get('action')}: {a.get('description', '')}" for a in previous_actions
        ])

    # ساخت پیام با تصویر
    system_prompt = """شما یک AI Agent هستید که می‌توانید صفحات وب را کنترل کنید.

## قابلیت‌های شما:
1. **click**: کلیک روی المان - نیاز به مختصات x,y (درصد از عرض و ارتفاع صفحه، 0-100)
2. **type**: تایپ متن در فیلد فعلی
3. **scroll**: اسکرول صفحه (up/down)
4. **wait**: صبر کردن
5. **done**: کار تمام شد

## قوانین مهم:
- تصویر صفحه را دقیق ببینید
- مختصات را به صورت درصد بدهید (مثلا x:50, y:30 یعنی وسط افقی، 30% از بالا)
- هر بار فقط یک اقدام پیشنهاد دهید
- اگر کار تمام شد، action را "done" قرار دهید

## فرمت پاسخ (JSON):
```json
{
    "thinking": "توضیح کوتاه از آنچه می‌بینم و تصمیمم",
    "action": "click|type|scroll|wait|done",
    "params": {
        "x": 50,           // برای click - درصد افقی
        "y": 30,           // برای click - درصد عمودی
        "text": "...",     // برای type
        "direction": "down", // برای scroll
        "seconds": 1       // برای wait
    },
    "element_description": "توضیح المانی که روی آن کلیک می‌کنم",
    "is_complete": false,
    "next_expectation": "انتظار دارم بعد از این اقدام چه اتفاقی بیفتد"
}
```"""

    user_prompt = f"""## وظیفه کاربر:
{task}
{previous_context}

## تصویر فعلی صفحه:
(تصویر پیوست شده)

لطفا تصویر را تحلیل کنید و اقدام بعدی را مشخص کنید."""

    # ساخت پیام با فرمت صحیح - استفاده از فیلد images
    messages = [
        Message(role="system", content=system_prompt),
        Message(
            role="user",
            content=user_prompt,
            images=[screenshot_base64]  # تصویر به صورت base64
        )
    ]

    try:
        response = await ai_manager.generate(
            model_id=model_id,
            messages=messages,
            max_tokens=1024,
            temperature=0.2
        )

        # تلاش برای parse JSON
        try:
            # پیدا کردن JSON در پاسخ
            json_match = re.search(r'\{[\s\S]*?\}', response.content)
            if json_match:
                result = json.loads(json_match.group())
                slog.info(f"AI Vision decision", action=result.get("action"), thinking=result.get("thinking", "")[:100])
                return result
        except Exception as parse_error:
            slog.warning(f"JSON parse failed", error=str(parse_error), content=response.content[:200])

        return {
            "thinking": response.content,
            "action": "done",
            "params": {},
            "is_complete": True,
            "error": "Could not parse AI response"
        }

    except Exception as e:
        slog.error("Vision analysis failed", exception=e)
        return {
            "error": str(e),
            "action": "done",
            "is_complete": True
        }


async def execute_ai_agent_task(
    session: BrowserSession,
    task: str,
    ai_manager,
    model_id: str = "gpt-4o",
    max_steps: int = 10,
    on_action_callback = None
) -> Dict:
    """
    اجرای یک task توسط AI Agent با حلقه تکرار

    این تابع:
    1. Screenshot می‌گیرد
    2. به AI Vision می‌فرستد
    3. اقدام پیشنهادی را اجرا می‌کند
    4. تکرار تا تکمیل task یا رسیدن به حداکثر steps

    Args:
        session: Browser session
        task: دستور کاربر
        ai_manager: AI manager instance
        model_id: مدل vision (مثل gpt-4o)
        max_steps: حداکثر تعداد اقدامات
        on_action_callback: تابع callback برای گزارش هر اقدام

    Returns:
        نتیجه شامل تمام اقدامات و وضعیت نهایی
    """
    actions_log = []
    cursor_positions = []
    step = 0

    slog.info(f"Starting AI agent task", task=task[:100], model=model_id, max_steps=max_steps)

    while step < max_steps:
        step += 1

        # 1. گرفتن screenshot
        try:
            screenshot = await session.take_screenshot()
        except Exception as e:
            slog.error(f"Screenshot failed at step {step}", exception=e)
            break

        # 2. ارسال به AI Vision
        try:
            ai_decision = await analyze_with_vision_ai(
                ai_manager=ai_manager,
                model_id=model_id,
                screenshot_base64=screenshot,
                task=task,
                previous_actions=actions_log
            )
        except Exception as e:
            slog.error(f"AI analysis failed at step {step}", exception=e)
            actions_log.append({
                "step": step,
                "action": "error",
                "description": f"AI analysis failed: {str(e)}",
                "status": "failed"
            })
            break

        action = ai_decision.get("action", "done")
        params = ai_decision.get("params", {})
        thinking = ai_decision.get("thinking", "")
        element_desc = ai_decision.get("element_description", "")
        is_complete = ai_decision.get("is_complete", False)

        # 3. لاگ کردن و callback
        action_entry = {
            "step": step,
            "action": action,
            "thinking": thinking,
            "element": element_desc,
            "params": params,
            "status": "running"
        }

        if on_action_callback:
            await on_action_callback(action_entry)

        # 4. بررسی تکمیل
        if action == "done" or is_complete:
            action_entry["status"] = "done"
            action_entry["description"] = "کار تکمیل شد"
            actions_log.append(action_entry)
            slog.info(f"Task completed at step {step}")
            break

        # 5. اجرای اقدام
        try:
            if action == "click":
                x_percent = params.get("x", 50)
                y_percent = params.get("y", 50)

                # تبدیل درصد به پیکسل
                x_pixel = (x_percent / 100) * session.viewport["width"]
                y_pixel = (y_percent / 100) * session.viewport["height"]

                await session.click(x_pixel, y_pixel)

                action_entry["description"] = f"کلیک روی {element_desc} (x:{x_percent}%, y:{y_percent}%)"
                action_entry["status"] = "done"

                cursor_positions.append({
                    "step": step,
                    "action": f"click: {element_desc}",
                    "x": x_percent,
                    "y": y_percent
                })

            elif action == "type":
                text = params.get("text", "")
                # تایپ در فیلد فعلی (فرض: فیلد قبلا فوکوس شده)
                if session.page:
                    await session.page.keyboard.type(text, delay=50)
                action_entry["description"] = f"تایپ: {text[:30]}..."
                action_entry["status"] = "done"

            elif action == "scroll":
                direction = params.get("direction", "down")
                delta = 300 if direction == "down" else -300
                await session.scroll(delta)
                action_entry["description"] = f"اسکرول {direction}"
                action_entry["status"] = "done"

            elif action == "wait":
                seconds = params.get("seconds", 1)
                await session.wait(seconds * 1000)
                action_entry["description"] = f"صبر {seconds} ثانیه"
                action_entry["status"] = "done"

            else:
                action_entry["description"] = f"اقدام ناشناخته: {action}"
                action_entry["status"] = "skipped"

        except Exception as e:
            slog.error(f"Action execution failed", action=action, exception=e)
            action_entry["status"] = "failed"
            action_entry["error"] = str(e)

        actions_log.append(action_entry)

        # 6. صبر کوتاه بین اقدامات
        await session.wait(500)

    # گرفتن screenshot نهایی
    try:
        final_screenshot = await session.take_screenshot()
    except:
        final_screenshot = None

    return {
        "success": step < max_steps or any(a.get("action") == "done" for a in actions_log),
        "total_steps": step,
        "actions": actions_log,
        "cursor_positions": cursor_positions,
        "final_screenshot": final_screenshot,
        "task": task
    }
