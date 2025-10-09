import streamlit as st
import google.generativeai as genai
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="성동구 상권 마케팅 클리닉", 
    page_icon="🏥",
    layout="wide"
)

# API 키 설정
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("⚠️ API 키를 설정해주세요.")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# 세션 상태 초기화
if "step" not in st.session_state:
    st.session_state.step = "접수"
if "store_info" not in st.session_state:
    st.session_state.store_info = {}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "diagnosis_result" not in st.session_state:
    st.session_state.diagnosis_result = {}

# 신한카드 빅데이터 기반 시스템 프롬프트
SYSTEM_PROMPT = """
당신은 신한카드 빅데이터 기반 성동구 상권 마케팅 전문 컨설턴트입니다.

# 핵심 데이터베이스 (반드시 활용)

## 1. 카페 업종 분석 (182개 매장)

### 1-1. 위치별 유형
- **유동형** (70개, 38%): 성수동·서울숲 / 유동 58%, 재방문 낮음(상관 -0.35)
- **거주형** (40개, 22%): 금호동·마장동 / 거주 36%, 재방문 높음
- **직장형** (26개, 14%): 성수 업무지구 / 직장 16%, 충성도 최고

### 1-2. 고객 패턴 (4분면)
- **위기형** (109개, 60%): 재방문↓ 신규↓, 매출 120%
- **체험형** (29개, 16%): 재방문↓ 신규↑, 매출 210%, 유동 57%
- **충성형** (18개, 10%): 재방문↑ 신규↓, 매출건수 370%, 거주 36%
- **확장형** (26개, 14%): 재방문↑ 신규↑, 매출 208%

### 1-3. 성별/연령
- 남성 20대: 522% 방문빈도 (다빈도 저단가)
- 남성 30대: 293% (100개 매장, 핵심층)
- 여성 20대: 트렌드 리더, SNS 중심
- 여성 30대: 프리미엄 지불의향, 안정적

### 1-4. 시간별 패턴 (카페, 재방문율 47.9%)
- **6~7월**: 재방문율 최저 26.77%, 신규 유입↑ 단골 이탈
- **9월**: 거주 고객 34.97%로 증가, 단골 회복
- **12월**: 직장 고객 12.25%로 연중 최고 (연말 수요)

## 2. 재방문율 분석 (전 업종)

### 2-1. 고객 구조 상관계수
- 거주 고객 비율: **+0.24** (양의 상관)
- 여성 40대: **+0.20** (단골 형성)
- 유동 고객: **-0.32** (가장 강한 음의 상관)
- 신규 고객: **-0.21** (리텐션 부재)

### 2-2. 매장 운영 특성
- 매출건수 1~2분위: 재방문율 33% (최고)
- 객단가 중상위(5.75~9.0): 재방문율 30%
- 고가형 Cluster 4: 재방문율 25.67%

### 2-3. 상권 경쟁
- 업종 내 거래건수 비율↑ → 재방문율↑
- 상권 내 상위 순위 → 재방문율↑
- 취소율 상위 1구간 → 재방문율↓

### 2-4. 지역 특성
- Cluster 0~3: 재방문율 16~19%, 유동 중심
- Cluster 4: 재방문율 25.67%, 고가형 안정

## 3. 요식업 분석

### 3-1. 핵심 문제
- 평균 재방문율 26.1% (하위 25%는 16%, 상위 25%는 34.8%)
- 유동 고객 의존도 과다
- 매장 간 편차 2배 이상

### 3-2. 주요 인사이트
- 객단가↑ → 재방문율↑
- 매출 중간층(3~4_25~75%) 재방문율 최고
- 거주 고객(+0.24), 직장 고객(+0.15) 양의 상관

## 4. 역세권 한식-육류 분석 (달구 사례)

### 4-1. 상권 특성
- 반경 500m 내 5,060개 동일 업종 (강한 경쟁)
- 유동 49.4%, 거주 37.8%, 직장 11.3%

### 4-2. 핵심 인사이트
- 상위 매출군(6_90%초과): 재방문율 10.5%
- 중간 매출군(4_50~75%): 재방문율 18.8% (최고)
- 유동 중심일수록 단골↓

## 5. 시간 민감형 카페 패턴

### 5-1. 월별 변동
- 6~7월: 재방문율 26.77% (최저), 여름 이탈
- 9월: 거주 고객 34.97% (회복), 로컬 수요↑
- 12월: 직장 고객 12.25% (최고), 연말 수요

### 5-2. 시간대별 특성
- 점심: 직장 고객 중심
- 퇴근: 유동 고객 증가
- 주말: 거주 고객 중심

---

# 응답 원칙

1. **모든 답변에 구체적 수치 포함 필수**
   - 상관계수, 비율, 매장수, 구간 데이터 명시
   - "신한카드 데이터 분석 결과" 문구 포함

2. **질문 유형별 대응**
   - 주요 고객 특성: 위치별 유형 + 성별/연령 + 시간 패턴
   - 재방문율: 고객 구조 상관 + 운영 특성 + 지역 분석
   - 요식업 문제: 유동 의존 + 객단가 + 매출 중간층
   - 역세권 단골: 유동형 문제 + 거주 고객 공략
   - 시간별 문제: 월별/계절별/요일별 패턴 + 시즌 전략

3. **전략 구성**
   - 문제 진단 (데이터 근거)
   - 구체적 실행 방법 (3~5개)
   - 예상 효과 (수치화)

4. **금지사항**
   - 데이터 없이 일반론 금지
   - 추상적 표현 금지
   - 근거 없는 수치 창작 금지
"""

