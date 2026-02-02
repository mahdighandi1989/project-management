# -*- coding: utf-8 -*-
"""
🔀 GitHub Pull Request Service
سرویس ایجاد و مدیریت Pull Request در GitHub

قابلیت‌ها:
1. ایجاد branch جدید
2. Commit تغییرات
3. ایجاد Pull Request
4. Push ایرادات به GitHub Issues
"""

import os
import json
import base64
import logging
import aiohttp
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.logging_utils import StructuredLogger

logger = logging.getLogger(__name__)
slog = StructuredLogger(__name__, "GITHUB_PR")


class GitHubPRService:
    """سرویس مدیریت Pull Request و Issues در GitHub"""

    GITHUB_API = "https://api.github.com"

    def __init__(self):
        self.default_token = os.environ.get("GITHUB_TOKEN", "")
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """دریافت یا ایجاد session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """بستن session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _get_headers(self, token: str = None) -> Dict[str, str]:
        """ساخت headers"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Creator-Engine/1.0"
        }
        use_token = token or self.default_token
        if use_token:
            headers["Authorization"] = f"token {use_token}"
        return headers

    def _parse_repo_url(self, github_path: str) -> Dict[str, str]:
        """استخراج owner و repo از URL یا path"""
        if not github_path:
            return {"owner": "", "repo": ""}

        # حذف .git از انتها
        github_path = github_path.replace(".git", "").strip("/")

        # اگر URL کامل است
        if "github.com" in github_path:
            parts = github_path.split("github.com/")[-1].split("/")
            if len(parts) >= 2:
                return {"owner": parts[0], "repo": parts[1]}

        # اگر فقط owner/repo است
        if "/" in github_path:
            parts = github_path.split("/")
            return {"owner": parts[0], "repo": parts[1] if len(parts) > 1 else ""}

        return {"owner": "", "repo": ""}

    # =====================================
    # Branch Operations
    # =====================================

    async def get_default_branch(
        self,
        owner: str,
        repo: str,
        token: str = None
    ) -> Optional[str]:
        """دریافت branch پیش‌فرض"""
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("default_branch", "main")
        except Exception as e:
            slog.error("Failed to get default branch", exception=e)

        return "main"

    async def get_branch_sha(
        self,
        owner: str,
        repo: str,
        branch: str,
        token: str = None
    ) -> Optional[str]:
        """دریافت SHA آخرین commit یک branch"""
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}/git/ref/heads/{branch}"
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("object", {}).get("sha")
        except Exception as e:
            slog.error("Failed to get branch SHA", exception=e)

        return None

    async def create_branch(
        self,
        owner: str,
        repo: str,
        new_branch: str,
        base_branch: str = None,
        token: str = None
    ) -> Dict[str, Any]:
        """ایجاد branch جدید"""
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            # دریافت branch پیش‌فرض
            if not base_branch:
                base_branch = await self.get_default_branch(owner, repo, token)

            # دریافت SHA base branch
            sha = await self.get_branch_sha(owner, repo, base_branch, token)
            if not sha:
                return {
                    "success": False,
                    "error": f"Branch '{base_branch}' not found"
                }

            # ایجاد branch جدید
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}/git/refs"
            payload = {
                "ref": f"refs/heads/{new_branch}",
                "sha": sha
            }

            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 201:
                    slog.success("Branch created", branch=new_branch)
                    return {
                        "success": True,
                        "branch": new_branch,
                        "sha": sha
                    }
                elif response.status == 422:
                    # Branch already exists
                    return {
                        "success": True,
                        "branch": new_branch,
                        "already_exists": True
                    }
                else:
                    error = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to create branch: {error}"
                    }

        except Exception as e:
            slog.error("Create branch failed", exception=e)
            return {"success": False, "error": str(e)}

    # =====================================
    # File Operations
    # =====================================

    async def get_file_sha(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: str = None,
        token: str = None
    ) -> Optional[str]:
        """دریافت SHA یک فایل (برای update)"""
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
            if branch:
                url += f"?ref={branch}"

            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("sha")
        except Exception:
            pass

        return None

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = None,
        token: str = None
    ) -> Dict[str, Any]:
        """ایجاد یا به‌روزرسانی فایل"""
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}/contents/{path}"

            # Encode content
            content_bytes = content.encode('utf-8')
            content_b64 = base64.b64encode(content_bytes).decode('utf-8')

            payload = {
                "message": message,
                "content": content_b64
            }

            if branch:
                payload["branch"] = branch

            # بررسی وجود فایل برای update
            sha = await self.get_file_sha(owner, repo, path, branch, token)
            if sha:
                payload["sha"] = sha

            async with session.put(url, headers=headers, json=payload) as response:
                if response.status in [200, 201]:
                    data = await response.json()
                    return {
                        "success": True,
                        "sha": data.get("content", {}).get("sha"),
                        "path": path
                    }
                else:
                    error = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to create/update file: {error}"
                    }

        except Exception as e:
            slog.error("File operation failed", exception=e)
            return {"success": False, "error": str(e)}

    # =====================================
    # Pull Request Operations
    # =====================================

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = None,
        token: str = None,
        draft: bool = False
    ) -> Dict[str, Any]:
        """ایجاد Pull Request"""
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            if not base_branch:
                base_branch = await self.get_default_branch(owner, repo, token)

            url = f"{self.GITHUB_API}/repos/{owner}/{repo}/pulls"
            payload = {
                "title": title,
                "body": body,
                "head": head_branch,
                "base": base_branch,
                "draft": draft
            }

            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 201:
                    data = await response.json()
                    slog.success("Pull request created", pr_number=data.get("number"))
                    return {
                        "success": True,
                        "pr_number": data.get("number"),
                        "pr_url": data.get("html_url"),
                        "state": data.get("state")
                    }
                else:
                    error = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to create PR: {error}"
                    }

        except Exception as e:
            slog.error("Create PR failed", exception=e)
            return {"success": False, "error": str(e)}

    async def create_pr_with_changes(
        self,
        github_path: str,
        branch_name: str,
        title: str,
        description: str,
        files: List[Dict[str, str]],
        token: str = None
    ) -> Dict[str, Any]:
        """
        ایجاد PR با تغییرات

        Args:
            github_path: owner/repo یا full URL
            branch_name: نام branch جدید
            title: عنوان PR
            description: توضیحات PR
            files: لیست فایل‌ها [{path: str, content: str}]
        """
        parsed = self._parse_repo_url(github_path)
        owner, repo = parsed["owner"], parsed["repo"]

        if not owner or not repo:
            return {"success": False, "error": "Invalid GitHub path"}

        slog.info("Creating PR with changes",
            owner=owner, repo=repo, branch=branch_name, files_count=len(files)
        )

        # 1. ایجاد branch
        branch_result = await self.create_branch(owner, repo, branch_name, token=token)
        if not branch_result.get("success"):
            return branch_result

        # 2. Commit فایل‌ها
        for file in files:
            file_result = await self.create_or_update_file(
                owner=owner,
                repo=repo,
                path=file["path"],
                content=file["content"],
                message=f"Add/Update {file['path']}",
                branch=branch_name,
                token=token
            )
            if not file_result.get("success"):
                return file_result

        # 3. ایجاد PR
        pr_result = await self.create_pull_request(
            owner=owner,
            repo=repo,
            title=title,
            body=description,
            head_branch=branch_name,
            token=token
        )

        return pr_result

    # =====================================
    # GitHub Issues Operations
    # =====================================

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        labels: List[str] = None,
        token: str = None
    ) -> Dict[str, Any]:
        """ایجاد Issue در GitHub"""
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}/issues"
            payload = {
                "title": title,
                "body": body
            }
            if labels:
                payload["labels"] = labels

            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 201:
                    data = await response.json()
                    slog.success("Issue created", issue_number=data.get("number"))
                    return {
                        "success": True,
                        "issue_number": data.get("number"),
                        "issue_url": data.get("html_url")
                    }
                else:
                    error = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to create issue: {error}"
                    }

        except Exception as e:
            slog.error("Create issue failed", exception=e)
            return {"success": False, "error": str(e)}

    async def push_issues_to_github(
        self,
        github_path: str,
        issues: List[Dict[str, Any]],
        token: str = None
    ) -> Dict[str, Any]:
        """
        Push ایرادات به GitHub Issues

        Args:
            github_path: owner/repo یا full URL
            issues: لیست ایرادات از issues_found پروژه
        """
        parsed = self._parse_repo_url(github_path)
        owner, repo = parsed["owner"], parsed["repo"]

        if not owner or not repo:
            return {"success": False, "error": "Invalid GitHub path"}

        results = {
            "success": True,
            "created": 0,
            "failed": 0,
            "issues": []
        }

        for issue in issues:
            # ساخت عنوان و بدنه
            title = f"[Auto] {issue.get('error_type', 'Issue')}: {issue.get('message', '')[:80]}"

            body = f"""## توضیحات
{issue.get('description', issue.get('message', 'No description'))}

