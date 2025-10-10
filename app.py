import streamlit as st
import google.generativeai as genai
from datetime import datetime

st.set_page_config(
    page_title="상권 마케팅 처방 클리닉", 
    page_icon="🏥",
    layout="wide"
)

# API Key 설정 및 모델 초기화
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("⚠️ API 키를 설정해주세요. (st.secrets['GEMINI_API_KEY'])")
    # API 키가 없어도 UI는 볼 수 있도록 st.stop()은 제거
    
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

SYSTEM_PROMPT = """
당신은 신한카드 빅데이터 기반 상권 마케팅 전문 의사입니다.

# 핵심 데이터베이스 (반드시 활용)

## 1. 카페 업종 분석 (182개 매장)

### 1-1. 위치별 유형
- **유동형** (70개, 38.5%): 성수동·서울숲 / 유동인구 58%, 거주 28%, 직장 14%
  - 재방문-유동 상관계수: **-0.35** (강한 음의 상관)
  - 재방문-신규 상관계수: **-0.09** (약한 음의 상관)
  - 매출금액 비율: 평균 183%
  - 매출건수 비율: 평균 313%

- **거주형** (40개, 22.0%): 금호동·마장동 / 거주 36%, 유동 28%, 직장 6%
  - 재방문-거주 상관계수: **+0.24** (양의 상관)
  - 매출 안정성: 중상위
  - 고객 충성도: 상위권

- **직장형** (26개, 14.3%): 성수 업무지구·왕십리역 / 직장 16%, 유동 31%, 거주 30%
  - 재방문-직장 상관계수: **+0.15** (양의 상관)
  - 점심·퇴근시간 매출 집중
  - 루틴형 소비 패턴

### 1-2. 고객 패턴 (4분면)
- **위기형** (109개, 59.9%): 재방문↓ 신규↓
  - 매출금액 비율: **120%** (가장 낮음)
  - 유동 고객: 53%
  - 상태: 생존 위기
 
- **체험형** (29개, 15.9%): 재방문↓ 신규↑
  - 매출금액 비율: **210%**
  - 유동 고객: **57%** (최고)
  - 문제: 신규 유입↑ but 재방문 전환 실패

- **충성형** (18개, 9.9%): 재방문↑ 신규↓
  - 매출건수 비율: **370%** (압도적)
  - 거주 고객: 36%
  - 특징: 단골 의존형 안정

- **확장형** (26개, 14.3%): 재방문↑ 신규↑
  - 매출금액 비율: 208%, 매출건수 비율: 380%
  - 유동 49%, 거주 31%, 직장 16%
  - 상태: 이상적 성장 모델

### 1-3. 성별/연령별 특성
**남성 고객**
- 20대 이하 (36개 매장): 매출건수 비율 **522%** (방문빈도 최고), 매출금액 비율 190%
  - 특징: 다빈도 저단가, 스탬프/할인 민감
- 30대 (100개 매장, 최다): 매출금액 비율 146%, 매출건수 비율 **293%**
  - 특징: 시장 핵심축, 안정적, 구독형 수용
- 40대+ (8개): 매출금액 비율 26~12%, 시장성 낮음

**여성 고객**
- 20대: 트렌드 리더, SNS·디저트 중심, 인스타그램 마케팅 핵심층
- 30대: 프리미엄 지불의향 높음, 구독권 수용도 최고
- 40대: 재방문 상관계수 **+0.20**, 가족 단위, 로컬 중심

### 1-4. 시간별 패턴 (카페, 평균 재방문율 47.9%)
- **6월**: 재방문율 **26.77%** (연중 최저), 유동 56.74%
- **7월**: 재방문율 27.18% (회복 시작)
- **9월**: 거주 고객 **34.97%**로 증가 (+3%p)
- **12월**: 직장 고객 **12.25%** (연중 최고)

## 2. 재방문율 관련 데이터
- 거주 고객 비율: **+0.24** 상관계수
- 유동 고객 비율: **-0.32** 상관계수 (강한 음의 상관)
- 신규 고객 비중: **-0.21** 상관계수

## 3. 응답 원칙
1. **모든 수치 명시 필수**: 상관계수, 비율, 매장수, %p 변화량
2. **신한카드 데이터** 명시 필수
3. **의료 컨셉**: 진단 → 처방 → 복약지도 형식
4. **근거 기반**: 수치 없는 일반론 금지
"""

