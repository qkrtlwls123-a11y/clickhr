import streamlit as st
import pandas as pd
import time
import random

# 페이지 설정
st.set_page_config(
    page_title="HR 진단 데이터 통합 시스템 (Demo)",
    page_icon="📊",
    layout="wide"
)

# 스타일 커스텀 (깔끔한 보고용)
st.markdown("""
    <style>
    .main {background-color: #F9F9F9;}
    .stButton>button {width: 100%; border-radius: 5px; font-weight: bold;}
    .metric-card {background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}
    </style>
    """, unsafe_allow_html=True)

# 사이드바 메뉴
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3064/3064197.png", width=50) # 로고 예시
    st.title("HR Data Hub")
    menu = st.radio("메뉴 선택", 
        ["1. 설문 데이터 등록 (Standardization)", 
         "2. 문항 기반 설문 생성 (Re-use)", 
         "3. 통합 대시보드 (Insight)"])
    st.info("※ 임원 보고용 데모 버전입니다.\n실제 데이터는 저장되지 않습니다.")

# --- [메뉴 1] 데이터 등록 및 표준화 ---
if menu == "1. 설문 데이터 등록 (Standardization)":
    st.title("📂 설문 데이터 등록 및 표준화")
    st.markdown("구글 시트의 데이터를 불러와 **표준 포맷으로 변환**하고 **문항 중복을 제거**합니다.")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("1. 프로젝트 정보")
        with st.form("input_form"):
            client = st.text_input("고객사", value="A전자")
            course = st.text_input("과정명", value="2026 신임 팀장 리더십 과정")
            instructor = st.text_input("강사명", value="김철수")
            date = st.date_input("진단 일자")
            url = st.text_input("구글 시트 URL", placeholder="https://docs.google.com/...")
            
            submit = st.form_submit_button("데이터 가져오기 및 분석 시작")

    with col2:
        if submit:
            # 1. 로딩 시뮬레이션
            with st.spinner('구글 시트 연결 중...'):
                time.sleep(1)
            st.success("✅ 구글 시트 데이터 로드 완료 (52명 응답)")
            
            # 2. 컬럼 매핑 시뮬레이션
            st.subheader("2. 데이터 컬럼 매핑 (자동 감지)")
            st.info("💡 AI가 시트의 컬럼을 분석하여 표준 필드와 매칭했습니다. 맞는지 확인해주세요.")
            
            map_df = pd.DataFrame({
                "표준 필드": ["참여자 성명", "사번/ID", "소속 부서", "직급"],
                "감지된 시트 헤더": ["이름", "사원번호", "팀명", "직위"],
                "신뢰도": ["99%", "98%", "95%", "90%"]
            })
            st.dataframe(map_df, hide_index=True, use_container_width=True)
            
            # 3. 문항 분석 및 중복 제거 (핵심 기능)
            with st.spinner('문항 텍스트 분석 및 중복 검사 중... (Natural Language Processing)'):
                time.sleep(2)
            
            st.subheader("3. 문항 표준화 및 중복 제거 결과")
            st.warning("⚠️ 총 10개 문항 중 **8개는 기존 DB에 존재**하며, **2개는 신규 문항**입니다.")
            
            # 문항 대조 시각화
            match_data = [
                {"구분": "✅ 일치 (자동병합)", "원본 문항 (Excel)": "이번 신임 팀장 리더십 과정에 만족하나요?", "표준화 문항 (DB)": "{{COURSE}} 과정에 만족하십니까?", "유사도": "98%"},
                {"구분": "✅ 일치 (자동병합)", "원본 문항 (Excel)": "김철수 강사의 강의 내용은 유익했나요?", "표준화 문항 (DB)": "{{INSTRUCTOR}} 강사의 강의 내용은 유익했습니까?", "유사도": "96%"},
                {"구분": "🆕 신규 (DB추가)", "원본 문항 (Excel)": "연수원 식당 메뉴는 입에 맞으셨나요?", "표준화 문항 (DB)": "(신규 등록 예정)", "유사도": "0%"},
            ]
            st.table(pd.DataFrame(match_data))
            
            st.button("분석 결과 확정 및 DB 저장", type="primary")

        else:
            st.info("👈 좌측 폼에 정보를 입력하고 버튼을 눌러주세요.")
            st.image("https://www.Notion.so/image/https%3A%2F%2Fs3-us-west-2.amazonaws.com%2Fsecure.notion-static.com%2F...dummy_image...", caption="데이터 흐름 예시", width=400) # (이미지 없어도 됨)


