import streamlit as st
import google.generativeai as genai
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="성동구 카페 처방 클리닉", 
    page_icon="☕",
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
if "cafe_info" not in st.session_state:
    st.session_state.cafe_info = {}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "diagnosis_result" not in st.session_state:
    st.session_state.diagnosis_result = {}

# 신한카드 데이터 기반 시스템 프롬프트
SYSTEM_PROMPT = """
당신은 신한카드 빅데이터를 기반으로 한 성동구 카페 전문 컨설턴트입니다.

[분석 데이터 기반 - 182개 카페 분석]

## 1. 위치별 카페 유형 (동선/이용 맥락)

### 유동형 카페 (70개, 전체의 38%)
- 위치: 성수동, 서울숲 인근
- 특징: 유동인구 58%, 재방문 낮음(상관 -0.35)
- 매출: 건당 높지만 재방문 낮음
- 주 고객: 20대 여성 중심

### 거주형 카페 (40개, 22%)
- 위치: 금호동(주거지역), 마장동
- 특징: 거주 고객 36%, 재방문 높음
- 매출: 안정적, 주기적 방문
- 주 고객: 30-40대 여성 중심

### 직장형 카페 (26개, 14%)
- 위치: 성수 업무지구, 왕십리역 인근
- 특징: 직장 고객 16%, 충성도 최고
- 매출: 점심·퇴근시간 집중
- 주 고객: 30대 남녀 균형

## 2. 고객 패턴 유형 (4분면 분석)

### 위기형 (재방문↓ 신규↓) - 109개 (60%)
- 매출금액 비율: 120% (최저)
- 특징: 고객 기반 부족, 생존 위기

### 체험형 (재방문↓ 신규↑) - 29개 (16%)
- 매출금액 비율: 210%
- 특징: 유동인구 57%, 신규는 오지만 재방문 안함

### 충성형 (재방문↑ 신규↓) - 18개 (10%)
- 매출건수 비율: 370%
- 특징: 단골 의존, 거주 고객 36%

### 확장형 (재방문↑ 신규↑) - 26개 (14%)
- 매출금액 비율: 208%, 매출건수 380%
- 특징: 균형잡힌 성장형, 이상적 모델

## 3. 성별/연령 분석

### 남성
- 20대: 522% 방문빈도 (다빈도 저단가)
- 30대: 293% (안정적 핵심층, 100개 매장)
- 40대 이상: 시장성 낮음

### 여성
- 20대: 트렌드 리더, SNS 중심
- 30대: 프리미엄 지불의향, 안정적
- 40대: 가족 단위, 로컬 중심

## 응답 원칙
1. 반드시 위 데이터의 구체적 수치를 근거로 제시
2. 카페 유형 → 고객 패턴 → 성별/연령 순으로 진단
3. 각 전략에 상관계수, 비율, 매장수 등 명확한 근거 포함
4. "신한카드 182개 카페 분석 결과" 문구 반드시 포함
"""

