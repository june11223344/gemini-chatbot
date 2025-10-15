import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import requests  # 👈 추가: GitHub 문서 로드용

st.set_page_config(
    page_title="상권 마케팅 처방 클리닉", 
    page_icon="🏥",
    layout="wide"
)

# ==================== GitHub 문서 로더 추가 ====================
@st.cache_data(ttl=3600)  # 1시간 캐시
def load_github_document(url):
    """GitHub Raw URL에서 HTML 문서 로드"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        return response.text
    except Exception as e:
        st.error(f"⚠️ 문서 로드 실패: {e}")
        return None

# GitHub 문서 URL (secrets에 저장 권장)
GITHUB_DOC_URL = "https://raw.githubusercontent.com/june11223344/gemini-chatbot/refs/heads/main/docs/%EC%83%81%EA%B6%8C%EB%B6%84%EC%84%9D%EA%B0%80%EC%9D%B4%EB%93%9C.html"

# 문서 로드 (캐싱되어 빠름)
reference_document = load_github_document(GITHUB_DOC_URL)

# API Key 설정
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("⚠️ API 키를 설정해주세요.")
    
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        MODEL_AVAILABLE = True
    except Exception as e:
        st.error(f"⚠️ 모델 초기화 오류: {e}")
        MODEL_AVAILABLE = False
else:
    MODEL_AVAILABLE = False

# Session State 초기화
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

# 재방문율 상관계수 데이터
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

# 👇 SYSTEM_PROMPT에 참고 문서 포함
SYSTEM_PROMPT = f"""
당신은 신한카드 빅데이터 기반 상권 마케팅 전문 의사입니다.

# 핵심 데이터베이스 (반드시 활용)

## 1. 카페 업종 분석 (182개 매장)

### 1-1. 위치별 유형
- **유동형** (70개, 38.5%): 성수동·서울숲 / 유동 58%, 거주 28%, 직장 14%
  - 재방문-유동 상관계수: **-0.35**
  - 매출금액 비율: 183%, 매출건수 비율: 313%

- **거주형** (40개, 22.0%): 금호동·마장동 / 거주 36%, 유동 28%, 직장 6%
  - 재방문-거주 상관계수: **+0.24**

- **직장형** (26개, 14.3%): 성수 업무지구 / 직장 16%, 유동 31%, 거주 30%
  - 재방문-직장 상관계수: **+0.15**

### 1-2. 고객 패턴 (4분면)
- **위기형** (109개, 59.9%): 재방문↓ 신규↓, 매출금액 비율 120%
- **체험형** (29개, 15.9%): 재방문↓ 신규↑, 매출금액 비율 210%, 유동 57%
- **충성형** (18개, 9.9%): 재방문↑ 신규↓, 매출건수 비율 370%, 거주 36%
- **확장형** (26개, 14.3%): 재방문↑ 신규↑, 매출 208%, 매출건수 380%

### 1-3. 성별/연령별 특성
**남성**
- 20대 이하 (36개): 매출건수 522%, 다빈도 저단가
- 30대 (100개): 매출건수 293%, 시장 핵심축
- 40대+ (8개): 시장성 낮음

**여성**
- 20대: 트렌드 리더, SNS 중심
- 30대: 프리미엄 지불의향, 구독권 수용
- 40대: 재방문 상관계수 **+0.20**, 로컬 중심

### 1-4. 시간별 패턴
- **6월**: 재방문율 26.77% (최저)
- **9월**: 거주 고객 34.97% (+3%p)
- **12월**: 직장 고객 12.25% (최고)

## 2. 재방문율 상관계수
- 거주 고객: **+0.24**
- 유동 고객: **-0.32**
- 신규 고객: **-0.21**
- 동일 업종 매출건수 비중: **+0.20**
- 동일 업종 내 해지 가맹점 비중: **-0.15**

## 3. 추가 참고 자료
{reference_document if reference_document else "참고 문서 로드 실패"}

## 4. 응답 원칙
1. **초기 진단은 간결하게**: 3-4줄 요약 형식
2. **모든 수치 명시**: 상관계수, 비율, 매장수
3. **의료 컨셉**: 진단 → 처방 형식
4. **참고 자료 활용**: 위의 HTML 문서 내용도 적극 활용
"""

# 헤더
st.markdown("""
    <div style='text-align: center; padding: 2.5rem; background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <div style='font-size: 3rem; margin-bottom: 0.5rem;'>🏥</div>
        <h1 style='color: white; margin: 0; font-size: 2.2rem;'>상권 마케팅 처방 클리닉</h1>
        <p style='color: #E8F5E9; margin-top: 0.8rem; font-size: 1.1rem;'>💊 신한카드 빅데이터 기반 맞춤 처방</p>
    </div>
