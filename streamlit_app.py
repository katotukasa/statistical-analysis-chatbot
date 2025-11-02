import streamlit as st
import google.generativeai as genai
import os
from pypdf import PdfReader 
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from docx import Document
from docx.shared import Inches
from io import BytesIO

# ==========================================================
# Matplotlibで日本語フォントを設定
# ==========================================================
FONT_PATH = 'ipaexg.ttf' 
try:
    font_prop = font_manager.FontProperties(fname=FONT_PATH)
    plt.rcParams['font.family'] = font_prop.get_name()
    plt.rcParams['axes.unicode_minus'] = False 
    st.session_state.font_prop = font_prop
except FileNotFoundError:
    st.warning(f"警告: 日本語フォントファイル '{FONT_PATH}' が見つかりません。グラフの日本語が文字化けする可能性があります。")
    plt.rcParams['font.family'] = 'DejaVu Sans'
    st.session_state.font_prop = None
# ==========================================================


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
    model = genai.GenerativeModel("gemini-2.5-flash") 
except Exception as e:
    st.error(f"APIキーの認証に失敗しました。正しいキーを入力してください。: {e}")
    st.stop()

# --- プロンプト設定 ---
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
        st.session_state.data_df = df
        
        col_info = "\n".join([f"- {col}: {dtype}" for col, dtype in df.dtypes.items()])
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

# --- グラフ生成およびセッションへの保存機能 (st.pyplotは呼ばない) ---
def generate_and_store_plots(df):
    """
    グラフを生成し、図オブジェクトと画像バッファをセッションに保存する。
    利用可能なグラフのタイトルリストを返す。
    """
    st.session_state.plot_images = {} # Wordレポート用バッファ
    st.session_state.plot_figures = {} # Streamlit表示用figureオブジェクト
    available_plots = []
    
    font_prop = st.session_state.get('font_prop', None)

    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    object_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    # 1. 数値型データのヒストグラム/箱ひげ図
    if numeric_cols:
        # ★【修正】全カラムを対象にする
        for col in numeric_cols:
            # ヒストグラム
            hist_title = f'{col} のヒストグラム'
            fig_hist, ax_hist = plt.subplots(figsize=(4, 3))
            ax
