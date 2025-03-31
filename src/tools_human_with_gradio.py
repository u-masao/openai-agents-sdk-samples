import asyncio
import functools
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

import gradio as gr
from agents import (
    Agent,
    ModelSettings,
    RunContextWrapper,
    Runner,
    function_tool,
)


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

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.context: HumanInteractContext = HumanInteractContext()
        self._loop: Optional[asyncio.AbstractEventLoop] = loop

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
        if self._loop and self._loop.is_running():
            print("Calling event.set() via loop.call_soon_threadsafe")
            self._loop.call_soon_threadsafe(self.context.event.set)
        else:
            print("Warinng: Main event loop not available or not running")

        print("event.set() to release event.wait()")
        self.context.event.set()

    def receive_human_to_system(self) -> str:
        """人間からシステムへメッセージを送る"""
        return self.context.human_to_system_message

    def reset_context(self) -> None:
        """コンテキストをリセットする"""
        if self.context is None:
            return
        self.context.system_to_human_message = None
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

    # 人間からメッセージを受信
    print("receive message from human to system")
    response = interact_manager.receive_human_to_system()

    # 完了
    print("receive message from human to system done")
    return response


class GradioUserInterface:
    """Gradio UI の定義"""

    def __init__(self):

        # カレントスレッドを取得(コンストラクタに移動できない？)
        self.loop = asyncio.get_running_loop()

        # Human Input のコンテキストを定義
        self.interact_manager = HumanInteractManager(self.loop)

    def set_components(self) -> gr.Blocks:
        """
        Gradio UI の定義とコールバックの設定
        """

        async def check_interact_update():
            """
            context の更新を確認
            """
            ctx: HumanInteractContext = self.interact_manager.context
            if ctx.status == "waiting_for_human":
                return (
                    gr.Textbox(
                        value=ctx.system_to_human_message,
                        interactive=False,
                    ),
                    gr.Textbox(
                        interactive=True,
                        placeholder="回答を入力してください",
                    ),
                    gr.Button(interactive=True),
                    gr.Textbox(
                        value=ctx.status,
                        interactive=False,
                    ),
                )
            else:
                return (
                    gr.Textbox(
                        value=ctx.system_to_human_message,
                        interactive=False,
                    ),
                    gr.Textbox(
                        interactive=False,
                        value=ctx.human_to_system_message,
                    ),
                    gr.Button(interactive=False),
                    gr.Textbox(
                        value=ctx.status,
                        interactive=False,
                    ),
                )

        async def submit_message(human_to_system_message: str):
            """
            Human Input を System へ送信
            """

            ctx: HumanInteractContext = self.interact_manager.context

            if ctx.status == "waiting_for_human":
                self.interact_manager.send_human_to_system(
                    human_to_system_message
                )

                return (
                    gr.Textbox(
                        value=ctx.system_to_human_message,
                        interactive=False,
                    ),
                    gr.Textbox(
                        value=ctx.human_to_system_message,
                        interactive=False,
                    ),
                    gr.Button(interactive=False),
                    gr.Textbox(
                        value=ctx.status,
                        interactive=False,
                    ),
                )
            else:
                return (
                    gr.Textbox(
                        value=ctx.system_to_human_message,
                        interactive=False,
                    ),
                    gr.Textbox(
                        interactive=False,
                        value=ctx.human_to_system_message,
                    ),
                    gr.Button(interactive=False),
                    gr.Textbox(
                        value=ctx.status,
                        interactive=False,
                    ),
                )

        # Gradio の UI を定義
        with gr.Blocks() as demo:
            output_text = gr.Textbox(label="システム -> 人間")
            input_text = gr.Textbox(label="人間 -> システム")
            submit_button = gr.Button("送信")
            status_text = gr.Textbox(label="コンテキストのステイタス")
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

        return demo

    def run_background(
        self, launch_config: Dict[str, Any] = {"share": False}
    ) -> None:
        """Gradio バックエンドを起動"""

        # Gradio コンポーネントを配置
        demo = self.set_components()

        # Gradio をバックグラウンドで起動
        self.loop.run_in_executor(
            None, functools.partial(demo.launch, launch_config)
        )


async def main():

    # Gradio Components を配置
    gradio_user_interface = GradioUserInterface()

    # Gradio をバックグラウンドで実行
    print("run gradio background")
    gradio_user_interface.run_background()

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
    interact_manager = gradio_user_interface.interact_manager
    result = await Runner.run(
        human_agent,
        input="今の東京の天気を言いやがれ？",
        context=interact_manager,
    )

    # 結果を確認
    print(f"観測された人間の応答: {result.final_output}")
    print(f"交流のコンテキスト: {interact_manager.context}")
    print("処理終了ですが Ctrl-C で抜けてください")


if __name__ == "__main__":

    asyncio.run(main())
