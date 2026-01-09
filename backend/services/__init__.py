"""Services module for JOBi."""

from .auto_apply import (
    UserProfile,
    AutoApplyService,
    trigger_auto_apply,
)

__all__ = [
    "UserProfile",
    "AutoApplyService", 
    "trigger_auto_apply",
]