""", unsafe_allow_html=True)

# 사이드바
with st.sidebar:
    st.markdown("""
        <div style='background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); padding: 1.5rem; border-radius: 10px; color: white; margin-bottom: 1.5rem; text-align: center;'>
            <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🏥</div>
            <h3 style='margin: 0;'>클리닉 진료실</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # 👇 참고 문서 표시 추가
    st.markdown("### 📚 참고 자료")
    with st.expander("📄 상권 분석 가이드", expanded=False):
        if reference_document:
            st.markdown(reference_document, unsafe_allow_html=True)
            st.success("✅ 문서 로드 완료")
        else:
            st.error("❌ 문서를 불러올 수 없습니다.")
    
    st.markdown("---")
    
    st.markdown("### 📋 사전 질문 선택")
    st.caption("질문을 클릭하면 자동으로 정보가 입력됩니다")
    
    q1 = st.button("❓ 질문 1: 카페 고객 타겟팅", key="btn_q1", use_container_width=True)
    st.caption("→ 주요 고객 특성 및 마케팅 채널 추천")
    
    q2 = st.button("❓ 질문 2: 재방문율 개선", key="btn_q2", use_container_width=True)
    st.caption("→ 재방문율 30% 이하 개선 전략")
    
    q3 = st.button("❓ 질문 3: 요식업 문제 해결", key="btn_q3", use_container_width=True)
    st.caption("→ 요식업 문제 진단 및 해결방안")

    if q1:
        st.session_state.selected_question = 1
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "카페",
            "location_detail": "역세권/대로변 (유동인구 많음)",
            "customer_type": "신규 고객 많음",
            "concern": "주요 고객 특성에 맞는 마케팅 채널과 홍보 방법을 알고 싶어요"
        }
        st.rerun()

    if q2:
        st.session_state.selected_question = 2
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "카페", 
            "location_detail": "주택가/골목 (거주민 중심)",
            "customer_type": "단골 손님 적음",
            "concern": "재방문율이 30% 이하인데 어떻게 높일 수 있을까요?"
        }
        st.rerun()

    if q3:
        st.session_state.selected_question = 3
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "한식-일반",
            "location_detail": "오피스/업무지구 (직장인 중심)",
            "customer_type": "신규 고객 많음",
            "concern": "요식업 매장의 가장 큰 문제점이 무엇인지 알고 이를 개선하고 싶어요"
        }
        st.rerun()
    
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
            st.session_state.selected_question = None
            st.rerun()

# ... 나머지 코드는 동일 (접수, 진료, 처방전 부분) ...

