import asyncio

# import os
# import random  # for example
# import time
from typing import Any, Dict, Literal, Optional

import gradio as gr

# import openai
from agents import (
    Agent,
    FunctionTool,
    ModelSettings,
    RunContextWrapper,
    Runner,
)
from pydantic import BaseModel, Field


# --- Assume these classes exist based on the user's snippet ---
# Mock implementations if the actual library isn't available
# In a real scenario, import these from 'openai-agents' or your custom library
class DummyModelSettings(BaseModel):
    model: str = "gpt-4o-mini"  # Example
    tool_choice: Optional[Literal["required", "auto"]] = None  # Example


class DummyRunContextWrapper(BaseModel):
    context: Any  # Assuming the original context is accessible here

    # Add other potential fields from the library if known
    class Config:
        arbitrary_types_allowed = True


class DummyBaseTool(BaseModel):  # Base class for tools
    name: str
    description: str


class DummyFunctionTool(DummyBaseTool):
    params_json_schema: Dict[str, Any]
    on_invoke_tool: callable  # Async function expected


class DummyAgent(BaseModel):
    name: str
    instructions: str
    tools: list[DummyBaseTool]  # Expecting tools here
    model_settings: Optional[ModelSettings] = None


class DummyRunnerResult(BaseModel):  # Example structure
    final_output: Optional[str] = None
    run_status: str = "completed"


class DummyRunner:  # Mock Runner
    @staticmethod
    async def run(
        agent: Agent, user_message: str, context: Any
    ) -> DummyRunnerResult:
        print("--- Mock Runner Start ---")
        print(f"Agent: {agent.name}")
        print(f"User Message: {user_message}")
        print(f"Context: {context}")

        # Simulate agent deciding to call the 'ask_human' tool
        ask_human_tool = next(
            (
                t
                for t in agent.tools
                if isinstance(t, FunctionTool) and t.name == "ask_human"
            ),
            None,
        )

        if (
            ask_human_tool and "質問して" in user_message
        ):  # Simple trigger condition
            print("Runner: Simulating call to 'ask_human' tool...")
            # In real library, agent decides the arguments based on user_message
            mock_args = AskHumanArgs(
                prompt="何か追加で聞きたいことはありますか？ (Mock)"
            ).model_dump_json()
            wrapper = RunContextWrapper(context=context)  # Wrap the context
            try:
                # Invoke the tool function
                human_response = await ask_human_tool.on_invoke_tool(
                    wrapper, mock_args
                )
                print(
                    f"Runner: Received human response from tool: {human_response}"
                )
                # Simulate generating final output based on response
                final_output = f"人間はこう答えました: '{human_response}'. これで処理を完了します。(Mock)"
                return DummyRunnerResult(
                    final_output=final_output, run_status="completed"
                )
            except Exception as e:
                print(f"Runner: Error during tool execution: {e}")
                return DummyRunnerResult(
                    final_output=f"ツールの実行中にエラーが発生しました: {e}",
                    run_status="failed",
                )
        else:
            # Simulate direct response without tool call
            print("Runner: Simulating direct response...")
            await asyncio.sleep(1)  # Simulate work
            return DummyRunnerResult(
                final_output="直接お答えします。ジョークですね？... (Mock)",
                run_status="completed",
            )
        print("--- Mock Runner End ---")


# --- 1. InteractionInfo & AskHumanArgs ---
class InteractionInfo(BaseModel):
    prompt_to_human: Optional[str] = None
    human_response: Optional[str] = None
    status: Literal["idle", "waiting_for_human", "human_responded"] = "idle"

    class Config:
        arbitrary_types_allowed = True  # Allow asyncio.Event if needed later


class AskHumanArgs(BaseModel):
    prompt: str = Field(..., description="The question to ask the human user.")


