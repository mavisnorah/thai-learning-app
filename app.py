# app.py
import streamlit as st
import pandas as pd
import random
import difflib
import unicodedata
from pathlib import Path

# ---------- 1) 載入題庫（cache_resource + Parquet） ----------
PARQUET_PATH = Path(__file__).parent / "thai_sentences.parquet"
CSV_PATH     = Path(__file__).parent / "thai_sentences.csv"

@st.cache_resource
def load_data() -> pd.DataFrame:
    """優先讀 Parquet；若不存在先讀 CSV 再轉存 Parquet。"""
    if PARQUET_PATH.exists():
        df = pd.read_parquet(PARQUET_PATH)
    else:
        df = pd.read_csv(CSV_PATH)
        try:
            df.to_parquet(PARQUET_PATH, index=False)   # 下次啟動更快
        except Exception:
            pass
    return df

input_df = load_data()

# ---------- 2) 單一隨機源 + 干擾池 ----------
rng = random.Random()                            # 只建一個 RNG
POOL_SIZE = min(500, len(input_df))              # 干擾池最多 500 句
TH_POOL   = rng.sample(input_df["泰文"].tolist(), POOL_SIZE)
CH_POOL   = rng.sample(input_df["中文句子"].tolist(), POOL_SIZE)

# ---------- 3) 初始化 session ----------
defaults = {
    "mode": "整句輸入",
    "input_index": rng.randrange(len(input_df)),
    "ct_index":    rng.randrange(len(input_df)),
    "tc_index":    rng.randrange(len(input_df)),
    "answered": False,
    "user_input": "",
    "ct_options": None, "ct_correct": None,
    "tc_options": None, "tc_correct": None,
    "ct_answered": False,   # 中→泰
    "tc_answered": False,   # 泰→中
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ---------- 4) 共用工具 ----------
def normalize(txt: str) -> str:
    txt = ''.join(c for c in str(txt) if not unicodedata.category(c).startswith('P'))
    return txt.replace(" ", "").lower()

def diff_mark(correct: str, user: str) -> str:
    seq = difflib.SequenceMatcher(None, correct, user)
    return "".join(
        correct[i1:i2] if tag == "equal" else f"**:red[{user[j1:j2]}]**"
        for tag, i1, i2, j1, j2 in seq.get_opcodes()
    )

def get_or_create_options(key_opt: str, key_ans: str,
                          correct: str, pool: list[str], k: int = 3):
    """每題只抽一次選項（快取於 session_state）。"""
    if st.session_state[key_opt] is None:
        distractors = rng.sample([x for x in pool if x != correct], k)
        opts = distractors + [correct]
        rng.shuffle(opts)
        st.session_state[key_opt] = opts
        st.session_state[key_ans] = correct
    return st.session_state[key_opt], st.session_state[key_ans]

# ---------- 5) 版面 ----------
st.title("📘 泰文練習 App")

modes = ["整句輸入", "選擇題（中揀泰）", "選擇題（泰揀中）"]
mode   = st.radio("請選擇練習模式：", modes,
                  index=modes.index(st.session_state.mode))

if mode != st.session_state.mode:                 # 切換模式 → 清舊狀態
    st.session_state.answered   = False
    st.session_state.user_input = ""
    st.session_state.ct_options = None
    st.session_state.tc_options = None
st.session_state.mode = mode

# ---------- A. 整句輸入 ----------
if mode == "整句輸入":
    row = input_df.iloc[st.session_state.input_index]
    st.subheader("🧠 中文句子：")
    st.write(row["中文句子"])

    with st.form("input_form"):
        input_method = st.radio("你想輸入：", ["泰文", "羅馬拼音"], key="method")
        user_input   = st.text_input(
            "✍️ 請輸入你的答案：",
            value=st.session_state.user_input,
            key="input"
        )
        submitted = st.form_submit_button("✅ 送出答案")

    if submitted and user_input.strip():
        st.session_state.answered     = True
        st.session_state.user_input   = user_input
        st.session_state.input_method = input_method

    if st.session_state.answered:
        correct_raw = (
            row["泰文"] if st.session_state.get("input_method") == "泰文"
            else row["羅馬拼音"]
        )
        if normalize(st.session_state.user_input) == normalize(correct_raw):
            st.success("✅ 答對啦！")
        else:
            st.error("❌ 答錯了～")
            st.markdown("**正確答案：** " + correct_raw)
            st.markdown(
                "**你輸入：** " +
                diff_mark(correct_raw, st.session_state.user_input)
            )

    if st.button("👉 下一題"):
        st.session_state.input_index = rng.randrange(len(input_df))
        st.session_state.answered    = False
        st.session_state.user_input  = ""

# ---------- B. 選擇題（中揀泰） ----------
elif mode == "選擇題（中揀泰）":
    row = input_df.iloc[st.session_state.ct_index]
    st.subheader("🧠 中文句子：")
    st.write(row["中文句子"])

    correct_th = row["泰文"]

    # 固定選項
    options, correct_th = get_or_create_options(
        "ct_options", "ct_correct",
        correct_th, TH_POOL
    )

    # 沒有預設值 → None 代表未選
    selected = st.radio(
        "請選出正確泰文句子：", options, index=None, key="ct_radio"
    )

    # ---------------- 送出答案 ----------------
    if st.button("✅ 送出答案（中→泰）"):
        if selected is None:
            st.warning("請先選一個選項喔！")
        else:
            st.session_state.ct_answered = True
            if selected == correct_th:
                st.success("✅ 正確！")
            else:
                st.error(f"❌ 錯喇～ 正確答案係：{correct_th}")

    # ---------------- 下一題 ----------------
    if st.button("👉 下一題（中→泰）"):
        if not st.session_state.ct_answered:
            st.warning("請先作答並送出，再下一題！")
        else:
            st.session_state.ct_index = rng.randrange(len(input_df))
            st.session_state.ct_options = None
            st.session_state.ct_correct = None
            st.session_state.ct_answered = False
            st.rerun()
            
# ---------- C. 選擇題（泰揀中） ----------
elif mode == "選擇題（泰揀中）":
    row = input_df.iloc[st.session_state.tc_index]
    st.subheader("🔤 泰文句子：")
    st.write(row["泰文"])

    correct_ch = row["中文句子"]

    # 固定選項
    options, correct_ch = get_or_create_options(
        "tc_options", "tc_correct",
        correct_ch, CH_POOL
    )

    # 無預設值 → None 代表未選
    selected = st.radio(
        "請選出正確中文意思：",
        options, index=None, key="tc_radio"
    )

    # ---------------- 送出答案 ----------------
    if st.button("✅ 送出答案（泰→中）"):
        if selected is None:
            st.warning("請先選一個選項喔！")
        else:
            st.session_state.tc_answered = True
            if selected == correct_ch:
                st.success("✅ 正確！")
            else:
                st.error(f"❌ 錯喇～ 正確答案係：{correct_ch}")

    # ---------------- 下一題 ----------------
    if st.button("👉 下一題（泰→中）"):
        if not st.session_state.tc_answered:
            st.warning("請先作答並送出，再下一題！")
        else:
            st.session_state.tc_index = rng.randrange(len(input_df))
            st.session_state.tc_options = None
            st.session_state.tc_correct = None
            st.session_state.tc_answered = False
            st.rerun()
            
