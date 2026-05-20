# core/enums.py
from enum import Enum

class TaskStatus(Enum):
    DEFINED = "defined"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"