import asyncio
import functools
import threading
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

import gradio as gr
import mlflow
from agents import (
    Agent,
    ModelSettings,
    RunContextWrapper,
    Runner,
    function_tool,
)

mlflow.set_experiment("gradio")
mlflow.openai.autolog()


@dataclass
class HumanInteractContext:
    """
    人間とシステムが交流するためのコンテキストオブジェクト
    System -> human -> System のメッセージのやり取りと状態を保持
    """

    system_to_human_message: Optional[str] = None
    human_to_system_message: Optional[str] = None
    status: Literal["idle", "waiting_for_human", "human_responded"] = "idle"
    event: asyncio.Event = field(default_factory=asyncio.Event)


class HumanInteractManager:
    """
    人間とシステムが交流するための方法と対話の状態を管理。
    """

    def __init__(self) -> None:
        self.context = HumanInteractContext()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def send_system_to_human(self, message: str) -> None:
        """システムから人間へメッセージを送る"""
        self.context.system_to_human_message = message
        self.context.status = "waiting_for_human"

    def receive_system_to_human(self) -> str:
        """システムから人間へメッセージを送る"""
        return self.context.system_to_human_message

    def send_human_to_system(self, message: str) -> None:
        """人間からシステムへメッセージを送る"""
        self.context.human_to_system_message = message
        self.context.status = "human_responded"
        print(
            f"send_human_to_system thread: {threading.current_thread().ident}"
        )
        if self._loop and self._loop.is_running():
            print("Calling event.set() via loop.call_soon_threadsafe")
            self._loop.call_soon_threadsafe(self.context.event.set)
        else:
            print("Warinng: Main event loop not available or not running")

        print("event.set()")
        self.context.event.set()

    def receive_human_to_system(self) -> str:
        """人間からシステムへメッセージを送る"""
        return self.context.human_to_system_message

    def reset_context(self) -> None:
        """コンテキストをリセットする"""
        if self.context is None:
            return
        self.context.system_to_human_message = None
        # self.context.system_to_human_prompt = None
        self.context.human_to_system_message = None
        self.context.status = "idle"
        self.context.event.clear()


async def async_wait_for_event(event):
    """
    非同期タスクでイベントを待機し、結果を返す
    """
    await event.wait()
    return "イベントが設定されました"


@function_tool
async def ask_to_human(run_ctx: RunContextWrapper[Any], question: str) -> str:
    """システムから人間へ問い合わせをする関数

    Args:
        question: システムから人間への質問の文字列
    """
    print("ask_to_human called")
    print(f"ask_to_human called in thread: {threading.current_thread().ident}")

    interact_manager: HumanInteractManager = run_ctx.context

    # イベントオブジェクトをクリア
    print("clear event")
    interact_manager.context.event.clear()

    # 人間へメッセージを送信
    print("send message from system to human")
    interact_manager.send_system_to_human(f"あなたに質問です。\n{question}")

    # イベントオブジェクトがセットされるまで待ち
    print("event wait")
    await interact_manager.context.event.wait()
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(
    # async_wait_for_event(interact_manager.context.event)
    # )

    # 人間のメッセージを受信
    print("receive message from human to system")
    response = interact_manager.receive_human_to_system()

    # done
    print("receive message from human to system done")
    return response


# Human Input のコンテキストを定義
interact_manager = HumanInteractManager()

# Gradio の UI を定義
with gr.Blocks() as demo:
    output_text = gr.Textbox(label="システム -> 人間")
    input_text = gr.Textbox(label="人間 -> システム")
    submit_button = gr.Button("送信")
    status_text = gr.Textbox(label="コンテキストのステイタス")

    async def check_interact_update():
        """
        context の更新を確認
        """
        if interact_manager.context.status == "waiting_for_human":
            return (
                gr.Textbox(
                    value=interact_manager.context.system_to_human_message,
                    interactive=False,
                ),
                gr.Textbox(
                    interactive=True, placeholder="回答を入力してください"
                ),
                gr.Button(interactive=True),
                gr.Textbox(
                    value=interact_manager.context.status,
                    interactive=False,
                ),
            )
        else:
            return (
                gr.Textbox(value="", interactive=False),
                gr.Textbox(interactive=False, value=""),
                gr.Button(interactive=False),
                gr.Textbox(
                    value=interact_manager.context.status,
                    interactive=False,
                ),
            )

    async def submit_message(human_to_system_message: str):
        """
        Human Input を System へ送信
        """

        if interact_manager.context.status == "waiting_for_human":
            interact_manager.send_human_to_system(human_to_system_message)

            return (
                gr.Textbox(
                    value=interact_manager.context.system_to_human_message,
                    interactive=False,
                ),
                gr.Textbox(
                    value=interact_manager.context.human_to_system_message,
                    interactive=False,
                ),
                gr.Button(interactive=False),
                gr.Textbox(
                    value=interact_manager.context.status,
                    interactive=False,
                ),
            )
        else:
            return (
                gr.Textbox(value="", interactive=False),
                gr.Textbox(value="", interactive=False),
                gr.Button(interactive=False),
                gr.Textbox(
                    value=interact_manager.context.status,
                    interactive=False,
                ),
            )

    timer = gr.Timer(value=1)

    timer.tick(
        fn=check_interact_update,
        inputs=[],
        outputs=[output_text, input_text, submit_button, status_text],
    )

    submit_button.click(
        submit_message,
        inputs=[input_text],
        outputs=[output_text, input_text, submit_button, status_text],
    )


async def main():

    # グローバル変数を参照(要改善)
    global interact_manager

    # Gradio をバックグラウンドで実行
    print("run gradio background")
    loop = asyncio.get_running_loop()
    interact_manager.set_loop(loop)
    print(f"main running thread: {threading.current_thread().ident}")

    # Gradio の起動関数をおまとめ
    launch_func = functools.partial(demo.launch, share=False)
    loop.run_in_executor(None, launch_func)

    await asyncio.sleep(2)

    # エージェントを定義
    print("create agent")
    human_agent = Agent(
        name="人間に質問するエージェント",
        instructions="人間に質問の見解を問います。"
        "相手には感情があるのでできる限り丁寧に聞いてください。",
        tools=[ask_to_human],
        tool_use_behavior="stop_on_first_tool",
        model_settings=ModelSettings(tool_choice="required"),
    )

    # 人間へ問い合わせるエージェントを実行
    print("run agent")
    result = await Runner.run(
        human_agent,
        input="今の東京の天気を言いやがれ？",
        context=interact_manager,
    )

    # 結果を確認
    print(f"人間の応答: {result.final_output}")
    print(f"交流のコンテキスト: {interact_manager.context}")


if __name__ == "__main__":

    asyncio.run(main())
