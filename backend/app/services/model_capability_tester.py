# -*- coding: utf-8 -*-
"""
سرویس تست توانایی مدل‌ها - Model Capability Tester

این سرویس توانایی‌های هر مدل را با سوالات استاندارد ارزیابی می‌کند
و نتایج را به صورت badge و امتیاز ذخیره می‌کند.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import time
import logging

from .ai_base import Message

logger = logging.getLogger(__name__)


# =====================================
# ثابت‌ها و سوالات تست
# =====================================

CAPABILITY_TEST_QUESTIONS = {
    "self_introduction": {
        "prompt": """
تو یک مدل هوش مصنوعی هستی. لطفاً خودت را در 2-3 جمله معرفی کن:
1. نام و نسخه‌ات چیست؟
2. چه کارهایی را بهتر انجام می‌دهی؟
3. چه محدودیت‌هایی داری؟

پاسخ را به فرمت JSON بده:
{
    "name": "نام مدل",
    "version": "نسخه",
    "strengths": ["توانایی 1", "توانایی 2"],
    "limitations": ["محدودیت 1"],
    "best_for": ["کاربرد 1", "کاربرد 2"]
}
""",
        "category": "identity",
        "weight": 1.0
    },

    "code_analysis": {
        "prompt": """
این کد پایتون را تحلیل کن و مشکلاتش را بگو:

```python
def calculate(x, y):
    result = x / y
    return result

numbers = [1, 2, 0, 4]
for n in numbers:
    print(calculate(10, n))
```

پاسخ JSON:
{
    "issues": [{"line": X, "problem": "توضیح", "severity": "high|medium|low"}],
    "suggestions": ["پیشنهاد 1"],
    "score": 0-100
}
""",
        "category": "code_analysis",
        "weight": 2.0
    },

    "code_generation": {
        "prompt": """
یک تابع پایتون بنویس که:
- لیستی از اعداد بگیرد
- میانگین، بزرگترین و کوچکترین را برگرداند
- مدیریت خطا داشته باشد

پاسخ JSON:
{
    "code": "کد تابع",
    "explanation": "توضیح کوتاه",
    "test_cases": ["تست 1"]
}
""",
        "category": "code_generation",
        "weight": 2.0
    },

    "documentation": {
        "prompt": """
برای این تابع docstring کامل بنویس:

```python
def process_data(items, threshold=0.5, normalize=True):
    results = []
    for item in items:
        if item['value'] > threshold:
            if normalize:
                item['value'] = item['value'] / max(i['value'] for i in items)
            results.append(item)
    return results
```

پاسخ JSON:
{
    "docstring": "متن docstring",
    "quality_score": 0-100
}
""",
        "category": "documentation",
        "weight": 1.5
    },

    "problem_solving": {
        "prompt": """
مسئله: یک آرایه از اعداد صحیح داریم. می‌خواهیم دو عدد پیدا کنیم که جمعشان برابر target باشد.

مثال: nums = [2, 7, 11, 15], target = 9
خروجی: [0, 1] (چون nums[0] + nums[1] = 2 + 7 = 9)

پاسخ JSON:
{
    "approach": "توضیح روش حل",
    "complexity": {"time": "O(?)", "space": "O(?)"},
    "code": "کد راه‌حل",
    "score": 0-100
}
""",
        "category": "problem_solving",
        "weight": 2.5
    },

    "security_awareness": {
        "prompt": """
این کد را از نظر امنیتی بررسی کن:

```python
import sqlite3

def get_user(username):
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchone()
```

پاسخ JSON:
{
    "vulnerabilities": [{"type": "نوع", "severity": "high|medium|low", "description": "توضیح"}],
    "fix_suggestions": ["پیشنهاد رفع"],
    "secure_code": "کد امن",
    "score": 0-100
}
""",
        "category": "security",
        "weight": 2.0
    },

    "persian_understanding": {
        "prompt": """
این متن فارسی را خلاصه کن و نکات کلیدی را استخراج کن:

«برنامه‌نویسی تنها نوشتن کد نیست، بلکه حل مسئله است. یک برنامه‌نویس خوب ابتدا مسئله را می‌فهمد، سپس راه‌حل‌های مختلف را بررسی می‌کند و در نهایت بهترین راه‌حل را پیاده‌سازی می‌کند. کیفیت کد به اندازه عملکرد آن اهمیت دارد.»

پاسخ JSON:
{
    "summary": "خلاصه در یک جمله",
    "key_points": ["نکته 1", "نکته 2"],
    "sentiment": "positive|neutral|negative",
    "score": 0-100
}
""",
        "category": "language",
        "weight": 1.0
    },

    "reasoning": {
        "prompt": """
