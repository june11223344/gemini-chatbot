import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import requests

st.set_page_config(
    page_title="상권 마케팅 처방 클리닉",
    page_icon="🏥",
    layout="wide"
)

# ==================== GitHub 문서 로더 ====================
@st.cache_data(ttl=3600)
def load_github_document(url):
    try:
        res = requests.get(url)
        res.raise_for_status()
        return res.text
    except Exception as e:
        return f"⚠️ 문서 로드 실패: {e}"

# ==================== HTML 문서 매핑 ====================
HTML_MAP = {
    1: "https://raw.githubusercontent.com/june11223344/gemini-chatbot/refs/heads/main/docs/q1_customer_targeting.html",
    2: "https://raw.githubusercontent.com/june11223344/gemini-chatbot/refs/heads/main/docs/%EC%83%81%EA%B6%8C%EB%B6%84%EC%84%9D%EA%B0%80%EC%9D%B4%EB%93%9C.html",
    3: "https://raw.githubusercontent.com/june11223344/gemini-chatbot/refs/heads/main/docs/q3_food_problem.html",
    4: "https://raw.githubusercontent.com/june11223344/gemini-chatbot/refs/heads/main/docs/q4_local_pattern.html",
    5: "https://raw.githubusercontent.com/june11223344/gemini-chatbot/refs/heads/main/docs/q5_time_trend.html"
}

# ==================== Session 초기화 ====================
if "step" not in st.session_state:
    st.session_state.step = "접수"
if "store_info" not in st.session_state:
    st.session_state.store_info = {}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "diagnosis_result" not in st.session_state:
    st.session_state.diagnosis_result = {}
if "selected_question" not in st.session_state:
    st.session_state.selected_question = None

# ==================== HTML 문서 불러오기 ====================
selected_q = st.session_state.selected_question or 2
reference_document = load_github_document(HTML_MAP.get(selected_q, HTML_MAP[2]))

# ==================== API Key ====================
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("⚠️ API 키를 설정해주세요.")
    api_key = None

MODEL_AVAILABLE = False
if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        MODEL_AVAILABLE = True
    except Exception as e:
        st.error(f"⚠️ 모델 초기화 오류: {e}")

# ==================== 상관 데이터 ====================
REVISIT_CORRELATION_DATA = {
    "피처 (Feature)": [
        "재방문 고객 비중",
        "동일 업종 매출건수 비중",
        "동일 상권 내 해지 가맹점 비중",
        "동일 업종 매출금액 비중",
        "동일 상권 내 매출 순위 비중",
        "동일 업종 내 해지 가맹점 비중",
        "동일 업종 내 매출 순위 비중"
    ],
    "상관계수": [1.0, 0.2, 0.024, -0.018, -0.14, -0.15, -0.17]
}

# ==================== SYSTEM PROMPT ====================
SYSTEM_PROMPT = f"""
당신은 신한카드 빅데이터 기반 상권 마케팅 전문 의사입니다.

아래 HTML 문서는 ‘질문 1~5’ 중 선택된 질문에 대한 신한카드 상권 분석 데이터입니다.  
각 HTML 문서의 표와 문단 안에 포함된 모든 수치(%, 상관계수, 매장수, 고객비중 등)는 실제 통계입니다.  

HTML은 단순한 설명이 아니라 **데이터 테이블**로 간주해야 하며,  
응답 시 반드시 이 데이터를 근거로 “진단 → 처방”을 작성해야 합니다.  

---

## 🧠 공통 응답 원칙

1. **데이터 인용**
   - HTML 안의 숫자(%, 상관계수, 매장수 등)를 그대로 복사해 문장에 포함하세요.
   - 예시: “유동형(70개, 38.5%)”, “재방문–거주 상관계수 +0.24”
   - 모든 판단에는 괄호로 근거를 표기합니다.  
     예시: (근거: 재방문–거주 상관계수 +0.24)

2. **응답 구조**
   - [진단]: 3~4줄 요약 — 상권 유형, 고객 구조, 주요 수치 포함  
   - [처방]: 1~2문단 구체적 개선전략 — 수치 및 상관계수 기반

3. **금지사항**
   - HTML에 없는 수치나 관계를 새로 추정하거나 만들지 마세요.  
   - “아마도”, “추정컨대” 등의 표현은 금지합니다.

4. **톤 & 스타일**
   - 의료 진단처럼 명료하고 분석적인 어조를 유지하세요.  
   - 불필요한 미사여구 없이 수치 중심으로 설명합니다.

---

## 📄 참고 데이터
{reference_document if reference_document else "⚠️ 참고 문서 로드 실패"}
"""

# ==================== 헤더 ====================
st.markdown("""
    <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); border-radius: 15px; margin-bottom: 2rem;'>
        <div style='font-size: 3rem;'>🏥</div>
        <h1 style='color: white;'>상권 마케팅 처방 클리닉</h1>
        <p style='color: #E8F5E9;'>💊 신한카드 빅데이터 기반 맞춤 처방</p>
    </div>
""", unsafe_allow_html=True)

