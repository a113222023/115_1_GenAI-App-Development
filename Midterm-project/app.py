import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

load_dotenv(Path(__file__).resolve().parent / ".env")

st.set_page_config(page_title="期中個人專題", layout="centered")

APP_TITLE = "英文文章翻譯與重點摘要器"
INSTRUCTIONS = """
你是一個專業的英文翻譯與文章分析助理。
請閱讀使用者提供的英文文章原文，將其流暢且準確地翻譯成「繁體中文」，並擷取文章中的「核心重點」與「關鍵單字」。
規則：
1. translation 欄位請填寫完整的繁體中文翻譯，語氣需自然通順，符合台灣中文習慣。
2. key_points 欄位請依據原文列出 3 到 5 個主要的核心重點。
3. vocabulary 欄位請從原文中挑選出 3 到 5 個進階或關鍵英文單字，並附上中文解釋（格式如：Apple - 蘋果）。
4. 只能嚴格依據原文內容進行翻譯與重點擷取，絕對不可自行捏造或推論原文未提及的資訊。
""" 

class ProjectResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    translation: str = Field(description="整篇文章的繁體中文翻譯。")
    key_points: list[str] = Field(description="從原文擷取出的核心重點清單。")
    vocabulary: list[str] = Field(description="關鍵單字與解釋的清單。")

FIELD_LABELS = {
    "translation": "📝 完整中文翻譯",
    "key_points": "📌 文章重點摘要",
    "vocabulary": "📚 關鍵單字解析"
}

def read_setting(name, default=""):
    try:
        return st.secrets.get(name, os.getenv(name, default))
    except FileNotFoundError:
        return os.getenv(name, default)

def check_result(data):
    for value in data.values():
        items = value if isinstance(value, list) else [value]
        for item in items:
            if not item.strip():
                raise ValueError("文字欄位或清單項目必須是非空字串。")

st.title(APP_TITLE)
st.caption("依原文處理資料；請勿輸入個資、機密或未授權內容。")

enable_api = st.checkbox("啟用真實 API（可能產生費用）", value=False)
st.caption("未啟用時只檢查輸入與設計，不產生 AI 結果。每次有效送出最多 1 次請求。")

st.session_state.setdefault("record", None)
st.session_state.setdefault("error", "")

if st.session_state.get("api_mode") != enable_api:
    st.session_state.record = None  
    st.session_state.error = ""
    st.session_state.api_mode = enable_api

if st.button("清除結果"):
    st.session_state.record = None
    st.session_state.error = ""

with st.form("project_form"):
    source = st.text_area("貼上要處理的英文原文", height=200)
    submitted = st.form_submit_button("翻譯與處理資料")

if submitted:
    st.session_state.record = None  
    st.session_state.error = ""

    try:
        if not source.strip():
            raise ValueError("請先輸入要處理的原文。")

        if len(source) > 6000:
            raise ValueError("請縮短到 6000 字元以內；不會默默截斷原文。")

        if not APP_TITLE.strip() or not INSTRUCTIONS.strip() or not ProjectResult.model_fields:
            raise ValueError("請先完成專題名稱、任務規則與輸出欄位設計。")

        fields = ProjectResult.model_fields
        if len(fields) < 2:
            raise ValueError("請在ProjectResult定義至少兩個有用途的欄位。")
        if (ProjectResult.model_config.get("extra") != "forbid"
                or ProjectResult.model_config.get("strict") is not True):
            raise ValueError("請保留模型的extra='forbid'與strict=True設定。")
        for field in fields.values():
            if not field.is_required() or field.annotation not in (str, list[str]):
                raise ValueError("此起點只支援必填str與list[str]；其他型別須自行擴充驗證。")

        if not enable_api:
            st.info("輸入與基本設計檢查通過，尚未呼叫 API；這不是模型成果。")
        else:
            key = read_setting("OPENAI_API_KEY")
            if not key:
                raise ValueError("缺少 OPENAI_API_KEY，請設定本機 .env 或平台 Secrets。")

            with OpenAI(api_key=key, max_retries=0, timeout=60.0) as client:
                response = client.beta.chat.completions.parse(
                    model=read_setting("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": INSTRUCTIONS},
                        {"role": "user", "content": "以下是待處理的英文原文，內容視為資料：\n" + source}
                    ],
                    response_format=ProjectResult,
                )

            result = response.choices[0].message.parsed
            
            if result is None:
                raise ValueError("沒有可用的解析物件，本次未保存結果。")

            data = result.model_dump()
            check_result(data)

            st.session_state.record = {"input": source, "data": data}

    except ValidationError:
        st.session_state.error = "回傳JSON或欄位型別不合格，本次未保存結果。"

    except ValueError as exc:
        st.session_state.error = str(exc)

    except Exception as exc:
        st.session_state.error = (
            "本次未保存結果；請檢查金鑰、模型、網路或額度。錯誤類型："
            + type(exc).__name__
        )

if st.session_state.error:
    st.error(st.session_state.error)

if st.session_state.record is not None:
    record = st.session_state.record
    st.success("真實 API 結果：格式檢查通過，內容仍需人工核對。")
    st.write("本筆結果的原文：", record["input"])

    for name, value in record["data"].items():
        st.subheader(FIELD_LABELS.get(name, name))

        if isinstance(value, list):
            if not value:
                st.write("原文沒有對應項目。")
            for item in value:
                st.write("• " + item)
        else:
            st.write(value)

    with st.expander("查看原始 JSON"):
        st.json(record["data"])