## علل احتمالی
{self._format_list(issue.get('possible_causes', []))}

## پیشنهاد رفع
{issue.get('suggested_fix', 'بررسی دستی نیاز است')}

## اطلاعات اضافی
- **نوع خطا:** {issue.get('error_type', 'unknown')}
- **اولویت:** {issue.get('priority', 'medium')}
- **منبع:** {issue.get('source', 'unknown')}
- **تعداد وقوع:** {issue.get('occurrence_count', 1)}
- **آخرین وقوع:** {issue.get('last_occurrence', 'N/A')}

---
*این Issue به صورت خودکار توسط سیستم تحلیل ایجاد شده است.*
"""

            # تعیین labels
            labels = ["auto-generated"]
            priority = issue.get("priority", "medium")
            if priority == "high" or priority == "critical":
                labels.append("priority: high")
            elif priority == "low":
                labels.append("priority: low")

            if issue.get("error_type"):
                labels.append(f"type: {issue.get('error_type')}")

            # ایجاد issue
            result = await self.create_issue(
                owner=owner,
                repo=repo,
                title=title,
                body=body,
                labels=labels,
                token=token
            )

            if result.get("success"):
                results["created"] += 1
                results["issues"].append({
                    "local_id": issue.get("id"),
                    "github_issue": result.get("issue_number"),
                    "url": result.get("issue_url")
                })
            else:
                results["failed"] += 1

        if results["failed"] > 0:
            results["success"] = results["created"] > 0

        slog.info("Push issues completed",
            created=results["created"], failed=results["failed"]
        )

        return results

    def _format_list(self, items: List[str]) -> str:
        """فرمت لیست به Markdown"""
        if not items:
            return "- نامشخص"
        return "\n".join(f"- {item}" for item in items)

    async def get_repo_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        labels: str = None,
        token: str = None
    ) -> Dict[str, Any]:
        """دریافت Issues یک repository"""
        session = await self._get_session()
        headers = self._get_headers(token)

        try:
            url = f"{self.GITHUB_API}/repos/{owner}/{repo}/issues"
            params = {"state": state}
            if labels:
                params["labels"] = labels

            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "success": True,
                        "issues": [
                            {
                                "number": issue.get("number"),
                                "title": issue.get("title"),
                                "state": issue.get("state"),
                                "url": issue.get("html_url"),
                                "labels": [l.get("name") for l in issue.get("labels", [])],
                                "created_at": issue.get("created_at")
                            }
                            for issue in data
                            if not issue.get("pull_request")  # فیلتر PRها
                        ]
                    }
                else:
                    error = await response.text()
                    return {"success": False, "error": error}

        except Exception as e:
            slog.error("Get issues failed", exception=e)
            return {"success": False, "error": str(e)}


# =====================================================
# Singleton Instance
# =====================================================

_github_pr_instance: Optional[GitHubPRService] = None


def get_github_pr_service() -> GitHubPRService:
    """دریافت نمونه GitHubPRService"""
    global _github_pr_instance
    if _github_pr_instance is None:
        _github_pr_instance = GitHubPRService()
    return _github_pr_instance
