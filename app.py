import streamlit as st
import pandas as pd
import random
import difflib
import unicodedata
import re
from pathlib import Path

# --------------------------------------------------
# 0) Google Translate (optional)
# --------------------------------------------------
try:
    from googletrans import Translator  # pip install googletrans==4.0.0-rc1
    translator = Translator()
except Exception:
    translator = None  # 若安裝失敗仍可離線使用

# --------------------------------------------------
# 1) 讀題庫
# --------------------------------------------------
PARQUET_PATH = Path(__file__).parent / "thai_sentences.parquet"
CSV_PATH     = Path(__file__).parent / "thai_sentences.csv"

@st.cache_resource(show_spinner="📥  載入句子資料庫 …")
def load_data() -> pd.DataFrame:
    if PARQUET_PATH.exists():
        return pd.read_parquet(PARQUET_PATH)
    df = pd.read_csv(CSV_PATH)
    try:
        df.to_parquet(PARQUET_PATH, index=False)
    except Exception:
        pass
    return df

full_df = load_data()

# --------------------------------------------------
# 2) 必備欄位檢查 + 課文選擇
# --------------------------------------------------
REQ = ["中文句子", "泰文", "羅馬拼音", "課文"]
miss = [c for c in REQ if c not in full_df.columns]
if miss:
    st.error(f"CSV 缺少欄位：{miss}")
    st.stop()

lesson_list = sorted(full_df["課文"].dropna().unique())
selected_lesson = st.sidebar.selectbox("📖 選擇課文：", lesson_list)

input_df = full_df[full_df["課文"] == selected_lesson].reset_index(drop=True)
if input_df.empty:
    st.warning("該課文暫無句子，請選擇其他課文。")
    st.stop()

# --------------------------------------------------
# 3) 切課文時重置 state
# --------------------------------------------------
if st.session_state.get("lesson") != selected_lesson:
    st.session_state.lesson = selected_lesson
    rnd = random.Random()
    for k in ("input_index", "ct_index", "tc_index", "wd_index", "frag_index"):
        st.session_state[k] = rnd.randrange(len(input_df))
    st.session_state.update(
        answered=False, user_input="",
        ct_answered=False, tc_answered=False,
        wd_answered=False, frag_answered=False,
        ct_options=None, tc_options=None,
        wd_options=None, frag_options=None,
    )

# --------------------------------------------------
# 4) 共用工具
# --------------------------------------------------

def normalize(txt: str) -> str:
    txt = ''.join(c for c in str(txt) if not unicodedata.category(c).startswith('P'))
    return txt.replace(" ", "").lower()


def diff_mark(correct: str, user: str) -> str:
    seq = difflib.SequenceMatcher(None, correct, user)
    return "".join(
        correct[i1:i2] if tag == "equal" else f"**:red[{user[j1:j2]}]**"
        for tag, i1, i2, j1, j2 in seq.get_opcodes()
    )


rnd = random.Random()
POOL_SIZE = min(500, len(input_df))
TH_POOL   = rnd.sample(input_df["泰文"].tolist(), POOL_SIZE)
CH_POOL   = rnd.sample(input_df["中文句子"].tolist(), POOL_SIZE)


def get_or_create_options(opt_key, ans_key, correct, pool, k=3):
    if st.session_state[opt_key] is None:
        distract = rnd.sample([x for x in pool if x != correct], k)
        opts = distract + [correct]
        rnd.shuffle(opts)
        st.session_state[opt_key] = opts
        st.session_state[ans_key] = correct
    return st.session_state[opt_key], st.session_state[ans_key]


def pick_word(zh: str):
    tokens = re.split(r"[ ，,。？！\s]+", zh)
    tokens = [t for t in tokens if 1 <= len(t) <= 4]
    return rnd.choice(tokens) if tokens else zh


def pick_fragment(zh: str, min_len=2, max_len=4):
    frag = re.findall(r"[\u4e00-\u9fff]{%d,%d}" % (min_len, max_len), zh)
    return rnd.choice(frag) if frag else zh

# --------------------------------------------------
# 5) 預設 session_state
# --------------------------------------------------
for k, v in dict(
    mode="整句輸入",
    input_index=0, ct_index=0, tc_index=0, wd_index=0, frag_index=0,
    answered=False, user_input="",
    ct_options=None, tc_options=None, wd_options=None, frag_options=None,
    ct_answered=False, tc_answered=False, wd_answered=False, frag_answered=False,
).items():
    st.session_state.setdefault(k, v)

# --------------------------------------------------
# 6) UI：模式選擇
# --------------------------------------------------
STYLES = [
    "整句輸入",
    "選擇題（中揀泰）",
    "選擇題（泰揀中）",
    "單字輸入（中→泰）",
]

st.title("📘 泰文練習 App")
mode = st.radio("請選擇練習模式：", STYLES, index=STYLES.index(st.session_state.mode))

if mode != st.session_state.mode:
    st.session_state.mode = mode
    for flag in ("answered", "ct_answered", "tc_answered", "wd_answered", "frag_answered"):
        st.session_state[flag] = False
    for opt in ("ct_options", "tc_options", "wd_options", "frag_options"):
        st.session_state[opt] = None
    st.session_state.user_input = ""

