from enum import Enum

class EventType (Enum):
    planning = 1
    task = 2
    result = 3

# event_types = {
#     "planning": EventType("planning"),
#     "task": EventType("task"),
#     "task_result": EventType("task result")
# }

class Event:
    def __init__(self, event_type: EventType, agent: str, content: str) -> None:
        self.event_type = event_type
        self.agent = agent
        self.content = content
