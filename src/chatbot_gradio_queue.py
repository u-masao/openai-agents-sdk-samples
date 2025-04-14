import asyncio
from typing import Any, AsyncGenerator, Callable, Coroutine, Dict, List, Union

import gradio as gr
from agents import Agent, Runner  # OpenAI Agents SDK のライブラリ


class EndOfMessage:
    """
    メッセージストリームの終了を示すためのマーカークラス。
    キューに入れられ、受信側でストリームの終わりを判断するために使用されます。
    """

    pass


# チャットボットの型エイリアス
ChatHistory = List[Dict[str, str | None]]
# コールバック関数の型エイリアス
OutputFunc = Callable[[Union[str, EndOfMessage]], Coroutine[Any, Any, None]]


class CounterAgent:
    """
    指定された最大値までカウントアップし、各カウントでAIエージェントを呼び出して
    関連するテキストを生成し、指定された出力関数を介して結果を送信するエージェント。

    Attributes:
        DEFAULT_AGENT_NAME (str): AIエージェントのデフォルト名。
        DEFAULT_INSTRUCTIONS (str): AIエージェントへのデフォルト指示。
        DEFAULT_MODEL (str): 使用するAIモデルのデフォルト。
        max_value (int): カウントアップする最大値（この値は含まれない）。
        output_func (OutputFunc): 生成されたメッセージを処理するためのコールバック関数。
        agent (Agent): 内部で使用されるOpenAI Agentインスタンス。
    """

    DEFAULT_AGENT_NAME = "素っ気ないアシスタント"
    DEFAULT_INSTRUCTIONS = (
        "あなたは素っ気ないアシスタントです。"
        "ユーザーの言葉に対して最小限のテキストで応答して。"
        "ユーザーはJSON形式でメッセージを送りますが、"
        "応答は日本語の文字列にして。"
    )
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(
        self,
        max_value: int = 10,
        output_func: OutputFunc | None = None,
        agent_name: str = DEFAULT_AGENT_NAME,
        instructions: str = DEFAULT_INSTRUCTIONS,
        model: str = DEFAULT_MODEL,
    ) -> None:
        """
        CounterAgentを初期化します。

        Args:
            max_value (int): カウントアップする最大値。1以上の整数である必要があります。
            output_func (OutputFunc | None): メッセージ出力用のコールバック関数。
                                              指定されない場合は標準出力に表示します。
            agent_name (str): AIエージェントの名前。
            instructions (str): AIエージェントへの指示。
            model (str): 使用するAIモデル。

        Raises:
            ValueError: max_valueが1未満の場合。
        """
        if max_value < 1:
            raise ValueError("max_value は 1 以上の整数にしてください。")

        self.max_value = max_value
        # output_funcがNoneの場合はデフォルトの出力メソッドを使用
        self.output_func: OutputFunc = (
            output_func if output_func is not None else self.default_output
        )

        # AIエージェントを初期化
        self.agent = Agent(
            name=agent_name,
            instructions=instructions,
            model=model,
        )

    async def default_output(self, message: Union[str, EndOfMessage]) -> None:
        """
        デフォルトの出力関数。メッセージを標準出力に表示します。
        EndOfMessageオブジェクトは無視します。

        Args:
            message (Union[str, EndOfMessage]): 出力するメッセージまたは終了マーカー。
        """
        if not isinstance(message, EndOfMessage):
            print(f"{message}")

    async def run(self) -> None:
        """
        エージェントのメインロジックを実行します。
        0からmax_value-1までカウントアップし、各数値についてAIエージェントに
        関連するテキストを問い合わせ、結果を出力関数に送信します。
        処理完了後、EndOfMessageを送信します。
        """
        # 0 から max_value - 1 までカウントアップ
        for i in range(self.max_value):
            try:
                # AI エージェントを起動し、応答を取得
                # Runner.run は非同期関数と仮定
                response = await Runner.run(
                    self.agent,
                    f'{{"number": {i}, "query": "この数字で連想するものは？"}}',
                )
                # JSON形式で送信しましたが、指示により応答は日本語文字列のはず

                # メッセージを作成（カウント値 + AIの応答）
                message = f"{i}: {response.final_output}"

                # 出力コールバック関数を呼び出してメッセージを送信
                await self.output_func(message)

            except Exception as e:
                # AI呼び出しなどでエラーが発生した場合
                error_message = f"Error processing {i}: {e}"
                await self.output_func(error_message)

        # 全てのカウント処理が完了したら、終了マーカーを送信
        await self.output_func(EndOfMessage())