# --- [메뉴 2] 설문지 생성 ---
elif menu == "2. 문항 기반 설문 생성 (Re-use)":
    st.title("📝 표준 문항 기반 설문 생성")
    st.markdown("DB에 축적된 **표준 문항(질문은행)**을 활용하여 구글 폼을 자동으로 생성합니다.")
    
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.subheader("STEP 1. 문항 장바구니")
        # 탭으로 카테고리 구분
        tab1, tab2, tab3 = st.tabs(["만족도(공통)", "리더십 진단", "강사 평가"])
        
        with tab1:
            st.markdown("##### 공통 만족도 문항 선택")
            q1 = st.checkbox("[객관식] 전반적인 과정 운영에 만족하십니까?")
            q2 = st.checkbox("[객관식] 교육 내용은 현업 활용도가 높습니까?")
            q3 = st.checkbox("[주관식] 본 과정에서 가장 유익했던 점은 무엇입니까?")
            q4 = st.checkbox("[객관식] 교육 장소 및 환경은 쾌적했습니까?")
        
        with tab2:
            st.write("리더십 진단 문항 리스트...")
            
    with col_b:
        st.subheader("STEP 2. 설정 및 생성")
        with st.container(border=True):
            st.text_input("설문지 제목", value="2026년 3월 신입사원 교육 만족도")
            st.selectbox("대상 변수 치환", ["{{COURSE}} → 신입사원 입문과정", "{{INSTRUCTOR}} → 홍길동"])
            
            if st.button("🚀 구글 폼 자동 생성하기", type="primary"):
                with st.spinner("Google Forms API 통신 중..."):
                    time.sleep(1.5)
                st.success("생성 완료!")
                st.markdown("**생성된 링크:** [https://forms.google.com/v/12345...](len)")
                st.balloons()

# --- [메뉴 3] 대시보드 ---
elif menu == "3. 통합 대시보드 (Insight)":
    st.title("📈 HR 진단 통합 대시보드")
    st.markdown("전사 교육/진단 현황을 실시간으로 모니터링합니다.")
    
    # 상단 지표 (Metric)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("누적 진단 데이터", "12,450건", "+152건")
    m2.metric("보유 표준 문항", "342개", "+2개")
    m3.metric("평균 만족도", "4.5/5.0", "▲ 0.1")
    m4.metric("올해 진행 프로젝트", "24건")
    
    st.markdown("---")
    
    # 차트 영역
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("과정별 만족도 비교")
        # 가짜 차트 데이터
        chart_data = pd.DataFrame({
            '과정명': ['신임팀장', '신입사원', '승진자과정', '임원특강', 'DT교육'],
            '만족도': [4.8, 4.2, 3.9, 4.5, 4.1]
        })
        st.bar_chart(chart_data.set_index('과정명'))
        
    with c2:
        st.subheader("주요 키워드 (Word Cloud)")
        st.write("💬 주관식 응답 AI 요약 결과")
        # 워드클라우드 대신 칩 형태로 표현
        st.markdown("""
        <span style='background:#E1F5FE; padding:5px; border-radius:5px;'>#실무적용</span>
        <span style='background:#FFF3E0; padding:5px; border-radius:5px;'>#강사열정</span>
        <span style='background:#FFEBEE; padding:5px; border-radius:5px;'>#시간부족</span>
        <span style='background:#E8F5E9; padding:5px; border-radius:5px;'>#동기부여</span>
        """, unsafe_allow_html=True)
        st.info("최근 '시간부족' 키워드가 상승하고 있습니다. (전월 대비 +15%)")