# 사이드바 - 질문 선택
with st.sidebar:
    st.markdown("""
        <div style='background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); padding: 1.5rem; border-radius: 10px; color: white; margin-bottom: 1.5rem; text-align: center;'>
            <div style='font-size: 2rem; margin-bottom: 0.5rem;'>🏥</div>
            <h3 style='margin: 0;'>클리닉 진료실</h3>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📋 사전 질문 선택")
    st.caption("아래 질문을 클릭하여 진료를 시작하세요")
    
    # st.button을 사용하여 변수에 할당 (오류 수정)
    q1 = st.button("질문 1: 카페 고객 타겟팅 (유동/보통)", key="btn_q1", use_container_width=True)
    q2 = st.button("질문 2: 재방문율 개선 (거주/보통)", key="btn_q2", use_container_width=True)
    q3 = st.button("질문 3: 요식업 문제 해결 (직장/낮음)", key="btn_q3", use_container_width=True)

    if q1:
        st.session_state.selected_question = 1
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "카페",
            "location_detail": "역세권/대로변 (유동인구 많음)",
            "sales_level": "보통 (업종 평균 수준)",
            "open_period": "1년~3년",
            "concern": "고객 타겟팅 및 홍보 채널 추천이 필요해"
        }
        st.rerun()

    
    if q2:
        st.session_state.selected_question = 2
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "카페", 
            "location_detail": "주택가/골목 (거주민 중심)",
            "sales_level": "보통 (업종 평균 수준)",
            "open_period": "1년~3년",
            "concern": "재방문율이 낮아 개선 전략 필요해"
        }
        st.rerun()

    if q3:
        st.session_state.selected_question = 3
        st.session_state.step = "접수"
        st.session_state.store_info = {
            "business_type": "한식-일반",
            "location_detail": "오피스/업무지구 (직장인 중심)",
            "sales_level": "낮음 (업종 평균 이하)",
            "open_period": "3개월~1년",
            "concern": "매장의 현재 가장 큰 문제점을 알고 싶고 이를 보완할 마케팅 아이디어와 근거를 제시해줘"
        }
        st.rerun()


    
    st.markdown("---")
    
    # ----------------------------------------------------
    # 요청에 따라 신한카드 데이터 요약 문구 삭제 완료
    # ----------------------------------------------------
    
    if st.session_state.step != "접수":
        st.markdown("---")
        if st.button("🏠 처음으로", use_container_width=True, type="primary"):
            st.session_state.step = "접수"
            st.session_state.store_info = {}
            st.session_state.messages = []
            st.session_state.selected_question = None
            st.rerun()

# 헤더
st.markdown("""
    <div style='text-align: center; padding: 2.5rem; background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%); border-radius: 15px; margin-bottom: 2rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <div style='font-size: 3rem; margin-bottom: 0.5rem;'>🏥</div>
        <h1 style='color: white; margin: 0; font-size: 2.2rem;'>상권 마케팅 처방 클리닉</h1>
        <p style='color: #E8F5E9; margin-top: 0.8rem; font-size: 1.1rem;'>💊 신한카드 빅데이터 기반 맞춤 처방 서비스</p>
        <p style='color: #C8E6C9; margin-top: 0.3rem; font-size: 0.9rem;'>진료시간: 24시간 | 예약: 불필요 | 보험: 데이터 적용</p>
    </div>
""", unsafe_allow_html=True)

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
        st.info(f"✅ 선택된 진료: {question_titles[st.session_state.selected_question]} (자동 입력된 정보를 확인/수정 후 '진료 접수하기'를 눌러주세요)")
    
    st.subheader("가맹점 기본 정보를 입력해주세요")
    
    col1, col2 = st.columns(2)
    
    with col1:
        store_name = st.text_input("🏪 가맹점명", placeholder="예: 달구 성수점", value=initial_store_info.get("store_name", ""))
        
        region_options = ["선택하세요", "서울 성동구", "서울 강남구", "서울 강서구", "서울 마포구", "서울 종로구", "부산", "대구", "대전", "인천", "광주", "기타 지역"]
        region_choice = st.selectbox(
            "🗺️ 지역 선택",
            region_options,
            index=region_options.index(initial_store_info.get("region", "선택하세요")) if initial_store_info.get("region") in region_options else 0
        )
        
        location_options = ["선택하세요", "성수동1가", "성수동2가", "서울숲길", "왕십리", "행당동", "금호동", "옥수동", "마장동", "응봉동"]
        if region_choice == "서울 성동구":
            location = st.selectbox(
                "📍 상세 위치 (성동구)",
                location_options,
                index=location_options.index(initial_store_info.get("location", "선택하세요")) if initial_store_info.get("location") in location_options else 0
            )
        elif region_choice and region_choice != "선택하세요":
            location = st.text_input("📍 상세 위치 직접 입력", placeholder="예: 강남구 역삼동", value=initial_store_info.get("location", ""))
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
        location_detail_default_index = location_detail_options.index(initial_store_info.get("location_detail", "역세권/대로변 (유동인구 많음)")) if initial_store_info.get("location_detail") in location_detail_options else 0
        location_detail = st.radio(
            "🏢 상권 특성",
            location_detail_options,
            index=location_detail_default_index
        )
        
        open_period_options = ["선택하세요", "3개월 미만", "3개월~1년", "1년~3년", "3년 이상"]
        open_period = st.selectbox(
            "📅 운영 기간",
            open_period_options,
            index=open_period_options.index(initial_store_info.get("open_period", "선택하세요")) if initial_store_info.get("open_period") in open_period_options else 0
        )
        
        sales_level_options = ["선택하세요", "낮음 (업종 평균 이하)", "보통 (업종 평균 수준)", "높음 (업종 평균 이상)"]
        sales_level = st.selectbox(
            "💰 매출 수준",
            sales_level_options,
            index=sales_level_options.index(initial_store_info.get("sales_level", "선택하세요")) if initial_store_info.get("sales_level") in sales_level_options else 0
        )
    
    concern = st.text_area(
        "😰 현재 겪고 있는 고민을 작성해주세요",
        placeholder="""예시:
- 손님은 많은데 단골이 안 생겨요
- 재방문율이 너무 낮아요 (30% 이하)
- 점심 시간대 매출이 약해요
- 여름/겨울에 매출이 떨어져요
- 어떤 고객층을 타겟해야 할지 모르겠어요""",
        height=120,
        value=initial_store_info.get("concern", "")
    )
    
    if st.button("🏥 진료 접수하기", type="primary", use_container_width=True):
        if (store_name and location and location != "선택하세요" and 
            business_type != "선택하세요" and region_choice != "선택하세요" and 
            open_period != "선택하세요" and sales_level != "선택하세요" and concern):
            
            st.session_state.store_info = {
                "store_name": store_name,
                "region": region_choice,
                "location": location,
                "location_detail": location_detail,
                "business_type": business_type,
                "open_period": open_period,
                "sales_level": sales_level,
                "concern": concern,
                "date": datetime.now().strftime("%Y년 %m월 %d일"),
                "question_type": st.session_state.selected_question
            }
            
            if not MODEL_AVAILABLE:
                 st.error("⚠️ API 키가 설정되지 않아 진단 기능을 사용할 수 없습니다. API 키를 설정해주세요.")
            else:
                with st.spinner("🔬 검사 및 초기 진단 중..."):
                    question_context = ""
                    if st.session_state.selected_question == 1:
                        question_context = "\n\n[중요] 이 진단은 '카페의 주요 고객 특성에 따른 마케팅 채널 추천'에 특화되어야 합니다."
                    elif st.session_state.selected_question == 2:
                        question_context = "\n\n[중요] 이 진단은 '재방문율 개선'에 특화되어야 합니다."
                    elif st.session_state.selected_question == 3:
                        question_context = "\n\n[중요] 이 진단은 '요식업 문제점 분석'에 특화되어야 합니다."
                    
                    initial_prompt = f"""
                    {SYSTEM_PROMPT}
                    {question_context}
                    
                    가맹점 정보:
                    - 가맹점명: {store_name}
                    - 지역: {region_choice} - {location}
                    - 상권 특성: {location_detail}
                    - 업종: {business_type}
                    - 운영 기간: {open_period}
                    - 매출 수준: {sales_level}
                    - 주 증상: {concern}
                    
                    다음 형식으로 초기 진단을 작성하세요:
                    
                    ## 🔬 초기 검사 결과
                    
                    ### 1. 상권 유형 분석
                    [위치 및 상권 특성 기반 예상 고객 구성]
                    - 유동/거주/직장 비율 예상
                    - 신한카드 데이터 매칭 (예: 유동형(70개, 38.5%)에 해당)
                    
                    ### 2. 핵심 문제 진단
                    [고민에 기반한 3가지 주요 문제점 + 데이터 근거]
                    
                    ### 3. 즉시 처방 필요 사항
                    [우선순위 높은 액션 3개]
                    
                    모든 분석에 신한카드 데이터의 구체적 수치를 포함하세요.
                    """
                    
                    try:
                        response = model.generate_content(initial_prompt)
                        st.session_state.diagnosis_result["initial"] = response.text
                        st.session_state.step = "진료"
                        st.rerun()
                    except Exception as e:
                        st.error(f"진단 오류: {str(e)}")
        else:
            st.error("⚠️ 모든 필수 항목을 입력해주세요!")

# 2단계: 진료
elif st.session_state.step == "진료":
    question_titles = {
        1: "질문 1: 카페 고객 타겟팅 및 마케팅 채널",
        2: "질문 2: 재방문율 개선 전략",
        3: "질문 3: 요식업 문제 해결방안"
    }
    
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%); padding: 1.5rem; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 1.5rem;'>
            <h2 style='margin: 0; color: #1B5E20;'>🩺 진료실</h2>
            <p style='margin: 0.5rem 0 0 0; color: #2E7D32; font-size: 1rem;'><strong>{st.session_state.store_info.get('store_name', '가맹점')}</strong> | {question_titles.get(st.session_state.store_info.get('question_type'), '일반 진료')}</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.expander("📄 환자 차트 (접수 정보)", expanded=False):
        info = st.session_state.store_info
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            **가맹점명:** {info.get('store_name', 'N/A')}  
            **업종:** {info.get('business_type', 'N/A')}  
            **위치:** {info.get('region', 'N/A')} - {info.get('location', 'N/A')}  
            **상권 특성:** {info.get('location_detail', 'N/A')}
            """)
        with col2:
            st.markdown(f"""
            **운영 기간:** {info.get('open_period', 'N/A')}  
            **매출 수준:** {info.get('sales_level', 'N/A')}  
            **접수일:** {info.get('date', 'N/A')}  
            **고민:** {info.get('concern', 'N/A')}
            """)
    
    st.markdown("### 📊 초기 진단 결과")
    with st.container(border=True):
        st.markdown(st.session_state.diagnosis_result.get("initial", "진단 중..."))
    
    st.markdown("---")
    st.markdown("### 💬 전문의 상담")
    
    if len(st.session_state.messages) == 0:
        initial_msg = f"""안녕하세요, **{st.session_state.store_info.get('store_name', '점주')}** 점주님!

초기 진단을 완료했습니다. 신한카드 빅데이터 기반으로 더 구체적인 마케팅 전략을 상담해드리겠습니다.

편하게 추가 질문이나 더 알고 싶은 부분을 물어봐주세요."""
        st.session_state.messages.append({"role": "assistant", "content": initial_msg})
    
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🏥" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])
    
    if prompt := st.chat_input("💬 전문의에게 질문하기..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        
        if not MODEL_AVAILABLE:
             st.error("⚠️ API 키가 설정되지 않아 상담 기능을 사용할 수 없습니다.")
        else:
            try:
                question_focus = ""
                if st.session_state.store_info.get('question_type') == 1:
                    question_focus = "고객 타겟팅 및 마케팅 채널 추천에 집중하세요."
                elif st.session_state.store_info.get('question_type') == 2:
                    question_focus = "재방문율 개선 전략에 집중하세요."
                elif st.session_state.store_info.get('question_type') == 3:
                    question_focus = "요식업 문제 분석 및 해결방안에 집중하세요."
                
                context = f"""
                {SYSTEM_PROMPT}
                
                {question_focus}
                
                가맹점 정보:
                - 이름: {st.session_state.store_info.get('store_name', 'N/A')}
                - 업종: {st.session_state.store_info.get('business_type', 'N/A')}
                - 위치: {st.session_state.store_info.get('region', 'N/A')} - {st.session_state.store_info.get('location', 'N/A')} ({st.session_state.store_info.get('location_detail', 'N/A')})
                - 운영: {st.session_state.store_info.get('open_period', 'N/A')}
                - 매출: {st.session_state.store_info.get('sales_level', 'N/A')}
                - 고민: {st.session_state.store_info.get('concern', 'N/A')}
                
                초기 진단:
                {st.session_state.diagnosis_result.get('initial', '')}
                
                점주 질문: {prompt}
                
                반드시 신한카드 데이터의 구체적 수치(상관계수, 비율, 매장수, %p)를 포함하여 답변하세요.
                """
                
                response = model.generate_content(context)
                answer = response.text
                
                st.session_state.messages.append({"role": "assistant", "content": answer})
                with st.chat_message("assistant", avatar="🏥"):
                    st.markdown(answer)
            except Exception as e:
                st.error(f"⚠️ 상담 중 오류: {str(e)}")
    
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("💊 충분한 상담이 이루어졌다면 최종 처방전을 발급받으세요!")
    with col2:
        if st.button("📋 처방전 발급", type="primary", use_container_width=True):
            if not MODEL_AVAILABLE:
                 st.error("⚠️ API 키가 설정되지 않아 처방전 기능을 사용할 수 없습니다.")
            else:
                with st.spinner("📝 처방전 작성 중..."):
                    try:
                        question_requirement = ""
                        if st.session_state.store_info.get('question_type') == 1:
                            question_requirement = "이 처방전은 카페의 고객 특성에 따른 마케팅 채널 추천을 중심으로 작성하세요."
                        elif st.session_state.store_info.get('question_type') == 2:
                            question_requirement = "이 처방전은 재방문율 개선에 필요한 구체적 전략을 중심으로 작성하세요."
                        elif st.session_state.store_info.get('question_type') == 3:
                            question_requirement = "이 처방전은 요식업의 가장 큰 문제점 분석과 해결방안을 중심으로 작성하세요."
                        
                        prescription_prompt = f"""
                        {SYSTEM_PROMPT}
                        
                        {question_requirement}
                        
                        다음 가맹점의 최종 마케팅 처방전을 작성하세요:
                        
                        가맹점 정보:
                        - 이름: {st.session_state.store_info.get('store_name', 'N/A')}
                        - 업종: {st.session_state.store_info.get('business_type', 'N/A')}
                        - 위치: {st.session_state.store_info.get('region', 'N/A')} - {st.session_state.store_info.get('location', 'N/A')}
                        - 특성: {st.session_state.store_info.get('location_detail', 'N/A')}
                        - 운영: {st.session_state.store_info.get('open_period', 'N/A')}
                        - 매출: {st.session_state.store_info.get('sales_level', 'N/A')}
                        - 고민: {st.session_state.store_info.get('concern', 'N/A')}
                        
                        초기 진단:
                        {st.session_state.diagnosis_result.get('initial', '')}
                        
                        상담 기록:
                        {chr(10).join([f"- {msg['role']}: {msg['content'][:200]}..." for msg in st.session_state.messages[-10:]])}
                        
                        다음 형식의 의료 처방전을 작성하세요:
                        
                        # 💊 마케팅 처방전
                        
                        ## 📋 환자 정보
                        - 환자명: {st.session_state.store_info.get('store_name', 'N/A')}
                        - 업종: {st.session_state.store_info.get('business_type', 'N/A')}
                        - 위치: {st.session_state.store_info.get('region', 'N/A')} - {st.session_state.store_info.get('location', 'N/A')}
                        - 발급일: {st.session_state.store_info.get('date', 'N/A')}
                        
                        ## 🔬 종합 진단
                        [상권 유형, 고객 구조, 핵심 문제 3가지를 신한카드 데이터로 분석]
                        
                        ## 💊 처방 내역
                        
                        ### 우선순위 1위 ⭐⭐⭐
                        **처방명:** [구체적 전략명]
                        **목표:** [재방문율/매출 증가 등 수치 목표]
                        **근거:** 신한카드 데이터 [상관계수, 비율, 사례]
                        **실행 방법:**
                        1. [구체적 실행 1]
                        2. [구체적 실행 2]
                        3. [구체적 실행 3]
                        **예상 효과:** [구체적 수치]
                        
                        ### 우선순위 2위 ⭐⭐
                        (동일 형식)
                        
                        ### 우선순위 3위 ⭐
                        (동일 형식)
                        
                        ## 📊 3개월 예상 성과
                        | 지표 | 현재 | 목표 | 개선율 |
                        |---|---|---|---|
                        | 재방문율 | XX% | XX% | +XX%p |
                        | 매출 | XX만원 | XX만원 | +XX% |
                        
                        ## ⚠️ 복약 지도 및 주의사항
                        [주의할 점 3가지 + 데이터 근거]
                        
                        ---
                        
                        **처방의:** AI 마케팅 전문의
                        **발급일:** {datetime.now().strftime('%Y년 %m월 %d일')}
                        **병원명:** 상권 마케팅 처방 클리닉
                        """
                        
                        prescription = model.generate_content(prescription_prompt)
                        st.session_state.diagnosis_result["prescription"] = prescription.text
                        st.session_state.step = "처방전"
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ 처방전 발급 오류: {str(e)}")

# 3단계: 처방전
elif st.session_state.step == "처방전":
    
    # ----------------------------------------------------
    # 이 부분이 오류가 난 HTML 테이블 부분입니다. 
    # 'unsafe_allow_html=True'가 확실히 적용되어 있습니다. (이전 코드와 동일)
    # ----------------------------------------------------
    st.markdown(f"""
        <div style='border: 3px solid #2E7D32; padding: 2rem; border-radius: 10px; background: white; margin-bottom: 2rem; box-shadow: 0 4px 8px rgba(0,0,0,0.1);'>
            <div style='text-align: center; margin-bottom: 1.5rem;'>
                <div style='font-size: 3rem; margin-bottom: 0.5rem;'>🏥</div>
                <h2 style='margin: 0; color: #1B5E20; font-size: 1.8rem;'>상권 마케팅 처방 클리닉</h2>
                <p style='margin: 0.3rem 0; color: #2E7D32;'>Marketing Strategy Prescription Clinic</p>
                <div style='border-top: 2px solid #4CAF50; margin: 1rem auto; width: 60%;'></div>
            </div>
            
            <table style='width: 100%; border-collapse: collapse;'>
                <tr>
                    <td style='padding: 0.5rem; border-bottom: 1px solid #E0E0E0; width: 30%; color: #666;'><strong>환자명 (가맹점)</strong></td>
                    <td style='padding: 0.5rem; border-bottom: 1px solid #E0E0E0;'>{st.session_state.store_info.get('store_name', 'N/A')}</td>
                    <td style='padding: 0.5rem; border-bottom: 1px solid #E0E0E0; width: 20%; color: #666;'><strong>차트번호</strong></td>
                    <td style='padding: 0.5rem; border-bottom: 1px solid #E0E0E0;'>{datetime.now().strftime('%Y%m%d')}</td>
                </tr>
                <tr>
                    <td style='padding: 0.5rem; border-bottom: 1px solid #E0E0E0; color: #666;'><strong>업종</strong></td>
                    <td style='padding: 0.5rem; border-bottom: 1px solid #E0E0E0;'>{st.session_state.store_info.get('business_type', 'N/A')}</td>
                    <td style='padding: 0.5rem; border-bottom: 1px solid #E0E0E0; color: #666;'><strong>발급일</strong></td>
                    <td style='padding: 0.5rem; border-bottom: 1px solid #E0E0E0;'>{st.session_state.store_info.get('date', 'N/A')}</td>
                </tr>
                <tr>
                    <td style='padding: 0.5rem; border-bottom: 1px solid #E0E0E0; color: #666;'><strong>위치</strong></td>
                    <td style='padding: 0.5rem; border-bottom: 1px solid #E0E0E0;' colspan='3'>{st.session_state.store_info.get('region', 'N/A')} - {st.session_state.store_info.get('location', 'N/A')}</td>
                </tr>
            </table>
            
            <div style='margin-top: 1rem; padding: 0.8rem; background: #F1F8E9; border-radius: 5px; text-align: center;'>
                <span style='color: #558B2F; font-weight: bold;'>📊 신한카드 빅데이터 기반 분석</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown(st.session_state.diagnosis_result.get("prescription", "⏳ 처방전 생성 중..."))
    
    st.markdown("---")
    st.markdown("""
        <div style='background: #FFF3E0; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; text-align: center;'>
            <p style='margin: 0; color: #E65100; font-weight: bold;'>⚕️ 처방전을 저장하여 마케팅 전략을 실행하세요</p>
        </div>
    """, unsafe_allow_html=True)
    
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
        store_name = st.session_state.store_info.get('store_name', '미입력')
        business_type = st.session_state.store_info.get('business_type', '미입력')
        region = st.session_state.store_info.get('region', '미입력')
        location = st.session_state.store_info.get('location', '미입력')
        date = st.session_state.store_info.get('date', datetime.now().strftime('%Y년 %m월 %d일'))

        full_prescription = f"""
┌────────────────────────────────────────────┐
│         상권 마케팅 처방 클리닉              │
│     Marketing Prescription Clinic            │
└────────────────────────────────────────────┘

환자명(가맹점): {store_name}
업종: {business_type}
위치: {region} - {location}
발급일: {date}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 신한카드 빅데이터 기반 분석

{prescription_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

본 처방전은 신한카드 빅데이터 분석에 기반합니다.
처방의: AI 마케팅 전문의
발급시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
병원명: 상권 마케팅 처방 클리닉
        """
        
        st.download_button(
            label="📥 처방전 다운로드",
            data=full_prescription,
            file_name=f"처방전_{store_name}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col3:
        st.info("💡 실행하세요!")

# 진행 단계 표시
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