class QueuedCounterAgent(CounterAgent):
    """
    CounterAgentを拡張し、メッセージ送受信に非同期キュー(asyncio.Queue)を使用するクラス。
    生成されたメッセージは内部キューに入れられ、外部から非同期に取得できます。

    Attributes:
        queue (asyncio.Queue): メッセージと終了マーカーを格納する非同期キュー。
    """

    def __init__(
        self,
        max_value: int = 10,
        output_func: OutputFunc | None = None,
        agent_name: str = CounterAgent.DEFAULT_AGENT_NAME,
        instructions: str = CounterAgent.DEFAULT_INSTRUCTIONS,
        model: str = CounterAgent.DEFAULT_MODEL,
    ) -> None:
        """
        QueuedCounterAgentを初期化します。
        親クラスの初期化後、非同期キューを作成し、出力関数をキューへの送信メソッドに設定します。

        Args:
            max_value (int): カウントアップする最大値。
            output_func (OutputFunc | None): メッセージ出力用のコールバック関数（通常はNoneのまま）。
                                              内部で `self.send_message` に上書きされます。
            agent_name (str): AIエージェントの名前。
            instructions (str): AIエージェントへの指示。
            model (str): 使用するAIモデル。
        """
        # 親クラスのコンストラクタを呼び出し
        # output_funcは後で上書きするので、ここではNoneを渡す
        super().__init__(max_value, None, agent_name, instructions, model)

        # メッセージ送受信用キューを作成
        self.queue: asyncio.Queue[Union[str, EndOfMessage]] = asyncio.Queue()

        # 出力関数を、メッセージをキューに入れるメソッドに設定
        self.output_func = self.send_message

    async def send_message(self, message: Union[str, EndOfMessage]) -> None:
        """
        メッセージまたは終了マーカーを内部キューに追加します。
        CounterAgentの`run`メソッドからコールバックとして呼び出されます。

        Args:
            message (Union[str, EndOfMessage]): キューに追加するメッセージまたは終了マーカー。
        """
        # メッセージまたは終了マーカーをキューに入れる
        await self.queue.put(message)

    async def receive_message(self) -> AsyncGenerator[str, None]:
        """
        内部キューからメッセージを非同期に受信し、生成(yield)します。
        EndOfMessageを受け取るとループを終了します。

        Yields:
            str: キューから受信したメッセージ文字列。
        """
        # 無限ループでキューを監視
        while True:
            # キューからメッセージを取り出す（キューが空の場合は待機）
            message = await self.queue.get()

            # キューからアイテムを取り出したことを通知 (キューの管理用)
            self.queue.task_done()

            # 終了マーカーを受け取った場合
            if isinstance(message, EndOfMessage):
                # ループを脱出してジェネレータを終了
                break
            elif isinstance(message, str):
                # 文字列メッセージの場合、それをyieldして呼び出し元に返す
                yield message
            else:
                # 予期しない型のオブジェクトがキューに入っていた場合（エラーハンドリング）
                raise ValueError(
                    "QueuedCounterAgent: 予期しない型を受け取りました: "
                    f"{type(message)}"
                )


