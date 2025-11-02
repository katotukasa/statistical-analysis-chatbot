CSVファイルの読み込み機能を追加する修正案を作成しました。

CSVファイルはデータそのものであるため、AIが分析の文脈を理解しやすいように、ファイル全体をテキストとして渡すのではなく、**データフレームの構造（カラム名とデータ型）と最初の数行**を要約してテキストとして渡すアプローチを採用します。これにより、トークン数の節約にもなり、大規模なCSVファイルに対応しやすくなります。

## 🛠️ 変更点の概要

1.  **`requirements.txt` の更新**: CSVファイルを効率的に扱うための **`pandas`** パッケージを追加します。
2.  **`streamlit_app.py` の修正**:
      * `pandas` をインポート。
      * `st.file_uploader` で `"csv"` を許可。
      * CSVを読み込み、構造を要約テキストとして生成する新しいロジックを追加。

-----

## 1\. `requirements.txt` の更新

以下の内容を **`requirements.txt`** に追記（または確認）してください。

```txt
streamlit
google-genai
pypdf
pandas  # ★これを追加
```

ローカルで実行する場合は、忘れずにインストールしてください。

```bash
pip install -r requirements.txt
```

-----

## 2\. `streamlit_app.py` の修正

`pandas` をインポートし、CSVファイル処理用の関数とロジックを追加したコード全体を以下に示します。

