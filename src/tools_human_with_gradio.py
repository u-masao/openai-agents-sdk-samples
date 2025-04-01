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

HUMAN_INPUT_TIMEOUT = 300


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
        self._loop: asyncio.AbstractEventLoop = loop

    def send_system_to_human(self, message: str) -> None:
        """システムから人間へメッセージを送る"""
        self.context.system_to_human_message = message
        self.context.status = "waiting_for_human"

    def receive_system_to_human(self) -> str:
        """システムから人間へのメッセージを受けとる"""
        return self.context.system_to_human_message

    def send_human_to_system(self, message: str) -> None:
        """人間からシステムへメッセージを送る"""
        self.context.human_to_system_message = message
        self.context.status = "human_responded"
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self.context.event.set)

    def receive_human_to_system(self) -> str:
        """人間からシステムへのメッセージを受けとる"""
        message = self.context.human_to_system_message
        self.set_status_idle()
        return message

    def set_status_idle(self) -> None:
        """会話のステイタスを idle に変更する"""
        self.context.status = "idle"


class HumanToSystemTimeoutException(Exception):
    """人間の入力がタイムアウトした場合に raise される例外"""

    def __init__(self, message: str = ""):
        super().__init__(message)


@function_tool
async def ask_to_human(run_ctx: RunContextWrapper[Any], question: str) -> str:
    """システムから人間へ問い合わせを行い結果を取得する関数

    Args:
        question: システムから人間への質問の文字列
    """
    interact_manager: HumanInteractManager = run_ctx.context
    interact_manager.context.event.clear()
    interact_manager.send_system_to_human(f"あなたに質問です。\n{question}")
    try:
        await asyncio.wait_for(
            interact_manager.context.event.wait(), timeout=HUMAN_INPUT_TIMEOUT
        )
        response = interact_manager.receive_human_to_system()
    except asyncio.TimeoutError:
        print(
            "人間の応答がありませんでした: Timeout "
            f"{HUMAN_INPUT_TIMEOUT} 秒"
        )
        interact_manager.set_status_idle()
        # funcion_tool は例外を吸収するようので適当な例外を飛ばす
        raise HumanToSystemTimeoutException("人間の応答がありませんでした")
    return response


class GradioUserInterface:
    """Gradio UI の定義"""

    def __init__(self):
        # カレントスレッドを取得
        self.loop = asyncio.get_running_loop()

        # Human Input のコンテキストを定義
        self.interact_manager = HumanInteractManager(self.loop)

    def _update_ui_components(self, ctx: HumanInteractContext):
        """現在のコンテキストに基づいて UI コンポーネントを返す"""
        is_waiting = ctx.status == "waiting_for_human"

        # 入力用 Textbox の設定
        input_textbox_kwargs = {
            "interactive": is_waiting,
            "placeholder": "回答を入力してください" if is_waiting else "",
        }
        if not is_waiting:
            input_textbox_kwargs["value"] = ctx.human_to_system_message

        # UI コンポーネントを作成して返す
        return (
            gr.Textbox(value=ctx.system_to_human_message, interactive=False),
            gr.Textbox(**input_textbox_kwargs),
            gr.Button(interactive=is_waiting),
            gr.Textbox(value=ctx.status, interactive=False),
        )

    def set_components(self) -> gr.Blocks:
        """Gradio UI の定義とコールバックの設定"""

        async def check_interact_update():
            """context の更新を確認"""
            return self._update_ui_components(self.interact_manager.context)

        async def submit_message(human_to_system_message: str):
            """Human Input を System へ送信"""

            if (
                self.interact_manager.context.status == "waiting_for_human"
                and str(human_to_system_message) != ""
            ):
                # 人間の入力内容を tool へ送信
                self.interact_manager.send_human_to_system(
                    human_to_system_message
                )

            return self._update_ui_components(self.interact_manager.context)

        # Gradio の UI を定義
        with gr.Blocks() as demo:
            output_text = gr.Textbox(label="システム -> 人間")
            input_text = gr.Textbox(label="人間 -> システム")
            submit_button = gr.Button("送信")
            status_text = gr.Textbox(label="コンテキストのステイタス")

            outputs = [output_text, input_text, submit_button, status_text]

            # gr.State() で監視したいところだが、event のポインタが
            # 渡らないため、やむを得ずポーリングしている
            gr.Timer(value=0.5).tick(
                fn=check_interact_update,
                inputs=[],
                outputs=outputs,
            )

            # 送信ボタン押下時に発火
            submit_button.click(
                submit_message,
                inputs=[input_text],
                outputs=outputs,
            )

        return demo

    def run_background(
        self, launch_config: Dict[str, Any] = {"share": False}
    ) -> None:
        """Gradio バックエンドをバックグラウンドで起動"""

        # Gradio コンポーネントを配置
        # demo にグローバルでアクセスできないので自動リロードが無効
        demo = self.set_components()

        # Gradio をバックグラウンドで起動
        self.loop.run_in_executor(
            None, functools.partial(demo.launch, launch_config)
        )


async def main():
    # Gradio Components を配置
    gradio_user_interface = GradioUserInterface()

    # Gradio をバックグラウンドで実行
    gradio_user_interface.run_background()

    # Gradio の起動待ちで軽くスリープ(簡易的な実装)
    await asyncio.sleep(3)

    # エージェントを定義
    human_agent = Agent(
        name="人間に質問するエージェント",
        instructions="人間に質問の見解を問います。"
        "相手には感情があるのでできる限り丁寧に聞いてください。",
        tools=[ask_to_human],
        tool_use_behavior="stop_on_first_tool",
        model_settings=ModelSettings(tool_choice="required"),
    )

    # 人間へ問い合わせるエージェントを実行
    interact_manager = gradio_user_interface.interact_manager
    result = await Runner.run(
        human_agent,
        input="今の東京の天気を言いやがれ？",
        context=interact_manager,
    )

    # 結果を表示
    print(f"観測された人間の応答: {result.final_output}")
    print(f"交流のコンテキスト: {interact_manager.context}")
    print("処理終了です。Ctrl-C で抜けてください")


if __name__ == "__main__":
    asyncio.run(main())
