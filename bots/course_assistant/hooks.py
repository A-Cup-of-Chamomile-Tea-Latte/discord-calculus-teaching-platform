"""Registration hooks for later buttons, modals, and Private Support."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from bots.common.errors import ConflictError, NotConfiguredError
from bots.course_assistant.models import HookResult, PrivateSupportRequest

InteractionHook = Callable[[str], Awaitable[HookResult]]
PrivateSupportHook = Callable[[PrivateSupportRequest], Awaitable[HookResult]]


class InteractionHookRegistry:
    def __init__(self) -> None:
        self._buttons: dict[str, InteractionHook] = {}
        self._modals: dict[str, InteractionHook] = {}
        self._private_support: PrivateSupportHook | None = None

    @property
    def button_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._buttons))

    @property
    def modal_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._modals))

    def register_button(self, name: str, hook: InteractionHook) -> None:
        self._register(self._buttons, name, hook)

    def register_modal(self, name: str, hook: InteractionHook) -> None:
        self._register(self._modals, name, hook)

    def register_private_support(self, hook: PrivateSupportHook) -> None:
        if self._private_support is not None:
            raise ConflictError("Private Support hook is already registered.")
        self._private_support = hook

    async def create_private_support(self, request: PrivateSupportRequest) -> HookResult:
        if self._private_support is None:
            raise NotConfiguredError("Private Support hook is not configured.")
        return await self._private_support(request)

    @staticmethod
    def _register(registry: dict[str, InteractionHook], name: str, hook: InteractionHook) -> None:
        if not name or not name.replace("_", "").isalnum():
            raise ValueError("Hook name must be alphanumeric with optional underscores.")
        if name in registry:
            raise ConflictError("Interaction hook is already registered.")
        registry[name] = hook
