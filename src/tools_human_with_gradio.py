import asyncio
from typing import Any, Callable, Literal, Optional

from agents import (
    Agent,
    ModelSettings,
    RunContextWrapper,
    Runner,
    function_tool,
)
from pydantic import BaseModel


class HumanInteractionContext(BaseModel):
    """
    人間とシステムが交流するためのコンテキストオブジェクト
    System -> human -> System のメッセージのやり取りと状態を保持
    """

    system_to_human_message: Optional[str] = None
    system_to_human_prompt: Optional[str] = None
    human_to_system_message: Optional[str] = None
    status: Literal["idle", "waiting_for_human", "human_responded"] = "idle"


class HumanInteractionMethod:
    """
    人間とシステムが交流するための方法と対話の状態を管理。
    """

    def __init__(
        self,
        system_to_human_func: Callable = print,
        human_to_system_func: Callable = input,
        interaction_context: Optional[HumanInteractionContext] = None,
    ) -> None:
        self.system_to_human_funk = system_to_human_func
        self.human_to_system_func = human_to_system_func
        self.interaction_context = None
        if interaction_context is not None:
            self.interaction_context = interaction_context

    def send_message_to_human(self, message: str) -> None:
        self.system_to_human_funk(message)
        if self.interaction_context is not None:
            self.interaction_context.status = "waiting_for_human"
            self.interaction_context.system_to_human_message = message

    def receive_message_from_human(self, prompt: str) -> str:
        response = self.human_to_system_func(prompt)
        if self.interaction_context is not None:
            self.interaction_context.status = "human_responded"
            self.interaction_context.system_to_human_prompt = prompt
            self.interaction_context.human_to_system_message = response
        return response

    def reset_interaction_context(self) -> None:
        if self.interaction_context is None:
            return
        self.interaction_context.system_to_human_message = None
        self.interaction_context.system_to_human_prompt = None
        self.interaction_context.human_to_system_message = None
        self.interaction_context.status = "idle"


@function_tool
def ask_to_human(ctx: RunContextWrapper[Any], question: str) -> str:
    ctx.context.send_message_to_human(f"あなたに質問です。\n{question}")
    response = ctx.context.receive_message_from_human(
        "回答を入力してください: "
    )
    return response


async def main():
    interaction_context = HumanInteractionContext()
    interaction_method = HumanInteractionMethod(
        interaction_context=interaction_context
    )
    human_agent = Agent(
        name="人間に質問するエージェント",
        instructions="人間に質問の見解を問います。"
        "相手には感情があるのでできる限り丁寧に聞いてください。",
        tools=[ask_to_human],
        tool_use_behavior="stop_on_first_tool",
        model_settings=ModelSettings(tool_choice="required"),
    )
    result = await Runner.run(
        human_agent,
        input="今の東京の天気を言いやがれ？",
        context=interaction_method,
    )
    print(f"人間の応答: {result.final_output}")
    print(f"交流のコンテキスト: {interaction_context}")


if __name__ == "__main__":
    asyncio.run(main())
