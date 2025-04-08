import asyncio
import os
import shutil

from agents import Agent, Runner, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStdio


async def run(mcp_server: MCPServer):
    """エージェントの定義と実行"""
    agent = Agent(
        name="アシスタント",
        instructions="ファイルシステムの読み込むツールを使って、"
        "ファイルの内容に基づいて質問に答えて。",
        mcp_servers=[mcp_server],
    )

    # ファイルの一覧
    message = "ファイルの一覧を取得して。"
    print(f"実行中: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

    # 書籍についての質問
    message = (
        "ファイルの一覧を取得して、好きな書籍のファイルを見て。"
        "私が最初に挙げている書籍は？"
    )
    print(f"\n\n実行中: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)

    # 理由に関する質問
    message = (
        "ファイルの一覧を取得して、好きな歌のファイルを見て。"
        "私が好きそうな新しい歌をサジェストして。"
    )
    print(f"\n\n実行中: {message}")
    result = await Runner.run(starting_agent=agent, input=message)
    print(result.final_output)


async def main():
    """メイン処理"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    samples_dir = os.path.join(current_dir, "sample_files")

    async with MCPServerStdio(
        name="MCP ファイルシステムサーバー",
        params={
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                samples_dir,
            ],
        },
    ) as server:
        trace_id = gen_trace_id()
        with trace(workflow_name="MCP ファイルシステム", trace_id=trace_id):
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