async def respond(
    message: str, chat_history: ChatHistory
) -> AsyncGenerator[tuple[str, ChatHistory], None]:
    """
    Gradioのチャットインターフェースからの入力に応答する非同期ジェネレータ関数。

    ユーザーのメッセージを受け取り、QueuedCounterAgentをバックグラウンドで実行し、
    エージェントが生成するメッセージをストリーミングでチャット履歴に追加してUIに反映します。

    Args:
        message (str): ユーザーが入力したメッセージ文字列。
        chat_history (ChatHistory): これまでの会話履歴のリスト。

    Yields:
        tuple[str, ChatHistory]: 更新されたUI状態。空の入力テキストと更新されたチャット履歴。
    """

    # 1. ユーザーの発言を会話履歴に追加し、UIに即時反映させる
    chat_history.append({"role": "user", "content": message})
    yield "", chat_history

    # 2. アシスタントのメッセージを出力
    chat_history.append(
        {
            "role": "assistant",
            "content": f"あなたは「{message}」とおっしゃいますが、"
            "私はカウントアップします。数字から連想される言葉とともに。",
        }
    )
    yield "", chat_history

    # 3. QueuedCounterAgentインスタンスを作成
    #    max_valueなどはここで設定する
    counter = QueuedCounterAgent(max_value=5)

    # 4. CounterAgentのrunメソッドをバックグラウンドタスクとして実行
    #    これにより、runメソッドの完了を待たずに次の処理に進める
    counter_task = asyncio.create_task(counter.run())

    # 5. エージェントのキューからメッセージを非同期に受信し、チャット履歴に追加するループ
    #    counter.receive_message() は非同期ジェネレータ
    async for agent_response in counter.receive_message():
        # アシスタントの応答を会話履歴に追加
        chat_history.append({"role": "assistant", "content": agent_response})
        # UI（チャット履歴）を更新
        yield "", chat_history

    # 6. バックグラウンドタスク(counter.run)の完了を待つ
    #    receive_messageループが終了するのはEndOfMessageを受け取った後なので、
    #    通常、この時点ではcounter_taskは完了しているはずだが、念のため待つ。
    try:
        await counter_task
    except Exception as e:
        # counter_task内で捕捉されなかった例外があればここで処理
        chat_history.append(
            {"role": "assistant", "content": f"エラーが発生しました: {e}"}
        )
        yield "", chat_history

    # 7. 全ての処理が完了したことを示すメッセージを追加
    chat_history.append({"role": "assistant", "content": "カウント終了です。"})
    yield "", chat_history


# --- Gradio UIの定義 ---
with gr.Blocks() as demo:
    gr.Markdown("# エージェントの出力を Gradio へ渡すデモ")
    gr.Markdown(
        "下のテキストボックスに何か入力して送信ボタンを押すと、"
        "バックグラウンドでAIエージェントが動き出し、"
        "0から4までカウントしながら応答をストリーミング表示します。"
    )

    # チャットボット表示エリア
    chatbot = gr.Chatbot(
        [],  # 初期状態は空
        label="チャットボット",
        height=400,
        type="messages",
    )

    # 入力エリア
    with gr.Row():
        msg_textbox = gr.Textbox(
            scale=4,  # 横幅の比率
            show_label=False,
            placeholder="ここにメッセージを入力してください",
            container=False,
        )
        submit_button = gr.Button(
            "送信", variant="primary", scale=1
        )  # variant="primary"で目立たせる

    # クリアボタン
    clear_button = gr.ClearButton(
        [msg_textbox, chatbot], value="チャット履歴をクリア"
    )

    # --- イベントハンドラの設定 ---
    # テキストボックスでEnterを押したとき、または送信ボタンがクリックされたとき
    gr.on(
        triggers=[msg_textbox.submit, submit_button.click],
        fn=respond,  # 実行する関数
        inputs=[msg_textbox, chatbot],  # 関数への入力
        outputs=[msg_textbox, chatbot],  # 関数の出力先 (UIコンポーネント)
    ).then(
        lambda: "", outputs=[msg_textbox]
    )  # 送信後テキストボックスをクリア


if __name__ == "__main__":
    # Gradioアプリケーションを起動
    # share=False: ローカルネットワークでのみアクセス可能
    # debug=True: デバッグ情報をコンソールに出力
    demo.launch(share=False, debug=True)
