import streamlit as st
import pandas as pd
import time
import random
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(
    page_title="Click Insight Hub (HR 진단 통합 시스템)",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 스타일 커스텀 (기업용 대시보드 느낌) ---
st.markdown("""
    <style>
    .main {background-color: #f8f9fa;}
    .block-container {padding-top: 2rem;}
    .stButton>button {width: 100%; border-radius: 5px; font-weight: 600;}
    .success-box {padding: 1rem; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 1rem;}
    </style>
    """, unsafe_allow_html=True)

# --- 사이드바: 4단계 프로세스 메뉴 ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2920/2920349.png", width=60) # 로고
    st.title("Click Insight Hub")
    st.caption("HR Consulting Data Platform")
    
    st.markdown("---")
    menu = st.radio("프로세스 단계 선택", [
        "1. 문항 구성 (Question Bank)",
        "2. 데이터 수집 (Data Collection)",
        "3. 데이터 분석 (AI Analysis)",
        "4. 보고서 작성 (Reporting)"
    ])
    
    st.markdown("---")
    st.info(f"System Status: Online\nDB Connection: BigQuery ✅\nAI Engine: Gemini Pro ⚡")

# --- [1단계] 문항 구성 (Deliverable: 문항 DB, 구글폼 생성) ---
if menu == "1. 문항 구성 (Question Bank)":
    st.header("1️⃣ 설문/진단 문항 구성")
    st.markdown("**목표:** 표준 문항 DB(BigQuery)에서 질문을 선택하여 구글 폼을 자동 생성합니다.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🛒 클릭 공용 문항 Pool (질문은행)")
        # 탭으로 카테고리 구분
        tab1, tab2, tab3 = st.tabs(["리더십 진단", "만족도 조사", "조직문화"])
        
        with tab1:
            st.markdown("##### 리더십 역량 진단 표준 문항")
            q_list = [
                "[전략] 리더는 우리 팀의 비전과 목표를 명확히 제시합니까?",
                "[소통] 리더는 팀원의 의견을 경청하고 피드백을 수용합니까?",
                "[육성] 리더는 팀원의 성장과 경력 개발을 지원합니까?",
                "[공정] 리더는 업무 배분과 평가를 공정하게 수행합니까?",
                "[윤리] 리더는 윤리 규범을 준수하고 솔선수범합니까?"
            ]
            selected_qs = []
            for q in q_list:
                if st.checkbox(q):
                    selected_qs.append(q)
                    
    with col2:
        st.subheader("⚙️ 설문지 생성 설정")
        with st.container(border=True):
            st.text_input("설문지 제목", value="2026년 상반기 팀장 리더십 진단")
            st.date_input("진단 종료일")
            st.selectbox("대상 변수 치환 설정", ["사용 안함", "{{NAME}} → 피진단자명", "{{TEAM}} → 부서명"])
            
            st.markdown(f"**선택된 문항 수:** {len(selected_qs)}개")
            
            if st.button("🚀 구글 폼 생성하기 (Google Forms API)", type="primary"):
                with st.spinner("Google Forms API와 통신 중..."):
                    time.sleep(2) # 로딩 시뮬레이션
                st.success("설문지가 생성되었습니다!")
                st.markdown(f"**생성된 링크:** [https://forms.google.com/view/leadership_2026](len)")
                st.info("클릭하면 구글 폼 미리보기로 이동합니다.")

# --- [2단계] 데이터 수집 (Deliverable: 데이터 업로드 Form, 통합 DB) ---
elif menu == "2. 데이터 수집 (Data Collection)":
    st.header("2️⃣ 데이터 수집 및 표준화")
    st.markdown("**목표:** 파편화된 구글 시트 데이터를 가져와 표준 포맷으로 변환 후 통합 DB에 적재합니다.")
    
    st.subheader("📤 설문 결과 데이터 업로드")
    
    with st.form("upload_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            client = st.text_input("고객사명", placeholder="ex) 삼성전자")
        with c2:
            course = st.text_input("과정/진단명", placeholder="ex) 신임 임원 과정")
        with c3:
            instructor = st.text_input("강사명 (필요시)", placeholder="ex) 홍길동")
            
        url = st.text_input("구글 시트 URL (편집 권한 필요)", placeholder="https://docs.google.com/spreadsheets/d/...")
        
        # 전처리 옵션 시각화
        st.caption("✅ **자동 전처리 적용:** 1.컬럼 매핑, 2.개인정보 비식별화, 3.과정명/강사명 변수({{VAR}}) 치환")
        
        submit = st.form_submit_button("데이터 가져오기 및 DB 적재")
        
    if submit and url:
        # 프로세스 시각화
        progress_text = "작업 진행 중..."
        my_bar = st.progress(0, text=progress_text)

        for percent_complete in range(100):
            time.sleep(0.02)
            if percent_complete == 20:
                my_bar.progress(percent_complete, text="구글 시트 데이터 로드 중...")
            elif percent_complete == 50:
                my_bar.progress(percent_complete, text="컬럼 표준화 및 변수 치환(Masking) 중...")
            elif percent_complete == 80:
                my_bar.progress(percent_complete, text="BigQuery 통합 테이블에 적재 중...")
            else:
                my_bar.progress(percent_complete, text=progress_text)
                
        time.sleep(0.5)
        st.success(f"**[{client}] {course}** 데이터 45건이 통합 DB에 성공적으로 저장되었습니다.")
        
        # 결과 미리보기 (가상의 데이터프레임)
        st.subheader("📊 적재 데이터 미리보기 (BigQuery)")
        df_mock = pd.DataFrame({
            "project_id": ["P-2026-001"]*3,
            "q_standard": ["{{COURSE}} 내용 만족도", "{{INSTRUCTOR}} 강의 전달력", "교육장 환경 만족도"],
            "response_avg": [4.8, 4.9, 4.2],
            "upload_date": [datetime.now().strftime("%Y-%m-%d")]*3
        })
        st.dataframe(df_mock, use_container_width=True)

# --- [3단계] 데이터 분석 (Deliverable: 정성 데이터 AI 분석, 개별 조회) ---
elif menu == "3. 데이터 분석 (AI Analysis)":
    st.header("3️⃣ 데이터 분석 (Gemini AI)")
    st.markdown("**목표:** 정량 데이터는 자동 통계 처리하고, 정성(주관식) 데이터는 Gemini가 분석합니다.")
    
    # 상단: 프로젝트 선택
    option = st.selectbox("분석할 프로젝트 선택", ["2026 A사 신임팀장 과정", "2025 B사 전사 조직진단", "2025 C사 임원 코칭"])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 정량 평가 분석 (Automated)")
        # 차트 시뮬레이션
        chart_data = pd.DataFrame({
            '항목': ['전략제시', '의사소통', '조직관리', '성과관리', '자기개발'],
            '점수': [4.2, 3.8, 4.5, 3.9, 4.1],
            '업계평균': [4.0, 4.0, 4.2, 3.8, 4.0]
        })
        st.bar_chart(chart_data.set_index('항목'))
        st.info("💡 '의사소통' 항목이 업계 평균 대비 0.2점 낮습니다.")

    with col2:
        st.subheader("🧠 정성 평가 AI 요약 (Gemini)")
        
        # AI 분석 로딩 효과
        with st.chat_message("ai", avatar="🤖"):
            st.write("주관식 응답 150건을 분석 중입니다...")
            time.sleep(1.5)
            st.markdown(f"""
            **[{option}] 주관식 핵심 요약**
            
            **1. 긍정 키워드 (Positive):**
            * **#실무적용:** 현업에 바로 쓸 수 있는 툴 제공이 좋았음.
            * **#강사전문성:** 강사님의 풍부한 사례 공유가 인상적임.
            
            **2. 개선 요청 (Negative):**
            * **#시간부족:** 실습 시간이 너무 짧아 아쉬움 (20건).
            * **#환경:** 교육장 환기가 잘 안 됨.
            
            **3. AI 제언:**
            차기 과정 설계 시 **실습 시간을 1시간 이상 추가**하고, 교육장 시설 점검이 필요합니다.
            """)

    st.markdown("---")
    with st.expander("🔍 개별 결과 조회 (Drill-down)"):
        st.write("특정 참가자나 부서별 상세 데이터를 조회합니다.")
        st.dataframe(pd.DataFrame({"부서":["영업팀","인사팀"], "성명":["김**","이**"], "평균점수":[4.5, 3.8]}), use_container_width=True)

# --- [4단계] 보고서 작성 (Deliverable: PDF 생성, 표준 양식) ---
elif menu == "4. 보고서 작성 (Reporting)":
    st.header("4️⃣ 결과 보고서 생성")
    st.markdown("**목표:** 분석된 데이터를 바탕으로 표준화된 '클릭 컨설팅'만의 보고서를 자동 생성합니다.")
    
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("📄 보고서 옵션 설정")
        rpt_type = st.selectbox("보고서 유형", ["과정 결과보고서 (PPT)", "진단 결과보고서 (PDF)", "개인별 피드백 리포트 (PDF)"])
        include_raw = st.checkbox("Raw Data 첨부", value=True)
        include_ai = st.checkbox("AI 분석 코멘트 포함", value=True)
        
    with c2:
        st.subheader("🖨️ 생성 및 다운로드")
        st.warning("⚠️ 현재 데이터 분석이 완료된 상태입니다.")
        
        if st.button("보고서 생성 (Python-pptx/pdf 엔진)", type="primary"):
            with st.spinner("보고서 레이아웃 구성 및 데이터 바인딩 중..."):
                time.sleep(2)
            
            st.success("보고서 생성이 완료되었습니다!")
            
            # 다운로드 버튼 시뮬레이션
            st.download_button(
                label="📥 결과보고서_2026_신임팀장과정.pdf 다운로드",
                data="fake data",
                file_name="report.pdf",
                mime="application/pdf"
            )
            
    # 보고서 미리보기 이미지 (예시)
    st.markdown("---")
    st.subheader("📑 생성된 보고서 미리보기")
    st.image("https://marketplace.canva.com/EAFhHMtxcBQ/1/0/1131w/canva-blue-simple-professional-business-project-report-pLw0Fv4fKzo.jpg", 
             width=600, caption="자동 생성된 보고서 표지 및 요약 장표")
