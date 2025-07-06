# app.py
import streamlit as st
import pandas as pd
import random
import difflib
import unicodedata          # ← 加入這行就解決 NameError
from pathlib import Path

# ---------- 讀檔 ----------
DATA_PATH = Path(__file__).parent / "thai_sentences.csv"

@st.cache_data
def load_data(path):
    return pd.read_csv(path)

input_df = load_data(DATA_PATH)

# ---------- 初始化 session ----------
defaults = {
    # 模式 + 各自題目 index
    "mode": "整句輸入",
    "input_index": random.randint(0, len(input_df) - 1),  # 中文→輸入
    "ct_index":    random.randint(0, len(input_df) - 1),  # 中文→泰 選擇題
    "tc_index":    random.randint(0, len(input_df) - 1),  # 泰→中 選擇題
    # 用戶狀態
    "answered": False,
    "user_input": "",
    # 選擇題（中→泰）暫存
    "ct_options": None,
    "ct_correct": None,
    # 選擇題（泰→中）暫存
    "tc_options": None,
    "tc_correct": None,
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

# ---------- 共用工具 ----------
def normalize(txt: str):
    """去標點、空格、大小寫，用作比對。"""
    txt = ''.join(c for c in txt if not unicodedata.category(c).startswith('P'))
    return txt.replace(" ", "").lower()

def diff_mark(correct: str, user: str):
    """把 user 打錯部分顯示成紅色粗體。"""
    seq = difflib.SequenceMatcher(None, correct, user)
    out = ""
    for tag, i1, i2, j1, j2 in seq.get_opcodes():
        out += correct[i1:i2] if tag == "equal" else f"**:red[{user[j1:j2]}]**"
    return out

def get_or_create_options(state_opts_key, state_ans_key,
                          correct, pool, k=3):
    """
    只在第一次／換題時生成 option，之後重跑沿用。
    - state_opts_key: e.g. 'ct_options'
    - state_ans_key : e.g. 'ct_correct'
    """
    if st.session_state[state_opts_key] is None:
        distractors = random.sample([x for x in pool if x != correct], k)
        opts = distractors + [correct]
        random.shuffle(opts)
        st.session_state[state_opts_key] = opts
        st.session_state[state_ans_key]  = correct
    return (st.session_state[state_opts_key],
            st.session_state[state_ans_key])

# ---------- 版面 ----------
st.title("📘 泰文練習 App")

modes = ["整句輸入", "選擇題（中揀泰）", "選擇題（泰揀中）"]
mode  = st.radio("請選擇練習模式：", modes,
                 index=modes.index(st.session_state.mode))

# 如模式改變，重置部份狀態
if mode != st.session_state.mode:
    st.session_state.answered = False
    st.session_state.user_input = ""
st.session_state.mode = mode

# ---------- A. 整句輸入 ----------
if mode == "整句輸入":
    row = input_df.iloc[st.session_state.input_index]

    st.subheader("🧠 中文句子：")
    st.write(row["中文句子"])

    # ---- 用 st.form 讓提交可重覆 ----
    with st.form("input_form"):
        input_method = st.radio("你想輸入：", ["泰文", "羅馬拼音"], key="method")
        user_input   = st.text_input(
            "✍️ 請輸入你的答案：",
            value=st.session_state.user_input,
            key="input"
        )
        submitted = st.form_submit_button("✅ 送出答案")

    # 僅在按提交時更新狀態
    if submitted and user_input.strip():
        st.session_state.answered     = True
        st.session_state.user_input   = user_input
        st.session_state.input_method = input_method   # 保存本次選擇

    # ---------- 批改 ----------
    if st.session_state.answered:
        # 取出剛才記錄的 input_method
        method = st.session_state.get("input_method", "泰文")
        correct_raw = row["泰文"] if method == "泰文" else row["羅馬拼音"]

        if normalize(st.session_state.user_input) == normalize(correct_raw):
            st.success("✅ 答對啦！")
        else:
            st.error("❌ 答錯了～")
            st.markdown("**正確答案：** " + correct_raw)
            st.markdown("**你輸入：** " +
                        diff_mark(correct_raw, st.session_state.user_input))

    # ---------- 下一題 ----------
    if st.button("👉 下一題"):
        st.session_state.input_index = random.randint(0, len(input_df) - 1)
        st.session_state.answered    = False
        st.session_state.user_input  = ""
        st.rerun()

# ---------- B. 選擇題（中揀泰） ----------
elif mode == "選擇題（中揀泰）":
    row = input_df.iloc[st.session_state.ct_index]
    st.subheader("🧠 中文句子：")
    st.write(row["中文句子"])

    correct_th = row["泰文"]

    # 固定選項
    options, correct_th = get_or_create_options(
        "ct_options", "ct_correct",
        correct_th,
        input_df["泰文"].tolist()
    )

    selected = st.radio("請選出正確泰文句子：",
                        options, key="ct_radio")

    if st.button("✅ 送出答案"):
        if selected == correct_th:
            st.toast("✅ 正確！")
        else:
            st.error(f"❌ 錯喇～ 正確答案係：{correct_th}")

    if st.button("👉 下一題（中→泰）"):
        st.session_state.ct_index   = random.randint(0, len(input_df) - 1)
        st.session_state.ct_options = None
        st.session_state.ct_correct = None
        st.rerun()

# ---------- C. 選擇題（泰揀中） ----------
else:
    row = input_df.iloc[st.session_state.tc_index]
    st.subheader("🔤 泰文句子：")
    st.write(row["泰文"])

    correct_ch = row["中文句子"]

    # 固定選項
    options, correct_ch = get_or_create_options(
        "tc_options", "tc_correct",
        correct_ch,
        input_df["中文句子"].tolist()
    )

    selected = st.radio("請選出正確中文意思：",
                        options, key="tc_radio")

    if st.button("✅ 送出答案"):
        if selected == correct_ch:
            st.toast("✅ 正確！")
        else:
            st.error(f"❌ 錯喇～ 正確答案係：{correct_ch}")

    if st.button("👉 下一題（泰→中）"):
        st.session_state.tc_index   = random.randint(0, len(input_df) - 1)
        st.session_state.tc_options = None
        st.session_state.tc_correct = None
        st.rerun()