# ==================== 사이드바 ====================
with st.sidebar:
    st.markdown("""
        <div style='background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); padding: 1.2rem; border-radius: 10px; color: white; text-align: center;'>
            <h3>🏥 클리닉 진료실</h3>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📚 참고 자료")
    with st.expander("📄 상권 분석 HTML 보기"):
        if reference_document:
            st.markdown(reference_document, unsafe_allow_html=True)
            st.success("✅ HTML 문서 로드 완료")
        else:
            st.error("❌ 문서를 불러올 수 없습니다.")
    st.markdown("---")

    # 질문 선택 버튼
    st.markdown("### 📋 사전 질문 선택")
    q1 = st.button("❓ 질문 1: 카페 고객 타겟팅", use_container_width=True)
    q2 = st.button("❓ 질문 2: 재방문율 개선", use_container_width=True)
    q3 = st.button("❓ 질문 3: 요식업 문제 해결", use_container_width=True)
    q4 = st.button("❓ 질문 4: 지역 상권 패턴", use_container_width=True)
    q5 = st.button("❓ 질문 5: 시계열 트렌드 분석", use_container_width=True)

    # 질문 선택 시 상태 업데이트
    if q1: st.session_state.selected_question = 1
    if q2: st.session_state.selected_question = 2
    if q3: st.session_state.selected_question = 3
    if q4: st.session_state.selected_question = 4
    if q5: st.session_state.selected_question = 5
    if any([q1, q2, q3, q4, q5]): st.rerun()

# ==================== 단계별 진행 ====================
# 단계: 접수
if st.session_state.step == "접수":
    st.header("📋 접수 데스크")

    st.info("질문을 선택하면 자동으로 관련 데이터가 로드됩니다.")

    # 기본 버튼
    if st.button("🏥 진료 시작하기", type="primary", use_container_width=True):
        if not MODEL_AVAILABLE:
            st.error("⚠️ API 키 미설정")
        else:
            with st.spinner("🔬 초기 검사 중..."):
                initial_prompt = f"""
                {SYSTEM_PROMPT}

                선택된 질문 유형: {st.session_state.selected_question}

                [진단]: 3~4줄 요약으로 상권 유형, 고객 구조, 핵심 수치 포함  
                [처방]: 수치와 상관계수 기반 구체 전략 작성
                """
                try:
                    response = model.generate_content(
                        f"{initial_prompt}\n\n⚠️ HTML 내 수치(%, 상관계수, 매장수 등)는 반드시 그대로 인용해야 합니다.",
                        generation_config=genai.types.GenerationConfig(temperature=0.2)
                    )
                    st.session_state.diagnosis_result["initial"] = response.text
                    st.session_state.step = "진료"
                    st.rerun()
                except Exception as e:
                    st.error(f"진단 오류: {str(e)}")

# 단계: 진료
elif st.session_state.step == "진료":
    st.header("🩺 진료실")

    st.markdown("### 🔬 초기 검사 결과")
    st.markdown(st.session_state.diagnosis_result.get("initial", "진단 중..."))
    st.markdown("---")

    st.markdown("### 💬 전문의 상담")
    if len(st.session_state.messages) == 0:
        st.session_state.messages.append({"role": "assistant", "content": "안녕하세요! 추가로 알고 싶은 내용을 물어보세요."})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("전문의에게 질문하기..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        if MODEL_AVAILABLE:
            context = f"{SYSTEM_PROMPT}\n\n사용자 질문: {prompt}"
            context += "\n\n⚠️ 반드시 HTML 내 수치(%, 상관계수 등)를 그대로 인용할 것."
            try:
                response = model.generate_content(
                    context,
                    generation_config=genai.types.GenerationConfig(temperature=0.3)
                )
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"⚠️ 상담 오류: {str(e)}")
        else:
            st.error("⚠️ API 키 미설정")

    if st.button("📋 처방전 발급", type="primary", use_container_width=True):
        if MODEL_AVAILABLE:
            with st.spinner("📝 처방전 작성 중..."):
                try:
                    prescription_prompt = f"""
                    {SYSTEM_PROMPT}

                    [처방전 작성 규칙]
                    - HTML 내 수치를 그대로 복사
                    - 모든 근거에 상관계수/비율 명시
                    - “진단 → 처방” 구조 유지
                    """
                    prescription = model.generate_content(
                        f"{prescription_prompt}\n\n⚠️ HTML 수치를 반드시 그대로 사용하세요.",
                        generation_config=genai.types.GenerationConfig(temperature=0.2)
                    )
                    st.session_state.diagnosis_result["prescription"] = prescription.text
                    st.session_state.step = "처방전"
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ 처방전 오류: {str(e)}")
        else:
            st.error("⚠️ API 키 미설정")

# 단계: 처방전
elif st.session_state.step == "처방전":
    st.header("💊 처방전")
    st.markdown(st.session_state.diagnosis_result.get("prescription", "생성 중..."))

    if st.button("🔄 새로 시작", use_container_width=True):
        for key in ["step", "store_info", "messages", "diagnosis_result", "selected_question"]:
            st.session_state.pop(key, None)
        st.rerun()
