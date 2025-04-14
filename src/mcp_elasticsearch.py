import asyncio
import os
import shutil

from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio
from dotenv import load_dotenv

load_dotenv()


async def run(mcp_server: MCPServer):
    """エージェントの定義と実行"""
    agent = Agent(
        name="アシスタント",
        instructions="ユーザーのリクエストにしたがってElasticsearch を操作して",
        mcp_servers=[mcp_server],
    )

    # ファイルの一覧
    message = "インデックス一覧を見せて"
    print(f"命令: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

    while True:
        message = input("Elasticsearch で何がしたいですか？")
        print(f"命令: {message}")
        result = await Runner.run(starting_agent=agent, input=message)
        print(result.final_output)


async def main():
    """メイン処理"""

    async with MCPServerStdio(
        name="MCP Elasticsearch",
        params={
            "command": "uv",
            "args": [
                "--directory",
                "../elasticsearch-mcp-server",
                "run",
                "elasticsearch-mcp-server",
            ],
            "env": {
                "ELASTICSEARCH_HOST": os.getenv("ELASTICSEARCH_URL"),
                "ELASTICSEARCH_USERNAME": os.getenv("ELASTICSEARCH_USERNAME"),
                "ELASTICSEARCH_PASSWORD": os.getenv("ELASTICSEARCH_PASSWORD"),
                "ELASTICSEARCH_CA_CERT": os.getenv("ELASTICSEARCH_CA_CERT"),
            },
        },
    ) as server:
        trace_id = gen_trace_id()
        with trace(workflow_name="MCP Elasticsearch", trace_id=trace_id):
            print(
                "トレース情報: https://platform.openai.com/traces/trace"
                f"?trace_id={trace_id}\n"
            )
            await run(server)


if __name__ == "__main__":
    # npx コマンドのチェック
    if not shutil.which("npx"):
        raise RuntimeError(
            "npx がインストールされていません。`npm install -g npx` "
            "コマンド等でインストールして下さい。"
        )

    asyncio.run(main())
