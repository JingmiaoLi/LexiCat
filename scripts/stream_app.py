words = [
    {"word": "express", "cn": "表达", "pos": "v.", "sentence": "She can ______ her feelings.", "options": ["express", "eat", "draw", "open"]},
    {"word": "scared", "cn": "害怕的", "pos": "adj.", "sentence": "I felt ______ during the thunderstorm.", "options": ["scared", "happy", "strong", "excited"]},
    {"word": "poem", "cn": "诗", "pos": "n.", "sentence": "I wrote a short ______ about spring.", "options": ["poem", "story", "letter", "song"]},
]

import streamlit as st
import random

# 初始化
if "q" not in st.session_state:
    st.session_state.q = random.choice(words)

if "checked" not in st.session_state:
    st.session_state.checked = False

q = st.session_state.q

# 显示题目
st.write(q["sentence"])

choice = st.radio("选择答案：", q["options"])

# 检查答案
if st.button("check"):
    st.session_state.checked = True
    if choice == q["word"]:
        st.success("🐱 吃到猫粮啦！")
    else:
        st.error("🐱 没吃到，好难过…")

# ⭐ 核心：答完才显示学习信息
if st.session_state.checked:
    st.write(f"📘 {q['word']} ({q['pos']}) = {q['cn']}")

# 下一题
if st.button("next"):
    st.session_state.q = random.choice(words)
    st.session_state.checked = False