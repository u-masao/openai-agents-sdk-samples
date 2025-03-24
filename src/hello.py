from agents import Agent, Runner

agent = Agent(
    name="アシスタント", instructions="あなたはとても親切なアシスタントです"
)
result = Runner.run_sync(
    agent, "今夜の夕飯のメニューを考えて。豚肉と野菜があります。"
)
print(result.final_output)