# 헤더
st.markdown("""
    <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>🏥 성동구 상권 마케팅 클리닉</h1>
        <p style='color: white; margin-top: 0.5rem;'>신한카드 빅데이터 기반 맞춤 마케팅 처방</p>
    </div>
""", unsafe_allow_html=True)

# 진행 단계
cols = st.columns(3)
steps = ["접수", "진료", "처방전"]
for idx, (col, step_name) in enumerate(zip(cols, steps)):
    with col:
        if st.session_state.step == step_name:
            st.markdown(f"### 🔵 {step_name}")
        elif steps.index(st.session_state.step) > idx:
            st.markdown(f"### ✅ {step_name}")
        else:
            st.markdown(f"### ⚪ {step_name}")

st.markdown("---")

# 1단계: 접수
if st.session_state.step == "접수":
    st.header("📋 접수 데스크")
    st.subheader("가맹점 정보를 입력해주세요")
    
    col1, col2 = st.columns(2)
    
    with col1:
        store_name = st.text_input("🏪 가맹점명", placeholder="예: 달구 성수점")
        
        location = st.selectbox(
            "📍 위치 (성동구)",
            ["선택하세요", "성수동1가", "성수동2가", "서울숲길", "왕십리", "행당동", "금호동", "옥수동", "마장동", "응봉동"]
        )
        
        business_type = st.selectbox(
            "🍽️ 업종",
            ["선택하세요", "카페", "한식-육류/고기", "한식-일반", "일식", "중식", "양식", "치킨", "분식", "기타 음식점"]
        )
        
    with col2:
        location_detail = st.radio(
            "🏢 상권 특성",
            ["역세권/대로변 (유동 인구 많음)", "주택가/골목 (거주민 중심)", "오피스/업무지구 (직장인 중심)"]
        )
        
        open_period = st.selectbox(
            "📅 운영 기간",
            ["선택하세요", "3개월 미만", "3개월~1년", "1년~3년", "3년 이상"]
        )
        
        sales_level = st.selectbox(
            "💰 매출 수준",
            ["선택하세요", "낮음 (업종 평균 이하)", "보통 (업종 평균 수준)", "높음 (업종 평균 이상)"]
        )
    
    concern = st.text_area(
        "😰 현재 고민을 자유롭게 작성해주세요",
        placeholder="""예시:
- 손님은 많은데 단골이 안 생겨요
- 재방문율이 너무 낮아요
- 점심 시간대 매출이 약해요
- 여름에 매출이 떨어져요
- 어떤 고객층을 타겟해야 할지 모르겠어요""",
        height=150
    )
    
    if st.button("🏥 진료 시작하기", type="primary", use_container_width=True):
        if store_name and location != "선택하세요" and business_type != "선택하세요" and concern:
            st.session_state.store_info = {
                "store_name": store_name,
                "location": location,
                "location_detail": location_detail,
                "business_type": business_type,
                "open_period": open_period,
                "sales_level": sales_level,
                "concern": concern,
                "date": datetime.now().strftime("%Y년 %m월 %d일")
            }
            
            # 초기 진단
            with st.spinner("초기 진단 중..."):
                initial_prompt = f"""
                {SYSTEM_PROMPT}
                
                다음 가맹점의 초기 진단을 수행하세요:
                
                - 가맹점명: {store_name}
                - 위치: {location} ({location_detail})
                - 업종: {business_type}
                - 운영 기간: {open_period}
                - 매출 수준: {sales_level}
                - 고민: {concern}
                
                다음 형식으로 진단하세요:
                
                ## 📊 초기 진단 결과
                
                ### 1. 상권 유형 분석
                [위치 기반 유형 판단 + 신한카드 데이터 근거]
                
                ### 2. 예상 고객 구조
                [유동/거주/직장 비율 추정 + 데이터 근거]
                
                ### 3. 핵심 문제 진단
                [고민 내용 기반 문제점 + 상관계수/비율 등 근거]
                
                ### 4. 우선 점검 사항
                [즉시 확인 필요한 3가지]
                
                모든 항목에 신한카드 데이터의 구체적 수치를 반드시 포함하세요.
                """
                
                try:
                    response = model.generate_content(initial_prompt)
                    st.session_state.diagnosis_result["initial"] = response.text
                    st.session_state.step = "진료"
                    st.rerun()
                except Exception as e:
                    st.error(f"진단 오류: {str(e)}")
        else:
            st.error("⚠️ 필수 항목을 모두 입력해주세요!")

