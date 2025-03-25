from pprint import pprint

from agents import Agent, Runner, WebSearchTool

qiita_search = Agent(
    name="Qiita から情報を取得するエージェント",
    tools=[WebSearchTool(search_context_size="high")],
)

result = Runner.run_sync(
    qiita_search,
    "Qiita で OpenAI Agents SDK について書いている記事を5件教えて",
)

print(result.final_output)
pprint(qiita_search)
