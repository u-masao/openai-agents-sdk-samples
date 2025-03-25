from __future__ import annotations as _annotations

import asyncio
import random
import uuid

from agents import (
    Agent,
    HandoffOutputItem,
    ItemHelpers,
    MessageOutputItem,
    RunContextWrapper,
    Runner,
    ToolCallItem,
    ToolCallOutputItem,
    TResponseInputItem,
    function_tool,
    handoff,
    trace,
)
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from pydantic import BaseModel

# CONTEXT


class AirlineAgentContext(BaseModel):
    passenger_name: str | None = None
    confirmation_number: str | None = None
    seat_number: str | None = None
    flight_number: str | None = None


# TOOLS


@function_tool(
    name_override="faq_lookup_tool",
    description_override="よく聞かれる質問",
)
async def faq_lookup_tool(question: str) -> str:
    print(f"faq_lookup_tool question: {question}")
    if "バッグ" in question or "荷物" in question:
        return (
            "飛行機にはバッグを1個持ち込むことができます。"
            "重量は50ポンド以下、サイズは22インチ×14インチ×9インチである必要があります。"
        )
    elif "席" in question or "飛行機" in question:
        return (
            "飛行機には120席あります。"
            "ビジネスクラスは22席、エコノミークラスは98席あります。"
            "非常口は4列目と16列目です。"
            "5～8 列目はエコノミープラスで、足元スペースが広くなっています。"
        )
    elif "wifi" in question:
        return "飛行機には無料Wi-Fiがあります。Airline-Wifiにご参加ください"
    return "申し訳ありませんが、その質問の答えはわかりません。"


@function_tool
async def update_seat(
    run_context: RunContextWrapper[AirlineAgentContext],
    confirmation_number: str,
    new_seat: str,
) -> str:
    """
    指定された確認番号の座席を更新します。

    Args:
        confirmation_number: フライトの確認番号。
        new_seat: 更新する新しいシート。
    """
    run_context.context.confirmation_number = confirmation_number
    run_context.context.seat_number = new_seat
    assert (
        run_context.context.flight_number is not None
    ), "Flight number is required"
    return f"確認番号 {confirmation_number} の座席を {new_seat} 番に変更しました。"


# HOOKS


async def on_seat_booking_handoff(
    context: RunContextWrapper[AirlineAgentContext],
) -> None:
    flight_number = f"FLT-{random.randint(100, 999)}"
    context.context.flight_number = flight_number


# AGENTS

faq_agent = Agent[AirlineAgentContext](
    name="FAQエージェント",
    handoff_description="航空会社に関する質問に答えてくれる親切なエージェント",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    あなたは FAQ エージェントです。顧客と話しているときは、
    トリアージ エージェントから転送された可能性があります。
    次のルーチンを使用して顧客をサポートします。
    # ルーチン
    1. 顧客が最後に尋ねた質問を特定します。
    2. FAQ 検索ツール'faq_lookup_tool'を使用して質問に答えます。自分の知識に頼らないでください。
    3. 質問に答えられない場合は、トリアージ エージェントに転送します。""",
    tools=[faq_lookup_tool],
)

seat_booking_agent = Agent[AirlineAgentContext](
    name="座席予約エージェント",
    handoff_description="フライトの座席を更新できる便利なエージェント。",
    instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
    あなたは座席予約エージェントです。顧客と話しているときは、
    トリアージ エージェントから転送された可能性があります。
    次のルーチンを使用して顧客をサポートします。
    ＃ ルーティーン
    1. 確認番号を尋ねます。
    2. 顧客に希望の座席番号を尋ねます。
    3. 座席更新ツール'update_seat'を使用して、フライトの座席を更新します。
    顧客がルーチンに関係のない質問をした場合は、トリアージ エージェントに転送します。""",
    tools=[update_seat],
)

triage_agent = Agent[AirlineAgentContext](
    name="トリアージエージェント",
    handoff_description="顧客のリクエストを適切なエージェントに委任できるトリアージエージェント",
    instructions=(
        f"{RECOMMENDED_PROMPT_PREFIX} "
        "あなたは役に立つトリアージエージェントです。ツールを使用して、"
        "質問を他の適切なエージェントに委任することができます。"
    ),
    handoffs=[
        faq_agent,
        handoff(agent=seat_booking_agent, on_handoff=on_seat_booking_handoff),
    ],
)

faq_agent.handoffs.append(triage_agent)
seat_booking_agent.handoffs.append(triage_agent)


# RUN


async def main():
    current_agent: Agent[AirlineAgentContext] = triage_agent
    input_items: list[TResponseInputItem] = []
    context = AirlineAgentContext()

    # 通常、ユーザーからの各入力はアプリへのAPIリクエストとなり、
    # そのリクエストをtrace()でラップすることができます。
    # ここでは、会話IDにランダムなUUIDを使用します
    conversation_id = uuid.uuid4().hex[:16]

    while True:
        print(f"context: {context}")
        user_input = input(">>> メッセージをお願いします: ")
        with trace("カスタマーサービス", group_id=conversation_id):
            input_items.append({"content": user_input, "role": "user"})
            result = await Runner.run(
                current_agent, input_items, context=context
            )

            for new_item in result.new_items:
                agent_name = new_item.agent.name
                if isinstance(new_item, MessageOutputItem):
                    print(
                        f"{agent_name}: "
                        f"{ItemHelpers.text_message_output(new_item)}"
                    )
                elif isinstance(new_item, HandoffOutputItem):
                    print(
                        f"Handed off from {new_item.source_agent.name}"
                        f" to {new_item.target_agent.name}"
                    )
                elif isinstance(new_item, ToolCallItem):
                    print(f"{agent_name}: ツール呼び出し")
                elif isinstance(new_item, ToolCallOutputItem):
                    print(
                        f"{agent_name}: ツール呼び出し結果: {new_item.output}"
                    )
                else:
                    print(
                        f"{agent_name}: スキップ: {new_item.__class__.__name__}"
                    )
            input_items = result.to_input_list()
            current_agent = result.last_agent


if __name__ == "__main__":
    asyncio.run(main())
