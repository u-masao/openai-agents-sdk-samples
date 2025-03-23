from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="You are a helpful assistant")
result = Runner.run_sync(agent, "今夜の夕飯のメニューを考えて。豚肉と野菜があります。")
print(result.final_output)
