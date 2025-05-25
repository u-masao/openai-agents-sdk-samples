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
        instructions="ユーザーのリクエストにしたがってYFinance APIから情報を取得",
        mcp_servers=[mcp_server],
    )

    while True:
        message = input("YFinance で何がしたいですか？")
        print(f"命令: {message}")
        result = await Runner.run(starting_agent=agent, input=message)
        print(result.final_output)


async def main():
    """メイン処理"""

    async with MCPServerStdio(
        name="MCP YFinance",
        params={
            "command": "uvx",
            "args": [
                "yfmcp@latest",
            ]
        }
    ) as server:
        trace_id = gen_trace_id()
        with trace(workflow_name="MCP YFinance", trace_id=trace_id):
            print(
                "トレース情報: https://platform.openai.com/traces/trace"
                f"?trace_id={trace_id}\n"
            )
            await run(server)


if __name__ == "__main__":
    asyncio.run(main())
