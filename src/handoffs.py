from agents import Agent, InputGuardrail,GuardrailFunctionOutput, Runner
from pydantic import BaseModel
import asyncio

class HomeworkOutput(BaseModel):
    is_homework: bool
    reasoning: str

guardrail_agent = Agent(
    name="Guardrail check",
    # instructions="Check if the user is asking about homework.",
    instructions="ユーザーが宿題について質問しているのかチェックして。",
    output_type=HomeworkOutput,
)

math_tutor_agent = Agent(
    name="Math Tutor",
    handoff_description="数学の専門家のエージェント",
    # handoff_description="Specialist agent for math questions",
    # instructions="You provide help with math problems. Explain your reasoning at each step and include examples",
    instructions="数学の問題について回答を与えて。回答の理由を例を交えてステップバイステップで示して",
)

history_tutor_agent = Agent(
    name="History Tutor",
    #handoff_description="Specialist agent for historical questions",
    #instructions="You provide assistance with historical queries. Explain important events and context clearly.",
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
    name="Triage Agent",
    instructions="ユーザーの質問が宿題に関するものなのかを判定して",
    # instructions="You determine which agent to use based on the user's homework question",
    handoffs=[history_tutor_agent, math_tutor_agent],
    input_guardrails=[
        InputGuardrail(guardrail_function=homework_guardrail),
    ],
)

async def main():
    # result = await Runner.run(triage_agent, "who was the first president of the united states?")
    result = await Runner.run(triage_agent, "アメリカの最初の大統領は誰？")
    print(result.final_output)

    result = await Runner.run(triage_agent, "その人生は？")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
