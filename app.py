import streamlit as st
import google.generativeai as genai

# 페이지 설정
st.set_page_config(page_title="Gemini 챗봇", page_icon="🤖")

# Secrets에서 API 키 가져오기
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("⚠️ API 키가 설정되지 않았습니다. Streamlit Cloud의 Secrets에 GEMINI_API_KEY를 추가해주세요.")
    st.stop()

# Gemini 설정
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 타이틀
st.title("💬 Gemini 챗봇")

# 사이드바 (대화 초기화 버튼만)
with st.sidebar:
    st.header("옵션")
    if st.button("대화 내역 초기화"):
        st.session_state.messages = []
        st.rerun()

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
