from __future__ import annotations

from typing import TYPE_CHECKING, Callable, List, Optional

import pydash
from loguru import logger

from sherpa_ai.actions.base import BaseAction, BaseRetrievalAction
from sherpa_ai.events import Event, EventType

if TYPE_CHECKING:
    from sherpa_ai.memory.state_machine import SherpaStateMachine


class Belief:
    """
    The belief of the agent. it contains
        1. events: the events observed by the agent, synchronized with the shared memory
        2. internal_events: the internal events generated by the agent through its reasoning process (actions)
    """  # noqa E501

    def __init__(self):
        self.events: List[Event] = []
        self.internal_events: List[Event] = []
        self.current_task: Event = None
        self.state_machine: SherpaStateMachine = None
        self.actions = []
        self.dict: dict = {}
        self.max_tokens = 4000

    def update(self, observation: Event):
        if observation in self.events:
            return

        self.events.append(observation)

    def update_internal(
        self,
        event_type: EventType,
        agent: str,
        content: str,
    ):
        event = Event(event_type=event_type, agent=agent, content=content)
        self.internal_events.append(event)

    def get_by_type(self, event_type):
        return [
            event for event in self.internal_events if event.event_type == event_type
        ]

    def set_current_task(self, task: Event):
        self.current_task = task

    def get_context(self, token_counter: Callable[[str], int]):
        """
        Get the context of the agent

        Args:
            token_counter: Token counter
            max_tokens: Maximum number of tokens

        Returns:
            str: Context of the agent
        """
        context = ""
        for event in reversed(self.events):
            if event.event_type in [
                EventType.task,
                EventType.result,
                EventType.user_input,
            ]:
                context = event.content + "\n" + context

                if token_counter(context) > self.max_tokens:
                    break

        return context

    def get_internal_history(self, token_counter: Callable[[str], int]):
        """
        Get the internal history of the agent

        Args:
            token_counter: Token counter

        Returns:
            str: Internal history of the agent with event content separated by newlines.
            History is truncated if the number of tokens exceeds `max_tokens`.
        """
        results = []
        current_tokens = 0

        for event in reversed(self.internal_events):
            results.append(event.content)
            current_tokens += token_counter(event.content)
            if current_tokens > self.max_tokens:
                break

        context = "\n".join(reversed(results))
        return context

    def get_histories_excluding_types(
        self,
        exclude_types: list[EventType],
        token_counter: Optional[Callable[[str], int]] = None,
        max_tokens=4000,
    ):
        """
            Get the internal history of the agent without events of excluded_type

        Args:
            token_counter: Token counter
            max_tokens: Maximum number of tokens
            exclude_types: List of events to be excluded

        Returns:
            str: Internal history of the agent with event content separated by newlines.
            History is truncated if the number of tokens exceeds `max_tokens`.
        """
        if token_counter is None:
            # if no token counter is provided, use the default word counter
            def token_counter(x):
                return len(x.split())

        results = []
        feedback = []
        current_tokens = 0
        for event in reversed(self.internal_events):
            if event.event_type not in exclude_types:
                if event.event_type == EventType.feedback:
                    feedback.append(event.content)
                else:
                    results.append(event.content)
            current_tokens += token_counter(event.content)
            if current_tokens > max_tokens:
                break
        context = "\n".join(set(reversed(results))) + "\n".join(set(feedback))
        return context

    def set_actions(self, actions: List[BaseAction]):
        if self.state_machine is not None:
            logger.warning(
                "State machine exists, please add actions as transitions directly to the state machine"  # noqa E501
            )
            return

        self.actions = actions

        # TODO: This is a quick an dirty way to set the current task
        # in actions, need to find a better way
        for action in actions:
            if isinstance(action, BaseRetrievalAction):
                action.current_task = self.current_task.content

    @property
    def action_description(self):
        return "\n".join([str(action) for action in self.get_actions()])

    def get_state(self):
        if self.state_machine is None:
            return None

        return self.state_machine.state

    def get_actions(self) -> List[BaseAction]:
        if self.state_machine is None:
            return self.actions

        return self.state_machine.get_actions()

    def get_action(self, action_name) -> BaseAction:
        if self.state_machine is not None:
            self.actions = self.state_machine.get_actions()

        result = None
        for action in self.actions:
            if action.name == action_name:
                result = action
                break
        return result

    def get_dict(self):
        return self.dict

    def get(self, key, default=None):
        """
        Get value from the dict, the key can be a dot separated string if the value is nested
        """  # noqa E501
        return pydash.get(self.dict, key, default)

    def get_all_keys(self):
        def get_all_keys(d, parent_key=""):
            keys = []
            for k, v in d.items():
                full_key = parent_key + "." + k if parent_key else k
                keys.append(full_key)
                if isinstance(v, dict):
                    keys.extend(get_all_keys(v, full_key))
            return keys

        return get_all_keys(self.dict)

    def has(self, key):
        """
        Check if the key exists in the dict
        """
        return pydash.has(self.dict, key)

    def set(self, key, value):
        """
        Set value in the dict, the key can be a dot separated string if the value is nested
        """  # noqa E501
        pydash.set_(self.dict, key, value)

    @property
    def __dict__(self):
        return {
            "events": [event.__dict__ for event in self.events],
            "internal_events": [event.__dict__ for event in self.internal_events],
            "current_task": self.current_task.__dict__ if self.current_task else None,
            "dict": self.dict,
        }

    @classmethod
    def from_dict(cls, data):
        belief = cls()
        belief.events = [Event.from_dict(event) for event in data["events"]]
        belief.internal_events = [
            Event.from_dict(event) for event in data["internal_events"]
        ]
        belief.current_task = (
            Event.from_dict(data["current_task"]) if data["current_task"] else None
        )

        belief.dict = data["dict"]

        return belief