# 2단계: 진료
elif st.session_state.step == "진료":
    st.header("🩺 진료실")
    st.subheader(f"{st.session_state.store_info['store_name']} 님의 정밀 상담")
    
    # 접수 정보
    with st.expander("📄 접수 정보", expanded=False):
        info = st.session_state.store_info
        st.write(f"**업종:** {info['business_type']}")
        st.write(f"**위치:** {info['location']} ({info['location_detail']})")
        st.write(f"**운영 기간:** {info['open_period']}")
        st.write(f"**매출 수준:** {info['sales_level']}")
        st.write(f"**고민:** {info['concern']}")
    
    # 초기 진단
    st.markdown("### 📊 초기 진단 결과")
    st.info(st.session_state.diagnosis_result.get("initial", "진단 중..."))
    
    st.markdown("---")
    st.markdown("### 💬 전문의 상담")
    st.caption("추가 질문이나 더 알고 싶은 전략을 물어보세요.")
    
    # 초기 메시지
    if len(st.session_state.messages) == 0:
        initial_msg = f"""안녕하세요, **{st.session_state.store_info['store_name']}** 점주님!

초기 진단을 완료했습니다. 신한카드 빅데이터 기반으로 더 구체적인 마케팅 전략을 상담해드리겠습니다.

**자주 묻는 질문 예시:**
- "우리 위치에서 어떤 고객층을 타겟해야 하나요?"
- "재방문율을 높이려면 구체적으로 뭘 해야 하나요?"
- "계절별로 다른 전략이 필요한가요?"
- "경쟁 매장과 차별화하려면?"
- "점심/저녁 시간대별 전략은?"
"""
        st.session_state.messages.append({"role": "assistant", "content": initial_msg})
    
    # 대화 내역
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 사용자 입력
    if prompt := st.chat_input("궁금한 점을 질문하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # AI 응답
        try:
            context = f"""
            {SYSTEM_PROMPT}
            
            가맹점 정보:
            - 이름: {st.session_state.store_info['store_name']}
            - 업종: {st.session_state.store_info['business_type']}
            - 위치: {st.session_state.store_info['location']} ({st.session_state.store_info['location_detail']})
            - 운영 기간: {st.session_state.store_info['open_period']}
            - 매출 수준: {st.session_state.store_info['sales_level']}
            - 고민: {st.session_state.store_info['concern']}
            
            초기 진단:
            {st.session_state.diagnosis_result.get('initial', '')}
            
            점주 질문: {prompt}
            
            반드시 신한카드 데이터의 구체적 수치(상관계수, 비율, 매장수 등)를 근거로 답변하세요.
            """
            
            response = model.generate_content(context)
            answer = response.text
            
            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)
        except Exception as e:
            st.error(f"오류: {str(e)}")
    
    # 처방전 발급
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("💊 상담이 충분히 이루어졌다면 최종 처방전을 발급받으세요!")
    with col2:
        if st.button("📋 처방전 발급", type="primary", use_container_width=True):
            with st.spinner("처방전 작성 중..."):
                try:
                    prescription_prompt = f"""
                    {SYSTEM_PROMPT}
                    
                    다음 가맹점의 최종 마케팅 처방전을 작성하세요:
                    
                    가맹점 정보:
                    - 이름: {st.session_state.store_info['store_name']}
                    - 업종: {st.session_state.store_info['business_type']}
                    - 위치: {st.session_state.store_info['location']} ({st.session_state.store_info['location_detail']})
                    - 운영: {st.session_state.store_info['open_period']}
                    - 매출: {st.session_state.store_info['sales_level']}
                    - 고민: {st.session_state.store_info['concern']}
                    
                    초기 진단:
                    {st.session_state.diagnosis_result.get('initial', '')}
                    
                    상담 내역:
                    {chr(10).join([f"{msg['role']}: {msg['content'][:150]}..." for msg in st.session_state.messages[-8:]])}
                    
                    다음 형식의 처방전을 작성하세요:
                    
                    # 📋 마케팅 처방전
                    
                    ## 1. 종합 진단
                    - **상권 유형**: [유동형/거주형/직장형] (근거: 신한카드 데이터 XXX)
                    - **고객 구조**: [유동/거주/직장 비율] (근거: 상관계수 XXX)
                    - **핵심 문제**: [구체적 문제 3가지]
                    - **현재 상태**: [4분면 중 위치]
                    
                    ## 2. 우선순위 처방
                    
                    ### 💊 1순위 처방: [전략명]
                    **목표**: [구체적 목표]
                    **데이터 근거**: 신한카드 분석 결과 [구체적 수치/상관계수]
                    **실행 방법**:
                    1. [구체적 실행 1]
                    2. [구체적 실행 2]
                    3. [구체적 실행 3]
                    **예상 효과**: [수치로 표현]
                    
                    ### 💊 2순위 처방: [전략명]
                    (동일 형식)
                    
                    ### 💊 3순위 처방: [전략명]
                    (동일 형식)
                    
                    ## 3. ⚠️ 주의사항
                    - [위험 요인 1]: [이유 + 데이터]
                    - [위험 요인 2]: [이유 + 데이터]
                    
                    ## 4. 📊 예상 성과 (3개월 기준)
                    - 재방문율: XX% → XX% (+XXp)
                    - 매출: 현재 대비 +XX%
                    - 신규/단골 비율: XX:XX → XX:XX
                    
                    ## 5. 📅 실행 로드맵
                    - **1주차**: [즉시 실행 액션]
                    - **2-4주차**: [단기 전략]
                    - **2-3개월**: [중기 전략]
                    
                    모든 수치와 전략은 신한카드 빅데이터를 근거로 제시하세요.
                    """
                    
                    prescription = model.generate_content(prescription_prompt)
                    st.session_state.diagnosis_result["prescription"] = prescription.text
                    st.session_state.step = "처방전"
                    st.rerun()
                except Exception as e:
                    st.error(f"처방전 생성 오류: {str(e)}")