# --- 2. Human Interaction Tool Implementation ---
async def invoke_ask_human_tool(
    ctx: RunContextWrapper[Dict[str, Any]], args: str
) -> str:
    """Tool's execution function. Updates context, waits for UI."""
    try:
        parsed_args = AskHumanArgs.model_validate_json(args)
        prompt = parsed_args.prompt
    except Exception as e:
        print(f"Error parsing tool arguments: {e}")
        return f"Error: Invalid arguments received - {e}"

    # --- Access shared context (InteractionInfo and Event) ---
    # Assuming ctx.context holds the dict passed to Runner.run
    if (
        not isinstance(ctx.context, dict)
        or "interaction_info" not in ctx.context
        or "event" not in ctx.context
    ):
        print("Error: Invalid context structure in RunContextWrapper")
        return "Error: Internal context configuration problem."

    interaction_info: InteractionInfo = ctx.context["interaction_info"]
    event: asyncio.Event = ctx.context["event"]

    print(f"Tool ask_human executing. Prompt: {prompt}")

    # Update InteractionInfo for UI polling
    interaction_info.prompt_to_human = prompt
    interaction_info.human_response = None
    interaction_info.status = "waiting_for_human"
    event.clear()

    print("Tool: Waiting for human response via UI...")
    try:
        # Wait for the UI handler to call event.set()
        await asyncio.wait_for(event.wait(), timeout=300.0)  # 5 minute timeout
    except asyncio.TimeoutError:
        print("Tool: Human response timed out.")
        interaction_info.status = "idle"  # Reset status
        return "Timeout: No response from human."
    except Exception as e:
        print(f"Tool: Error while waiting for event: {e}")
        interaction_info.status = "idle"
        return f"Error: Failed while waiting for human input - {e}."

    # Event was set, response should be in interaction_info
    response = interaction_info.human_response
    if response is None:
        print("Tool: Event set, but no response found in context.")
        response = (
            "Error: No response data received from UI."  # Or provide a default
        )

    print(f"Tool: Received human response: {response}")

    # Reset context status
    interaction_info.status = "idle"
    interaction_info.prompt_to_human = None
    # Keep human_response for the tool's return value

    return response


# --- 3. Define the ask_human FunctionTool ---
ask_human_tool = FunctionTool(
    name="ask_human",
    description="Asks the human user for input or clarification when needed.",
    params_json_schema=AskHumanArgs.model_json_schema(),
    on_invoke_tool=invoke_ask_human_tool,
)

# --- 4. Define the Agent ---
# Example agent definition using the structure
agent = Agent(
    name="Gradio Human Interaction Agent",
    instructions="You are a helpful assistant. If you need clarification or more information, use the 'ask_human' tool.",
    tools=[ask_human_tool],
    # model_settings=ModelSettings(tool_choice='required'), # Force tool? Only if appropriate
    model_settings=ModelSettings(),  # Let agent decide or force via prompt
)


