import datetime

import mlflow
from agents import Agent, Runner, function_tool

mlflow.openai.autolog()


@function_tool(description_override="指定の都市の天気を返す関数です")
def get_weather(city: str) -> str:
    return f"{city} の天気は雪です"


@function_tool(description_override="現在時刻を返す関数です")
def get_datetime(city: str) -> str:
    return str(datetime.datetime.now())


agent = Agent(
    name="俳句エージェント",
    instructions="常に俳句で応答してね",
    model="o3-mini",
    tools=[get_weather, get_datetime],
)

result = Runner.run_sync(agent, "沖縄の天気知ってる？")
print(result.final_output + "\n")

result = Runner.run_sync(agent, "昨日って何月何日だったっけ？")
print(result.final_output + "\n")

result = Runner.run_sync(agent, "沖縄の名物料理を知ってる？")
print(result.final_output + "\n")

result = Runner.run_sync(
    agent, "今夜の夕飯のメニューを考えて。豚肉と野菜があります。"
)
print(result.final_output + "\n")
