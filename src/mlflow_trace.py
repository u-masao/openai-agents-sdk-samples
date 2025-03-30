import mlflow
from agents import Agent, Runner

mlflow.set_experiment("evaluate")
mlflow.openai.autolog()
agent = Agent(
    name="アシスタント", instructions="あなたは役に立つアシスタントです"
)
result = Runner.run_sync(agent, "鉄釘の磁化について俳句を書いて")
print(result.final_output)
