import json
from pprint import pprint

from agents import Agent, FunctionTool, RunContextWrapper, function_tool
from typing_extensions import Any, TypedDict


class Location(TypedDict):
    lat: float
    long: float


@function_tool
async def fetch_weather(location: Location) -> str:
    """与えられたロケーションの天気を取得

    Args:
        location: 天気を取得したいロケーション
    """
    # 外部 API などで外部の天気を取得したつもり
    weather = "濃霧"
    return weather


@function_tool(name_override="fetch_data")
def read_file(
    ctx: RunContextWrapper[Any], path: str, directory: str | None = None
) -> str:
    """ファイルの中身を読む

    Args:
        path: ファイル名
        directory: ファイルのディレクトリ名
    """
    # 例えばこんな感じでファイルを読んだつもり
    # import json
    # from pathlib import Path
    # contents = json.load(open(Path(directory) / path, "r"))
    contents = """{"diary": "今日は豚肉と野菜で炒めものを作ったよ"}"""
    return contents


agent = Agent(
    name="アシスタント",
    tools=[fetch_weather, read_file],
)

for tool in agent.tools:
    if isinstance(tool, FunctionTool):
        print(tool.name)
        pprint(tool)
        print(
            json.dumps(tool.params_json_schema, indent=2, ensure_ascii=False)
        )
        print()
