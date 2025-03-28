"""
A dynamic action that the behavior can be defined at runtime when creating the action.
"""

from typing import Callable

from sherpa_ai.actions.base import AsyncBaseAction, BaseAction


class DynamicAction(BaseAction):
    """
    Dynamic action that the behavior can be defined at runtime when creating the action.

    Attributes:
        action (Callable): Function that defines the behavior of the action.
    """

    action: Callable

    def execute(self, **kwargs):
        return self.action(**kwargs)


class AsyncDynamicAction(AsyncBaseAction):
    """
    Dynamic action that the behavior can be defined at runtime when creating the action.

    Attributes:
        action (Callable): Function that defines the behavior of the action.
    """

    action: Callable

    async def execute(self, **kwargs):
        return await self.action(**kwargs)
