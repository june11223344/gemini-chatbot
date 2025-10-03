import streamlit as st
import google.generativeai as genai

# 페이지 설정
st.set_page_config(page_title="신한카드 AI 어시스턴트", page_icon="💳")

# Secrets에서 API 키 가져오기
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("⚠️ API 키가 설정되지 않았습니다. Streamlit Cloud의 Secrets에 GEMINI_API_KEY를 추가해주세요.")
    st.stop()

# Gemini 2.5 Flash 설정
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# 시스템 프롬프트 (신한카드 데이터 기반)
SYSTEM_PROMPT = """
당신은 신한카드 고객을 위한 AI 어시스턴트입니다.

[신한카드 데이터 기반 정보]
- 신한카드는 국내 주요 신용카드사로, 다양한 카드 상품과 혜택을 제공합니다
- 주요 카드: Deep Dream, Deep On, Deep Oil, Mr. Life, Love 카드 등
- 제공 서비스: 포인트 적립, 할인 혜택, 무이자 할부, 캐시백 등
- 디지털 서비스: 신한 페이판, 모바일 앱, AI 챗봇

[응답 가이드라인]
1. 신한카드 데이터와 서비스에 기반하여 답변합니다
2. 고객의 금융 니즈를 이해하고 적절한 카드 상품을 추천합니다
3. 친절하고 전문적인 톤을 유지합니다
4. 정확한 정보를 제공하며, 불확실한 경우 명시합니다

고객의 질문에 신한카드 데이터를 활용하여 답변해주세요.
"""

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat" not in st.session_state:
    st.session_state.chat = model.start_chat(history=[])

# 타이틀
st.title("💳 신한카드 AI 어시스턴트")
st.caption("신한카드 데이터 기반 맞춤형 상담 서비스")

# 사이드바
with st.sidebar:
    st.header("📊 서비스 정보")
    st.info("신한카드 데이터를 활용한 AI 상담 서비스입니다.")
    
    st.markdown("### 주요 기능")
    st.markdown("""
    - 카드 상품 추천
    - 혜택 안내
    - 포인트 조회 안내
    - 서비스 문의 응대
    """)
    
    if st.button("대화 내역 초기화"):
        st.session_state.messages = []
        st.session_state.chat = model.start_chat(history=[])
        st.rerun()

# 이전 대화 내역 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 받기
if prompt := st.chat_input("신한카드 관련 질문을 입력하세요..."):
    # 사용자 메시지 추가 및 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Gemini API 호출
    try:
        # 시스템 프롬프트와 사용자 질문 결합
        full_prompt = f"{SYSTEM_PROMPT}\n\n고객 질문: {prompt}"
        
        # 응답 생성
        response = st.session_state.chat.send_message(full_prompt)
        answer = response.text
        
        # 봇 응답 추가 및 표시
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
            
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        st.info("API 모델명이나 할당량을 확인해주세요.")
