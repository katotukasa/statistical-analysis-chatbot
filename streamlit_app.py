import streamlit as st
import google.generativeai as genai
import os
from pypdf import PdfReader 
import pandas as pd
import matplotlib.pyplot as plt # グラフ描画ライブラリをインポート

# --- アプリケーションの基本設定 ---
st.set_page_config(
    page_title="統計分析支援チャットボット",
    page_icon="🤖",
    layout="wide",
)

st.title("📊 統計分析支援チャットボット")
st.write(
    "ようこそ！このチャットボットは、あなたがアップロードした文書（統計分析の計画など）やデータ（CSVファイル）に基づいて、**記述統計**、**グラフ化**、**推奨統計処理**の提案を行います。"
)
st.write(
    "まずは、お持ちのGemini APIキーを入力し、分析計画が書かれたファイルまたはCSVファイルをアップロードしてください。"
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
    # モデル名を gemini-2.5-flash に設定
    model = genai.GenerativeModel("gemini-2.5-flash") 
except Exception as e:
    st.error(f"APIキーの認証に失敗しました。正しいキーを入力してください。: {e}")
    st.stop()

# --- プロンプト設定 (クイズ削除、役割変更) ---
SYSTEM_PROMPT = """
あなたは、統計分析の専門家であり、教育者です。
ユーザーから提供された文書（研究計画、分析のメモ、データ構造の概要など）を深く理解し、以下の役割を担ってください。

1.  **記述統計とグラフの解説**: 提供されたCSVファイルの記述統計結果やグラフの内容を、分析の文脈に沿って分かりやすく解説します。
2.  **推奨統計処理の提案**: ドキュメントの内容とデータの特性（記述統計、グラフ）に基づき、最も適切だと思われる統計手法を複数提案し、それぞれのメリット・デメリットを分かりやすく説明します。
3.  **質問応答**: 統計学の概念、特定の手法、ツールの使い方（例：Pythonのライブラリ）など、ユーザーからのあらゆる質問に、初心者にも理解できるように丁寧に答えます。
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

# --- CSVファイルから構造と記述統計を抽出する関数 ---
def get_csv_analysis_text(csv_file):
    """
    アップロードされたCSVファイルから構造、記述統計を抽出し、データフレームをセッションに保存する
    """
    try:
        csv_file.seek(0)
        df = pd.read_csv(csv_file)
        st.session_state.data_df = df # データフレームをセッションに保存
        
        # 1. カラム情報（名前とデータ型）
        col_info = "\n".join([f"- {col}: {dtype}" for col, dtype in df.dtypes.items()])

        # 2. 記述統計
        # 数値型だけでなく、オブジェクト型(カテゴリ)も含めて統計情報を取得
        desc_stats = df.describe(include='all').to_markdown()

        content = (
            f"これは、アップロードされたCSVファイル「{csv_file.name}」のデータ構造と記述統計の概要です。\n"
            f"行数: {len(df)}、列数: {len(df.columns)}\n\n"
            f"### カラム名とデータ型:\n{col_info}\n\n"
            f"### 記述統計の結果:\n{desc_stats}"
        )
        return content
    except Exception as e:
        st.error(f"CSVファイルの読み込みまたは処理中にエラーが発生しました: {e}")
        st.session_state.data_df = pd.DataFrame()
        return ""

# --- グラフ描画機能 ---
def plot_data(df):
    st.subheader("📊 データのグラフ化")
    
    # 数値型とカテゴリ型のカラムを分類
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    object_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    if not numeric_cols and not object_cols:
        st.warning("グラフ化できる適切なデータが見つかりませんでした。")
        return

    # 1. 数値型データのヒストグラム/箱ひげ図
    if numeric_cols:
        st.markdown("#### 🔢 数値データの分布")
        cols = st.columns(2)
        
        # サンプルとして最初の4つの数値カラムのみを表示
        for i, col in enumerate(numeric_cols[:4]):
            with cols[i % 2]:
                st.write(f"**{col}**")
                
                # ヒストグラム
                fig_hist, ax_hist = plt.subplots(figsize=(6, 4))
                ax_hist.hist(df[col].dropna(), bins='auto', edgecolor='black')
                ax_hist.set_title(f'{col} のヒストグラム')
                st.pyplot(fig_hist)
                plt.close(fig_hist) # メモリ解放
                
                # 箱ひげ図
                fig_box, ax_box = plt.subplots(figsize=(6, 4))
                ax_box.boxplot(df[col].dropna())
                ax_box.set_title(f'{col} の箱ひげ図')
                st.pyplot(fig_box)
                plt.close(fig_box) # メモリ解放
                
    # 2. カテゴリ型データの度数分布
    if object_cols:
        st.markdown("#### 🔠 カテゴリデータの分布")
        
        # サンプルとして最初の2つのカテゴリカラムのみを表示
        for col in object_cols[:2]:
            st.write(f"**{col}**")
            
            # 棒グラフ
            counts = df[col].value_counts().head(10) # 上位10項目
            fig_bar, ax_bar = plt.subplots(figsize=(8, 5))
            ax_bar.bar(counts.index.astype(str), counts.values)
            ax_bar.set_title(f'{col} の度数分布')
            ax_bar.tick_params(axis='x', rotation=45)
            plt.tight_layout() # ラベルがはみ出さないように調整
            st.pyplot(fig_bar)
            plt.close(fig_bar) # メモリ解放


# ファイルアップローダー
uploaded_file = st.file_uploader(
    "分析計画のファイル（.md、.txt、.pdf）またはデータファイル（.csv）をアップロードしてください",
    type=["md", "txt", "pdf", "csv"]
)

if uploaded_file is not None:
    # ファイルが変わった場合、メッセージ履歴と要約をリセット
    if "last_uploaded_filename" not in st.session_state or st.session_state.last_uploaded_filename != uploaded_file.name:
        st.session_state.last_uploaded_filename = uploaded_file.name
        st.session_state.messages = []
        st.session_state.summary = None 
        st.session_state.data_df = pd.DataFrame() # 新しいデータフレーム

        file_extension = uploaded_file.name.split(".")[-1].lower()
        st.session_state.document_content = ""
        
        try:
            with st.spinner(f"「{uploaded_file.name}」の内容を読み込み中..."):
                if file_extension in ["md", "txt"]:
                    uploaded_file.seek(0)
                    st.session_state.document_content = uploaded_file.read().decode("utf-8")
                elif file_extension == "pdf":
                    st.session_state.document_content = read_pdf_text(uploaded_file)
                elif file_extension == "csv":
                    # CSVの場合は、記述統計結果とデータフレームをセッションに格納
                    st.session_state.document_content = get_csv_analysis_text(uploaded_file)
                else:
                    st.error("サポートされていないファイル形式です。")
                    st.stop()
            
            if st.session_state.document_content:
                st.success(f"「{uploaded_file.name}」の読み込みが完了しました。")
            else:
                st.warning(f"「{uploaded_file.name}」から内容を抽出できませんでした。ファイル内容を確認してください。")
                st.stop()

        except Exception as e:
            st.error(f"ファイル内容の処理中に致命的なエラーが発生しました: {e}")
            st.stop()
    
    # --- 記述統計とグラフの表示 ---
    is_csv_file = st.session_state.last_uploaded_filename.split(".")[-1].lower() == "csv"

    if is_csv_file and not st.session_state.data_df.empty:
        # CSVファイルの場合、記述統計の結果を常に表示
        with st.expander("📚 CSVデータ構造と記述統計の結果", expanded=True):
            st.markdown(st.session_state.document_content)
            
        # グラフ化機能を実行
        plot_data(st.session_state.data_df)
        
    # --- AIによる推奨処理の提案 ---
    if st.session_state.document_content and not st.session_state.summary:
        with st.spinner("AIが推奨統計処理の提案を作成しています..."):
            try:
                # CSVの場合は、推奨統計処理の提案を生成
                if is_csv_file:
                    summary_prompt = (
                        f"{SYSTEM_PROMPT}\n\n---\n\n"
                        f"以下のCSVデータ構造の概要と記述統計の結果に基づき、このデータで可能な**推奨統計処理を簡潔に提案し、そのメリットを説明してください。**\n\n"
                        f"{st.session_state.document_content}"
                    )
                    expander_title = "アップロードされたデータに基づいた推奨統計処理の提案"
                # それ以外の文書の場合は、要約を生成
                else:
                    summary_prompt = f"{SYSTEM_PROMPT}\n\n---\n\n以下のドキュメントを3〜5行で簡潔に要約し、文書内容に基づいた統計手法の候補を提案してください。\n\n{st.session_state.document_content}"
                    expander_title = "アップロードされたドキュメントの要約と統計手法の候補"

                response = model.generate_content(summary_prompt)
                st.session_state.summary = response.text
                st.session_state.expander_title = expander_title

            except Exception as e:
                st.error(f"AIによる提案の生成中にエラーが発生しました: {e}")

    if st.session_state.summary:
        with st.expander(st.session_state.expander_title, expanded=True):
            st.markdown(st.session_state.summary)

    # --- チャット機能 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 過去のメッセージを表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザーからの新しいメッセージ
    if prompt := st.chat_input("ファイル内容や分析結果について質問してください"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        try:
            with st.chat_message("assistant"):
                with st.spinner("AIが応答を生成中です..."):
                    # プロンプトにシステム設定、ドキュメント、会話履歴をすべて含める
                    full_prompt = (
                        f"{SYSTEM_PROMPT}\n\n"
                        f"--- 以下はアップロードされたファイルの内容（またはCSVの記述統計）です ---\n"
                        f"{st.session_state.document_content}\n\n"
                        f"--- 以下はこれまでの会話履歴と現在の質問です ---\n"
                    )
                    # メッセージ履歴をプロンプトに追加
                    for msg in st.session_state.messages:
                        full_prompt += f"{msg['role']}: {msg['content']}\n"

                    response_stream = model.generate_content(full_prompt, stream=True)
                    
                    full_response = ""
                    response_placeholder = st.empty()
                    for chunk in response_stream:
                        if chunk.text:
                            full_response += chunk.text
                            response_placeholder.markdown(full_response + " ▌")
                    response_placeholder.markdown(full_response)

            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"応答の生成中にエラーが発生しました: {e}")

else:
    st.info("ファイルをアップロードすると、チャットが開始できます。")
