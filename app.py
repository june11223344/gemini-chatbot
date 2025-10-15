import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import requests
import re

# ==================== 기본 셋업 ====================
st.set_page_config(
    page_title="상권 마케팅 처방 클리닉",
    page_icon="🏥",
    layout="wide"
)

# ==================== 문서 로더/전처리 ====================
@st.cache_data(ttl=3600)
def load_github_document(url: str):
    """GitHub Raw URL에서 HTML 문서 로드"""
    if not url:
        return None
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        resp.encoding = "utf-8"
        return resp.text
    except Exception as e:
        st.error(f"⚠️ 문서 로드 실패: {e}")
        return None

def clip_html(html: str, max_chars: int = 12000) -> str:
    """LLM 컨텍스트 폭주 방지를 위한 HTML 길이 제한 (태그는 그대로 둠)"""
    if not html:
        return ""
    if len(html) <= max_chars:
        return html
    head = html[:max_chars]
    # 열려있는 태그가 비정상적으로 끊겨도 LLM용이므로 크게 문제 없음
    return head + "\n<!-- clipped -->"

# 질문별 레퍼런스 URL 매핑 (지금은 Q2만 실제 문서 존재)
DOC_URLS = {
    1: None,  # 카페 고객 타겟팅 (추가되면 URL로 교체)
    2: "https://raw.githubusercontent.com/june11223344/gemini-chatbot/refs/heads/main/docs/%EC%83%81%EA%B6%8C%EB%B6%84%EC%84%9D%EA%B0%80%EC%9D%B4%EB%93%9C.html",
    3: None,  # 요식업 문제 해결
    4: None,  # 좋은 상권인데 매출이 적은 이유
    5: None,  # 시간(계절) 민감형 문제/전략
}

# ==================== API Key ====================
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = None
    st.error("⚠️ API 키를 설정해주세요.")

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        MODEL_AVAILABLE = True
    except Exception as e:
        st.error(f"⚠️ 모델 초기화 오류: {e}")
        MODEL_AVAILABLE = False
else:
    MODEL_AVAILABLE = False

# ==================== 세션 상태 ====================
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
if "reference_document" not in st.session_state:
    st.session_state.reference_document = None

# ==================== 통계 데이터(예: 질문2에서 테이블 노출) ====================
REVISIT_CORRELATION_DATA = {
    "피처 (Feature)": [
        "재방문 고객 비중",
        "동일 업종 매출건수 비중",
        "동일 상권 내 해지 가맹점 비중",
        "동일 업종 매출금액 비중",
        "동일 상권 내 매출 순위 비중",
        "동일 업종 내 해지 가맹점 비중",
        "동일 업종 내 매출 순위 비중",
    ],
    "상관계수": [1.0, 0.2, 0.024, -0.018, -0.14, -0.15, -0.17],
}

# ==================== SYSTEM PROMPT 빌더 ====================
def build_system_prompt(qid: int, reference_html: str) -> str:
    """
    질문(1~5)에 맞는 역할/인용 규칙을 포함한 시스템 프롬프트 구성
    - 기존 구조/톤/원칙은 유지
    - HTML 인용을 더 강하게 유도
    """
    qid_name = {
        1: "카페 고객 타겟팅",
        2: "재방문율 개선",
        3: "요식업 문제 해결",
        4: "동일 상권 대비 매출 저조 원인",
        5: "시간/계절 민감형 고민과 전략",
    }.get(qid, "일반")

    reference_block = clip_html(reference_html or "", max_chars=12000)
    reference_block = reference_block if reference_block else "참고 문서 없음"

    # 인용 규칙: 문장 끝에 [ref:q{qid}] 혹은 [ref:q{qid} §섹션] 형태로 추가하도록 지시
    system_prompt = f"""
당신은 신한카드 빅데이터 기반 상권 마케팅 전문 **컨설턴트**입니다.
현재 질의 유형: **질문 {qid}. {qid_name}**

# 핵심 지침
- **의료 컨셉** 톤으로 **진단 → 처방** 형식 유지.
- **초기 진단은 3~4줄 요약**으로 시작.
- **모든 수치**(상관계수, 비율, 매장수 등)를 **가능한 범위에서 구체적으로** 제시.
- 아래 '참고 자료(HTML)'의 내용을 **가능한 한 직접 인용/요약**하여 답변에 반영.
- 문장 끝에 가능한 한 **인용 마커**를 붙이세요: `[ref:q{qid}]` 또는 `[ref:q{qid} §섹션명]`
- 참고 자료에 수치/표가 없는 경우에는 **'수치 미제공'**이라고 명시하고 추론/전문가견과 구분.

# 참고 자료(HTML)
{reference_block}

# 출력 형식 원칙
1) **3~4줄 진단 요약** → 2) **근거(데이터/상관계수 명시)** → 3) **처방(즉시 실행 1~3가지)** → 4) **추가 권고/주의**
2) 가능한 한 **[ref:q{qid}]** 인용 마커를 문장 끝에 붙임.
3) 표/리스트/불릿 사용 허용.
"""
    return system_prompt

