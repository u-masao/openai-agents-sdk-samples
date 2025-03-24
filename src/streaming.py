import asyncio

from agents import Agent, Runner
from openai.types.responses import ResponseTextDeltaEvent


async def main():
    agent = Agent(
        name="ジョーカー",
        instructions="あなたは役に立つアシスタントです",
    )

    result = Runner.run_streamed(agent, input="5個の冗談を言って。")
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(
            event.data, ResponseTextDeltaEvent
        ):
            print(event.data.delta, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
