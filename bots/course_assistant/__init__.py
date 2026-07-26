"""Fixture-first Course Assistant services and discord.py command skeleton."""

from bots.course_assistant.discord_app import CourseAssistantDiscordApp
from bots.course_assistant.repositories import generate_course_alias
from bots.course_assistant.service import CourseAssistantService

__all__ = ["CourseAssistantDiscordApp", "CourseAssistantService", "generate_course_alias"]