# 1단계: 접수
if st.session_state.step == "접수":
    st.header("📋 접수 데스크")
    
    question_titles = {
        1: "질문 1: 카페 고객 타겟팅",
        2: "질문 2: 재방문율 개선",
        3: "질문 3: 요식업 문제 해결"
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
            index=region_options.index(initial_store_info.get("region", "선택하세요")) if initial_store_info.get("region") in region_options else 0
        )
        
        location_options = ["선택하세요", "성수동1가", "성수동2가", "서울숲길", "왕십리", "행당동", "금호동", "옥수동", "마장동", "응봉동"]
        if region_choice == "서울 성동구":
            location = st.selectbox(
                "📍 상세 위치",
                location_options,
                index=location_options.index(initial_store_info.get("location", "선택하세요")) if initial_store_info.get("location") in location_options else 0
            )
        elif region_choice and region_choice != "선택하세요":
            location = st.text_input("📍 상세 위치", placeholder="예: 역삼동", value=initial_store_info.get("location", ""))
        else:
            location = "선택하세요"
        
        business_type_options = ["선택하세요", "카페", "한식-육류/고기", "한식-일반", "일식", "중식", "양식", "치킨", "분식", "베이커리", "기타"]
        business_type = st.selectbox(
            "🍽️ 업종",
            business_type_options,
            index=business_type_options.index(initial_store_info.get("business_type", "선택하세요")) if initial_store_info.get("business_type") in business_type_options else 0
        )
        
    with col2:
        location_detail_options = ["역세권/대로변 (유동인구 많음)", "주택가/골목 (거주민 중심)", "오피스/업무지구 (직장인 중심)"]
        location_detail = st.radio(
            "🏢 상권 특성",
            location_detail_options,
            index=location_detail_options.index(initial_store_info.get("location_detail", location_detail_options[0])) if initial_store_info.get("location_detail") in location_detail_options else 0
        )
        
        customer_type_options = ["단골 손님 많음", "신규 고객 많음", "단골/신규 비슷", "잘 모르겠음"]
        customer_type = st.radio(
            "👥 손님 특성",
            customer_type_options,
            index=customer_type_options.index(initial_store_info.get("customer_type", customer_type_options[0])) if initial_store_info.get("customer_type") in customer_type_options else 0
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
        value=initial_store_info.get("concern", "")
    )
    
    if st.button("🏥 진료 접수하기", type="primary", use_container_width=True):
        # 선택된 고객층 정리 (여성 먼저)
        selected_customers = []
        if female_20: selected_customers.append("여성 20대 이하")
        if female_30: selected_customers.append("여성 30대")
        if female_40: selected_customers.append("여성 40대")
        if female_50: selected_customers.append("여성 50대")
        if female_60: selected_customers.append("여성 60대 이상")
        if male_20: selected_customers.append("남성 20대 이하")
        if male_30: selected_customers.append("남성 30대")
        if male_40: selected_customers.append("남성 40대")
        if male_50: selected_customers.append("남성 50대")
        if male_60: selected_customers.append("남성 60대 이상")
        
        customer_demographics = ", ".join(selected_customers) if selected_customers else "미선택"
        
        if (store_name and location and location != "선택하세요" and 
            business_type != "선택하세요" and region_choice != "선택하세요" and concern):
            
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
                "male_20": male_20, "male_30": male_30, "male_40": male_40, "male_50": male_50, "male_60": male_60,
                "female_20": female_20, "female_30": female_30, "female_40": female_40, "female_50": female_50, "female_60": female_60
            }
            
            if not MODEL_AVAILABLE:
                st.error("⚠️ API 키 미설정")
            else:
                with st.spinner("🔬 초기 검사 중..."):
                    question_context = ""
                    if st.session_state.selected_question == 1:
                        question_context = "\n\n[중요] 카페 고객 특성 및 마케팅 채널 추천에 집중"
                    elif st.session_state.selected_question == 2:
                        question_context = "\n\n[중요] 재방문율 개선 전략에 집중"
                    elif st.session_state.selected_question == 3:
                        question_context = "\n\n[중요] 요식업 문제 분석에 집중"
                    
                    initial_prompt = f"""
                    {SYSTEM_PROMPT}
                    {question_context}
                    
                    가맹점:
                    - 이름: {store_name}
                    - 지역: {region_choice} - {location} ({location_detail})
                    - 업종: {business_type}
                    - 손님 특성: {customer_type}
                    - 주요 고객층: {customer_demographics}
                    - 고민: {concern}
                    
                    다음 형식으로 **3-4줄 요약** 진단:
                    
                    ## 🔬 초기 검사 결과
                    
                    **📍 상권 유형:** [유동형/거주형/직장형] (근거: 신한카드 XX개 매장, 고객 구성 유동XX%/거주XX%)
                    
                    **👥 고객 분석:** 주 고객층은 [{customer_demographics}]으로 추정. 신한카드 데이터에서 [특징] (매출건수 XXX%, 재방문 상관 ±X.XX)
                    
                    **⚠️ 핵심 문제:** {concern} → 원인은 [1가지 핵심 원인 + 상관계수/비율 근거]
                    
                    **💊 우선 처방:** [즉시 실행 가능한 액션 1개]
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

# 2단계: 진료
elif st.session_state.step == "진료":
    question_titles = {
        1: "질문 1: 카페 고객 타겟팅",
        2: "질문 2: 재방문율 개선",
        3: "질문 3: 요식업 문제 해결"
    }
    
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); padding: 1.5rem; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 1.5rem;'>
            <h2 style='margin: 0; color: #1B5E20;'>🩺 진료실</h2>
            <p style='margin: 0.5rem 0 0 0; color: #2E7D32;'><strong>{st.session_state.store_info.get('store_name', '')}</strong> | {question_titles.get(st.session_state.store_info.get('question_type'), '일반 진료')}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 환자 차트
    with st.expander("📄 환자 차트", expanded=False):
        info = st.session_state.store_info
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **가맹점:** {info.get('store_name', 'N/A')}  
            **업종:** {info.get('business_type', 'N/A')}  
            **위치:** {info.get('region', 'N/A')} - {info.get('location', 'N/A')}  
            **상권:** {info.get('location_detail', 'N/A')}
            """)
        with col2:
            st.markdown(f"""
            **손님 특성:** {info.get('customer_type', 'N/A')}  
            **주요 고객:** {info.get('customer_demographics', 'N/A')}  
            **접수일:** {info.get('date', 'N/A')}  
            **고민:** {info.get('concern', 'N/A')}
            """)
    
    # 재방문율 데이터 표시 (질문 2일 때)
    if st.session_state.store_info.get('question_type') == 2:
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
                context = f"""
                {SYSTEM_PROMPT}
                
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
                
                신한카드 데이터의 구체적 수치로 답변하세요.
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
                        prescription_prompt = f"""
                        {SYSTEM_PROMPT}
                        
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
                        
                        상담 기록:
                        {chr(10).join([f"- {msg['content'][:150]}..." for msg in st.session_state.messages[-10:]])}
                        
                        다음 형식의 처방전:
                        
                        # 💊 마케팅 처방전
                        
                        ## 📋 환자 정보
                        - 환자명: {st.session_state.store_info.get('store_name', '')}
                        - 업종: {st.session_state.store_info.get('business_type', '')}
                        - 위치: {st.session_state.store_info.get('region', '')} - {st.session_state.store_info.get('location', '')}
                        - 발급일: {st.session_state.store_info.get('date', '')}
                        
                        ## 🔬 종합 진단
                        [상권 유형 + 고객 구조 + 핵심 문제 3가지 (신한카드 데이터 근거)]
                        
                        ## 💊 처방 내역
                        
                        ### 우선순위 1위 ⭐⭐⭐
                        **처방명:** [구체적 전략]
                        **목표:** [수치 목표]
                        **근거:** 신한카드 데이터 [상관계수, 비율]
                        **실행:**
                        1. [실행 1]
                        2. [실행 2]
                        3. [실행 3]
                        **효과:** [구체적 수치]
                        
                        ### 우선순위 2위 ⭐⭐
                        (동일 형식)
                        
                        ### 우선순위 3위 ⭐
                        (동일 형식)
                        
                        ## 📊 3개월 예상 성과
                        | 지표 | 현재 | 목표 | 개선 |
                        |---|---|---|---|
                        | 재방문율 | XX% | XX% | +XX%p |
                        | 매출 | 현재 | +XX% | 증가 |
                        
                        ## ⚠️ 주의사항
                        [주의점 3가지 + 데이터 근거]
                        
                        **처방의:** AI 마케팅 전문의
                        **발급일:** {datetime.now().strftime('%Y년 %m월 %d일')}
                        """
                        
                        prescription = model.generate_content(prescription_prompt)
                        st.session_state.diagnosis_result["prescription"] = prescription.text
                        st.session_state.step = "처방전"
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ 처방전 오류: {str(e)}")

# 3단계: 처방전
elif st.session_state.step == "처방전":
    st.markdown(f"""
        <div style='text-align: center; padding: 1.5rem; background: #E8F5E9; border-radius: 10px; margin-bottom: 2rem;'>
            <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>🏥</div>
            <h2 style='margin: 0; color: #1B5E20;'>상권 마케팅 처방 클리닉</h2>
            <p style='margin: 0.3rem 0; color: #2E7D32;'>Marketing Strategy Prescription Clinic</p>
        </div>
    """, unsafe_allow_html=True)

    info = st.session_state.store_info
    st.markdown("### 📋 환자 차트")
    st.info(f"""
    - **환자명:** {info.get('store_name', 'N/A')}
    - **업종:** {info.get('business_type', 'N/A')}
    - **위치:** {info.get('region', 'N/A')} - {info.get('location', 'N/A')}
    - **발급일:** {info.get('date', 'N/A')}
    """)
    
    # 재방문율 데이터 (질문 2일 때)
    if st.session_state.store_info.get('question_type') == 2:
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
            st.rerun()
    
    with col2:
        prescription_text = st.session_state.diagnosis_result.get("prescription", "")
        store_name = info.get('store_name', '미입력')
        business_type = info.get('business_type', '미입력')
        region = info.get('region', '미입력')
        location = info.get('location', '미입력')
        date = info.get('date', datetime.now().strftime('%Y년 %m월 %d일'))

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
처방의: AI 마케팅 전문의
발급: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        st.download_button(
            label="📥 처방전 다운로드",
            data=full_prescription,
            file_name=f"처방전_{store_name}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col3:
        st.info("💡 실행!")

# 진행 단계
st.markdown("---")
cols = st.columns(3)
steps = ["📋 접수", "🩺 진료", "💊 처방전"]
step_names = ["접수", "진료", "처방전"]

for idx, (col, step_icon, step_name) in enumerate(zip(cols, steps, step_names)):
    with col:
        if st.session_state.step == step_name:
            st.markdown(f"""
                <div style='background: #4CAF50; color: white; padding: 1rem; border-radius: 10px; text-align: center; font-weight: bold;'>
                    {step_icon}
                </div>
            """, unsafe_allow_html=True)
        elif step_names.index(st.session_state.step) > idx:
            st.markdown(f"""
                <div style='background: #C8E6C9; color: #1B5E20; padding: 1rem; border-radius: 10px; text-align: center;'>
                    ✅ {step_icon}
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style='background: #F5F5F5; color: #9E9E9E; padding: 1rem; border-radius: 10px; text-align: center;'>
                    {step_icon}
                </div>
            """, unsafe_allow_html=True)