# 헤더
st.markdown("""
    <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #FF6B6B 0%, #FFE66D 100%); border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>☕ 성동구 카페 처방 클리닉</h1>
        <p style='color: white; margin-top: 0.5rem;'>신한카드 빅데이터 기반 맞춤형 마케팅 처방</p>
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
    st.subheader("카페 정보를 입력해주세요")
    
    col1, col2 = st.columns(2)
    
    with col1:
        cafe_name = st.text_input("☕ 카페명", placeholder="예: 커피스미스 성수점")
        
        location = st.selectbox(
            "📍 위치 (성동구)",
            ["선택하세요", "성수동1가", "성수동2가", "서울숲길", "왕십리", "행당동", "금호동", "옥수동", "마장동"]
        )
        
        location_detail = st.radio(
            "🏢 상권 특성",
            ["역세권/대로변", "주택가/골목", "오피스/업무지구", "공원/문화시설 인근"]
        )
        
    with col2:
        current_issue = st.multiselect(
            "😰 현재 고민 (복수 선택)",
            ["매출이 낮아요", "재방문율이 낮아요", "신규 고객이 안 와요", "경쟁이 심해요", "마케팅 방법을 모르겠어요"]
        )
        
        monthly_sales = st.selectbox(
            "💰 월 평균 매출",
            ["선택하세요", "1천만원 미만", "1천~2천만원", "2천~3천만원", "3천만원 이상"]
        )
        
        open_period = st.selectbox(
            "📅 운영 기간",
            ["선택하세요", "3개월 미만", "3개월~1년", "1년~3년", "3년 이상"]
        )
        
    additional_info = st.text_area(
        "📝 추가 정보",
        placeholder="예: 주 고객층이 궁금해요, 인스타그램 마케팅 효과가 있을까요? 등"
    )
    
    if st.button("🏥 진료 시작하기", type="primary", use_container_width=True):
        if cafe_name and location != "선택하세요" and current_issue and monthly_sales != "선택하세요":
            st.session_state.cafe_info = {
                "cafe_name": cafe_name,
                "location": location,
                "location_detail": location_detail,
                "current_issue": current_issue,
                "monthly_sales": monthly_sales,
                "open_period": open_period,
                "additional_info": additional_info,
                "date": datetime.now().strftime("%Y년 %m월 %d일")
            }
            
            # 초기 진단 생성
            with st.spinner("초기 진단 중..."):
                initial_diagnosis_prompt = f"""
                {SYSTEM_PROMPT}
                
                다음 카페의 초기 진단을 수행하세요:
                
                - 위치: {location} ({location_detail})
                - 현재 고민: {', '.join(current_issue)}
                - 월 매출: {monthly_sales}
                - 운영 기간: {open_period}
                
                다음 형식으로 간단히 진단하세요:
                
                1. 카페 유형 판단 (유동형/거주형/직장형 중 1개, 근거 포함)
                2. 고객 패턴 추정 (위기형/체험형/충성형/확장형 중 1개, 근거 포함)
                3. 예상 주 고객층 (성별/연령)
                4. 핵심 문제점 1가지
                
                각 항목마다 반드시 신한카드 데이터의 구체적 수치(비율, 상관계수 등)를 근거로 제시하세요.
                """
                
                try:
                    response = model.generate_content(initial_diagnosis_prompt)
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
    st.subheader(f"{st.session_state.cafe_info['cafe_name']} 님의 정밀 진단")
    
    # 접수 정보
    with st.expander("📄 접수 정보", expanded=False):
        info = st.session_state.cafe_info
        st.write(f"**위치:** {info['location']} ({info['location_detail']})")
        st.write(f"**고민:** {', '.join(info['current_issue'])}")
        st.write(f"**월 매출:** {info['monthly_sales']}")
        st.write(f"**운영 기간:** {info['open_period']}")
    
    # 초기 진단 결과
    st.markdown("### 📊 초기 진단 결과")
    st.info(st.session_state.diagnosis_result.get("initial", "진단 중..."))
    
    st.markdown("---")
    st.markdown("### 💬 전문의 상담")
    st.caption("추가로 궁금한 점을 물어보세요. 신한카드 데이터 기반으로 답변드립니다.")
    
    # 초기 메시지
    if len(st.session_state.messages) == 0:
        initial_msg = f"""안녕하세요, **{st.session_state.cafe_info['cafe_name']}** 점주님!

초기 진단을 완료했습니다. 위 진단 결과를 바탕으로 더 구체적인 마케팅 전략을 상담해드리겠습니다.

궁금하신 점이나 더 알고 싶은 전략이 있으시면 편하게 질문해주세요!

예시 질문:
- "인스타그램 마케팅이 효과가 있을까요?"
- "재방문율을 높이려면 어떻게 해야 하나요?"
- "어떤 메뉴를 추가하면 좋을까요?"
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
            
            카페 정보:
            - 카페명: {st.session_state.cafe_info['cafe_name']}
            - 위치: {st.session_state.cafe_info['location']} ({st.session_state.cafe_info['location_detail']})
            - 고민: {', '.join(st.session_state.cafe_info['current_issue'])}
            - 월 매출: {st.session_state.cafe_info['monthly_sales']}
            
            초기 진단:
            {st.session_state.diagnosis_result.get('initial', '')}
            
            점주 질문: {prompt}
            
            반드시 신한카드 182개 카페 분석 데이터의 구체적 수치(비율, 상관계수, 매장수 등)를 근거로 답변하세요.
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
                    
                    다음 카페의 최종 처방전을 작성하세요:
                    
                    카페 정보:
                    - 카페명: {st.session_state.cafe_info['cafe_name']}
                    - 위치: {st.session_state.cafe_info['location']} ({st.session_state.cafe_info['location_detail']})
                    - 고민: {', '.join(st.session_state.cafe_info['current_issue'])}
                    - 월 매출: {st.session_state.cafe_info['monthly_sales']}
                    - 운영 기간: {st.session_state.cafe_info['open_period']}
                    
                    초기 진단:
                    {st.session_state.diagnosis_result.get('initial', '')}
                    
                    상담 내역:
                    {chr(10).join([f"{msg['role']}: {msg['content'][:100]}..." for msg in st.session_state.messages[-6:]])}
                    
                    다음 형식의 상세 처방전을 작성하세요:
                    
                    # 📋 마케팅 처방전
                    
                    ## 1. 진단 요약
                    - 카페 유형: [유동형/거주형/직장형] (근거: 신한카드 데이터 XXX)
                    - 고객 패턴: [위기형/체험형/충성형/확장형] (근거: 재방문율 XX%, 신규 XX%)
                    - 주 고객층: [성별/연령] (근거: 182개 매장 분석 결과)
                    - 핵심 문제: [구체적 문제점]
                    
                    ## 2. 처방 내용
                    
                    ### 💊 1순위 처방: [전략명]
                    **목표**: [구체적 목표]
                    **실행 방법**:
                    - [구체적 실행 1]
                    - [구체적 실행 2]
                    - [구체적 실행 3]
                    **근거**: 신한카드 데이터에서 [유형]은 [구체적 수치/상관관계]를 보임
                    **예상 효과**: [수치로 표현]
                    
                    ### 💊 2순위 처방: [전략명]
                    **목표**: [구체적 목표]
                    **실행 방법**:
                    - [구체적 실행 1]
                    - [구체적 실행 2]
                    **근거**: [데이터 기반 근거]
                    **예상 효과**: [수치로 표현]
                    
                    ### 💊 3순위 처방: [전략명]
                    (동일 형식)
                    
                    ## 3. ⚠️ 주의사항 (복약 지도)
                    - [주의점 1]: [이유]
                    - [주의점 2]: [이유]
                    
                    ## 4. 📊 예상 성과 (3개월 기준)
                    - 매출: 현재 대비 +XX%
                    - 재방문율: XX% → XX%
                    - 신규 고객: 월 XX명 → XX명
                    
                    ## 5. 📅 실행 로드맵
                    - 1주차: [액션]
                    - 2-4주차: [액션]
                    - 2-3개월: [액션]
                    
                    모든 전략과 수치는 반드시 신한카드 182개 카페 분석 데이터를 근거로 제시하세요.
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
    <div style='border: 3px solid #FF6B6B; padding: 1.5rem; border-radius: 10px; background-color: #FFF5F5; margin-bottom: 2rem;'>
        <h3 style='margin: 0; color: #FF6B6B;'>☕ 성동구 카페 처방 클리닉</h3>
        <p style='margin: 0.5rem 0 0 0;'><strong>발급일:</strong> {st.session_state.cafe_info['date']}</p>
        <p style='margin: 0.3rem 0 0 0;'><strong>카페명:</strong> {st.session_state.cafe_info['cafe_name']}</p>
        <p style='margin: 0.3rem 0 0 0;'><strong>위치:</strong> {st.session_state.cafe_info['location']}</p>
        <p style='margin: 0.3rem 0 0 0; color: #666;'>📊 신한카드 빅데이터 182개 카페 분석 기반</p>
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
            st.session_state.cafe_info = {}
            st.session_state.messages = []
            st.session_state.diagnosis_result = {}
            st.rerun()
    
    with col2:
        prescription_text = st.session_state.diagnosis_result.get("prescription", "")
        st.download_button(
            label="💾 처방전 다운로드",
            data=prescription_text,
            file_name=f"카페처방전_{st.session_state.cafe_info['cafe_name']}_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col3:
        st.info("💡 처방전을 저장하여 실행하세요!")

# 사이드바
with st.sidebar:
    st.markdown("### 🏥 클리닉 안내")
    st.markdown("""
    **📊 데이터 기반**
    - 신한카드 182개 카페 분석
    - 성동구 상권 빅데이터
    
    **🎯 진료 과목**
    - 유동형/거주형/직장형 진단
    - 재방문율 개선 처방
    - 신규 유입 전략 수립
    """)
    
    st.markdown("---")
    
    st.markdown("### 📈 분석 기준")
    with st.expander("카페 유형 (3가지)"):
        st.write("• **유동형** (70개): 성수동, 유동 58%")
        st.write("• **거주형** (40개): 금호동, 거주 36%")
        st.write("• **직장형** (26개): 성수 업무지구")
    
    with st.expander("고객 패턴 (4가지)"):
        st.write("• **위기형**: 재방문↓ 신규↓")
        st.write("• **체험형**: 재방문↓ 신규↑")
        st.write("• **충성형**: 재방문↑ 신규↓")
        st.write("• **확장형**: 재방문↑ 신규↑")
    
    if st.session_state.step != "접수":
        st.markdown("---")
        if st.button("🏠 처음으로", use_container_width=True):
            st.session_state.step = "접수"
            st.session_state.cafe_info = {}
            st.session_state.messages = []
            st.rerun()
