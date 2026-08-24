from __future__ import annotations

import hashlib
import re

USERNAME_RE = re.compile(r"^[a-z0-9._]{2,32}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
CLASS_RE = re.compile(r"^(?:C)?(0[1-9]|1[0-6])$")


def normalize_email(value: str) -> str:
    normalized = value.strip().casefold()
    if not EMAIL_RE.fullmatch(normalized):
        raise ValueError("請輸入有效的 Email。")
    return normalized


def normalize_ntu_email(value: str) -> str:
    normalized = normalize_email(value)
    if not normalized.endswith("@ntu.edu.tw"):
        raise ValueError("臺大學生請使用 @ntu.edu.tw 的 NTU Mail。")
    return normalized


def normalize_optional_gmail(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    normalized = normalize_email(value)
    if not normalized.endswith("@gmail.com"):
        raise ValueError("聯絡 Gmail 請使用 @gmail.com，或將欄位留空。")
    return normalized


def normalize_discord_username(value: str) -> str:
    normalized = value.strip().casefold()
    if normalized.startswith("@"):
        raise ValueError("Discord 使用者名稱不需要加 @。")
    if not USERNAME_RE.fullmatch(normalized):
        raise ValueError("Discord 使用者名稱格式不正確。")
    return normalized


def normalize_class_code(value: str) -> str:
    normalized = value.strip().upper()
    match = CLASS_RE.fullmatch(normalized)
    if match is None:
        raise ValueError("班別必須是 C01 至 C16。")
    return match.group(1)


def applicant_identity_key(applicant_type: str, email: str, username: str) -> str:
    material = f"{applicant_type}:{normalize_email(email)}:{normalize_discord_username(username)}"
    return hashlib.sha256(material.encode()).hexdigest()
