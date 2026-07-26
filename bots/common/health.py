"""Non-sensitive health projection."""

from __future__ import annotations

from bots.common.config import BotConfig
from bots.common.models import HealthInfo, HealthStatus


def build_health(
    config: BotConfig,
    *,
    status: HealthStatus,
    checked_at: str,
) -> HealthInfo:
    return HealthInfo(
        component=config.bot_name,
        status=status,
        runtime_mode=config.runtime_mode.value,
        ready=status is HealthStatus.READY,
        network_enabled=config.network_enabled,
        guild_configured=config.guild_id is not None,
        allowed_channel_count=len(config.channel_ids),
        checked_at=checked_at,
    )
