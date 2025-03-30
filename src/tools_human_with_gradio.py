import asyncio

from agents import (
    Agent,
    ModelSettings,
    Runner,
    function_tool,
)
from pydantic import BaseModel


class Weather(BaseModel):
    city: str
    temperature_range: str
    conditions: str


@function_tool
def get_weather(city: str) -> Weather:
    print("[debug] get_weather called")
    return Weather(
        city=city, temperature_range="14-20C", conditions="Sunny with wind"
    )


async def main():
    agent = Agent(
        name="Weather agent",
        instructions="You are a helpful agent.",
        tools=[get_weather],
        tool_use_behavior="stop_on_first_tool",
        model_settings=ModelSettings(tool_choice="required"),
    )

    result = await Runner.run(agent, input="What's the weather in Tokyo?")
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
