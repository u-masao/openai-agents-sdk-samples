include .env
export OPENAI_API_KEY := $(OPENAI_API_KEY)

streaming:
	uv run python -m src.streaming

agent:
	uv run python -i -m src.agents

hello:
	uv run python -i -m src.hello

handoff:
	uv run python -m src.handoffs

lint:
	uv run isort src
	uv run black src -l 79
	uv run flake8 src
