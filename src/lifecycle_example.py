import asyncio
import random
from typing import Any

from agents import (
    Agent,
    AgentHooks,
    RunContextWrapper,
    RunHooks,
    Runner,
    Tool,
    Usage,
    function_tool,
)
from pydantic import BaseModel


class CustomAgentHooks(AgentHooks):
    def __init__(self, display_name: str):
        self.event_counter = 0
        self.display_name = display_name

    async def on_start(self, context: RunContextWrapper, agent: Agent) -> None:
        self.event_counter += 1
        print(
            f"### AH {self.display_name} {self.event_counter}: "
            f"Agent {agent.name} started"
        )

    async def on_end(
        self, context: RunContextWrapper, agent: Agent, output: Any
    ) -> None:
        self.event_counter += 1
        print(
            f"### AH {self.display_name} {self.event_counter}: "
            f"Agent {agent.name} ended with output {output}"
        )

    async def on_handoff(
        self, context: RunContextWrapper, agent: Agent, source: Agent
    ) -> None:
        self.event_counter += 1
        print(
            f"### AH {self.display_name} {self.event_counter}: "
            f"Agent {source.name} handed off to {agent.name}"
        )

    async def on_tool_start(
        self, context: RunContextWrapper, agent: Agent, tool: Tool
    ) -> None:
        self.event_counter += 1
        print(
            f"### AH {self.display_name} {self.event_counter}: "
            f"Agent {agent.name} started tool {tool.name}"
        )

    async def on_tool_end(
        self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str
    ) -> None:
        self.event_counter += 1
        print(
            f"### AH {self.display_name} {self.event_counter}: "
            f"Agent {agent.name} ended tool {tool.name} with result {result}"
        )


class CustomRunHooks(RunHooks):
    def __init__(self):
        self.event_counter = 0

    def _usage_to_str(self, usage: Usage) -> str:
        return (
            f"{usage.requests} requests, {usage.input_tokens} input tokens, "
            f"{usage.output_tokens} output tokens, {usage.total_tokens}"
            " total tokens"
        )

    async def on_agent_start(
        self, context: RunContextWrapper, agent: Agent
    ) -> None:
        self.event_counter += 1
        print(
            f"### RH {self.event_counter}: Agent {agent.name} started. "
            f"Usage: {self._usage_to_str(context.usage)}"
        )

    async def on_agent_end(
        self, context: RunContextWrapper, agent: Agent, output: Any
    ) -> None:
        self.event_counter += 1
        print(
            f"### RH {self.event_counter}: Agent {agent.name} ended with "
            f"output {output}. Usage: {self._usage_to_str(context.usage)}"
        )

    async def on_tool_start(
        self, context: RunContextWrapper, agent: Agent, tool: Tool
    ) -> None:
        self.event_counter += 1
        print(
            f"### RH {self.event_counter}: Tool {tool.name} started. Usage: "
            f"{self._usage_to_str(context.usage)}"
        )

    async def on_tool_end(
        self, context: RunContextWrapper, agent: Agent, tool: Tool, result: str
    ) -> None:
        self.event_counter += 1
        print(
            f"### RH {self.event_counter}: Tool {tool.name} ended with "
            f"result {result}. Usage: {self._usage_to_str(context.usage)}"
        )

    async def on_handoff(
        self, context: RunContextWrapper, from_agent: Agent, to_agent: Agent
    ) -> None:
        self.event_counter += 1
        print(
            f"### RH {self.event_counter}: Handoff from {from_agent.name} to "
            f"{to_agent.name}. Usage: {self._usage_to_str(context.usage)}"
        )


@function_tool
def random_number(max: int) -> int:
    """指定された最大値までの乱数を生成します"""
    return random.randint(0, max)


@function_tool
def multiply_by_two(x: int) -> int:
    """x を 2 倍して返す"""
    return x * 2


class FinalResult(BaseModel):
    number: int


multiply_agent = Agent(
    name="乗算エージェント",
    instructions="数値を2倍にして最終結果を返します",
    tools=[multiply_by_two],
    output_type=FinalResult,
    hooks=CustomAgentHooks(display_name="乗算 Agent"),
)

orchestration_agent = Agent(
    name="オーケストレーションエージェント",
    instructions="乱数を生成します。偶数の場合は停止します。奇数の場合は乗算エージェントに渡します。",
    tools=[random_number],
    output_type=FinalResult,
    handoffs=[multiply_agent],
    hooks=CustomAgentHooks(display_name="オーケストレーション Agent"),
)


async def main() -> None:
    user_input = input("最大数を入力してください: ")
    await Runner.run(
        orchestration_agent,
        hooks=CustomRunHooks(),
        input=f"0 から {user_input} までのランダムな整数を生成して。",
    )
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