# ==================== 헤더 ====================
st.markdown(
    """
    <div style='text-align: center; padding: 2.5rem; background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <div style='font-size: 3rem; margin-bottom: 0.5rem;'>🏥</div>
        <h1 style='color: white; margin: 0; font-size: 2.2rem;'>상권 마케팅 처방 클리닉</h1>
        <p style='color: #E8F5E9; margin-top: 0.8rem; font-size: 1.1rem;'>💊 신한카드 빅데이터 기반 맞춤 처방</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==================== 사이드바 ====================
with st.sidebar:
    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); padding: 1.5rem; border-radius: 10px; color: white; margin-bottom: 1.5rem; text-align: center;'>
            <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🏥</div>
            <h3 style='margin: 0;'>클리닉 진료실</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 질문 사전 선택
    st.markdown("### 📋 사전 질문 선택")
    st.caption("질문을 클릭하면 자동으로 정보가 입력됩니다")

    c1, c2 = st.columns(2)
    with c1:
        q1 = st.button("❓ 질문 1", key="btn_q1", use_container_width=True)
        q2 = st.button("❓ 질문 2", key="btn_q2", use_container_width=True)
        q3 = st.button("❓ 질문 3", key="btn_q3", use_container_width=True)
    with c2:
        q4 = st.button("❓ 질문 4", key="btn_q4", use_container_width=True)
        q5 = st.button("❓ 질문 5", key="btn_q5", use_container_width=True)

    # 질문 선택 처리(원본 로직 유지 + Q4/Q5 확장)
    if q1:
        st.session_state.selected_question = 1
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "카페",
            "location_detail": "역세권/대로변 (유동인구 많음)",
            "customer_type": "신규 고객 많음",
            "concern": "주요 고객 특성에 맞는 마케팅 채널과 홍보 방법을 알고 싶어요",
        }
        st.session_state.reference_document = load_github_document(DOC_URLS.get(1))
        st.rerun()
    if q2:
        st.session_state.selected_question = 2
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "카페",
            "location_detail": "주택가/골목 (거주민 중심)",
            "customer_type": "단골 손님 적음",
            "concern": "재방문율이 30% 이하인데 어떻게 높일 수 있을까요?",
        }
        st.session_state.reference_document = load_github_document(DOC_URLS.get(2))
        st.rerun()
    if q3:
        st.session_state.selected_question = 3
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "한식-일반",
            "location_detail": "오피스/업무지구 (직장인 중심)",
            "customer_type": "신규 고객 많음",
            "concern": "요식업 매장의 가장 큰 문제점이 무엇인지 알고 이를 개선하고 싶어요",
        }
        st.session_state.reference_document = load_github_document(DOC_URLS.get(3))
        st.rerun()
    if q4:
        st.session_state.selected_question = 4
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "한식-육류/고기",
            "location_detail": "역세권/대로변 (유동인구 많음)",
            "customer_type": "신규 고객 많음",
            "concern": "같은 상권/동일업종 대비 매출이 낮은 원인이 뭔지 알고 싶어요",
        }
        st.session_state.reference_document = load_github_document(DOC_URLS.get(4))
        st.rerun()
    if q5:
        st.session_state.selected_question = 5
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "카페",
            "location_detail": "역세권/대로변 (유동인구 많음)",
            "customer_type": "단골/신규 비슷",
            "concern": "계절(겨울)에 매출이 급감하는 원인과 대응 방안을 알고 싶어요",
        }
        st.session_state.reference_document = load_github_document(DOC_URLS.get(5))
        st.rerun()

    st.markdown("---")

    # 참고 문서 표시 (선택된 질문에 맞춰)
    st.markdown("### 📚 참고 자료")
    with st.expander("📄 질문별 가이드(HTML)", expanded=False):
        if st.session_state.reference_document:
            st.markdown(st.session_state.reference_document, unsafe_allow_html=True)
            st.success("✅ 문서 로드 완료")
        else:
            st.info("ℹ️ 해당 질문의 전용 HTML 문서가 아직 없습니다. (추가 예정)")

    st.markdown("---")

    # 재방문율 데이터 표시 (질문 2일 때만)
    if st.session_state.selected_question == 2:
        st.markdown("### 📊 재방문율 상관 데이터")
        df = pd.DataFrame(REVISIT_CORRELATION_DATA)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("※ 신한카드 빅데이터 분석 결과")

    st.markdown("---")

    if st.session_state.step != "접수":
        if st.button("🏠 처음으로", use_container_width=True, type="primary"):
            st.session_state.step = "접수"
            st.session_state.store_info = {}
            st.session_state.messages = []
            st.session_state.diagnosis_result = {}
            st.session_state.selected_question = None
            st.session_state.reference_document = None
            st.rerun()

# ==================== 1단계: 접수 ====================
if st.session_state.step == "접수":
    st.header("📋 접수 데스크")

    question_titles = {
        1: "질문 1: 카페 고객 타겟팅",
        2: "질문 2: 재방문율 개선",
        3: "질문 3: 요식업 문제 해결",
        4: "질문 4: 동일 상권 대비 매출 저조 원인",
        5: "질문 5: 시간(계절) 민감형 문제/전략",
    }

    initial_store_info = st.session_state.store_info

    if st.session_state.selected_question:
        st.info(f"✅ 선택: {question_titles[st.session_state.selected_question]} (정보 확인 후 '진료 접수하기')")

    st.subheader("가맹점 기본 정보")

    col1, col2 = st.columns(2)
    with col1:
        store_name = st.text_input("🏪 가맹점명", placeholder="예: 달구 성수점", value=initial_store_info.get("store_name", ""))

        region_options = ["선택하세요", "서울 성동구", "서울 강남구", "서울 강서구", "서울 마포구", "서울 종로구", "부산", "대구", "기타"]
        region_choice = st.selectbox(
            "🗺️ 지역",
            region_options,
            index=region_options.index(initial_store_info.get("region", "선택하세요")) if initial_store_info.get("region") in region_options else 0,
        )

        location_options = ["선택하세요", "성수동1가", "성수동2가", "서울숲길", "왕십리", "행당동", "금호동", "옥수동", "마장동", "응봉동"]
        if region_choice == "서울 성동구":
            location = st.selectbox(
                "📍 상세 위치",
                location_options,
                index=location_options.index(initial_store_info.get("location", "선택하세요")) if initial_store_info.get("location") in location_options else 0,
            )
        elif region_choice and region_choice != "선택하세요":
            location = st.text_input("📍 상세 위치", placeholder="예: 역삼동", value=initial_store_info.get("location", ""))
        else:
            location = "선택하세요"

        business_type_options = ["선택하세요", "카페", "한식-육류/고기", "한식-일반", "일식", "중식", "양식", "치킨", "분식", "베이커리", "기타"]
        business_type = st.selectbox(
            "🍽️ 업종",
            business_type_options,
            index=business_type_options.index(initial_store_info.get("business_type", "선택하세요")) if initial_store_info.get("business_type") in business_type_options else 0,
        )

    with col2:
        location_detail_options = ["역세권/대로변 (유동인구 많음)", "주택가/골목 (거주민 중심)", "오피스/업무지구 (직장인 중심)"]
        location_detail = st.radio(
            "🏢 상권 특성",
            location_detail_options,
            index=location_detail_options.index(initial_store_info.get("location_detail", location_detail_options[0])) if initial_store_info.get("location_detail") in location_detail_options else 0,
        )

        customer_type_options = ["단골 손님 많음", "신규 고객 많음", "단골/신규 비슷", "잘 모르겠음"]
        customer_type = st.radio(
            "👥 손님 특성",
            customer_type_options,
            index=customer_type_options.index(initial_store_info.get("customer_type", customer_type_options[0])) if initial_store_info.get("customer_type") in customer_type_options else 0,
        )

    # 고객 성별/연령 비중
    st.markdown("### 👩👨 주요 고객 성별/연령 (상위 2개 선택)")
    st.caption("주로 방문하는 고객층 2개를 선택해주세요 (선택사항)")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**여성 고객**")
        female_20 = st.checkbox("여성 20대 이하", value=initial_store_info.get("female_20", False))
        female_30 = st.checkbox("여성 30대", value=initial_store_info.get("female_30", False))
        female_40 = st.checkbox("여성 40대", value=initial_store_info.get("female_40", False))
        female_50 = st.checkbox("여성 50대", value=initial_store_info.get("female_50", False))
        female_60 = st.checkbox("여성 60대 이상", value=initial_store_info.get("female_60", False))
    with col2:
        st.markdown("**남성 고객**")
        male_20 = st.checkbox("남성 20대 이하", value=initial_store_info.get("male_20", False))
        male_30 = st.checkbox("남성 30대", value=initial_store_info.get("male_30", False))
        male_40 = st.checkbox("남성 40대", value=initial_store_info.get("male_40", False))
        male_50 = st.checkbox("남성 50대", value=initial_store_info.get("male_50", False))
        male_60 = st.checkbox("남성 60대 이상", value=initial_store_info.get("male_60", False))

    concern = st.text_area(
        "😰 현재 고민",
        placeholder="예: 손님은 많은데 단골이 안 생겨요 / 재방문율이 낮아요",
        height=100,
        value=initial_store_info.get("concern", ""),
    )

    if st.button("🏥 진료 접수하기", type="primary", use_container_width=True):
        # 선택된 고객층 요약
        selected_customers = []
        if female_20:
            selected_customers.append("여성 20대 이하")
        if female_30:
            selected_customers.append("여성 30대")
        if female_40:
            selected_customers.append("여성 40대")
        if female_50:
            selected_customers.append("여성 50대")
        if female_60:
            selected_customers.append("여성 60대 이상")
        if male_20:
            selected_customers.append("남성 20대 이하")
        if male_30:
            selected_customers.append("남성 30대")
        if male_40:
            selected_customers.append("남성 40대")
        if male_50:
            selected_customers.append("남성 50대")
        if male_60:
            selected_customers.append("남성 60대 이상")

        customer_demographics = ", ".join(selected_customers) if selected_customers else "미선택"

        if (
            store_name
            and location
            and location != "선택하세요"
            and business_type != "선택하세요"
            and region_choice != "선택하세요"
            and concern
        ):
            st.session_state.store_info = {
                "store_name": store_name,
                "region": region_choice,
                "location": location,
                "location_detail": location_detail,
                "business_type": business_type,
                "customer_type": customer_type,
                "customer_demographics": customer_demographics,
                "concern": concern,
                "date": datetime.now().strftime("%Y년 %m월 %d일"),
                "question_type": st.session_state.selected_question,
                # 체크박스 저장
                "male_20": male_20,
                "male_30": male_30,
                "male_40": male_40,
                "male_50": male_50,
                "male_60": male_60,
                "female_20": female_20,
                "female_30": female_30,
                "female_40": female_40,
                "female_50": female_50,
                "female_60": female_60,
            }

            if not MODEL_AVAILABLE:
                st.error("⚠️ API 키 미설정")
            else:
                with st.spinner("🔬 초기 검사 중..."):
                    qid = st.session_state.selected_question or 1
                    # 질문별 컨텍스트 태그
                    qctx = {
                        1: "\n\n[중요] 카페 고객 특성 및 마케팅 채널 추천에 집중",
                        2: "\n\n[중요] 재방문율 개선 전략에 집중",
                        3: "\n\n[중요] 요식업 문제 분석에 집중",
                        4: "\n\n[중요] 동일 상권 대비 매출 저조 원인 분석에 집중",
                        5: "\n\n[중요] 시간(계절) 민감형 문제와 대응 전략에 집중",
                    }.get(qid, "")

                    system_prompt = build_system_prompt(qid, st.session_state.reference_document)

                    initial_prompt = f"""
{system_prompt}
{qctx}

가맹점:
- 이름: {store_name}
- 지역: {region_choice} - {location} ({location_detail})
- 업종: {business_type}
- 손님 특성: {customer_type}
- 주요 고객층: {customer_demographics}
- 고민: {concern}

다음 형식으로 **3-4줄 요약** 진단:

## 🔬 초기 검사 결과

**📍 상권 유형:** [유동형/거주형/직장형] (근거: 신한카드 XX개 매장, 고객 구성 유동XX%/거주XX%) [ref:q{qid}]

**👥 고객 분석:** 주 고객층 [{customer_demographics}] 관련 신한카드 데이터 특징(매출건수/재방문 상관) 요약 [ref:q{qid}]

**⚠️ 핵심 문제:** {concern} → [핵심 원인 + 상관계수/비율 근거 1가지] [ref:q{qid}]

**💊 우선 처방:** [즉시 실행 1개, 간단명료] [ref:q{qid}]
"""

                    try:
                        response = model.generate_content(initial_prompt)
                        st.session_state.diagnosis_result["initial"] = response.text
                        st.session_state.step = "진료"
                        st.rerun()
                    except Exception as e:
                        st.error(f"진단 오류: {str(e)}")
        else:
            st.error("⚠️ 필수 항목을 입력해주세요!")

# ==================== 2단계: 진료 ====================
elif st.session_state.step == "진료":
    question_titles = {
        1: "질문 1: 카페 고객 타겟팅",
        2: "질문 2: 재방문율 개선",
        3: "질문 3: 요식업 문제 해결",
        4: "질문 4: 동일 상권 대비 매출 저조 원인",
        5: "질문 5: 시간(계절) 민감형 문제/전략",
    }

    st.markdown(
        f"""
        <div style='background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); padding: 1.5rem; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 1.5rem;'>
            <h2 style='margin: 0; color: #1B5E20;'>🩺 진료실</h2>
            <p style='margin: 0.5rem 0 0 0; color: #2E7D32;'><strong>{st.session_state.store_info.get('store_name', '')}</strong> | {question_titles.get(st.session_state.store_info.get('question_type'), '일반 진료')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 환자 차트
    with st.expander("📄 환자 차트", expanded=False):
        info = st.session_state.store_info
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"""
            **가맹점:** {info.get('store_name', 'N/A')}  
            **업종:** {info.get('business_type', 'N/A')}  
            **위치:** {info.get('region', 'N/A')} - {info.get('location', 'N/A')}  
            **상권:** {info.get('location_detail', 'N/A')}
            """
            )
        with col2:
            st.markdown(
                f"""
            **손님 특성:** {info.get('customer_type', 'N/A')}  
            **주요 고객:** {info.get('customer_demographics', 'N/A')}  
            **접수일:** {info.get('date', 'N/A')}  
            **고민:** {info.get('concern', 'N/A')}
            """
            )

    # 재방문율 데이터 표시 (질문 2일 때)
    if st.session_state.store_info.get("question_type") == 2:
        st.markdown("### 📊 재방문율 상관 데이터")
        df = pd.DataFrame(REVISIT_CORRELATION_DATA)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption("※ 신한카드 빅데이터 - 재방문 고객 비중과의 상관계수")
        st.markdown("---")

    st.markdown("### 🔬 초기 검사 결과")
    with st.container(border=True):
        st.markdown(st.session_state.diagnosis_result.get("initial", "진단 중..."))

    st.markdown("---")
    st.markdown("### 💬 전문의 상담")

    if len(st.session_state.messages) == 0:
        initial_msg = f"""안녕하세요, **{st.session_state.store_info.get('store_name', '')}** 점주님!

초기 진단을 완료했습니다. 추가 질문이나 더 알고 싶은 전략을 물어보세요."""
        st.session_state.messages.append({"role": "assistant", "content": initial_msg})

    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🏥" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])

    if prompt := st.chat_input("💬 전문의에게 질문하기..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        if not MODEL_AVAILABLE:
            st.error("⚠️ API 키 미설정")
        else:
            try:
                qid = st.session_state.store_info.get("question_type") or 1
                system_prompt = build_system_prompt(qid, st.session_state.reference_document)

                context = f"""
{system_prompt}

가맹점 정보:
- 이름: {st.session_state.store_info.get('store_name', '')}
- 업종: {st.session_state.store_info.get('business_type', '')}
- 위치: {st.session_state.store_info.get('region', '')} - {st.session_state.store_info.get('location', '')}
- 상권: {st.session_state.store_info.get('location_detail', '')}
- 손님 특성: {st.session_state.store_info.get('customer_type', '')}
- 주요 고객: {st.session_state.store_info.get('customer_demographics', '')}
- 고민: {st.session_state.store_info.get('concern', '')}

초기 진단:
{st.session_state.diagnosis_result.get('initial', '')}

점주 질문: {prompt}

답변은 신한카드 데이터/참고 HTML의 구체적 수치를 우선 인용하고, 문장 끝에 [ref:q{qid}] 마커를 붙이세요.
"""
                response = model.generate_content(context)
                answer = response.text

                st.session_state.messages.append({"role": "assistant", "content": answer})
                with st.chat_message("assistant", avatar="🏥"):
                    st.markdown(answer)
            except Exception as e:
                st.error(f"⚠️ 상담 오류: {str(e)}")

    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("💊 충분한 상담 후 처방전을 발급받으세요!")
    with col2:
        if st.button("📋 처방전 발급", type="primary", use_container_width=True):
            if not MODEL_AVAILABLE:
                st.error("⚠️ API 키 미설정")
            else:
                with st.spinner("📝 처방전 작성 중..."):
                    try:
                        qid = st.session_state.store_info.get("question_type") or 1
                        system_prompt = build_system_prompt(qid, st.session_state.reference_document)

                        prescription_prompt = f"""
{system_prompt}

가맹점 최종 처방전:

- 이름: {st.session_state.store_info.get('store_name', '')}
- 업종: {st.session_state.store_info.get('business_type', '')}
- 위치: {st.session_state.store_info.get('region', '')} - {st.session_state.store_info.get('location', '')}
- 상권: {st.session_state.store_info.get('location_detail', '')}
- 손님: {st.session_state.store_info.get('customer_type', '')}
- 주요 고객: {st.session_state.store_info.get('customer_demographics', '')}
- 고민: {st.session_state.store_info.get('concern', '')}

초기 진단:
{st.session_state.diagnosis_result.get('initial', '')}

상담 기록(최근 10개 요약):
{chr(10).join([f"- {msg['content'][:150]}..." for msg in st.session_state.messages[-10:]])}

다음 형식의 처방전으로 작성:

# 💊 마케팅 처방전

## 📋 환자 정보
- 환자명: {st.session_state.store_info.get('store_name', '')}
- 업종: {st.session_state.store_info.get('business_type', '')}
- 위치: {st.session_state.store_info.get('region', '')} - {st.session_state.store_info.get('location', '')}
- 발급일: {st.session_state.store_info.get('date', '')}

## 🔬 종합 진단
[상권 유형 + 고객 구조 + 핵심 문제 3가지 (신한카드 데이터 근거)] [ref:q{qid}]

## 💊 처방 내역

### 우선순위 1위
**처방명:** [구체적 전략]
**목표:** [수치 목표]
**근거:** 신한카드 데이터/HTML [상관계수, 비율 등] [ref:q{qid}]
**실행:**
1. [실행 1]
2. [실행 2]
3. [실행 3]
**예상 효과:** [구체적 수치/범위]

### 우선순위 2위
(동일 형식)

## ⚠️ 주의사항
[주의점 3가지 + 데이터 근거] [ref:q{qid}]

**발급일:** {datetime.now().strftime('%Y년 %m월 %d일')}
"""
                        prescription = model.generate_content(prescription_prompt)
                        st.session_state.diagnosis_result["prescription"] = prescription.text
                        st.session_state.step = "처방전"
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ 처방전 오류: {str(e)}")

# ==================== 3단계: 처방전 ====================
elif st.session_state.step == "처방전":
    st.markdown(
        f"""
        <div style='text-align: center; padding: 1.5rem; background: #E8F5E9; border-radius: 10px; margin-bottom: 2rem;'>
            <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>🏥</div>
            <h2 style='margin: 0; color: #1B5E20;'>상권 마케팅 처방 클리닉</h2>
            <p style='margin: 0.3rem 0; color: #2E7D32;'>Marketing Strategy Prescription Clinic</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    info = st.session_state.store_info
    st.markdown("### 📋 환자 차트")
    st.info(
        f"""
    - **환자명:** {info.get('store_name', 'N/A')}
    - **업종:** {info.get('business_type', 'N/A')}
    - **위치:** {info.get('region', 'N/A')} - {info.get('location', 'N/A')}
    - **발급일:** {info.get('date', 'N/A')}
    """
    )

    # 재방문율 데이터 (질문 2일 때)
    if st.session_state.store_info.get("question_type") == 2:
        st.markdown("#### 📊 재방문율 상관계수 참고")
        df = pd.DataFrame(REVISIT_CORRELATION_DATA)
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 💊 처방전 내용")

    with st.container(border=True):
        st.markdown(st.session_state.diagnosis_result.get("prescription", "⏳ 생성 중..."))

    st.markdown("---")
    st.success("⚕️ 처방전을 저장하여 마케팅 전략을 실행하세요")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 새로운 환자 접수", use_container_width=True):
            st.session_state.step = "접수"
            st.session_state.store_info = {}
            st.session_state.messages = []
            st.session_state.diagnosis_result = {}
            st.session_state.selected_question = None
            st.session_state.reference_document = None
            st.rerun()

    with col2:
        prescription_text = st.session_state.diagnosis_result.get("prescription", "")
        store_name = info.get("store_name", "미입력")
        business_type = info.get("business_type", "미입력")
        region = info.get("region", "미입력")
        location = info.get("location", "미입력")
        date = info.get("date", datetime.now().strftime("%Y년 %m월 %d일"))

        full_prescription = f"""
┌────────────────────────────────────────────┐
│       상권 마케팅 처방 클리닉                │
│   Marketing Prescription Clinic              │
└────────────────────────────────────────────┘

환자명: {store_name}
업종: {business_type}
위치: {region} - {location}
발급일: {date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 신한카드 빅데이터 기반 분석

{prescription_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

본 처방전은 신한카드 빅데이터 분석 기반
발급: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        st.download_button(
            label="📥 처방전 다운로드",
            data=full_prescription,
            file_name=f"처방전_{store_name}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col3:
        st.info("💡 실행!")

# ==================== 진행 단계 표시 ====================
st.markdown("---")
cols = st.columns(3)
steps = ["📋 접수", "🩺 진료", "💊 처방전"]
step_names = ["접수", "진료", "처방전"]

for idx, (col, step_icon, step_name) in enumerate(zip(cols, steps, step_names)):
    with col:
        if st.session_state.step == step_name:
            st.markdown(
                f"""
                <div style='background: #4CAF50; color: white; padding: 1rem; border-radius: 10px; text-align: center; font-weight: bold;'>
                    {step_icon}
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif step_names.index(st.session_state.step) > idx:
            st.markdown(
                f"""
                <div style='background: #C8E6C9; color: #1B5E20; padding: 1rem; border-radius: 10px; text-align: center;'>
                    ✅ {step_icon}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style='background: #F5F5F5; color: #9E9E9E; padding: 1rem; border-radius: 10px; text-align: center;'>
                    {step_icon}
                </div>
                """,
                unsafe_allow_html=True,
            )
