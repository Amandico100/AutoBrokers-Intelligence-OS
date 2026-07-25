"""Skill Registry e Tool Gateway. SPEC-056.

O Core deixa de receber todas as ferramentas e passa a receber apenas o
pacote da Skill escolhida. A capability continua sendo a autoridade de
poder — o Gateway apenas escolhe, do que já está autorizado, o mínimo
necessário.
"""

from .gateway import GatewayDecision, ToolGateway, ToolGrant  # noqa: F401
from .registry import ResolvedSkill, SkillCandidate, SkillRegistry, content_hash  # noqa: F401

__all__ = ["SkillRegistry", "ToolGateway", "GatewayDecision", "ToolGrant",
           "ResolvedSkill", "SkillCandidate", "content_hash"]
