from dotenv import load_dotenv

load_dotenv()

from agents import Agent, Runner  # noqa: E402

agent = Agent(
    name="アシスタント", instructions="あなたはとても親切なアシスタントです"
)
result = Runner.run_sync(
    agent, "今夜の夕飯のメニューを考えて。豚肉と野菜があります。"
)
print(result.final_output)
