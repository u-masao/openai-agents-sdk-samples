include .env
export OPENAI_API_KEY := $(OPENAI_API_KEY)
export OPENAI_AGENTS_DISABLE_TRACING := $(OPENAI_AGENTS_DISABLE_TRACING)

voice_chat:
	uv run gradio src/voice_chat.py

gradio_audio_io:
	uv run gradio src/gradio_audio_io.py

mcp_elasticsearch:
	uv run python src/mcp_elasticsearch.py

mcp_filesystem:
	uv run python src/mcp_filesystem.py

chatbot_gradio_queue:
	uv run gradio src/chatbot_gradio_queue.py

chatbot_gradio:
	uv run python src/chatbot_gradio.py

visualize:
	uv run gradio src/visualize.py

tools_human_stdio:
	uv run python src/tools_human_with_stdio.py

tools_human:
	uv run python src/tools_human_with_gradio.py

mlflow_trace:
	uv run python -i -m src.mlflow_trace

customer_service:
	uv run python -m src.customer_service

dynamic_system_prompt:
	uv run python -m src.dynamic_system_prompt

lifecycle_example:
	uv run python -m src.lifecycle_example

discussion_three:
	uv run python -m src.discussion_three

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
	uv run isort src --skip src/examples/
	uv run black src -l 79 --exclude 'src/examples/.*'
	uv run flake8 src --exclude 'src/examples/'
