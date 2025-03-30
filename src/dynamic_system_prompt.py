import asyncio
import random
from pprint import pprint
from typing import Literal

from agents import Agent, RunContextWrapper, Runner


class CustomContext:
    def __init__(self, style: Literal["俳句", "海賊", "ロボット"]):
        self.style = style


def custom_instructions(
    run_context: RunContextWrapper[CustomContext], agent: Agent[CustomContext]
) -> str:
    context = run_context.context
    pprint(run_context)
    if context.style == "俳句":
        return "俳句のみをレスポンスして"
    elif context.style == "海賊":
        return "海賊のようにレスポンスして"
    else:
        return "ロボットのようにレスポンスして。'ピコ' と音を出す感じ"


agent = Agent(
    name="チャットエージェント",
    instructions=custom_instructions,
)


async def main():
    choice: Literal["俳句", "海賊", "ロボット"] = random.choice(
        ["俳句", "海賊", "ロボット"]
    )
    context = CustomContext(style=choice)
    print(f"このスタイルで行きますよ: {choice}\n")

    user_message = "ジョークを言ってちょうだいな"
    print(f"ユーザー: {user_message}")
    result = await Runner.run(agent, user_message, context=context)

    print(f"アシスタント: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
