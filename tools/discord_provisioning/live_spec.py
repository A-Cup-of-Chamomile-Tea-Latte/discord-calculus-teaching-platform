"""Authoritative live Discord infrastructure specification for the allowlisted test Guild."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoleSpec:
    key: str
    name: str


@dataclass(frozen=True, slots=True)
class CategorySpec:
    key: str
    name: str


@dataclass(frozen=True, slots=True)
class ChannelSpec:
    key: str
    name: str
    kind: str
    category_key: str
    policy: str
    topic: str | None = None
    managed_case: bool = False


ROLES = (
    RoleSpec("role.admin", "Admin"),
    RoleSpec("role.staff", "Staff / TA"),
    RoleSpec("role.verified_member", "Verified Member"),
    RoleSpec("role.guest", "Guest"),
)

CATEGORIES = (
    CategorySpec("category.information", "資訊 / Information"),
    CategorySpec("category.question", "課程問題 / Question"),
    CategorySpec("category.community", "一般交流 / Community"),
    CategorySpec("category.private_support", "隱密案件 / Private Support"),
    CategorySpec("category.voice", "語音與視訊 / Voice Chat"),
    CategorySpec("category.staff", "教學團隊 / Staff"),
)

CHANNELS = (
    ChannelSpec("channel.welcome", "welcome", "text", "category.information", "welcome"),
    ChannelSpec(
        "forum.announcements",
        "公告-announcements",
        "forum",
        "category.information",
        "staff_forum",
        "課程公告與伺服器規範。",
    ),
    ChannelSpec(
        "forum.course_resources",
        "課程資源-course-resources",
        "forum",
        "category.information",
        "member_forum",
        "教材、題目、工具與參考資料；不建立案件。",
    ),
    ChannelSpec(
        "forum.faq",
        "常見問答-faq",
        "forum",
        "category.information",
        "staff_forum",
        "常見問題整理；一般成員唯讀。",
    ),
    ChannelSpec(
        "forum.math_questions",
        "數學問題-math-questions",
        "forum",
        "category.question",
        "case_forum",
        "微積分與數學觀念、計算及解題討論。",
        True,
    ),
    ChannelSpec(
        "forum.coursework_systems",
        "課務與系統-coursework-systems",
        "forum",
        "category.question",
        "case_forum",
        "作業、評量、NTU COOL 與課程系統問題。",
        True,
    ),
    ChannelSpec(
        "forum.other_questions",
        "其他問題-other-questions",
        "forum",
        "category.question",
        "case_forum",
        "其他適合保留脈絡的課程問題。",
        True,
    ),
    ChannelSpec("channel.zh_chat", "中文聊天", "text", "category.community", "member_text"),
    ChannelSpec("channel.en_chat", "english-chat", "text", "category.community", "member_text"),
    ChannelSpec(
        "forum.error_report",
        "錯誤回報-error-report",
        "forum",
        "category.community",
        "member_forum",
        "回報教材、系統或伺服器錯誤；不建立案件。",
    ),
    ChannelSpec("voice.office_hours", "Office Hours", "voice", "category.voice", "member_voice"),
    ChannelSpec("voice.study_room", "Study Room", "voice", "category.voice", "member_voice"),
    ChannelSpec("channel.staff_chat", "staff-chat", "text", "category.staff", "staff_only"),
    ChannelSpec("channel.bot_control", "bot-control", "text", "category.staff", "staff_bot"),
    ChannelSpec("channel.system_log", "system-log", "text", "category.staff", "staff_bot"),
)

MANAGED_FORUM_KEYS = frozenset(
    {
        "forum.math_questions",
        "forum.coursework_systems",
        "forum.other_questions",
    }
)

WELCOME_CONTENT = """歡迎加入本課程 Discord。

請先閱讀「公告 / Announcements」中的
「伺服器使用總則 / Server Guidelines」。

完成 Email 認證後，可使用課程問題、一般交流及語音與視訊頻道。
認證入口會在 Portal 串接完成後提供。

課程問題請依類型發表於：
- 數學問題
- 課務與系統
- 其他問題

教材與參考資料請查看「課程資源」；
常見問題請先查看「常見問答」。

涉及個人資料、成績或不適合公開討論的內容，
請使用「隱密案件 / Private Support」。

正式教材、作業、成績、截止日期與課程公告仍以 NTU COOL 為準。"""

GUIDELINES_TITLE = "伺服器使用總則 / Server Guidelines"
GUIDELINES_CONTENT = """- 請依各頻道用途發文，避免重複洗版。
- 不得冒充教學團隊、管理員、官方帳號或機器人。
- 不得公開他人的個人資料、成績或私人對話。
- 個人資料、成績及私人課務問題請使用 Private Support。
- 語音與視訊空間不錄音，也不自動轉錄。
- 課程正式資料仍以 NTU COOL 為準。
- 管理團隊可在必要時整理、移動或移除明顯違反規範的內容。"""


def validate_spec() -> None:
    resources = [item.key for item in (*ROLES, *CATEGORIES, *CHANNELS)]
    if len(resources) != len(set(resources)):
        raise ValueError("duplicate logical key in live provisioning spec")
    names_by_kind: dict[str, set[str]] = {}
    for item in CHANNELS:
        if item.kind not in {"text", "forum", "voice"}:
            raise ValueError(f"unsupported channel kind: {item.kind}")
        if item.category_key not in {category.key for category in CATEGORIES}:
            raise ValueError(f"unknown category key: {item.category_key}")
        if item.name in names_by_kind.setdefault(item.kind, set()):
            raise ValueError(f"duplicate {item.kind} channel name: {item.name}")
        names_by_kind[item.kind].add(item.name)
    actual_managed = {item.key for item in CHANNELS if item.managed_case}
    if actual_managed != MANAGED_FORUM_KEYS:
        raise ValueError("managed_case flags do not match the approved three forums")
    if any(re.fullmatch(r"C\d\d", role.name) for role in ROLES):
        raise ValueError("Cxx roles are forbidden")


validate_spec()
