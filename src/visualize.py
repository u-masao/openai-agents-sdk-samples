import io

import gradio as gr
from agents import Agent, Runner, function_tool
from agents.extensions.visualization import draw_graph, get_main_graph
from PIL import Image
from pydantic import BaseModel


# 英語とインドネシア語のエージェントの定義
@function_tool
def get_weather(city: str) -> str:
    """指定の都市の天気を取得するツール"""
    return f"{city} の天気は晴れだっちゃ。"


bahasa_indonesia_agent = Agent(
    name="インドネシア語エージェント",
    instructions="あなたはインドネシア語しか出力しません。",
)

english_agent = Agent(
    name="英語エージェント",
    instructions="あなたは英語しか出力しません。",
)

triage_agent = Agent(
    name="トリアージエージェント",
    instructions="リクエストの言語に基づいて適切なエージェントに引き継ぎます",
    handoffs=[bahasa_indonesia_agent, english_agent],
    tools=[get_weather],
)


# ダイアグラムを変換するエージェント
class DiagramMessage(BaseModel):
    body: str
    comment: str


diagram_agent = Agent(
    name="ダイアグラムエージェント",
    instructions="""
        あなたはダイアグラムの専門家です。
        Graphviz dot、Mermaid、PlantUML 等のダイアグラム描画ライブラリの
        利用方法に精通しています。
        ユーザーのリクエストに応じてダイアグラムを修正または変換して。
        body にはダイアグラムのコードのみを記載して。
        comment には変換結果のコメントを日本語で記載して。
    """,
    output_type=DiagramMessage,
)


async def on_load():
    """
    Gradio がロードされた後に呼ばれる関数
    """

    # convert
    diagram_string = get_main_graph(triage_agent)
    mermaid = await Runner.run(
        diagram_agent,
        input=f"""
        Mermaid に変換して。色は無視して。

        ```
        {diagram_string}
        ```
    """,
    )

    text = f"""
    ダイアグラムのコードを変換しました。

    ### 変換前(Graphviz dot)

    ```
    {diagram_string}
    ```

    ### 変換後(Mermaid)

    {mermaid.final_output.body}

    ### 変換コメント

    {mermaid.final_output.comment}
    """

    return (
        gr.Markdown(mermaid.final_output.body),
        gr.Textbox(text, lines=40),
    )


def get_pil_image_from_agent(agent):
    """OpenAI Agents SDK のビジュアライズ機能を利用
    Graphviz で PIL イメージを作成"""
    graph = draw_graph(agent)
    image_stream = io.BytesIO(graph.pipe(format="png"))
    return Image.open(image_stream)


with gr.Blocks() as demo:
    with gr.Row():
        image = gr.Image(
            get_pil_image_from_agent(triage_agent),
            label="オリジナル(Graphviz)",
        )
        with gr.Column():
            with gr.Group():
                markdown = gr.Markdown(label="mermaid")
            with gr.Accordion(open=False):
                text = gr.Textbox(lines=40)
    demo.load(fn=on_load, inputs=[], outputs=[markdown, text])

if __name__ == "__main__":
    demo.launch(share=False, debug=True)
