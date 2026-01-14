import streamlit as st
import pandas as pd
import time
import random
from datetime import datetime

# --- 1. 페이지 및 스타일 설정 ---
st.set_page_config(
    page_title="Click Insight Hub (Pro)",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 기존 CSS 부분을 이걸로 교체하세요
st.markdown("""
    <style>
    /* 전체 배경 */
    .main {background-color: #f8f9fa;}
    
    /* 사이드바 배경 및 폰트 색상 강제 지정 */
    section[data-testid="stSidebar"] {
        background-color: #2c3e50;
    }
    section[data-testid="stSidebar"] * {
        color: white !important; /* 모든 하위 요소 글자색 흰색 고정 */
    }
    
    /* 버튼 스타일 */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        height: 3em;
    }
    </style>
    """, unsafe_allow_html=True)
    
    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] {
        background-color: #2c3e50;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 세션 스테이트 초기화 (인터랙션용) ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'db_data' not in st.session_state:
    st.session_state.db_data = []

# --- 3. 사이드바 메뉴 ---
with st.sidebar:
    st.markdown("## 💠 Click Insight Hub")
    st.caption("Enterprise HR Data Platform")
    st.markdown("---")
    
    menu = st.radio("MAIN MODULES", [
        "1. 질문은행 (Question Bank)",
        "2. 데이터 수집/표준화 (ETL)",
        "3. AI 분석 인사이트 (Analytics)",
        "4. 리포트 센터 (Reporting)"
    ])
    
    st.markdown("---")
    # 로그인 정보 시뮬레이션
    with st.container():
        st.write("👤 **Administrator**")
        st.caption("Access Level: Lv.1 (Master)")
        st.caption(f"Last Login: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# --- 메인 헤더 영역 ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title(menu.split("(")[0])
    st.markdown(f"**현재 모듈:** {menu}")
with col_h2:
    # 시스템 상태 표시
    st.success("🟢 System Online")

st.markdown("---")

# ==============================================================================
# [MODULE 1] 질문은행 (쇼핑하듯 담기 기능 구현)
# ==============================================================================
if "1." in menu:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📚 표준 문항 라이브러리")
        st.info("검증된 표준 문항을 선택하여 설문지를 구성하세요. (AI 중복 검사 완료됨)")
        
        # 탭으로 카테고리 분류
        tab1, tab2 = st.tabs(["🔴 리더십 역량", "🔵 조직 만족도"])
        
        with tab1:
            # 데이터 에디터로 체크박스 구현 (더 깔끔함)
            q_data = pd.DataFrame([
                {"선택": False, "영역": "전략", "문항": "리더는 우리 팀의 비전과 목표를 명확히 제시합니까?", "ID": "L-001"},
                {"선택": False, "영역": "소통", "문항": "리더는 팀원의 의견을 경청하고 피드백을 수용합니까?", "ID": "L-002"},
                {"선택": False, "영역": "육성", "문항": "리더는 팀원의 성장과 경력 개발을 지원합니까?", "ID": "L-003"},
                {"선택": False, "영역": "공정", "문항": "리더는 업무 배분과 평가를 공정하게 수행합니까?", "ID": "L-004"},
                {"선택": False, "영역": "실행", "문항": "리더는 목표 달성을 위해 주도적으로 업무를 추진합니까?", "ID": "L-005"},
            ])
            edited_df = st.data_editor(
                q_data, 
                column_config={"선택": st.column_config.CheckboxColumn(required=True)}, 
                hide_index=True, 
                use_container_width=True
            )
            
    with col2:
        st.subheader("🛒 문항 장바구니")
        # 선택된 문항 계산
        selected_rows = edited_df[edited_df["선택"] == True]
        count = len(selected_rows)
        
        with st.container(border=True):
            st.metric("선택된 문항 수", f"{count}개")
            if count > 0:
                st.write("선택 목록:")
                for idx, row in selected_rows.iterrows():
                    st.text(f"- {row['문항'][:15]}...")
            else:
                st.caption("좌측 리스트에서 문항을 선택하세요.")
            
            st.markdown("---")
            st.text_input("설문지 제목", value="2026 상반기 리더십 진단")
            
            if st.button("🚀 Google Forms 생성", type="primary", disabled=(count==0)):
                with st.spinner("Google API 연동 중..."):
                    time.sleep(1.5)
                st.toast("설문지 생성이 완료되었습니다!", icon="✅")
                st.success(f"**[링크 생성 완료]** forms.google.com/v/leadership_2026")

# ==============================================================================
# [MODULE 2] 데이터 수집 및 표준화 (핵심: 마스킹 시각화)
# ==============================================================================
elif "2." in menu:
    st.info("💡 **핵심 기능:** 파편화된 구글 시트를 업로드하면, AI가 개인정보와 고유명사를 **자동으로 치환(Masking)**하여 표준화합니다.")
    
    # 1. 업로드 섹션
    with st.expander("📤 데이터 불러오기 (Google Sheets)", expanded=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            url = st.text_input("구글 시트 URL 입력", placeholder="https://docs.google.com/spreadsheets/...")
        with c2:
            st.write("") # 여백
            st.write("") 
            load_btn = st.button("데이터 로드 및 분석", type="primary")
            
    if load_btn:
        # 가짜 로딩 애니메이션
        with st.status("데이터 파이프라인 가동 중...", expanded=True) as status:
            st.write("1. 구글 시트 연결 중... (API)")
            time.sleep(0.5)
            st.write("2. 컬럼 헤더 자동 매핑 중...")
            time.sleep(0.5)
            st.write("3. 자연어 처리(NLP)를 통한 변수 치환(Masking) 중...")
            time.sleep(1)
            status.update(label="전처리 완료!", state="complete", expanded=False)
            
        st.divider()
        
        # 2. 전처리 결과 비교 (Before & After) - 이 부분이 중요!
        st.subheader("🔍 데이터 표준화 결과 (Before vs After)")
        
        # 시뮬레이션 데이터
        comparison_data = [
            {
                "상태": "✅ 변환", 
                "원본 문항 (User Input)": "이번 **신임팀장과정**은 만족스러웠나요?", 
                "표준화 문항 (DB Stored)": "이번 **{{COURSE}}**은 만족스러웠나요?", 
                "비고": "과정명 자동 치환"
            },
            {
                "상태": "✅ 변환", 
                "원본 문항 (User Input)": "**김철수 강사님**의 강의는 어땠습니까?", 
                "표준화 문항 (DB Stored)": "**{{INSTRUCTOR}}**의 강의는 어땠습니까?", 
                "비고": "강사명 자동 치환"
            },
            {
                "상태": "🆕 신규", 
                "원본 문항 (User Input)": "연수원 식당 밥맛은 어땠나요?", 
                "표준화 문항 (DB Stored)": "연수원 식당 밥맛은 어땠나요?", 
                "비고": "DB에 없는 문항 (자동 추가)"
            }
        ]
        
        st.dataframe(
            pd.DataFrame(comparison_data), 
            use_container_width=True,
            column_config={
                "상태": st.column_config.TextColumn("Status", width="small"),
                "원본 문항 (User Input)": st.column_config.TextColumn("원본 데이터", width="large"),
                "표준화 문항 (DB Stored)": st.column_config.TextColumn("표준화 데이터 (DB적재용)", width="large"),
            }
        )
        
        btn_col1, btn_col2 = st.columns([1,4])
        with btn_col1:
            if st.button("최종 승인 및 DB 저장"):
                st.balloons()
                st.success("BigQuery 데이터베이스에 152건의 데이터가 안전하게 저장되었습니다.")

# ==============================================================================
# [MODULE 3] AI 분석 (차트 + 채팅 UI)
# ==============================================================================
elif "3." in menu:
    # 탭으로 정량/정성 분석 분리
    tab_quant, tab_qual = st.tabs(["📊 정량 데이터 분석", "💬 정성 데이터(AI) 분석"])
    
    with tab_quant:
        # 지표 카드
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("총 응답자", "1,240명", "+12%")
        m2.metric("평균 만족도", "4.5 / 5.0", "+0.2")
        m3.metric("NPS (추천의향)", "72점", "Excellent")
        m4.metric("응답률", "94%", "+2%")
        
        st.write("")
        
        # 차트 영역
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 📌 과정별 만족도 비교")
            chart_data = pd.DataFrame({
                "과정명": ["신임팀장", "승진자", "핵심가치", "DT교육"],
                "만족도": [4.8, 4.2, 4.5, 3.9],
                "목표치": [4.5, 4.5, 4.5, 4.5]
            })
            st.bar_chart(chart_data, x="과정명", y=["만족도", "목표치"], color=["#4e73df", "#eaecf4"])
            
        with c2:
            st.markdown("##### 📌 항목별 상세 점수")
            df_detail = pd.DataFrame({
                "항목": ["강사 전문성", "교육 내용", "운영 원활성", "환경/시설"],
                "점수": [4.9, 4.5, 4.2, 3.8]
            })
            st.dataframe(df_detail, use_container_width=True, hide_index=True)

    with tab_qual:
        st.markdown("""
        <div style="background-color:#e8f4f8; padding:15px; border-radius:10px; margin-bottom:15px;">
        🤖 <b>Gemini AI Analysis</b><br>
        수백 개의 주관식 코멘트를 AI가 읽고, 긍정/부정/제언 사항으로 자동 분류합니다.
        </div>
        """, unsafe_allow_html=True)
        
        col_chat, col_result = st.columns([1, 2])
        
        with col_chat:
            st.write("Analyzing...")
            with st.chat_message("user"):
                st.write("이번 과정의 주관식 피드백을 요약해줘.")
            with st.chat_message("ai", avatar="🤖"):
                st.write("네, 총 152건의 데이터를 분석했습니다.")
                st.write("주요 키워드는 **#실무적용**, **#시간부족** 입니다.")
        
        with col_result:
            st.subheader("📝 AI 핵심 요약 리포트")
            with st.expander("1. 긍정 피드백 (Positive)", expanded=True):
                st.markdown("- **현업 적용성:** 배운 툴을 당장 내일 쓸 수 있어서 좋았다는 평이 지배적 (45건)")
                st.markdown("- **강사 열정:** 강사님의 사례 중심 설명이 이해를 도왔음 (30건)")
            
            with st.expander("2. 개선 요청 (Negative)", expanded=True):
                st.markdown("- **시간 부족:** 실습 시간이 턱없이 부족했다는 의견이 많음. (20건)")
                st.markdown("- **시설 문제:** 오후에 에어컨 소음 때문에 집중하기 어려웠음. (5건)")
            
            st.info("💡 **AI 제언:** 차기 차수에는 실습 시간을 2시간 더 배정하는 커리큘럼 조정이 필요합니다.")

# ==============================================================================
# [MODULE 4] 보고서 (미리보기 UI 개선)
# ==============================================================================
elif "4." in menu:
    col_opt, col_preview = st.columns([1, 2])
    
    with col_opt:
        st.subheader("⚙️ 보고서 설정")
        with st.container(border=True):
            st.selectbox("프로젝트 선택", ["2026 신임팀장 과정", "2025 전사 조직진단"])
            st.radio("포맷 선택", ["PDF (상세보고용)", "PPT (발표용)", "Excel (Raw Data)"])
            st.checkbox("AI 요약 포함", value=True)
            st.checkbox("부서별 비교 장표 포함", value=True)
            
            st.write("")
            if st.button("보고서 생성 및 다운로드", type="primary"):
                with st.spinner("문서 렌더링 중..."):
                    time.sleep(2)
                st.success("다운로드 준비 완료!")
    
    with col_preview:
        st.subheader("📄 미리보기")
        # HTML과 CSS로 문서를 흉내낸 박스 생성
        st.markdown("""
        <div style="border:1px solid #ddd; padding:40px; background-color:white; height:500px; box-shadow: 5px 5px 15px rgba(0,0,0,0.1);">
            <div style="text-align:center; border-bottom:2px solid #333; padding-bottom:20px; margin-bottom:20px;">
                <h2 style="color:#000;">2026 신임팀장 리더십 진단 결과보고</h2>
                <p style="color:#666;">2026.01.15 | HRD팀</p>
            </div>
            <h4>1. Executive Summary</h4>
            <p style="font-size:14px; color:#555; line-height:1.6;">
                본 과정의 종합 만족도는 <b>4.5점</b>으로 전년 대비 <b>0.2점 상승</b>하였습니다.<br>
                특히 '강사 전문성' 영역이 4.9점으로 가장 높았으며, 참여자들은 실무 적용성에 높은 점수를 주었습니다.<br>
                다만, 실습 시간 부족에 대한 개선 요구가 식별되었습니다.
            </p>
            <br>
            <h4>2. 주요 지표 (KPI)</h4>
            <div style="display:flex; justify-content:space-around; background:#f0f2f6; padding:15px; border-radius:5px;">
                <div style="text-align:center;"><b>만족도</b><br><span style="color:blue; font-size:20px;">4.5</span></div>
                <div style="text-align:center;"><b>NPS</b><br><span style="color:green; font-size:20px;">72</span></div>
                <div style="text-align:center;"><b>수료율</b><br><span style="color:black; font-size:20px;">98%</span></div>
            </div>
            <br>
            <p style="text-align:center; color:#999; margin-top:50px;">- Click Insight Hub Generated Report -</p>
        </div>
        """, unsafe_allow_html=True)
