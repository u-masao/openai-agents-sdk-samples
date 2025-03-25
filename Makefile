include .env
export OPENAI_API_KEY := $(OPENAI_API_KEY)

streaming:
	uv run python -m src.streaming

tools_custom:
	uv run python -m src.tools_custom

tools:
	uv run python -m src.tools

hello:
	uv run python -i -m src.hello

handoff:
	uv run python -m src.handoffs

lint:
	uv run isort src
	uv run black src -l 79
	uv run flake8 src
