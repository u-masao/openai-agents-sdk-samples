include .env

hello:
	uv run python -i -m src.hello

handoff:
	uv run python -i -m src.handoffs

lint:
	uv run isort src
	uv run black src -l 79
	uv run flake8 src
