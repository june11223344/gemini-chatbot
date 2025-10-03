import streamlit as st
import google.generativeai as genai

# 페이지 설정
st.set_page_config(page_title="Gemini 챗봇", page_icon="🤖")

# 타이틀
st.title("💬 Gemini 챗봇")

# 사이드바에서 API 키 입력
with st.sidebar:
    st.header("설정")
    api_key = st.text_input("Gemini API Key", type="password")
    st.markdown("[API 키 발급받기](https://aistudio.google.com/app/apikey)")
    
    if st.button("대화 내역 초기화"):
        st.session_state.messages = []
        st.rerun()

# API 키가 입력되지 않은 경우
if not api_key:
    st.info("👈 사이드바에서 Gemini API 키를 입력해주세요.")
    st.stop()

# Gemini 설정
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 이전 대화 내역 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 받기
if prompt := st.chat_input("메시지를 입력하세요..."):
    # 사용자 메시지 추가 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Gemini API 호출
    try:
        # 대화 컨텍스트 구성
        chat = model.start_chat(history=[])
        
        # 이전 대화 내역을 컨텍스트로 전달
        for msg in st.session_state.messages[:-1]:
            if msg["role"] == "user":
                chat.send_message(msg["content"])
        
        # 현재 메시지에 대한 응답 생성
        response = chat.send_message(prompt)
        answer = response.text
        
        # 봇 응답 추가 및 표시
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
            
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        st.info("API 키가 올바른지 확인해주세요.")
