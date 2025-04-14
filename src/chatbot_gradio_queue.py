import asyncio
from typing import Callable

import gradio as gr
from agents import Agent, Runner


class EndOfMessage:
    pass


# エージェントを定義
class CounterAgent:
    def __init__(
        self, max_value: int = 10, output_func: Callable | None = None
    ):
        # 入力チェック
        if max_value < 1:
            raise ValueError("max_value は 1 以上の整数にしてね")

        # カウントする最大値を保存
        self.max_value = max_value

        # コールバックを設定
        self.output_func = (
            output_func if output_func is not None else self.default_output
        )

        # AI エージェントを初期化
        self.agent = Agent(
            name="素っ気ないアシスタント",
            instructions="あなたは素っ気ないアシスタントです。"
            "ユーザーの言葉に対して最小限のテキストで応答して。"
            "ユーザーはJSON形式でメッセージを送りますが、"
            "応答は日本語の文字列にして。",
            model="gpt-4o-mini",
        )

    def default_output(self, message):
        # 標準出力へ出力
        print(f"{message}")

    async def run(self):
        """非同期処理や同期処理をするメソッド"""

        # 入力チェック
        if self.max_value <= 0:
            await self.output_func(EndOfMessage())

        # カウントアップ
        for i in range(self.max_value):

            # AI エージェントを起動
            response = await Runner.run(
                self.agent, f"数字の {i} で連想するものは？"
            )

            # メッセージを作成
            message = f"{i} {response.final_output}"

            # 出力へ送信
            await self.output_func(message)

        # 完了の合図を送信
        await self.output_func(EndOfMessage())


class QueuedCounterAgent(CounterAgent):
    """CounterAgent にメッセージ送受信用の Queue を追加したクラス"""

    def __init__(
        self, max_value: int = 10, output_func: Callable | None = None
    ):
        """コンストラクタ"""
        # 親クラスのコンストラクタを呼び出し
        super().__init__(max_value, output_func)

        # キューを作成
        self.queue = asyncio.Queue()

    async def send_message(self, message: str | EndOfMessage):
        """メッセージをキューに入れる"""
        # メッセージと終了の合図をキューに入れる
        await self.queue.put(message)

    async def receive_message(self):
        """メッセージをキューから出す"""
        # 無限ループ
        while True:
            # キューからメッセージを取り出す(タイムアウトせずにブロッキング)
            message = await self.queue.get()

            # 取り出したタスクが完了したことを宣言
            self.queue.task_done()

            # 終了の合図を受けたらループ脱出
            if isinstance(message, EndOfMessage):
                break

            # メッセージを返して次の呼び出しを待つ
            yield message


async def respond(message, chat_history):
    """タスクの実行と表示"""

    # 会話履歴にユーザーの発言を追加
    chat_history.append({"role": "user", "content": message})
    yield "", chat_history

    # エージェントを初期化
    counter = QueuedCounterAgent()

    # 出力先を変更
    counter.output_func = counter.send_message

    # バックグラウンドでタスクを実行
    counter_task = asyncio.create_task(counter.run())

    # キューからメッセージを取り出すループ
    # EndOfMessage を queue から取り出したら終了
    async for message in counter.receive_message():

        # 会話履歴に追加
        chat_history.append({"role": "assistant", "content": str(message)})
        yield "", chat_history

    # タスクの終了待ち
    await counter_task

    # タスク終了のメッセージを表示
    chat_history.append({"role": "assistant", "content": "カウント終了"})
    yield "", chat_history


with gr.Blocks() as demo:
    # UI を設定
    chatbot = gr.Chatbot(type="messages")
    with gr.Row():
        msg = gr.Textbox(scale=5, label="メッセージを入力してくだされ")
        with gr.Column(scale=1):
            submit = gr.Button("送信")
            clear = gr.ClearButton([msg, chatbot], value="リセット")

    # Gradio UI にコールバックを設定
    gr.on(
        triggers=[msg.submit, submit.click],
        fn=respond,
        inputs=[msg, chatbot],
        outputs=[msg, chatbot],
    )

if __name__ == "__main__":
    # gradio を起動
    demo.launch(share=False, debug=True)
