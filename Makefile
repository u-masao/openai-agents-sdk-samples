include .env
export OPENAI_API_KEY := $(OPENAI_API_KEY)

tools_websearch:
	uv run python -m src.tools_websearch

streaming:
	uv run python -m src.streaming

tools_agents:
	uv run python -m src.tools_agents_as_tools

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
