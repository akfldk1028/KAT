"""
Prompt Templates for KAT Security Agents
"""
from .outgoing_agent import (
    OUTGOING_AGENT_PRINCIPLES,  # 3대 원칙 (최우선 발동)
    OUTGOING_AGENT_SYSTEM_PROMPT_TEMPLATE,
    OUTGOING_TOOLS_DESCRIPTION,
    get_outgoing_system_prompt,
    clear_prompt_cache,
)
