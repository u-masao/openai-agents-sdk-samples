from pprint import pprint
from typing import Any

from agents import FunctionTool, RunContextWrapper
from pydantic import BaseModel


def do_some_work(data: str) -> str:
    return "完了"


class FunctionArgs(BaseModel):
    username: str
    age: int


async def run_function(ctx: RunContextWrapper[Any], args: str) -> str:
    parsed = FunctionArgs.model_validate_json(args)
    return do_some_work(data=f"{parsed.username} は {parsed.age} 歳です。")


tool = FunctionTool(
    name="処理する担当者",
    description="抽出されたユーザーを処理します",
    params_json_schema=FunctionArgs.model_json_schema(),
    on_invoke_tool=run_function,
)

pprint(tool)
