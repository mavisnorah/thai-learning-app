import streamlit as st
import pandas as pd
import random
import difflib

# 預設資料
input_data_path = "thai_sentences.csv"
mc_data_path = "thai_mc_questions_final.csv"

# 載入資料
input_df = pd.read_csv(input_data_path)
mc_df = pd.read_csv(mc_data_path)

# 初始化狀態
if "mode" not in st.session_state:
    st.session_state.mode = "整句輸入"
if "index" not in st.session_state:
    st.session_state.index = random.randint(0, len(input_df) - 1)
if "answered" not in st.session_state:
    st.session_state.answered = False
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# 主題
st.title("📘 泰文練習 App")
mode = st.radio("請選擇練習模式：", ["整句輸入", "選擇題"])
st.session_state.mode = mode

# 顯示題目
if st.session_state.mode == "整句輸入":
    row = input_df.iloc[st.session_state.index]
    st.subheader("🧠 中文句子：")
    st.write(row["中文句子"])
    input_method = st.radio("你想輸入：", ["泰文", "羅馬拼音"])
    user_input = st.text_input("✍️ 請輸入你的答案：", value=st.session_state.user_input, key="input")

    if st.button("✅ 送出答案"):
        if user_input.strip() != "":
            st.session_state.answered = True
            st.session_state.user_input = user_input.strip()

    if st.session_state.answered:
        correct = row["泰文_clean"] if input_method == "泰文" else row["羅馬拼音_clean"]
        user_ans = st.session_state.user_input.strip().lower()

        if user_ans == correct:
            st.success("✅ 答對啦！")
        else:
            def highlight_diff(correct, user_input):
                seq = difflib.SequenceMatcher(None, correct, user_input)
                result = ""
                for tag, i1, i2, j1, j2 in seq.get_opcodes():
                    if tag == 'equal':
                        result += correct[i1:i2]
                    else:
                        result += f"**:red[{correct[i1:i2]}]**"
                return result

            st.error("❌ 答錯了，正確答案如下：")
            st.markdown(highlight_diff(correct, user_ans))

    if st.button("👉 下一題"):
        st.session_state.index = random.randint(0, len(input_df) - 1)
        st.session_state.answered = False
        st.session_state.user_input = ""
        st.rerun()

else:
    row = mc_df.iloc[st.session_state.index]
    st.subheader("🧠 中文句子：")
    st.write(row["中文句子"])

    options = [row["選項1"], row["選項2"], row["選項3"], row["選項4"]]
    selected = st.radio("請選出正確的泰文句子：", options)

    if st.button("✅ 送出選擇題答案"):
        if selected == row["正確泰文句子"]:
            st.success("✅ 答對啦！")
        else:
            st.error(f"❌ 錯喇～ 正確答案係：{row['正確泰文句子']}")

    if st.button("👉 下一題（選擇題）"):
        st.session_state.index = random.randint(0, len(mc_df) - 1)
        st.rerun()