این مسئله منطقی را حل کن:

علی از بهرام بلندتر است.
بهرام از کامران بلندتر است.
کامران از داود کوتاه‌تر نیست.

سوال: آیا علی از داود بلندتر است؟

پاسخ JSON:
{
    "answer": "بله|خیر|نامشخص",
    "reasoning": "استدلال گام به گام",
    "confidence": 0-100
}
""",
        "category": "reasoning",
        "weight": 1.5
    }
}

# تعریف badge ها بر اساس نمره
CAPABILITY_BADGES = {
    "master": {"min_score": 90, "color": "gold", "label": "استاد", "icon": "👑"},
    "expert": {"min_score": 80, "color": "purple", "label": "متخصص", "icon": "🎯"},
    "proficient": {"min_score": 70, "color": "blue", "label": "ماهر", "icon": "⭐"},
    "competent": {"min_score": 60, "color": "green", "label": "توانمند", "icon": "✓"},
    "developing": {"min_score": 40, "color": "yellow", "label": "در حال رشد", "icon": "📈"},
    "novice": {"min_score": 0, "color": "gray", "label": "مبتدی", "icon": "🌱"}
}


class ModelCapabilityTester:
    """
    سرویس تست توانایی مدل‌ها

    این سرویس:
    1. سوالات استاندارد از مدل می‌پرسد
    2. پاسخ‌ها را ارزیابی می‌کند
    3. نتایج را به صورت badge ذخیره می‌کند
    """

    def __init__(self, ai_manager=None):
        self.ai_manager = ai_manager
        self._test_results: Dict[str, Dict] = {}  # Cache of test results

    async def test_model(self, model_id: str, categories: List[str] = None) -> Dict[str, Any]:
        """
        تست یک مدل با سوالات استاندارد

        Args:
            model_id: شناسه مدل
            categories: دسته‌بندی‌های تست (خالی = همه)

        Returns:
            نتایج تست با badge ها
        """
        logger.info(f"🧪 Testing model capabilities: {model_id}")

        # 🔴 چک کردن فعال بودن مدل در تنظیمات
        try:
            from ..core.database import get_db
            from ..models.ai_profile import ModelSettings
            db = next(get_db())
            db_setting = db.query(ModelSettings).filter(ModelSettings.model_id == model_id).first()
            if db_setting and not db_setting.enabled:
                logger.warning(f"Model {model_id} is disabled, skipping test")
                return {
                    "model_id": model_id,
                    "tested_at": datetime.now().isoformat(),
                    "error": "این مدل غیرفعال است",
                    "disabled": True,
                    "overall_score": 0,
                    "badges": [],
                    "categories": {}
                }
        except Exception as e:
            logger.debug(f"Could not check model settings: {e}")

        start_time = time.time()

        results = {
            "model_id": model_id,
            "tested_at": datetime.now().isoformat(),
            "categories": {},
            "overall_score": 0,
            "badges": [],
            "self_description": {},
            "strengths": [],
            "weaknesses": []
        }

        # انتخاب سوالات
        questions = CAPABILITY_TEST_QUESTIONS
        if categories:
            questions = {k: v for k, v in questions.items() if v["category"] in categories}

        total_weight = sum(q["weight"] for q in questions.values())
        weighted_score = 0

        # اجرای تست‌ها
        for test_name, test_config in questions.items():
            logger.info(f"  Running test: {test_name}")

            try:
                response = await self._run_single_test(model_id, test_config["prompt"])
                parsed = self._parse_response(response, test_name)

                # استخراج نمره
                score = parsed.get("score", 50)
                if test_name == "self_introduction":
                    results["self_description"] = parsed
                    score = 100 if parsed.get("strengths") else 50

                category = test_config["category"]
                if category not in results["categories"]:
                    results["categories"][category] = {
                        "tests": [],
                        "avg_score": 0
                    }

                results["categories"][category]["tests"].append({
                    "name": test_name,
                    "score": score,
                    "response": parsed
                })

                weighted_score += score * test_config["weight"]

            except Exception as e:
                logger.error(f"  Error in test {test_name}: {e}")
                results["categories"].setdefault(test_config["category"], {
                    "tests": [],
                    "avg_score": 0
                })["tests"].append({
                    "name": test_name,
                    "score": 0,
                    "error": str(e)
                })

        # محاسبه نمره کلی
        results["overall_score"] = weighted_score / total_weight if total_weight > 0 else 0

        # محاسبه میانگین هر دسته
        for category, data in results["categories"].items():
            scores = [t["score"] for t in data["tests"] if "score" in t]
            data["avg_score"] = sum(scores) / len(scores) if scores else 0

        # تعیین badge ها
        results["badges"] = self._determine_badges(results)

        # تعیین نقاط قوت و ضعف
        results["strengths"], results["weaknesses"] = self._analyze_strengths_weaknesses(results)

        results["elapsed_time"] = time.time() - start_time

        # ذخیره در cache
        self._test_results[model_id] = results

        logger.info(f"🧪 Test completed for {model_id}: overall={results['overall_score']:.1f}, badges={len(results['badges'])}")

        return results

    async def _run_single_test(self, model_id: str, prompt: str) -> str:
        """اجرای یک تست"""
        if not self.ai_manager:
            raise ValueError("AI Manager not available")

        messages = [
            Message(role="system", content="تو یک دستیار هوشمند هستی. فقط خروجی JSON برگردان."),
            Message(role="user", content=prompt)
        ]

        response = await self.ai_manager.generate(
            model_id=model_id,
            messages=messages,
            max_tokens=2000,
            temperature=0.3
        )

        if hasattr(response, 'content'):
            return response.content
        return str(response)

    def _parse_response(self, response: str, test_name: str) -> Dict:
        """پارس پاسخ مدل"""
        import re

        try:
            # پیدا کردن JSON در پاسخ
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        # اگر JSON نبود، تلاش برای استخراج نمره
        score = 50  # default
        if "score" in response.lower():
            numbers = re.findall(r'\d+', response)
            if numbers:
                score = min(100, max(0, int(numbers[-1])))

        return {"raw_response": response, "score": score}

    def _determine_badges(self, results: Dict) -> List[Dict]:
        """تعیین badge ها بر اساس نمرات"""
        badges = []

        # Badge کلی
        overall = results["overall_score"]
        for badge_id, badge_config in CAPABILITY_BADGES.items():
            if overall >= badge_config["min_score"]:
                badges.append({
                    "type": "overall",
                    "badge_id": badge_id,
                    "label": badge_config["label"],
                    "icon": badge_config["icon"],
                    "color": badge_config["color"],
                    "score": overall
                })
                break

        # Badge های دسته‌بندی
        category_badges_map = {
            "code_analysis": ("code_reviewer", "تحلیل‌گر کد", "🔍"),
            "code_generation": ("code_generator", "کدنویس", "💻"),
            "security": ("security_expert", "متخصص امنیت", "🔒"),
            "problem_solving": ("problem_solver", "حل‌کننده مسئله", "🧩"),
            "documentation": ("documenter", "مستندنگار", "📝"),
            "language": ("linguist", "زبان‌شناس", "🌐"),
            "reasoning": ("logician", "منطق‌دان", "🎓")
        }

        for category, data in results["categories"].items():
            if data["avg_score"] >= 75:  # فقط اگر خوب باشد
                if category in category_badges_map:
                    badge_info = category_badges_map[category]
                    badges.append({
                        "type": "category",
                        "category": category,
                        "badge_id": badge_info[0],
                        "label": badge_info[1],
                        "icon": badge_info[2],
                        "color": "blue" if data["avg_score"] >= 85 else "green",
                        "score": data["avg_score"]
                    })

        return badges

    def _analyze_strengths_weaknesses(self, results: Dict) -> tuple:
        """تحلیل نقاط قوت و ضعف"""
        strengths = []
        weaknesses = []

        for category, data in results["categories"].items():
            avg = data["avg_score"]
            if avg >= 75:
                strengths.append({"category": category, "score": avg})
            elif avg < 50:
                weaknesses.append({"category": category, "score": avg})

        # مرتب‌سازی
        strengths.sort(key=lambda x: x["score"], reverse=True)
        weaknesses.sort(key=lambda x: x["score"])

        return strengths[:3], weaknesses[:3]

    def get_cached_results(self, model_id: str) -> Optional[Dict]:
        """دریافت نتایج cache شده"""
        return self._test_results.get(model_id)

    async def test_all_models(self) -> Dict[str, Dict]:
        """تست همه مدل‌های موجود"""
        if not self.ai_manager:
            return {}

        results = {}
        models = self.ai_manager.get_available_models()

        for model in models:
            try:
                result = await self.test_model(model.id)
                results[model.id] = result
            except Exception as e:
                logger.error(f"Error testing {model.id}: {e}")
                results[model.id] = {"error": str(e)}

        return results


# Singleton instance
_capability_tester: Optional[ModelCapabilityTester] = None


def get_capability_tester(ai_manager=None) -> ModelCapabilityTester:
    """دریافت نمونه ModelCapabilityTester"""
    global _capability_tester
    if _capability_tester is None:
        _capability_tester = ModelCapabilityTester(ai_manager)
    elif ai_manager and not _capability_tester.ai_manager:
        _capability_tester.ai_manager = ai_manager
    return _capability_tester
