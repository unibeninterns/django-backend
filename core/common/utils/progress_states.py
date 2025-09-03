from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime


class ContentState(Enum):
    """Defines all possible states for learning content."""
    LOCKED = "locked"  # Cannot access - requirements not met
    AVAILABLE = "available"  # Can start this content
    IN_PROGRESS = "in_progress"  # Started but not completed
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Failed assessment, needs retry

    @classmethod
    def accessible_states(cls):
        """States that allow content access."""
        return [cls.AVAILABLE, cls.IN_PROGRESS, cls.COMPLETED]

    @classmethod
    def startable_states(cls):
        """
        States from which content can be started.
        Added LOCKED and FAILED to allow starting and retrying a quiz.
        """
        return {cls.AVAILABLE, cls.LOCKED, cls.FAILED}

    @classmethod
    def completable_states(cls):
        """States from which content can be completed."""
        return [cls.IN_PROGRESS]
