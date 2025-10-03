import streamlit as st
import google.generativeai as genai
from datetime import datetime

# 페이지 설정
st.set_page_config(
    page_title="성동구 상권 처방 클리닉", 
    page_icon="🏥",
    layout="wide"
)

# Secrets에서 API 키 가져오기
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("⚠️ API 키가 설정되지 않았습니다.")
    st.stop()

# Gemini 설정
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# 세션 상태 초기화
if "step" not in st.session_state:
    st.session_state.step = "접수"
if "patient_info" not in st.session_state:
    st.session_state.patient_info = {}
if "diagnosis" not in st.session_state:
    st.session_state.diagnosis = ""
if "prescription" not in st.session_state:
    st.session_state.prescription = ""

# 시스템 프롬프트
SYSTEM_PROMPT = """
당신은 성동구 상권 분석 전문의입니다. 신한카드 데이터를 기반으로 창업을 원하는 사업자에게 최적의 상권과 업종을 처방합니다.

[성동구 주요 상권 데이터]
- 성수동: 힙한 카페, 편집샵, 공방 밀집 지역. 20-30대 유동인구 많음
- 왕십리: 대학가, 유흥가. 음식점, 주점, 학원 수요 높음
- 행당동: 주거지역. 생활밀착형 상권 (마트, 약국, 편의점)
- 금호동: 재개발 진행중. 신규 상권 형성 중

[진료 프로세스]
1. 환자(창업자)의 증상(창업 고민) 청취
2. 정확한 진단(상권 분석) 제공
3. 맞춤 처방전(추천 상권 및 업종) 작성

전문의답게 데이터 기반으로 명확하고 구체적인 조언을 제공하세요.
"""

# 헤더
st.markdown("""
    <div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 2rem;'>
        <h1 style='color: white; margin: 0;'>🏥 성동구 상권 처방 클리닉</h1>
        <p style='color: white; margin-top: 0.5rem;'>신한카드 데이터 기반 맞춤형 상권 처방 서비스</p>
    </div>
""", unsafe_allow_html=True)

# 진행 단계 표시
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
    st.subheader("창업을 위한 첫 걸음, 환자 정보를 입력해주세요")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("👤 성함", placeholder="홍길동")
        business_type = st.selectbox(
            "💼 희망 업종",
            ["선택하세요", "음식점 (카페/레스토랑)", "소매업 (옷/잡화)", "서비스업 (미용/학원)", "기타"]
        )
        budget = st.selectbox(
            "💰 예산 규모",
            ["선택하세요", "5천만원 이하", "5천만원 ~ 1억", "1억 ~ 2억", "2억 이상"]
        )
    
    with col2:
        experience = st.radio(
            "📊 창업 경험",
            ["초보 (처음입니다)", "경험 있음 (재창업)", "전문가 (다수 창업)"]
        )
        target_area = st.multiselect(
            "📍 관심 지역 (복수 선택 가능)",
            ["성수동", "왕십리", "행당동", "금호동", "옥수동"]
        )
        additional_info = st.text_area(
            "📝 추가 고민사항",
            placeholder="예: 주차공간이 필요해요, 유동인구가 많은 곳이 좋아요 등"
        )
    
    if st.button("🏥 진료 접수하기", type="primary", use_container_width=True):
        if name and business_type != "선택하세요" and budget != "선택하세요" and target_area:
            st.session_state.patient_info = {
                "name": name,
                "business_type": business_type,
                "budget": budget,
                "experience": experience,
                "target_area": target_area,
                "additional_info": additional_info,
                "date": datetime.now().strftime("%Y년 %m월 %d일")
            }
            st.session_state.step = "진료"
            st.rerun()
        else:
            st.error("⚠️ 필수 항목을 모두 입력해주세요!")

