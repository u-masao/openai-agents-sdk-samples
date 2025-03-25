import asyncio
from pprint import pprint

from agents import Agent, Runner

spanish_agent = Agent(
    name="スペイン語エージェント",
    instructions="ユーザーのメッセージをスペイン語にして",
)

french_agent = Agent(
    name="フランス語エージェント",
    instructions="ユーザーのメッセージをフランス語にして",
)

orchestrator_agent = Agent(
    name="オーケストレーターエージェント",
    instructions=(
        "あなたは翻訳エージェントです。"
        "与えられた tools を使って翻訳してください。"
        "複数の翻訳を求められたら関連する tools を呼び出してください。"
    ),
    tools=[
        spanish_agent.as_tool(
            tool_name="translate_to_spanish",
            tool_description="ユーザーのメッセージをスペイン語に翻訳します",
        ),
        french_agent.as_tool(
            tool_name="translate_to_franch",
            tool_description="ユーザーのメッセージをフランス語に翻訳します",
        ),
    ],
)


async def main():
    result = await Runner.run(
        orchestrator_agent,
        input="'こんにちは、あるいはこんばんは' をスペイン語とフランス語と英語で言うと？",
    )
    print(result.final_output)
    pprint(orchestrator_agent)


if __name__ == "__main__":
    asyncio.run(main())
