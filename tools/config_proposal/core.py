"""Single-source proposed config loader, validator, and deterministic docs generator."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from jsonschema import Draft202012Validator

Severity = Literal["ERROR", "WARNING"]
Document = dict[str, Any]

CONFIG_FILES = {
    "server": "server.yaml",
    "portal": "portal.yaml",
    "workflow": "case-workflow.yaml",
    "data_policy": "data-policy.yaml",
}

SCHEMA_FILES = {
    "server": "server.schema.json",
    "portal": "portal.schema.json",
    "workflow": "case-workflow.schema.json",
    "data_policy": "data-policy.schema.json",
}

BOT_PERMISSION_ALLOWLIST = frozenset(
    {
        "VIEW_CHANNEL",
        "SEND_MESSAGES",
        "SEND_MESSAGES_IN_THREADS",
        "CREATE_PUBLIC_THREADS",
        "READ_MESSAGE_HISTORY",
        "EMBED_LINKS",
        "ATTACH_FILES",
        "MANAGE_THREADS",
        "MANAGE_NICKNAMES",
        "MANAGE_ROLES",
        "MANAGE_CHANNELS",
        "USE_APPLICATION_COMMANDS",
    }
)


@dataclass(frozen=True)
class ConfigBundle:
    server: Document
    portal: Document
    workflow: Document
    data_policy: Document


@dataclass(frozen=True)
class ValidationIssue:
    severity: Severity
    code: str
    path: str
    message: str


def _read_document(path: Path) -> Document:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON-compatible YAML object")
    return value


def load_bundle(root: Path) -> ConfigBundle:
    config_dir = root / "config" / "proposed"
    loaded = {key: _read_document(config_dir / filename) for key, filename in CONFIG_FILES.items()}
    return ConfigBundle(
        server=loaded["server"],
        portal=loaded["portal"],
        workflow=loaded["workflow"],
        data_policy=loaded["data_policy"],
    )


def _schema_issues(root: Path, bundle: ConfigBundle) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    values = {
        "server": bundle.server,
        "portal": bundle.portal,
        "workflow": bundle.workflow,
        "data_policy": bundle.data_policy,
    }
    for key, filename in SCHEMA_FILES.items():
        schema = _read_document(root / "config" / "schema" / filename)
        validator = Draft202012Validator(schema)
        for error in sorted(validator.iter_errors(values[key]), key=lambda item: list(item.path)):
            location = ".".join(str(part) for part in error.absolute_path) or "$"
            issues.append(
                ValidationIssue(
                    "ERROR",
                    "SCHEMA",
                    f"{CONFIG_FILES[key]}:{location}",
                    error.message,
                )
            )
    return issues


def _duplicates(items: list[Document], field: str) -> set[str]:
    counts = Counter(str(item.get(field, "")) for item in items)
    return {value for value, count in counts.items() if value and count > 1}


def _custom_server_issues(server: Document) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    roles = list(server.get("roles", []))
    categories = list(server.get("categories", []))
    channels = list(server.get("channels", []))
    role_keys = {str(item.get("key")) for item in roles}
    category_keys = {str(item.get("key")) for item in categories}

    for field, items, code in (
        ("key", roles, "DUPLICATE_ROLE_KEY"),
        ("name", roles, "DUPLICATE_ROLE_NAME"),
        ("key", categories, "DUPLICATE_CATEGORY_KEY"),
        ("name", categories, "DUPLICATE_CATEGORY_NAME"),
        ("key", channels, "DUPLICATE_CHANNEL_KEY"),
        ("name", channels, "DUPLICATE_CHANNEL_NAME"),
    ):
        for value in sorted(_duplicates(items, field)):
            issues.append(
                ValidationIssue("ERROR", code, f"server.{field}", f"duplicate value: {value}")
            )

    for channel in channels:
        key = str(channel.get("key"))
        parent = str(channel.get("parent"))
        if parent not in category_keys:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    "MISSING_PARENT",
                    f"server.channels.{key}.parent",
                    f"unknown category: {parent}",
                )
            )
        permissions = channel.get("permissions", {})
        if not isinstance(permissions, dict):
            continue
        for actor, raw_decision in permissions.items():
            if actor not in role_keys:
                issues.append(
                    ValidationIssue(
                        "ERROR",
                        "UNKNOWN_ROLE_REFERENCE",
                        f"server.channels.{key}.permissions.{actor}",
                        "permission actor is not a declared role",
                    )
                )
                continue
            if not isinstance(raw_decision, dict):
                continue
            allow = set(raw_decision.get("allow", []))
            deny = set(raw_decision.get("deny", []))
            contradiction = allow & deny
            if contradiction:
                issues.append(
                    ValidationIssue(
                        "ERROR",
                        "CONTRADICTORY_PERMISSION",
                        f"server.channels.{key}.permissions.{actor}",
                        f"same permission is allowed and denied: {sorted(contradiction)}",
                    )
                )
        if channel.get("type") != "FORUM" and channel.get("forumTags"):
            issues.append(
                ValidationIssue(
                    "ERROR",
                    "TAGS_ON_NON_FORUM",
                    f"server.channels.{key}.forumTags",
                    "only forum channels may declare tags",
                )
            )
        if len(channel.get("forumTags", [])) > 20:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    "FORUM_TAG_LIMIT",
                    f"server.channels.{key}.forumTags",
                    "Discord forum tag limit exceeded",
                )
            )
        dump_decision = permissions.get("dump_bot", {})
        dump_allow = set(dump_decision.get("allow", []))
        if parent in {"questions", "resources"}:
            if not {"VIEW", "EXPORT"} <= dump_allow:
                issues.append(
                    ValidationIssue(
                        "ERROR",
                        "DUMP_BOT_READ_SCOPE_MISSING",
                        f"server.channels.{key}.permissions.dump_bot",
                        "public archive scope must explicitly allow VIEW and EXPORT",
                    )
                )
            write_permissions = dump_allow & {"POST", "REPLY", "MANAGE"}
            if write_permissions:
                issues.append(
                    ValidationIssue(
                        "ERROR",
                        "DUMP_BOT_PUBLIC_WRITE_FORBIDDEN",
                        f"server.channels.{key}.permissions.dump_bot",
                        f"public archive scope must stay read-only: {sorted(write_permissions)}",
                    )
                )

    private_channel = next(
        (item for item in channels if item.get("key") == "private_case_template"), None
    )
    if private_channel:
        private_permissions = private_channel.get("permissions", {})
        for actor in ("student", "guest"):
            decision = private_permissions.get(actor, {})
            if "VIEW" in set(decision.get("allow", [])) or "VIEW" not in set(
                decision.get("deny", [])
            ):
                issues.append(
                    ValidationIssue(
                        "ERROR",
                        "PRIVATE_SUPPORT_LEAK",
                        f"server.channels.private_case_template.permissions.{actor}",
                        "general learners must be denied visibility",
                    )
                )

    for bot in server.get("botPermissions", []):
        bot_key = str(bot.get("key"))
        permissions = set(bot.get("permissions", []))
        if "ADMINISTRATOR" in permissions:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    "ADMINISTRATOR_FORBIDDEN",
                    f"server.botPermissions.{bot_key}",
                    "bots must never receive Administrator",
                )
            )
        unsupported = permissions - BOT_PERMISSION_ALLOWLIST
        if unsupported:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    "BOT_PERMISSION_NOT_ALLOWLISTED",
                    f"server.botPermissions.{bot_key}",
                    f"unsupported permissions: {sorted(unsupported)}",
                )
            )
        scopes = set(bot.get("scopedAreas", []))
        if not scopes <= category_keys:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    "UNKNOWN_BOT_SCOPE",
                    f"server.botPermissions.{bot_key}",
                    f"unknown scoped areas: {sorted(scopes - category_keys)}",
                )
            )
        if bot_key == "dump_bot" and "community" in scopes:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    "DUMP_BOT_SCOPE_TOO_BROAD",
                    f"server.botPermissions.{bot_key}",
                    "community dump/analysis is unresolved and must remain outside scope",
                )
            )
    return issues


def _workflow_issues(workflow: Document) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    states = list(workflow.get("states", []))
    state_keys = {str(item.get("key")) for item in states}
    for duplicate in sorted(_duplicates(states, "key")):
        issues.append(
            ValidationIssue(
                "ERROR", "DUPLICATE_STATE", "workflow.states", f"duplicate state: {duplicate}"
            )
        )
    for index, transition in enumerate(workflow.get("transitions", [])):
        source = str(transition.get("from"))
        target = str(transition.get("to"))
        if source not in state_keys or target not in state_keys:
            issues.append(
                ValidationIssue(
                    "ERROR",
                    "INVALID_STATE_TRANSITION",
                    f"workflow.transitions.{index}",
                    f"unknown state reference: {source} -> {target}",
                )
            )
    return issues


def _portal_issues(portal: Document, workflow: Document) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    pages = list(portal.get("pages", []))
    for field, code in (("key", "DUPLICATE_PAGE_KEY"), ("path", "DUPLICATE_PAGE_PATH")):
        for value in sorted(_duplicates(pages, field)):
            issues.append(
                ValidationIssue("ERROR", code, f"portal.pages.{field}", f"duplicate: {value}")
            )
    submission_fields = set(portal.get("submissionFields", []))
    required_fields = {
        "forum",
        "title",
        "content",
        "classCode",
        "module",
        "mainTag",
        "aiPermission",
    }
    missing = required_fields - submission_fields
    if missing:
        issues.append(
            ValidationIssue(
                "ERROR",
                "PORTAL_CASE_FIELD_DRIFT",
                "portal.submissionFields",
                f"required workflow fields missing: {sorted(missing)}",
            )
        )
    if workflow.get("aiPermission", {}).get("preselected") is not False:
        issues.append(
            ValidationIssue(
                "ERROR",
                "AI_CHOICE_PRESELECTED",
                "workflow.aiPermission.preselected",
                "AI Yes/No must be explicit and unselected",
            )
        )
    return issues


def _drift_warnings(root: Path) -> list[ValidationIssue]:
    stale_tokens = {
        "ANSWERED",
        "TEMPORARILY_CLOSED",
        "REOPENED",
        "WAITING_FOR_STUDENT",
        "ESCALATED",
    }
    matches: Counter[str] = Counter()
    scan_roots = (root / "apps" / "portal" / "src", root / "fixtures", root / "contracts")
    allowed_suffixes = {".astro", ".ts", ".json", ".md"}
    for scan_root in scan_roots:
        for path in scan_root.rglob("*"):
            if not path.is_file() or path.suffix not in allowed_suffixes:
                continue
            text = path.read_text(encoding="utf-8")
            for token in stale_tokens:
                if token in text:
                    matches[token] += 1
    if not matches:
        return []
    summary = ", ".join(f"{token} ({count} files)" for token, count in sorted(matches.items()))
    return [
        ValidationIssue(
            "WARNING",
            "LEGACY_STATUS_DRIFT",
            "apps/portal|fixtures|contracts",
            f"legacy Task 34 states remain for compatibility: {summary}",
        )
    ]


def validate_bundle(root: Path, bundle: ConfigBundle) -> tuple[ValidationIssue, ...]:
    issues = _schema_issues(root, bundle)
    issues.extend(_custom_server_issues(bundle.server))
    issues.extend(_workflow_issues(bundle.workflow))
    issues.extend(_portal_issues(bundle.portal, bundle.workflow))
    issues.extend(_drift_warnings(root))
    return tuple(issues)


def _frontmatter(title: str, notice: str) -> list[str]:
    return [
        f"# {title}",
        "",
        (
            "> 由 `python -m tools.config_proposal generate` 自動產生。"
            "請修改 `config/proposed/`，不要直接編輯本檔。"
        ),
        f"> {notice}",
        "",
    ]


def _channel_tree(server: Document) -> str:
    lines = _frontmatter("提案頻道樹", "本機提案；未套用至 Discord。")
    categories = list(server["categories"])
    channels = list(server["channels"])
    for category in categories:
        lines.append(f"## {category['name']}")
        lines.append("")
        selected = [item for item in channels if item["parent"] == category["key"]]
        for channel in selected:
            state = "第一版" if channel["enabled"] else "樣板／動態建立"
            case_flag = "案件" if channel["managedCase"] else "非案件"
            lines.append(
                f"- `{channel['name']}` — {channel['type']}；{state}；{case_flag}；"
                f"slowmode {channel['slowmodeSeconds']}s；archive {channel['autoArchiveMinutes']}m"
            )
        if not selected:
            lines.append("- 尚未定案")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _permission_matrix(server: Document) -> str:
    lines = _frontmatter("有效權限矩陣", "只顯示 proposed fixture 的合併結果。")
    actors = ["student", "guest", "staff", "course_assistant", "dump_bot"]
    lines.extend(
        [
            "| 區域 | Student | Guest | Staff | course_assistant | dump_bot |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for channel in server["channels"]:
        cells: list[str] = []
        permissions = channel["permissions"]
        for actor in actors:
            decision = permissions.get(actor)
            if not decision:
                cells.append("繼承／未指定")
                continue
            allow = "、".join(decision["allow"]) or "—"
            deny = "、".join(decision["deny"]) or "—"
            cells.append(f"允：{allow}<br>拒：{deny}")
        lines.append(f"| {channel['name']} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("`Administrator` 不得出現在任何 Bot 權限中。")
    return "\n".join(lines) + "\n"


def _forum_tags(server: Document) -> str:
    lines = _frontmatter("Forum 標籤", "每篇案件只有一個 main tag 進入標題。")
    for channel in server["channels"]:
        if channel["type"] != "FORUM":
            continue
        tags = "、".join(channel["forumTags"]) or "尚未設定"
        lines.append(f"- **{channel['name']}**：{tags}")
    lines.extend(
        [
            "",
            "最終 main tag 清單與同義詞策略仍需人工核准；目前清單用於本機展示與驗證。",
        ]
    )
    return "\n".join(lines) + "\n"


def _bot_permissions(server: Document) -> str:
    lines = _frontmatter("Bot 最小權限", "權限均為提案，沒有 live adapter 或套用入口。")
    for bot in server["botPermissions"]:
        lines.extend(
            [
                f"## `{bot['key']}`",
                "",
                f"- 權限：{', '.join(bot['permissions'])}",
                f"- 限定區域：{', '.join(bot['scopedAreas'])}",
                "",
            ]
        )
    lines.extend(
        [
            "共同禁止：`ADMINISTRATOR`、Kick、Ban，以及不受範圍限制的管理能力。",
        ]
    )
    return "\n".join(lines) + "\n"


def _case_lifecycle(workflow: Document) -> str:
    lines = _frontmatter("案件生命週期", "以最新 Discord Side CONFIG 為展示依據。")
    lines.extend(["## 狀態", ""])
    for state in workflow["states"]:
        lines.append(f"- **{state['label']}** (`{state['key']}`)：{state['description']}")
    lines.extend(["", "## 允許轉移", ""])
    for transition in workflow["transitions"]:
        lines.append(
            f"- `{transition['from']}` → `{transition['to']}`："
            f"`{transition['event']}`（{transition['actor']}）"
        )
    timers = workflow["timers"]
    lines.extend(
        [
            "",
            "## 計時",
            "",
            f"- TA 最後留言後 {timers['idleAfterHours']} 小時進入 Idle。",
            f"- Idle 後再 {timers['autoCloseAfterIdleHours']} 小時進入 Auto Closed。",
            "- 不做語意式「輪到誰」判斷。",
            "- Discord thread auto-archive 與產品案件狀態分離。",
        ]
    )
    return "\n".join(lines) + "\n"


def _portal_page_map(portal: Document) -> str:
    lines = _frontmatter("Portal 頁面地圖", "所有頁面只使用 fixtures。")
    lines.extend(
        [
            "| 路徑 | 頁面 | 對象 | 第一版本機展示 |",
            "| --- | --- | --- | --- |",
        ]
    )
    for page in portal["pages"]:
        lines.append(
            f"| `{page['path']}` | {page['label']} | {page['audience']} | "
            f"{'是' if page['enabled'] else '否'} |"
        )
    return "\n".join(lines) + "\n"


def _config_summary(bundle: ConfigBundle, issues: tuple[ValidationIssue, ...]) -> str:
    server = bundle.server
    portal = bundle.portal
    workflow = bundle.workflow
    lines = _frontmatter("提案設定摘要", "設定已驗證，但不是已套用 production 設定。")
    lines.extend(
        [
            f"- 來源：`{server['source']['package']}` / `{server['source']['document']}`",
            f"- 角色：{len(server['roles'])}",
            f"- 分類：{len(server['categories'])}",
            f"- 頻道／樣板：{len(server['channels'])}",
            f"- Portal 頁面：{len(portal['pages'])}",
            f"- 案件狀態：{len(workflow['states'])}",
            f"- 驗證錯誤：{sum(issue.severity == 'ERROR' for issue in issues)}",
            f"- 驗證警告：{sum(issue.severity == 'WARNING' for issue in issues)}",
            "",
            "## 安全邊界",
            "",
            "- `fixtureOnly=true`；不連 Discord、Google、Email、OAuth 或 AI API。",
            "- 沒有 `--apply`、token 欄位或部署入口。",
            "- 115-1 Class → Module 對照已經來源與課程 owner 確認；尚未套用至 Discord。",
            "- 資料保存政策與部分產品項目仍明確未決。",
        ]
    )
    return "\n".join(lines) + "\n"


def _drift_report(issues: tuple[ValidationIssue, ...]) -> str:
    lines = _frontmatter(
        "設定與程式差異", "警告不會被誤報為完成；實際 domain migration 仍須後續審查。"
    )
    lines.extend(
        [
            "| 等級 | 代碼 | 位置 | 說明 |",
            "| --- | --- | --- | --- |",
        ]
    )
    if not issues:
        lines.append("| — | — | — | 目前未偵測到差異 |")
    for issue in issues:
        lines.append(f"| {issue.severity} | `{issue.code}` | `{issue.path}` | {issue.message} |")
    lines.extend(
        [
            "",
            "## 已知主要差異",
            "",
            (
                "- Task 34 contracts 使用 `ANSWERED`、`TEMPORARILY_CLOSED`、"
                "`REOPENED` 等舊狀態；最新 Side CONFIG 使用 "
                "Open／Tracked／Idle／Closed／Auto Closed。"
            ),
            (
                "- 本輪 Portal 以顯示轉譯與新情境庫呈現最新提案；"
                "既有 fixture contracts 保留相容性並列為後續 domain migration。"
            ),
            (
                "- 115-1 已有 C01–C16 對應 M1–M4 的來源確認對照；"
                "Portal fixture 與實際 Discord membership 尚未套用。"
            ),
            (
                "- Canonical title 提案已更新為 `[M1 | C01][main tag] 標題`；"
                "正式 Discord runtime 仍使用舊格式，必須先接上可信任的 Class membership resolver。"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _decision_migration() -> str:
    rows = [
        ("身份模型", "Staff／Student／Guest／Bot；Module 是屬性", "程式落後設定"),
        (
            "班級與 Module",
            "C01–C04 → M1、C05–C09 → M2、C10–C13 → M3、C14–C16 → M4",
            "115-1 spec 已確認；尚未套用 Discord",
        ),
        ("學生暱稱", "Discord 身份或 Student_nnmmm", "只有假資料"),
        ("公開 Forum", "三個 Questions Forum", "一致"),
        ("Forum 標籤", "單一 main tag；最終清單未決", "設定仍未決"),
        ("學生直接發文", "本人發文，Bot 補欄位與整理標題", "程式落後設定"),
        ("Bot 標題整理", "[M#][main_tag] 使用者標題", "只有假資料"),
        ("網站代為發文", "完整結構化替代入口", "只有假資料"),
        ("匿名提問", "私有表單後由 Bot 直接代發", "一致"),
        ("Private Support", "每案暫時文字頻道", "需要真實服務測試"),
        ("案號", "Cxx-token-MMDD-HHMM[-P]", "一致"),
        ("案件狀態", "Open／Tracked／Idle／Closed／Auto Closed", "程式落後設定"),
        ("結案與自動結案", "48h 提醒＋48h 自動結案", "已被新規則取代"),
        ("AI 分析選項", "逐案明確 Yes／No、無預選", "一致"),
        ("course_assistant", "發文、狀態、Private Support writer", "只有假資料"),
        ("dump_bot", "讀取、保存、限定 log／private cleanup", "需要真實服務測試"),
        ("網頁案件欄位", "reduced projection＋完整 fixture 流程", "只有假資料"),
        ("Working／archive", "分離；實際儲存與 retention 未決", "設定仍未決"),
        ("三年證據", "Forum 案件化、低頻道數、單一主標籤", "一致"),
    ]
    lines = _frontmatter("決策遷移表", "最新設定優先於 Task 34 與更早共享背景。")
    lines.extend(
        [
            "| 項目 | 最新提案 | 狀態 |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(f"| {topic} | {decision} | {status} |" for topic, decision, status in rows)
    return "\n".join(lines) + "\n"


def _evidence_matrix() -> str:
    lines = _frontmatter(
        "三年證據到新設計矩陣",
        "只使用既有彙總報告；本輪沒有讀取新的歷史訊息正文或附件。",
    )
    lines.extend(
        [
            "| 彙總證據 | 判讀 | 設計影響 | 限制 |",
            "| --- | --- | --- | --- |",
            (
                "| 112 頻道多、無 Forum、權限與導覽較複雜 "
                "| 應避免按章節大量開頻道 | Module 作屬性；"
                "Questions 集中為三個 Forum | 112 有 8 個不可讀頻道 |"
            ),
            (
                "| 113、114 都使用四個 Forum | Forum 案件化具有延續性 "
                "| 保留三個求助 Forum，教材另用 course-materials "
                "| 舊標籤不直接複製 |"
            ),
            (
                "| 114 一般求助高度案件化且有明確結案前綴 "
                "| 視覺化結案有助於收束 | 手動結案保留 `✅`；"
                "狀態由資料庫權威 | 不能由紀錄證明因果 |"
            ),
            (
                "| 113 社群與趣味題較活躍、114 社群較安靜 "
                "| 案件效率與社群活力需分區 | 中文／English Chat 保留；"
                "趣味題可放 Other Problem / Free Talk | API 無法判斷學生主觀感受 |"
            ),
            (
                "| 系統／其他問題占比不低 | 系統問題不可當例外 "
                "| Coursework / Systems 提供常見系統類型 "
                "| 共享事故的狀態仍需 Staff 控制 |"
            ),
            (
                "| 多數正式求助含附件 | 附件提示是主要流程 "
                "| Portal 顯示 metadata marker 與 Discord link，不下載／代理 "
                "| 附件內容未檢視 |"
            ),
            (
                "| 回應工作集中於少數核心帳號 | 有負載與維運風險 "
                "| 增加案件負責人、轉交與彙總介面 "
                "| 不揭露個人帳號或進行績效推論 |"
            ),
            (
                "| 語音沒有可用資料 | 無法由歷史證據設計複雜語音區 "
                "| 第一版只保留中／英文自習室 | 需要人工觀察 |"
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def _source_inventory() -> str:
    rows = [
        (
            "project-exchange/10_CFG_DiscordSide.zip",
            "最新已確認 Discord Side 設定包",
            "有效；最高優先",
            "否",
            "ZIP 否；衍生 proposed config 可",
        ),
        (
            "project-exchange/14_Discord_112_113_114_三年比較分析包.zip",
            "三年彙總比較證據",
            "只採彙總結論；不讀原始正文",
            "可能含私人研究衍生資料",
            "ZIP 否；本矩陣可",
        ),
        (
            "docs/decisions/PRODUCT_DECISIONS_2026-07-23.md",
            "Task 34 產品決策",
            "未與最新 CONFIG 衝突時有效",
            "否",
            "可",
        ),
        (
            "docs/reports/TASK-34-REPORT.md",
            "Task 34 實作與驗證證據",
            "歷史實作狀態",
            "否",
            "可",
        ),
        (
            "docs/CONFIGURATION.md",
            "目前程式 runtime 設定",
            "有效；描述 code，不取代產品設定",
            "否",
            "可",
        ),
        (
            "docs/decisions/UNRESOLVED.md",
            "跨產品／技術未決事項",
            "有效；需分層",
            "否",
            "可",
        ),
        (
            "CODEX_TASKS/01_SHARED_CONTEXT.md",
            "早期共享背景",
            "只補充未衝突內容",
            "否",
            "可",
        ),
        (
            "外部 Task 35 reports／private outputs",
            "一次性 GET-only 匯出證據",
            "不複製進 canonical root",
            "是",
            "不可",
        ),
    ]
    lines = _frontmatter(
        "NAP Build 設定來源盤點",
        "來源優先序：最新確認設定包 → 最新產品決策 → Task 35 狀態 → Task 34 → 早期背景。",
    )
    lines.extend(
        [
            "| 路徑／來源 | 性質 | 目前效力 | 真實資料 | 可進 Git |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    lines.extend(
        [
            "",
            "## 衝突處理",
            "",
            (
                "- 最新 Side CONFIG 的 Open／Tracked／Idle／Closed／Auto Closed "
                "與 48h＋48h 規則，取代 Task 34 的展示狀態與 3／7 日規則。"
            ),
            (
                "- Task 34 的隨機案號、逐案 AI Yes／No、Working／Archive 分離"
                "與 Portal one-case boundary 繼續有效。"
            ),
            "- 三年比較只能形成設計證據，不會把舊伺服器直接複製為新設定。",
        ]
    )
    return "\n".join(lines) + "\n"


def generate_documents(
    root: Path, bundle: ConfigBundle, issues: tuple[ValidationIssue, ...]
) -> tuple[Path, ...]:
    generated_dir = root / "docs" / "generated"
    reports_dir = root / "docs" / "reports"
    generated_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        generated_dir / "channel-tree.md": _channel_tree(bundle.server),
        generated_dir / "role-permission-matrix.md": _permission_matrix(bundle.server),
        generated_dir / "forum-tags.md": _forum_tags(bundle.server),
        generated_dir / "bot-permissions.md": _bot_permissions(bundle.server),
        generated_dir / "case-lifecycle.md": _case_lifecycle(bundle.workflow),
        generated_dir / "portal-page-map.md": _portal_page_map(bundle.portal),
        generated_dir / "config-summary.md": _config_summary(bundle, issues),
        generated_dir / "config-code-drift.md": _drift_report(issues),
        generated_dir / "decision-migration-table.md": _decision_migration(),
        generated_dir / "evidence-to-design-matrix.md": _evidence_matrix(),
        reports_dir / "NAP_BUILD_SOURCE_INVENTORY.md": _source_inventory(),
    }
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
    return tuple(outputs)
