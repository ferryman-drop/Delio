from enum import Enum, auto

class State(Enum):
    IDLE = auto()
    OBSERVE = auto()
    RETRIEVE = auto()
    PLAN = auto()
    DECIDE = auto()
    ACT = auto()
    RESPOND = auto()
    SCHEDULE = auto()
    REFLECT = auto()
    MEMORY_WRITE = auto()
    DEEP_THINK = auto()
    NOTIFY = auto()
    ERROR = auto()
