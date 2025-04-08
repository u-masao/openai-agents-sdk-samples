from agents import Agent, function_tool
from agents.extensions.visualization import draw_graph


@function_tool
def get_weather(city: str) -> str:
    return f"{city} の天気は晴れだっちゃ。"


bahasa_indonesia_agent = Agent(
    name="インドネシア語エージェント",
    instructions="あなたはインドネシア語しか出力しません。",
)

english_agent = Agent(
    name="英語エージェント",
    instructions="あなたは英語しか出力しません。",
)

triage_agent = Agent(
    name="トリアージエージェント",
    instructions="リクエストの言語に基づいて適切なエージェントに引き継ぎます",
    handoffs=[bahasa_indonesia_agent, english_agent],
    tools=[get_weather],
)

draw_graph(triage_agent, filename="agents_dag.png")