# --------------------------------------------------
# 7) 各模式邏輯
# --------------------------------------------------

def show_google_check(thai_answer: str, zh_correct: str):
    """使用 Google 翻譯檢查泰文 → 中文是否相符"""
    if not translator:
        st.info("（本機未安裝 googletrans，略過線上檢查）")
        return
    try:
        g_zh = translator.translate(thai_answer, src='th', dest='zh-tw').text
        st.markdown(f"🌐 **Google 翻譯結果：** {g_zh}")
        if normalize(g_zh) == normalize(zh_correct):
            st.success("🌐 與正確中文意思相符！")
        else:
            st.warning("🌐 與標準答案不一致：" + diff_mark(zh_correct, g_zh))
    except Exception as e:
        st.info(f"（Google 翻譯失敗：{e}）")

### A) 整句輸入 --------------------------------------------------
if mode == "整句輸入":
    idx = st.session_state.input_index
    row = input_df.iloc[idx]
    st.subheader("🧠 中文句子：")
    st.write(row["中文句子"])

    with st.form("input_form"):
        method = st.radio("你想輸入：", ["泰文", "羅馬拼音"], key="met")
        ans_in = st.text_input("✍️ 請輸入答案：", key=f"ans_{idx}")
        ok = st.form_submit_button("✅ 送出")

    if ok and ans_in.strip():
        correct_raw = row["泰文"] if method == "泰文" else row["羅馬拼音"]
        if normalize(ans_in) == normalize(correct_raw):
            st.success("✅ 答對！")
        else:
            st.error("❌ 答錯～")
            st.write("正確答案：", correct_raw)
            st.markdown("**你的輸入：** " + diff_mark(correct_raw, ans_in))
        # --- Google Translate check (僅泰文輸入時) ---
        if method == "泰文":
            show_google_check(ans_in, row["中文句子"])
        st.session_state.answered = True

    if st.button("👉 下一題", key="next_full"):
        if not st.session_state.answered:
            st.warning("請先作答再下一題！")
        else:
            st.session_state.input_index = rnd.randrange(len(input_df))
            st.session_state.answered = False
            st.rerun()

### B) 選擇題（中→泰） ------------------------------------------
elif mode == "選擇題（中揀泰）":
    idx = st.session_state.ct_index
    row = input_df.iloc[idx]
    st.subheader("🧠 中文句子：")
    st.write(row["中文句子"])

    opts, correct = get_or_create_options("ct_options", "ct_correct", row["泰文"], TH_POOL)
    choose = st.radio("選出正確泰文：", opts, index=None)

    if st.button("✅ 送出", key="ct_submit"):
        if choose is None:
            st.warning("請選一個選項！")
        else:
            st.session_state.ct_answered = True
            if choose == correct:
                st.success("✅ 正確！")
            else:
                st.error("❌ 錯～")
                st.write(f"正確答案：{correct}")

    if st.button("👉 下一題", key="ct_next"):
        if not st.session_state.ct_answered:
            st.warning("請先作答！")
        else:
            st.session_state.update(ct_index=rnd.randrange(len(input_df)), ct_options=None, ct_answered=False)
            st.rerun()

### C) 選擇題（泰→中） ------------------------------------------
elif mode == "選擇題（泰揀中）":
    idx = st.session_state.tc_index
    row = input_df.iloc[idx]
    st.subheader("🔤 泰文句子：")
    st.write(row["泰文"])

    opts, correct = get_or_create_options("tc_options", "tc_correct", row["中文句子"], CH_POOL)
    choose = st.radio("選出中文意思：", opts, index=None)

    if st.button("✅ 送出", key="tc_submit"):
        if choose is None:
            st.warning("請選一個選項！")
        else:
            st.session_state.tc_answered = True
            if choose == correct:
                st.success("✅ 正確！")
            else:
                st.error("❌ 錯～")
                st.write(f"正確答案：{correct}")

    if st.button("👉 下一題", key="tc_next"):
        if not st.session_state.tc_answered:
            st.warning("請先作答！")
        else:
            st.session_state.update(tc_index=rnd.randrange(len(input_df)), tc_options=None, tc_answered=False)
            st.rerun()

### D) 單字輸入（中→泰） ---------------------------------------
elif mode == "單字輸入（中→泰）":
    idx = st.session_state.wd_index
    row = input_df.iloc[idx]
    zh_word = pick_word(row["中文句子"])
    st.subheader("中文生字：")
    st.write(zh_word)

    ans = st.text_input("✍️ 請輸入泰文：", key=f"wd_{idx}")
    if st.button("✅ 送出", key="wd_submit") and ans.strip():
        if normalize(ans) == normalize(row["泰文"]):
            st.success("✅ 正確！")
        else:
            st.error("❌ 答錯～")
            st.write("完整泰文句子：", row["泰文"])
        # Google translate assist
        show_google_check(ans, zh_word)
        st.session_state.wd_answered = True

    if st.button("👉 下一題", key="wd_next"):
        if not st.session_state.wd_answered:
            st.warning("請先作答！")
        else:
            st.session_state.update(wd_index=rnd.randrange(len(input_df)), wd_answered=False)
            st.rerun()