# 3단계: 처방전
elif st.session_state.step == "처방전":
    st.header("📋 마케팅 처방전")
    
    # 처방전 헤더
    st.markdown(f"""
    <div style='border: 3px solid #667eea; padding: 1.5rem; border-radius: 10px; background-color: #f8f9ff; margin-bottom: 2rem;'>
        <h3 style='margin: 0; color: #667eea;'>🏥 성동구 상권 마케팅 클리닉</h3>
        <p style='margin: 0.5rem 0 0 0;'><strong>발급일:</strong> {st.session_state.store_info['date']}</p>
        <p style='margin: 0.3rem 0 0 0;'><strong>가맹점:</strong> {st.session_state.store_info['store_name']}</p>
        <p style='margin: 0.3rem 0 0 0;'><strong>업종:</strong> {st.session_state.store_info['business_type']}</p>
        <p style='margin: 0.3rem 0 0 0;'><strong>위치:</strong> {st.session_state.store_info['location']}</p>
        <p style='margin: 0.3rem 0 0 0; color: #666;'>📊 신한카드 빅데이터 기반 분석</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 처방 내용
    st.markdown(st.session_state.diagnosis_result.get("prescription", "처방전 생성 중..."))
    
    # 하단 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 새로운 진료", use_container_width=True):
            st.session_state.step = "접수"
            st.session_state.store_info = {}
            st.session_state.messages = []
            st.session_state.diagnosis_result = {}
            st.rerun()
    
    with col2:
        prescription_text = st.session_state.diagnosis_result.get("prescription", "")
        st.download_button(
            label="💾 처방전 다운로드",
            data=prescription_text,
            file_name=f"마케팅처방전_{st.session_state.store_info['store_name']}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col3:
        st.info("💡 처방전을 실행하세요!")

# 사이드바
with st.sidebar:
    st.markdown("### 🏥 클리닉 안내")
    st.markdown("""
    **📊 데이터 기반**
    - 신한카드 빅데이터 분석
    - 성동구 상권 전문
    
    **🎯 진료 분야**
    - 주요 고객 특성 분석
    - 재방문율 개선 전략
    - 시간대/계절별 대응
    - 상권 경쟁력 강화
    """)
    
    st.markdown("---")
    
    st.markdown("### 📈 주요 질문 예시")
    with st.expander("1. 고객 타겟팅"):
        st.write("우리 위치에서 어떤 고객층을 타겟해야 하나요?")
    
    with st.expander("2. 재방문율 개선"):
        st.write("재방문율이 30% 이하인데 어떻게 높이나요?")
    
    with st.expander("3. 요식업 문제"):
        st.write("매출은 있는데 단골이 안 생겨요")
    
    with st.expander("4. 역세권 고민"):
        st.write("손님 많은데 점심 매출이 약해요")
    
    with st.expander("5. 시간별 전략"):
        st.write("계절/요일/시간대별 대응 전략은?")
    
    if st.session_state.step != "접수":
        st.markdown("---")
        if st.button("🏠 처음으로", use_container_width=True):
            st.session_state.step = "접수"
            st.session_state.store_info = {}
            st.session_state.messages = []
            st.rerun()