# 2단계: 진료
elif st.session_state.step == "진료":
    st.header("🩺 진료실")
    st.subheader(f"{st.session_state.patient_info['name']} 님의 상권 진단")
    
    # 환자 정보 요약
    with st.expander("📄 접수 정보 확인", expanded=True):
        info = st.session_state.patient_info
        st.write(f"**희망 업종:** {info['business_type']}")
        st.write(f"**예산:** {info['budget']}")
        st.write(f"**경험:** {info['experience']}")
        st.write(f"**관심 지역:** {', '.join(info['target_area'])}")
        if info['additional_info']:
            st.write(f"**추가 고민:** {info['additional_info']}")
    
    st.markdown("### 💬 의사 상담")
    st.info("궁금한 점이나 추가로 고려하고 싶은 사항을 의사에게 물어보세요!")
    
    # 채팅 인터페이스
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # 초기 인사말
        initial_msg = f"""안녕하세요, {st.session_state.patient_info['name']} 님! 
        
저는 성동구 상권 전문의입니다. 접수하신 내용을 확인했습니다.

{st.session_state.patient_info['business_type']} 창업을 희망하시고, 
{', '.join(st.session_state.patient_info['target_area'])} 지역에 관심이 있으시군요.

더 정확한 진단을 위해 몇 가지 질문드리겠습니다. 편하게 답변해주세요!"""
        st.session_state.messages.append({"role": "assistant", "content": initial_msg})
    
    # 대화 내역 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 사용자 입력
    if prompt := st.chat_input("의사에게 질문하기..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # AI 응답 생성
        try:
            context = f"""
            환자 정보:
            - 이름: {st.session_state.patient_info['name']}
            - 희망 업종: {st.session_state.patient_info['business_type']}
            - 예산: {st.session_state.patient_info['budget']}
            - 경험: {st.session_state.patient_info['experience']}
            - 관심 지역: {', '.join(st.session_state.patient_info['target_area'])}
            - 추가 고민: {st.session_state.patient_info['additional_info']}
            
            {SYSTEM_PROMPT}
            
            환자의 질문에 전문의 입장에서 답변하세요: {prompt}
            """
            
            response = model.generate_content(context)
            answer = response.text
            
            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)
        except Exception as e:
            st.error(f"오류: {str(e)}")
    
    # 처방전 발급 버튼
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col1:
        st.info("💊 상담이 충분히 이루어졌다면 처방전을 발급받으세요!")
    with col2:
        if st.button("📋 처방전 발급", type="primary", use_container_width=True):
            with st.spinner("처방전 작성 중..."):
                # 최종 처방전 생성
                try:
                    prescription_prompt = f"""
                    {SYSTEM_PROMPT}
                    
                    다음 환자 정보를 바탕으로 상세한 처방전을 작성하세요:
                    
                    환자 정보:
                    - 이름: {st.session_state.patient_info['name']}
                    - 희망 업종: {st.session_state.patient_info['business_type']}
                    - 예산: {st.session_state.patient_info['budget']}
                    - 경험: {st.session_state.patient_info['experience']}
                    - 관심 지역: {', '.join(st.session_state.patient_info['target_area'])}
                    
                    진료 내용 요약:
                    {chr(10).join([f"- {msg['content'][:100]}" for msg in st.session_state.messages[-5:]])}
                    
                    다음 형식으로 처방전을 작성하세요:
                    
                    ## 📊 진단 결과
                    [환자의 상황과 시장 분석 요약]
                    
                    ## 💊 처방 내용
                    ### 1순위 추천
                    - 상권: [구체적 위치]
                    - 업종: [세부 업종]
                    - 예상 투자비: [금액]
                    - 추천 이유: [데이터 기반 근거]
                    
                    ### 2순위 추천
                    [동일 형식]
                    
                    ## ⚠️ 주의사항
                    [리스크 요인 및 유의점]
                    
                    ## 📌 처방전 복약 지도
                    [실행 단계 및 팁]
                    """
                    
                    prescription = model.generate_content(prescription_prompt)
                    st.session_state.prescription = prescription.text
                    st.session_state.step = "처방전"
                    st.rerun()
                except Exception as e:
                    st.error(f"처방전 생성 오류: {str(e)}")

# 3단계: 처방전
elif st.session_state.step == "처방전":
    st.header("📋 처방전")
    
    # 처방전 헤더
    st.markdown(f"""
    <div style='border: 2px solid #667eea; padding: 1.5rem; border-radius: 10px; background-color: #f8f9ff; margin-bottom: 2rem;'>
        <h3 style='margin: 0; color: #667eea;'>🏥 성동구 상권 처방 클리닉</h3>
        <p style='margin: 0.5rem 0 0 0;'>발급일: {st.session_state.patient_info['date']}</p>
        <p style='margin: 0.3rem 0 0 0;'>환자명: {st.session_state.patient_info['name']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 처방 내용
    st.markdown(st.session_state.prescription)
    
    # 하단 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 다시 접수하기", use_container_width=True):
            st.session_state.step = "접수"
            st.session_state.patient_info = {}
            st.session_state.messages = []
            st.session_state.diagnosis = ""
            st.session_state.prescription = ""
            st.rerun()
    
    with col2:
        if st.button("📥 처방전 다운로드", use_container_width=True):
            st.download_button(
                label="💾 텍스트 파일로 저장",
                data=st.session_state.prescription,
                file_name=f"상권처방전_{st.session_state.patient_info['name']}_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    with col3:
        st.info("💡 처방전을 저장하여 창업 계획에 활용하세요!")

# 사이드바
with st.sidebar:
    st.markdown("### 🏥 클리닉 안내")
    st.markdown("""
    **진료 과목**
    - 상권 분석과
    - 창업 컨설팅과
    - 입지 전략과
    
    **진료 시간**
    - 24시간 운영
    - 예약 없이 방문 가능
    """)
    
    st.markdown("---")
    st.markdown("### 📊 데이터 기반")
    st.markdown("신한카드 빅데이터를 활용한 과학적 진단")
    
    if st.session_state.step != "접수":
        if st.button("🏠 처음으로", use_container_width=True):
            st.session_state.step = "접수"
            st.session_state.patient_info = {}
            st.session_state.messages = []
            st.rerun()
