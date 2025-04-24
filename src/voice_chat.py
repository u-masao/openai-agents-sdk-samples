import asyncio

import gradio as gr
import numpy as np


async def reverse_numpy_array_async(data: np.ndarray) -> np.ndarray:
    """
    NumPy 配列を非同期的に逆順にする関数 (デモンストレーション用)。
    実際の処理は同期的だが、async/await の使い方を示す。

    Args:
        data (np.ndarray): 逆順にする NumPy 配列。

    Returns:
        np.ndarray: 逆順になった NumPy 配列。
    """
    await asyncio.sleep(0.1)  # 例: I/O待ちなど非同期処理をシミュレート
    reversed_data = data[::-1]
    return reversed_data


async def reverse_audio(audio):
    """
    入力された音声データを非同期で逆再生する関数。

    Args:
        audio (tuple or None): (サンプリングレート, NumPy配列) のタプル、または None。

    Returns:
        tuple or None: (サンプリングレート, 逆再生されたNumPy配列) のタプル、または None。
                       入力が無効な場合や処理に失敗した場合は None を返す。
    """
    # --- 入力チェック ---
    if audio is None:
        gr.Warning("音声が入力されていません。マイクで録音してください。")
        return None

    sampling_rate, audio_data = audio

    if audio_data is None or audio_data.size == 0:
        gr.Warning("録音データが空です。もう一度録音してください。")
        return None

    # --- 音声処理 (非同期呼び出し) ---
    try:
        # 別の非同期関数を呼び出して音声データを逆順にする
        reversed_audio_data = await reverse_numpy_array_async(audio_data)

        gr.Info("音声を逆再生しました。")

        return (sampling_rate, reversed_audio_data)

    # --- エラーハンドリング ---
    except Exception as e:
        gr.Error(f"音声処理中にエラーが発生しました: {e}")
        return None


# --- Gradio アプリケーションの UI 定義 ---
with gr.Blocks() as demo:
    gr.Markdown(
        """
        # 音声逆再生アプリ (非同期版)
        マイクで録音し、「逆再生実行」ボタンで逆再生します。
        """
    )

    with gr.Row():
        mic_input = gr.Audio(
            sources=["microphone"],
            type="numpy",
            label="マイク入力",
        )
        audio_output = gr.Audio(
            label="逆再生された音声",
            autoplay=True,
            interactive=False,
        )

    reverse_button = gr.Button("逆再生実行")

    # ボタンクリック時または録音終了時の動作を設定
    gr.on(
        [reverse_button.click, mic_input.stop_recording],
        fn=reverse_audio,  # async def 関数を指定
        inputs=mic_input,
        outputs=audio_output,
    )

# --- アプリケーションの起動 ---
if __name__ == "__main__":
    demo.launch(share=False)
