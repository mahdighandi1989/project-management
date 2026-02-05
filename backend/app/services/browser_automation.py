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
        self._element_handles: List = []  # 🆕 برای کلیک مستقیم روی المان

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

    async def extract_interactive_elements(self) -> List[Dict]:
        """
        استخراج تمام المان‌های قابل تعامل از صفحه

        این تابع لینک‌ها، دکمه‌ها و المان‌های کلیک‌پذیر را پیدا می‌کند
        و موقعیت دقیق هر کدام را برمی‌گرداند.

        Returns:
            لیستی از المان‌ها با index, text, type, و bounding_box
        """
        if not self.page:
            return []

        elements = []
        index = 0

        # 🆕 ذخیره element handles برای کلیک مستقیم
        self._element_handles = []

        # سلکتورهای المان‌های قابل کلیک
        selectors = [
            'a[href]',           # لینک‌ها
            'button',            # دکمه‌ها
            '[role="button"]',   # المان‌های با نقش دکمه
            'input[type="submit"]',
            'input[type="button"]',
            '[onclick]',         # المان‌های با onclick
            '.nav-link',         # لینک‌های نویگیشن
            '.menu-item',        # آیتم‌های منو
            '[class*="btn"]',    # کلاس‌های حاوی btn
        ]

        for selector in selectors:
            try:
                found = await self.page.query_selector_all(selector)
                for el in found:
                    try:
                        # چک کنیم که المان visible باشد
                        is_visible = await el.is_visible()
                        if not is_visible:
                            continue

                        box = await el.bounding_box()
                        if not box or box["width"] < 5 or box["height"] < 5:
                            continue

                        # گرفتن متن المان
                        text = ""
                        try:
                            text = await el.inner_text()
                            text = text.strip()[:50]  # حداکثر 50 کاراکتر
                        except:
                            pass

                        if not text:
                            try:
                                text = await el.get_attribute("aria-label") or ""
                            except:
                                pass

                        if not text:
                            try:
                                text = await el.get_attribute("title") or ""
                            except:
                                pass

                        # جلوگیری از تکرار
                        center_x = box["x"] + box["width"] / 2
                        center_y = box["y"] + box["height"] / 2

                        # چک برای تکراری نبودن (موقعیت مشابه)
                        is_duplicate = False
                        for existing in elements:
                            if abs(existing["center_x"] - center_x) < 10 and abs(existing["center_y"] - center_y) < 10:
                                is_duplicate = True
                                break

                        if is_duplicate:
                            continue

                        tag = await el.evaluate("el => el.tagName.toLowerCase()")

                        # 🆕 گرفتن href برای لینک‌ها
                        href = ""
                        try:
                            href = await el.get_attribute("href") or ""
                        except:
                            pass

                        # 🆕 ذخیره element handle برای کلیک مستقیم
                        self._element_handles.append(el)

                        elements.append({
                            "index": index,
                            "handle_index": len(self._element_handles) - 1,  # 🆕
                            "text": text if text else f"[{tag}]",
                            "tag": tag,
                            "href": href,  # 🆕 آدرس لینک
                            "selector": selector,
                            "box": {
                                "x": box["x"],
                                "y": box["y"],
                                "width": box["width"],
                                "height": box["height"]
                            },
                            "center_x": center_x,
                            "center_y": center_y,
                            # درصد نسبت به viewport
                            "percent_x": round((center_x / self.viewport["width"]) * 100, 1),
                            "percent_y": round((center_y / self.viewport["height"]) * 100, 1)
                        })
                        index += 1

                    except Exception as e:
                        continue

            except Exception as e:
                slog.warning(f"Selector failed: {selector}", error=str(e))
                continue

        # مرتب‌سازی بر اساس موقعیت (بالا به پایین، راست به چپ برای RTL)
        elements.sort(key=lambda e: (e["center_y"], -e["center_x"]))

        # بازنشانی index بعد از مرتب‌سازی
        for i, el in enumerate(elements):
            el["index"] = i

        slog.info(f"Extracted {len(elements)} interactive elements")
        return elements

    async def click_element_directly(self, element_info: Dict) -> Dict:
        """
        🆕 کلیک مستقیم روی المان - چندین روش تلاش می‌کند
        اگر کلیک کار نکرد، از href مستقیم استفاده می‌کند
        """
        if not self.page:
            return {"success": False, "error": "No page"}

        handle_index = element_info.get("handle_index", -1)
        element_text = element_info.get("text", "unknown")
        element_href = element_info.get("href", "")

        slog.info(f"🖱️ CLICK ATTEMPT | element='{element_text}' | href='{element_href}' | handle_index={handle_index} | total_handles={len(self._element_handles)}")

        if handle_index < 0 or handle_index >= len(self._element_handles):
            slog.warning(f"Invalid handle_index, using coordinate click")
            return await self.click(element_info["center_x"], element_info["center_y"])

        element_handle = self._element_handles[handle_index]
        old_url = self.page.url
        slog.info(f"Current URL before click: {old_url}")

        # 🆕 تأیید که المان درست است - گرفتن متن و href از handle فعلی
        try:
            actual_text = await element_handle.inner_text()
            actual_text = actual_text.strip()[:50] if actual_text else ""
        except:
            actual_text = ""

        try:
            current_href = await element_handle.get_attribute("href")
        except:
            current_href = element_href

        slog.info(f"📋 ELEMENT VERIFICATION | expected='{element_text}' | actual='{actual_text}' | href='{current_href}'")

        # 🚨 اگر متن مطابقت نداشت، هشدار بده
        if actual_text and element_text and actual_text != element_text:
            slog.warning(f"⚠️ MISMATCH! Expected '{element_text}' but handle points to '{actual_text}'")

        try:
            # روش 1: JavaScript click (قوی‌ترین روش)
            slog.info(f"🖱️ Method 1: JavaScript el.click()")
            try:
                await self.page.evaluate("el => el.click()", element_handle)
                slog.info(f"✅ JavaScript click executed")
            except Exception as js_err:
                slog.warning(f"JavaScript click failed: {js_err}")

                # روش 2: Playwright force click
                slog.info(f"🖱️ Method 2: Playwright force click")
                await element_handle.click(timeout=5000, force=True)
                slog.info(f"✅ Playwright force click executed")

            # صبر برای navigation
            slog.info(f"⏳ Waiting for navigation...")
            await self.page.wait_for_timeout(2000)

            new_url = self.page.url
            url_changed = new_url != old_url
            slog.info(f"📍 URL after click: '{new_url}' | changed={url_changed}")

            # 🆕 روش 3: اگر کلیک کار نکرد و href معتبر داریم، مستقیم برو
            if not url_changed and current_href:
                # چک کنیم href معتبر باشد (نه # یا javascript:)
                if current_href.startswith("http") or (current_href.startswith("/") and not current_href.startswith("//")):
                    slog.info(f"🔗 Method 3: Direct navigation to href: '{current_href}'")

                    # ساخت URL کامل اگر نسبی بود
                    if current_href.startswith("/"):
                        base_url = f"{self.page.url.split('://')[0]}://{self.page.url.split('/')[2]}"
                        full_url = base_url + current_href
                    else:
                        full_url = current_href

                    slog.info(f"🌐 Navigating to: '{full_url}'")
                    try:
                        await self.page.goto(full_url, wait_until='networkidle', timeout=15000)
                        new_url = self.page.url
                        url_changed = new_url != old_url
                        slog.info(f"✅ Direct navigation complete! URL: '{new_url}' | changed={url_changed}")
                    except Exception as nav_err:
                        slog.warning(f"Direct navigation failed: {nav_err}")
                else:
                    slog.info(f"⚠️ href is not navigable: '{current_href}' (starts with # or javascript:)")

            if url_changed:
                try:
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
                    slog.info(f"✅ Page loaded!")
                except Exception as nav_err:
                    slog.warning(f"Load wait timeout: {nav_err}")

            return {
                "success": True,
                "method": "direct_click" if url_changed else "click_no_nav",
                "element": element_text,
                "href": current_href,
                "url": new_url,
                "url_changed": url_changed
            }

        except Exception as e:
            slog.error(f"❌ ALL CLICK METHODS FAILED | element='{element_text}' | error={str(e)}")
            # آخرین تلاش
            slog.info(f"🖱️ Final fallback: coordinate click at ({element_info['center_x']}, {element_info['center_y']})")
            return await self.click(element_info["center_x"], element_info["center_y"])

    async def click_element_by_index(self, elements: List[Dict], index: int) -> Dict:
        """
        کلیک روی المان با شماره index

        Args:
            elements: لیست المان‌ها از extract_interactive_elements
            index: شماره المان

        Returns:
            نتیجه کلیک
        """
        if index < 0 or index >= len(elements):
            return {"success": False, "error": f"Invalid index: {index}"}

        element = elements[index]
        x = element["center_x"]
        y = element["center_y"]

        try:
            await self.click(x, y)
            return {
                "success": True,
                "clicked_element": element["text"],
                "position": {"x": x, "y": y}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

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

    async def click(self, x: float, y: float, wait_for_navigation: bool = True) -> Dict:
        """کلیک در موقعیت مشخص"""
        if not self.page:
            return {"success": False, "error": "No page"}

        old_url = self.page.url

        await self.page.mouse.click(x, y)

        # صبر برای navigation احتمالی
        if wait_for_navigation:
            try:
                # صبر کوتاه برای شروع navigation
                await self.page.wait_for_timeout(500)

                # اگر URL تغییر کرد، صبر برای لود کامل
                if self.page.url != old_url:
                    await self.page.wait_for_load_state('networkidle', timeout=10000)
                    slog.info(f"Navigation detected: {old_url} -> {self.page.url}")
                else:
                    # شاید SPA باشد - صبر بیشتر برای تغییرات DOM
                    await self.page.wait_for_timeout(1000)
            except Exception as e:
                slog.warning(f"Wait after click failed", error=str(e))

        self.action_log.append({
            "action": "click",
            "x": x,
            "y": y,
            "timestamp": datetime.utcnow().isoformat(),
            "url_after": self.page.url
        })

        return {"success": True, "x": x, "y": y, "url": self.page.url}

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
    previous_actions: List[Dict] = None,
    interactive_elements: List[Dict] = None  # 🆕 لیست المان‌های قابل کلیک
) -> Dict:
    """
    تحلیل screenshot با AI Vision و تصمیم‌گیری برای اقدام بعدی

    رویکرد جدید:
    - لیست المان‌های قابل کلیک با موقعیت دقیق به AI داده می‌شود
    - AI با شماره index المان را انتخاب می‌کند
    - دیگر نیاز به حدس زدن مختصات نیست
    """
    from ..services.ai_base import Message

    previous_context = ""
    if previous_actions:
        previous_context = "\n\n## اقدامات قبلی:\n" + "\n".join([
            f"- {a.get('action')}: {a.get('description', '')}" for a in previous_actions
        ])

    # ساخت لیست المان‌ها برای نمایش به AI
    elements_list = ""
    if interactive_elements:
        elements_list = "\n\n## المان‌های قابل کلیک در صفحه:\n"
        for el in interactive_elements[:30]:  # حداکثر 30 المان
            href_info = f" -> {el['href']}" if el.get('href') else ""
            elements_list += f"[{el['index']}] \"{el['text']}\" ({el['tag']}{href_info})\n"

    # پرامپت جدید - انتخاب با index
    system_prompt = """شما یک AI Agent هستید که صفحات وب را کنترل می‌کنید.

## روش کار:
لیست المان‌های قابل کلیک صفحه به شما داده شده است. هر المان یک شماره (index) دارد.
برای کلیک، فقط کافیست شماره المان را بدهید.

## قابلیت‌ها:
1. **click_element**: کلیک روی المان با شماره - params: {"index": شماره}
2. **type**: تایپ متن - params: {"text": "متن"}
3. **scroll**: اسکرول برای دیدن المان‌های بیشتر - params: {"direction": "up" یا "down"}
4. **wait**: صبر برای لود صفحه - params: {"seconds": عدد}
5. **done**: وظیفه انجام شد (فقط وقتی صفحه مورد نظر باز شد)

## قوانین مهم:
- اگر المان مورد نظر در لیست هست، شماره‌اش را بده
- اگر المان مورد نظر در لیست نیست، scroll کن تا پیدا شود
- تصویر صفحه را با لیست المان‌ها تطبیق بده
- فقط وقتی done بگو که URL صفحه تغییر کرده و به هدف رسیدی
- اگر همان صفحه قبلی است، done نگو!

## فرمت پاسخ (فقط JSON):
{
    "thinking": "توضیح: چه می‌بینم، کدام المان مربوط به وظیفه است",
    "action": "click_element",
    "params": {"index": شماره_المان},
    "element_description": "نام المان",
    "is_complete": false
}"""

    user_prompt = f"""## وظیفه:
{task}
{previous_context}
{elements_list}

## تصویر صفحه ضمیمه شده.

**دستورالعمل:**
1. تصویر را ببین
2. لیست المان‌ها را بررسی کن
3. المانی که مربوط به وظیفه "{task}" است را پیدا کن
4. شماره (index) آن المان را در پاسخ بده

پاسخ را فقط به فرمت JSON بده."""

    # ساخت پیام با فرمت صحیح - استفاده از فیلد images
    messages = [
        Message(role="system", content=system_prompt),
        Message(
            role="user",
            content=user_prompt,
            images=[screenshot_base64]  # تصویر به صورت base64
        )
    ]

    slog.info(f"🔍 Sending to AI Vision",
        model=model_id,
        task=task[:50],
        image_size=len(screenshot_base64),
        image_prefix=screenshot_base64[:20]  # برای تأیید PNG/JPEG
    )

    try:
        response = await ai_manager.generate(
            model_id=model_id,
            messages=messages,
            max_tokens=1024,
            temperature=0.2
        )

        # 🔍 لاگ کامل پاسخ AI
        slog.info(f"🤖 AI Vision RAW response",
            model=model_id,
            content_length=len(response.content),
            content_preview=response.content[:500]
        )

        # تلاش برای parse JSON
        try:
            # پیدا کردن JSON در پاسخ - با پشتیبانی از nested objects
            content = response.content

            # ابتدا سعی کن کل پاسخ را parse کنی
            try:
                result = json.loads(content)
                slog.info(f"AI Vision decision (direct parse)", ai_action=result.get("action"), ai_thinking=result.get("thinking", "")[:100])
                return result
            except:
                pass

            # پیدا کردن JSON block در پاسخ
            # ابتدا markdown code block
            code_block_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
            if code_block_match:
                try:
                    result = json.loads(code_block_match.group(1))
                    slog.info(f"AI Vision decision (code block)", ai_action=result.get("action"), ai_thinking=result.get("thinking", "")[:100])
                    return result
                except:
                    pass

            # پیدا کردن JSON با شمارش براکت‌ها
            start_idx = content.find('{')
            if start_idx != -1:
                bracket_count = 0
                end_idx = start_idx
                for i, char in enumerate(content[start_idx:]):
                    if char == '{':
                        bracket_count += 1
                    elif char == '}':
                        bracket_count -= 1
                        if bracket_count == 0:
                            end_idx = start_idx + i + 1
                            break

                json_str = content[start_idx:end_idx]
                try:
                    result = json.loads(json_str)
                    slog.info(f"AI Vision decision (bracket count)", ai_action=result.get("action"), ai_thinking=result.get("thinking", "")[:100])
                    return result
                except Exception as e:
                    slog.warning(f"JSON parse failed", parse_error=str(e), json_preview=json_str[:200])

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
    ai_responses = []  # 🆕 برای debug - پاسخ‌های خام AI
    step = 0

    slog.info(f"Starting AI agent task", task=task[:100], model=model_id, max_steps=max_steps)

    # ذخیره المان‌ها برای استفاده در کلیک
    current_elements = []

    while step < max_steps:
        step += 1

        # 1. استخراج المان‌های قابل کلیک
        try:
            current_elements = await session.extract_interactive_elements()
            slog.info(f"Step {step}: Found {len(current_elements)} interactive elements")
        except Exception as e:
            slog.warning(f"Element extraction failed at step {step}", exception=e)
            current_elements = []

        # 2. گرفتن screenshot
        try:
            screenshot = await session.take_screenshot()
        except Exception as e:
            slog.error(f"Screenshot failed at step {step}", exception=e)
            break

        # 3. ارسال به AI Vision با لیست المان‌ها
        try:
            ai_decision = await analyze_with_vision_ai(
                ai_manager=ai_manager,
                model_id=model_id,
                screenshot_base64=screenshot,
                task=task,
                previous_actions=actions_log,
                interactive_elements=current_elements  # 🆕 ارسال لیست المان‌ها
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

        # 🆕 ذخیره پاسخ خام AI برای debug
        ai_responses.append({
            "step": step,
            "raw_decision": ai_decision
        })

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

        # 4. بررسی اقدام "done" (بدون نیاز به اجرا)
        if action == "done":
            action_entry["status"] = "done"
            action_entry["description"] = "کار تکمیل شد"
            actions_log.append(action_entry)
            slog.info(f"Task completed at step {step}")
            break

        # 5. اجرای اقدام (حتی اگر is_complete=true باشد، اول اقدام را انجام بده)
        try:
            # 🆕 کلیک با شماره المان (روش جدید و دقیق)
            if action == "click_element":
                element_index = params.get("index", -1)

                if element_index >= 0 and element_index < len(current_elements):
                    element = current_elements[element_index]
                    x_percent = element["percent_x"]
                    y_percent = element["percent_y"]

                    # 🆕 استفاده از کلیک مستقیم روی المان (دقیق‌تر از کلیک مختصاتی)
                    click_result = await session.click_element_directly(element)

                    url_changed = click_result.get("url_changed", False)
                    nav_status = "✅ صفحه تغییر کرد" if url_changed else "⚠️ صفحه تغییر نکرد!"

                    action_entry["description"] = f"کلیک روی [{element_index}] {element['text']} - {nav_status}"
                    action_entry["status"] = "done" if click_result.get("success") else "failed"
                    action_entry["click_method"] = click_result.get("method", "unknown")
                    action_entry["url_after"] = click_result.get("url", "")
                    action_entry["url_changed"] = url_changed  # 🆕 برای اطلاع AI

                    cursor_positions.append({
                        "step": step,
                        "action": f"click: {element['text']}",
                        "x": x_percent,
                        "y": y_percent
                    })

                else:
                    action_entry["description"] = f"المان با شماره {element_index} پیدا نشد"
                    action_entry["status"] = "failed"
                    slog.warning(f"Invalid element index: {element_index}, available: 0-{len(current_elements)-1}")

            # کلیک قدیمی با درصد (برای backward compatibility)
            elif action == "click":
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
            slog.error(f"Action execution failed", action_type=action, exception=e)
            action_entry["status"] = "failed"
            action_entry["error"] = str(e)

        actions_log.append(action_entry)

        # 6. بررسی is_complete بعد از اجرای اقدام
        if is_complete:
            slog.info(f"Task marked complete after executing action at step {step}")
            break

        # 7. صبر کوتاه بین اقدامات
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
        "ai_responses": ai_responses,  # 🆕 برای debug
        "task": task
    }