# --- 5. Gradio UI Definition ---
with gr.Blocks() as demo:
    gr.Markdown("## OpenAI Agent with Gradio Human Interaction")

    # Session state holding the context dict (InteractionInfo + Event)
    interaction_context_state = gr.State(
        value={"interaction_info": InteractionInfo(), "event": asyncio.Event()}
    )

    # UI Components
    # Using Textbox for output as streaming is not assumed from Runner.run
    agent_output_display = gr.Textbox(
        label="Agent Output", lines=10, interactive=False
    )
    human_prompt_display = gr.Textbox(
        label="Agentからの質問", interactive=False, visible=False
    )  # Initially hidden
    human_input = gr.Textbox(
        label="あなたの応答",
        placeholder="Agentからの質問に答えてください...",
        interactive=False,
        visible=False,
    )
    submit_button = gr.Button("応答を送信", interactive=False, visible=False)
    initial_user_message = gr.Textbox(
        label="最初のメッセージ",
        value="こんにちは！何かお手伝いできることは？ 必要なら質問してください。",
    )
    start_button = gr.Button("Agentとの対話を開始")
    status_display = gr.Textbox(label="Status", interactive=False)

    # UI Updater (Polling)
    async def check_interaction_update_ui(current_context_dict: dict):
        info: InteractionInfo = current_context_dict["interaction_info"]
        status = info.status
        prompt = info.prompt_to_human

        if status == "waiting_for_human":
            print("UI Poller: Detected 'waiting_for_human'")
            return {
                human_prompt_display: gr.Textbox(
                    value=prompt, interactive=False, visible=True
                ),
                human_input: gr.Textbox(
                    interactive=True,
                    placeholder="応答を入力してください...",
                    visible=True,
                ),
                submit_button: gr.Button(interactive=True, visible=True),
                status_display: gr.Textbox(value="Waiting for your input..."),
            }
        elif (
            status == "human_responded"
        ):  # Status after submit, before tool returns
            print("UI Poller: Detected 'human_responded'")
            return {
                status_display: gr.Textbox(
                    value="Response sent to Agent. Waiting for Agent..."
                )
            }
        elif status == "idle":
            # Check if the UI elements are currently visible, if so, hide them.
            # This might need a check against component's current state if possible,
            # or rely on the submit handler to hide them.
            # print("UI Poller: Status is idle.")
            # Hide UI elements if they were previously visible after interaction
            # Note: Gradio's direct state check of visibility isn't straightforward here.
            # Let's rely on the submit handler to manage visibility on completion.
            return {
                status_display: gr.Textbox(value="Idle")
            }  # Keep status updated
        return {}  # No change

    demo.load(
        None,
        None,
        None,
        every=1,
        fn=check_interaction_update_ui,
        inputs=[interaction_context_state],
        outputs=[
            human_prompt_display,
            human_input,
            submit_button,
            status_display,
        ],
    )

    # Human Input Submit Handler
    async def handle_human_input_submit(
        current_context_dict: dict, user_text: str
    ):
        info: InteractionInfo = current_context_dict["interaction_info"]
        event: asyncio.Event = current_context_dict["event"]

        if info.status == "waiting_for_human":
            print(f"UI Submit: Received response: {user_text}")
            info.human_response = user_text
            info.status = "human_responded"  # Mark as responded
            event.set()  # Wake up the waiting tool function

            # Disable/hide input elements immediately
            return {
                human_prompt_display: gr.Textbox(visible=False),
                human_input: gr.Textbox(
                    value="", interactive=False, visible=False
                ),
                submit_button: gr.Button(interactive=False, visible=False),
                status_display: gr.Textbox(
                    "Response sent. Waiting for Agent..."
                ),
                agent_output_display: gr.Textbox(
                    value="応答をAgentに送信しました。\nAgentの最終応答を待っています..."
                ),  # Update main output
            }
        else:
            print("UI Submit: Input submitted when not waiting.")
            # Maybe show an error or do nothing
            return {}

    submit_button.click(
        handle_human_input_submit,
        inputs=[interaction_context_state, human_input],
        outputs=[
            human_prompt_display,
            human_input,
            submit_button,
            status_display,
            agent_output_display,
        ],
    )

    # Agent Execution Trigger
    async def run_agent_interaction(
        current_context_dict: dict, user_message: str
    ):
        # Reset UI elements at the start of a new run
        yield {
            agent_output_display: gr.Textbox("Agent is processing..."),
            human_prompt_display: gr.Textbox(visible=False),
            human_input: gr.Textbox(interactive=False, visible=False),
            submit_button: gr.Button(interactive=False, visible=False),
            status_display: gr.Textbox("Processing..."),
        }

        # Ensure context is fresh for this run (optional, depends on desired state persistence)
        current_context_dict["interaction_info"] = InteractionInfo()
        current_context_dict["event"] = (
            asyncio.Event()
        )  # Need a new event per run potentially? Or reset is enough? Let's reset.

        print("Starting Agent run...")
        try:
            # Run the agent logic in a background task to avoid blocking Gradio
            # Pass the specific context dict for this session
            runner_task = asyncio.create_task(
                Runner.run(agent, user_message, context=current_context_dict)
            )

            # Wait for the task to complete
            result: DummyRunnerResult = await runner_task

            print(f"Agent run finished. Status: {result.run_status}")
            final_output = (
                result.final_output if result else "No output received."
            )

            # Update the main display with the final result
            yield {
                agent_output_display: gr.Textbox(value=final_output),
                status_display: gr.Textbox(
                    f"Run finished: {result.run_status}"
                ),
            }

        except Exception as e:
            print(f"Error during agent execution: {e}")
            yield {
                agent_output_display: gr.Textbox(
                    value=f"An error occurred: {e}"
                ),
                status_display: gr.Textbox("Error"),
            }

        # Final check to ensure input UI is hidden if run ends without human input
        info_final: InteractionInfo = current_context_dict["interaction_info"]
        if info_final.status != "waiting_for_human":
            yield {
                human_prompt_display: gr.Textbox(visible=False),
                human_input: gr.Textbox(interactive=False, visible=False),
                submit_button: gr.Button(interactive=False, visible=False),
            }

    start_button.click(
        run_agent_interaction,
        inputs=[interaction_context_state, initial_user_message],
        outputs=[
            agent_output_display,
            human_prompt_display,
            human_input,
            submit_button,
            status_display,
        ],
    )


if __name__ == "__main__":
    print("Starting Gradio App...")
    demo.queue().launch()