```python
import streamlit as st
import google.generativeai as genai
import os
from pypdf import PdfReader
import pandas as pd # ★【追加】pandasをインポート

# --- アプリケーションの基本設定 ---
st.set_page_config(
    page_title="統計分析支援チャットボット",
    page_icon="🤖",
    layout="wide",
)

st.title("📊 統計分析支援チャットボット")
st.write(
    "ようこそ！このチャットボットは、あなたがアップロードした文書（統計分析の計画など）に基づいて、統計手法の提案や質問への回答、学習のためのクイズ出題などを行います。"
)
st.write(
    "まずは、お持ちのGemini APIキーを入力し、分析計画が書かれたファイルをアップロードしてください。"
)

# --- サイドバーでのAPIキー入力 ---
with st.sidebar:
    gemini_api_key = st.text_input("Gemini API Key", type="password", key="gemini_api_key")
    "[Gemini APIキーを取得する](https://aistudio.google.com/app/apikey)"

# --- メインコンテンツ ---
if not gemini_api_key:
    st.info("サイドバーからGemini APIキーを入力してください。")
    st.stop()

# APIキーの認証
try:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel("gemini-pro")
except Exception as e:
    st.error(f"APIキーの認証に失敗しました。正しいキーを入力してください。: {e}")
    st.stop()

# --- プロンプト設定 ---
SYSTEM_PROMPT = """
あなたは、統計分析の専門家であり、教育者です。
ユーザーから提供された文書（研究計画や分析したいことのメモ）を深く理解し、以下の役割を担ってください。

1.  **統計手法の提案**: 文書の内容に基づき、最も適切だと思われる統計手法を複数提案し、それぞれのメリット・デメリットを分かりやすく説明します。
2.  **質問応答**: 統計学の概念、特定の手法、ツールの使い方（例：Pythonのライブラリ）など、ユーザーからのあらゆる質問に、初心者にも理解できるように丁寧に答えます。
3.  **クイズ出題**: ユーザーの学習を促進するため、会話の流れに応じて統計に関するクイズを出題します。
4.  **対話の記憶**: 過去の会話を記憶し、文脈に沿った対話を続けます。

あなたの目的は、ユーザーが自身の研究や学習において、統計分析を正しく、かつ自信を持って活用できるようになることを支援することです。
"""

# --- PDFファイルからテキストを抽出する関数 ---
def read_pdf_text(pdf_file):
    """
    アップロードされたPDFファイルからすべてのページテキストを抽出する
    """
    try:
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n\n"
        return text
    except Exception as e:
        st.error(f"PDFの読み込み中にエラーが発生しました: {e}")
        return ""

# --- CSVファイルから構造とサンプルを抽出する関数 ---
def read_csv_text(csv_file):
    """
    アップロードされたCSVファイルから構造と最初の数行を抽出する
    """
    try:
        # StreamlitのUploadedFileオブジェクトからCSVを読み込む
        df = pd.read_csv(csv_file)
        
        # カラム情報（名前とデータ型）の作成
        col_info = "\n".join([f"- {col}: {dtype}" for col, dtype in df.dtypes.items()])

        # 最初の5行をMarkdownテーブルとして表示
        sample_data = df.head(5).to_markdown(index=False)
        
        content = (
            f"これは、アップロードされたCSVファイル「{csv_file.name}」のデータ構造の概要です。\n"
            f"行数: {len(df)}、列数: {len(df.columns)}\n\n"
            f"### カラム名とデータ型:\n{col_info}\n\n"
            f"### 最初の5行のサンプルデータ:\n{sample_data}"
        )
        return content
    except Exception as e:
        st.error(f"CSVファイルの読み込みまたは処理中にエラーが発生しました: {e}")
        return ""

# ファイルアップローダー
uploaded_file = st.file_uploader(
    # ★【修正】typeリストに "csv" を追加
    "分析計画のファイル（.md、.txt、.pdf、.csv）をアップロードしてください",
    type=["md", "txt", "pdf", "csv"]
)

if uploaded_file is not None:
    # アップロードされたファイルはセッション状態で管理
    # ファイルが変わった場合、メッセージ履歴と要約をリセット
    if "last_uploaded_filename" not in st.session_state or st.session_state.last_uploaded_filename != uploaded_file.name:
        st.session_state.last_uploaded_filename = uploaded_file.name
        st.session_state.messages = []
        st.session_state.summary = None # ファイルが変わったら要約もリセット

        file_extension = uploaded_file.name.split(".")[-1].lower()
        st.session_state.document_content = ""
        
        try:
            with st.spinner(f"「{uploaded_file.name}」の内容を読み込み中..."):
                if file_extension in ["md", "txt"]:
                    # .md または .txt の場合
                    uploaded_file.seek(0)
                    st.session_state.document_content = uploaded_file.read().decode("utf-8")
                elif file_extension == "pdf":
                    # .pdf の場合
                    st.session_state.document_content = read_pdf_text(uploaded_file)
                elif file_extension == "csv": # ★【追加】CSVの場合の処理
                    # .csv の場合
                    st.session_state.document_content = read_csv_text(uploaded_file)
                else:
                    st.error("サポートされていないファイル形式です。")
                    st.stop()
            
            if st.session_state.document_content:
                st.success(f"「{uploaded_file.name}」の内容を読み込みました。")
            else:
                st.warning(f"「{uploaded_file.name}」からテキストを抽出できませんでした。ファイル内容を確認してください。")
                st.stop()

        except Exception as e:
            st.error(f"ファイル内容の処理中に致命的なエラーが発生しました: {e}")
            st.stop()

    # --- 要約機能 ---
    if st.session_state.document_content and not st.session_state.summary:
        with st.spinner("AIがドキュメントの要約を作成しています..."):
            try:
                # CSVの場合は要約プロンプトを調整（データ構造として認識させるため）
                if st.session_state.last_uploaded_filename.split(".")[-1].lower() == "csv":
                    summary_prompt = (
                        f"{SYSTEM_PROMPT}\n\n---\n\n"
                        f"以下のCSVデータ構造の概要に基づき、このデータでどのような統計分析が可能か、3〜5行で簡潔に提案してください。\n\n"
                        f"{st.session_state.document_content}"
                    )
                else:
                    summary_prompt = f"{SYSTEM_PROMPT}\n\n---\n\n以下のドキュメントを3〜5行で簡潔に要約してください。\n\n{st.session_state.document_content}"
                
                response = model.generate_content(summary_prompt)
                st.session_state.summary = response.text
            except Exception as e:
                st.error(f"要約の生成中にエラーが発生しました: {e}")

    if st.session_state.summary:
        with st.expander("アップロードされたドキュメントの要約/分析提案", expanded=True):
            st.markdown(st.session_state.summary)

    # --- チャット機能 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 過去のメッセージを表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザーからの新しいメッセージ
    if prompt := st.chat_input("ファイル内容について質問してください"):
        # ユーザーのメッセージを保存して表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AIからの応答を生成・表示
        try:
            with st.chat_message("assistant"):
                with st.spinner("AIが応答を生成中です..."):
                    # プロンプトにシステム設定、ドキュメント、会話履歴をすべて含める
                    full_prompt = (
                        f"{SYSTEM_PROMPT}\n\n"
                        f"--- 以下はアップロードされたドキュメントです ---\n"
                        f"{st.session_state.document_content}\n\n"
                        f"--- 以下はこれまでの会話履歴と現在の質問です ---\n"
                    )
                    for msg in st.session_state.messages:
                        full_prompt += f"{msg['role']}: {msg['content']}\n"

                    # ストリーミングで応答を生成
                    response_stream = model.generate_content(full_prompt, stream=True)
                    
                    # レスポンスを結合するための変数
                    full_response = ""
                    response_placeholder = st.empty()
                    for chunk in response_stream:
                        if chunk.text:
                            full_response += chunk.text
                            response_placeholder.markdown(full_response + " ▌")
                    response_placeholder.markdown(full_response)

            # AIの応答をセッション状態に保存
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"応答の生成中にエラーが発生しました: {e}")

else:
    st.info("ファイルをアップロードすると、チャットが開始できます。")
```
