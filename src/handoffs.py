import asyncio
from dataclasses import asdict
from pprint import pprint

from agents import Agent, GuardrailFunctionOutput, InputGuardrail, Runner
from pydantic import BaseModel


class HomeworkOutput(BaseModel):
    is_homework: bool
    reasoning: str


guardrail_agent = Agent(
    name="ガードレールチェック",
    instructions="ユーザーが宿題について質問しているのかチェックして。",
    output_type=HomeworkOutput,
)

math_tutor_agent = Agent(
    name="数学の家庭教師",
    handoff_description="数学の専門家のエージェント",
    instructions="数学の問題について回答を与えて。回答の理由を例を交えてステップバイステップで示して",
)

history_tutor_agent = Agent(
    name="歴史の家庭教師",
    handoff_description="歴史の専門家エージェント",
    instructions="歴史の問題に回答して。重要なイベントとコンテキストを明らかにして。",
)


async def homework_guardrail(ctx, agent, input_data):
    result = await Runner.run(guardrail_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(HomeworkOutput)
    return GuardrailFunctionOutput(
        output_info=final_output,
        tripwire_triggered=not final_output.is_homework,
    )


triage_agent = Agent(
    name="トリアージエージェント",
    instructions="ユーザーの質問が宿題に関するものなのかを判定して",
    handoffs=[history_tutor_agent, math_tutor_agent],
    input_guardrails=[
        InputGuardrail(guardrail_function=homework_guardrail),
    ],
)


async def main():
    pprint([x for x in dir(triage_agent) if not x.startswith("_")])
    pprint(asdict(triage_agent))

    pprint([x for x in dir(guardrail_agent) if not x.startswith("_")])
    pprint(asdict(guardrail_agent))

    try:
        result = await Runner.run(
            triage_agent,
            "これは宿題ではないですが、二人の擲弾兵という曲について教えて。",
        )
        print(result.final_output)
        pprint([x for x in dir(result) if not x.startswith("_")])
        pprint(asdict(result))

    except Exception as e:
        print(e)

    try:
        result = await Runner.run(triage_agent, "アメリカの最初の大統領は誰？")
        print(result.final_output)
        pprint([x for x in dir(result) if not x.startswith("_")])
        pprint(asdict(result))

    except Exception as e:
        print(e)

    try:
        result = await Runner.run(
            triage_agent, "アメリカ最初の大統領の人生は？"
        )
        print(result.final_output)
        pprint([x for x in dir(result) if not x.startswith("_")])
        pprint(asdict(result))

    except Exception as e:
        print(e)

    try:
        result = await Runner.run(
            triage_agent,
            "宿題じゃなくて自己学習ですが、特異値分解と主成分分析の関係は？",
        )
        print(result.final_output)
        pprint([x for x in dir(result) if not x.startswith("_")])
        pprint(asdict(result))

    except Exception as e:
        print(e)


if __name__ == "__main__":
    asyncio.run(main())
