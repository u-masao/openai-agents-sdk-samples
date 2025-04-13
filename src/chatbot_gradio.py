import json

import gradio as gr
from agents import Agent, Runner

with gr.Blocks() as demo:
    # UI を定義
    chatbot = gr.Chatbot(type="messages")
    with gr.Row():
        msg = gr.Textbox(show_label=False, scale=7)
        with gr.Column(scale=1):
            submit = gr.Button("送信")
            clear = gr.ClearButton([msg, chatbot], value="リセット")

    # エージェントを定義
    agent = Agent(
        name="素っ気ないアシスタント",
        instructions="あなたは素っ気ないアシスタントです。"
        "ユーザーの言葉に対して最小限のテキストで応答して。"
        "ユーザーはJSON形式でメッセージを送りますが、"
        "応答は日本語の文字列にして。",
        model="gpt-4o-mini",
    )

    # Runner.run() を非同期で呼ぶので async def を指定
    async def respond(message, chat_history):
        """メッセージ送信時の処理"""
        # 会話履歴にユーザーの発言を追加
        chat_history.append({"role": "user", "content": message})

        # エージェントに会話履歴を送信
        response = await Runner.run(
            # ensure_ascii=False することで JSON エンコードを抑制
            # LLM がメッセージを解釈しやすくなるようです
            agent,
            json.dumps(chat_history, ensure_ascii=False),
        )

        # エージェントの出力を取得
        bot_message = response.final_output

        # エージェントの出力を会話履歴に追加
        chat_history.append({"role": "assistant", "content": bot_message})

        # Gradui UI に会話履歴を返す
        return "", chat_history

    # Gradio UI にコールバックを設定
    gr.on(
        triggers=[msg.submit, submit.click],
        fn=respond,
        inputs=[msg, chatbot],
        outputs=[msg, chatbot],
    )

if __name__ == "__main__":
    # gradio を起動
    demo.launch(share=True, debug=True)
