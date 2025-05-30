import pytest

from sherpa_ai.agents import QAAgent
from sherpa_ai.memory.shared_memory import SharedMemory
from sherpa_ai.runtime import ThreadedRuntime


@pytest.fixture
def agents():
    agent_a = QAAgent(name="agent_a", num_runs=0)
    agent_runtime_a = ThreadedRuntime.start(agent=agent_a)
    agent_b = QAAgent(name="agent_b", num_runs=0)
    agent_runtime_b = ThreadedRuntime.start(agent=agent_b)
    yield agent_a, agent_runtime_a, agent_b, agent_runtime_b
    agent_runtime_a.stop()
    agent_runtime_b.stop()


@pytest.mark.asyncio
async def test_shared_memory(agents):
    """Test the SharedMemory class."""
    # Create a SharedMemory instance
    memory = SharedMemory("Complete the task")

    # Add an event to shared memory
    await memory.async_add("task", "initial_task", content="Process data")
    assert len(memory.events) == 1
    assert memory.events[0].event_type == "task"
    assert memory.events[0].name == "initial_task"
    assert memory.events[0].content == "Process data"

    agent_a, agent_runtime_a, agent_b, agent_runtime_b = agents
    # Subscribe to an event type
    memory.subscribe_event_type("task", agent_runtime_a)
    assert len(memory.event_type_subscriptions["task"]) == 1

    # Subscribe to an event type
    memory.subscribe_event_type("task", agent_runtime_b)
    assert len(memory.event_type_subscriptions["task"]) == 2

    # Subscribe to a sender
    memory.subscribe_sender("agent_a", agent_runtime_b)
    assert len(memory.sender_subscriptions) == 1

    # Handle events
    await memory.async_add("task", "task_1", sender="", content="Task 1", wait=True)
    await memory.async_add(
        "dummy", "task_2", sender="agent_a", content="Task 1", wait=True
    )
    await memory.async_add("dummy", "dummy", sender="", content="Task 1", wait=True)

    # Check the number of events
    assert len(memory.events) == 4
    assert len(agent_a.belief.internal_events) == 1
    assert agent_a.belief.internal_events[0].name == "task_1"
    assert len(agent_b.belief.internal_events) == 2
    assert agent_b.belief.internal_events[0].name == "task_1"
    assert agent_b.belief.internal_events[1].name == "task_2"
