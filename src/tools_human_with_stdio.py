import asyncio

from agents import Agent, ModelSettings, Runner, function_tool


@function_tool
async def ask_to_human(question: str) -> str:
    """システムから人間へ問い合わせを行い結果を取得する関数

    Args:
        question: システムから人間への質問の文字列
    """
    return input(question)


async def main():
    # エージェントを定義
    human_agent = Agent(
        name="人間に質問するエージェント",
        instructions="人間に質問の見解を問います。"
        "相手には感情があるのでできる限り丁寧に聞いてください。",
        tools=[ask_to_human],
        tool_use_behavior="stop_on_first_tool",
        model_settings=ModelSettings(tool_choice="required"),
    )

    # 人間へ問い合わせるエージェントを実行
    result = await Runner.run(
        human_agent,
        input="今の東京の天気を言いやがれ？",
    )

    # 結果を表示
    print(f"観測された人間の応答: {result.final_output}")


if __name__ == "__main__":
    asyncio.run(main())
