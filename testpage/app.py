import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import time
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parents[1]))

from etl import (  # noqa: E402
    map_columns,
    mask_entities,
    split_raw_questions,
    match_questions,
    update_question_bank,
)

# --- 1. 페이지 및 스타일 설정 ---
st.set_page_config(
    page_title="Click Insight Hub (Pro)",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사용자 요청 CSS 적용 (사이드바 가독성 해결 + 모달/카드 스타일 추가)
st.markdown("""
    <style>
    /* 메인 배경 */
    .main {background-color: #f8f9fa;}
    
    /* 사이드바 스타일 강제 적용 */
    section[data-testid="stSidebar"] {
        background-color: #2c3e50;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    section[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
        background-color: transparent !important;
    }

    /* 버튼 스타일 */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        height: 3em;
        width: 100%;
    }
    
    /* 카드 스타일 (React UI 느낌) */
    .custom-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    
    /* 상태 뱃지 스타일 */
    .badge-new { background-color: #fff7ed; color: #c2410c; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; border: 1px solid #ffedd5; }
    .badge-exist { background-color: #f1f5f9; color: #475569; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; border: 1px solid #e2e8f0; }
    .badge-sim { background-color: #fef9c3; color: #854d0e; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; border: 1px solid #fef08a; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 세션 스테이트 초기화 ---
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'survey_info' not in st.session_state:
    st.session_state.survey_info = []
if 'responses' not in st.session_state:
    st.session_state.responses = pd.DataFrame(
        columns=["survey_id", "respondent_id", "question_id", "answer_value"]
    )
if 'question_bank' not in st.session_state:
    st.session_state.question_bank = [
        {
            "question_id": "QB-001",
            "question_text": "{{COURSE}} 과정의 난이도는 적절했나요?",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "merged_count": 0,
        },
        {
            "question_id": "QB-002",
            "question_text": "{{INSTRUCTOR}} 강사의 전문성은 어떠했나요?",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "merged_count": 0,
        },
        {
            "question_id": "QB-003",
            "question_text": "강의장은 쾌적했나요?",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "merged_count": 0,
        },
        {
            "question_id": "QB-004",
            "question_text": "교육 내용은 실무에 도움이 되나요?",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "merged_count": 0,
        },
        {
            "question_id": "QB-005",
            "question_text": "향후 추천할 의향이 있나요?",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "merged_count": 0,
        },
        {
            "question_id": "QB-006",
            "question_text": "교육 시간 배분은 적절했나요?",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "merged_count": 0,
        },
    ]
if 'last_etl_results' not in st.session_state:
    st.session_state.last_etl_results = []

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
    with st.container():
        st.write("👤 Administrator")
        st.caption("Access Level: Lv.1 (Master)")
        st.caption(f"Last Login: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# --- 메인 헤더 ---
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.title(menu.split("(")[0])
    st.caption(f"Current Module: {menu}")
with col_h2:
    st.success("🟢 System Online")
st.divider()

# ==============================================================================
# [MODULE 1] 질문은행 (React의 장바구니 기능 반영)
# ==============================================================================
if "1." in menu:
    col1, col2 = st.columns([2, 1])
    survey_meta_container = st.container()
    
    with col1:
        st.subheader("📚 표준 문항 라이브러리")
        st.info("검증된 표준 문항을 선택하여 설문지를 구성하세요.")
        
        tab1, tab2 = st.tabs(["🔴 리더십 역량", "🔵 조직 만족도"])
        
        with tab1:
            q_data = pd.DataFrame([
                {"선택": False, "카테고리": "전략", "문항": "{{COURSE}} 과정의 난이도는 적절했나요?", "ID": "L-001"},
                {"선택": False, "카테고리": "소통", "문항": "{{INSTRUCTOR}} 강사의 전문성은 어떠했나요?", "ID": "L-002"},
                {"선택": False, "카테고리": "운영", "문항": "강의장은 쾌적했나요?", "ID": "L-003"},
                {"선택": False, "카테고리": "성과", "문항": "교육 내용은 실무에 도움이 되나요?", "ID": "L-004"},
                {"선택": False, "카테고리": "NPS", "문항": "향후 추천할 의향이 있나요?", "ID": "L-005"},
            ])
            edited_df = st.data_editor(
                q_data, 
                column_config={
                    "선택": st.column_config.CheckboxColumn(required=True),
                    "문항": st.column_config.TextColumn(width="large")
                }, 
                hide_index=True, 
                use_container_width=True
            )
            
    with col2:
        st.subheader("🛒 문항 장바구니")
        # 선택된 문항 계산
        selected_rows = edited_df[edited_df["선택"] == True]
        count = len(selected_rows)
        
        with st.container(border=True):
            st.markdown(f"선택된 문항: <span style='color:#4f46e5; font-size:1.2em; font-weight:bold;'>{count}개</span>", unsafe_allow_html=True)
            
            if count > 0:
                st.divider()
                for idx, row in selected_rows.iterrows():
                    st.text(f"• {row['카테고리']}: {row['문항'][:15]}...")
            
            st.divider()
            form_title = st.text_input("설문지 제목", value="3월 신입사원 교육 만족도 조사")
            
            if st.button("🚀 Google Form 생성", type="primary", disabled=(count==0)):
                with st.spinner("Google API 연동 중..."):
                    time.sleep(1.5)
                survey_id = f"SUR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{count}"
                st.session_state.survey_info.append({
                    "survey_id": survey_id,
                    "title": form_title,
                    "question_count": count,
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                st.toast("설문지가 생성되었습니다!", icon="✅")
                st.success(f"[링크 생성 완료]\n\nforms.google.com/v/simulation_1234")
                st.success(f"발급된 설문 ID: {survey_id}")

    with survey_meta_container:
        st.subheader("🗂️ 설문 메타데이터 저장소 (survey_info)")
        if st.session_state.survey_info:
            st.dataframe(pd.DataFrame(st.session_state.survey_info), use_container_width=True, hide_index=True)
        else:
            st.caption("아직 생성된 설문이 없습니다. 설문을 생성하면 메타데이터가 저장됩니다.")

# ==============================================================================
# [MODULE 2] 데이터 수집/표준화 (React UI 로직 이식)
# ==============================================================================
elif "2." in menu:
    st.info("💡 핵심 기능: 입력된 자연어를 AI가 분석하여 '변수(과정명, 강사명)'를 치환하고 중복 문항을 걸러냅니다.")

    col_input, col_preview = st.columns([1.5, 1])

    with col_input:
        st.markdown("### 1. 데이터 입력 및 설정")
        with st.container(border=True):
            st.markdown("#### 🔄 응답 데이터 적재 (responses)")
            if st.session_state.survey_info:
                survey_id_options = [s["survey_id"] for s in st.session_state.survey_info]
                selected_survey_id = st.selectbox("survey_id 선택", survey_id_options)
            else:
                selected_survey_id = None
                st.warning("먼저 Module 1에서 설문을 생성해 survey_id를 발급하세요.")

            st.markdown("**파일 업로드 (CSV)**")
            uploaded_file = st.file_uploader(
                "CSV 업로드",
                type=["csv"],
                help="필수 컬럼: survey_id, respondent_id, question_id, answer_value"
            )
            if uploaded_file is not None:
                incoming = pd.read_csv(uploaded_file)
                mapped = map_columns(incoming)
                required_cols = {"survey_id", "respondent_id", "question_id", "answer_value"}
                missing = required_cols.difference(mapped.columns)
                mapping_rows = [
                    {
                        "원본 컬럼": col,
                        "표준 컬럼": mapped.columns[idx],
                    }
                    for idx, col in enumerate(incoming.columns)
                ]
                if missing:
                    st.error(f"필수 컬럼 누락: {', '.join(sorted(missing))}")
                else:
                    st.session_state.responses = pd.concat(
                        [st.session_state.responses, mapped],
                        ignore_index=True
                    )
                    st.success(f"{len(incoming)}건의 응답이 responses에 적재되었습니다.")
                    with st.expander("표준 컬럼 매핑 결과", expanded=False):
                        st.dataframe(pd.DataFrame(mapping_rows), use_container_width=True, hide_index=True)

            st.markdown("**Sheets 연결 (시뮬레이션)**")
            sheets_url = st.text_input("Google Sheets URL", placeholder="https://docs.google.com/spreadsheets/...")
            if st.button("Sheets 연결 및 적재", disabled=(selected_survey_id is None)):
                simulated = pd.DataFrame([
                    {
                        "survey_id": selected_survey_id,
                        "respondent_id": "R-001",
                        "question_id": "L-001",
                        "answer_value": 5
                    },
                    {
                        "survey_id": selected_survey_id,
                        "respondent_id": "R-002",
                        "question_id": "L-002",
                        "answer_value": 4
                    }
                ])
                st.session_state.responses = pd.concat(
                    [st.session_state.responses, simulated],
                    ignore_index=True
                )
                st.success("Sheets 연결 완료: 2건의 샘플 응답이 적재되었습니다.")

            if not st.session_state.responses.empty:
                st.markdown("**현재 responses 데이터**")
                st.dataframe(st.session_state.responses, use_container_width=True, hide_index=True)

            # React 앱의 변수 설정 부분 반영
            c1, c2 = st.columns(2)
            with c1:
                course_name = st.text_input("과정명 (Variable A)", value="신임팀장과정")
            with c2:
                instructor_name = st.text_input("강사명 (Variable B)", value="김철수")
            
            raw_text = st.text_area(
                "원시 데이터 (Raw Data from Excel)", 
                height=200,
                value="""1. 신임팀장과정 과정에 대해 만족하십니까?
Q2) 김철수 강사의 강의는 어땠나요?
3. 강의 시간은 적절했나요?
4. 식사는 맛있었나요?"""
            )
            
            analyze_btn = st.button("데이터 분석 및 전처리 실행 (Analyze)", type="primary")

    with col_preview:
        st.markdown("### 2. 실시간 처리 로직 Preview")
        with st.container(border=True):
            st.markdown("""
            <div style="background-color:#f1f5f9; padding:10px; border-radius:5px; margin-bottom:10px;">
                <code style="color:#4f46e5; font-weight:bold;">STEP 1: Cleaning</code><br>
                <span style="font-size:12px; color:#64748b;">숫자, 특수문자, 공백 제거 (Regex)</span>
            </div>
            <div style="background-color:#f1f5f9; padding:10px; border-radius:5px; margin-bottom:10px;">
                <code style="color:#4f46e5; font-weight:bold;">STEP 2: Masking</code><br>
                <span style="font-size:12px; color:#64748b;">변수 치환 (Privacy & Standardization)</span><br>
                <span style="font-size:12px;">• {course} → <b>{{COURSE}}</b></span><br>
                <span style="font-size:12px;">• {instructor} → <b>{{INSTRUCTOR}}</b></span>
            </div>
            """, unsafe_allow_html=True)
            st.caption("※ 분석 버튼을 누르면 DB 대조 결과가 아래에 표시됩니다.")

    # 분석 결과 표시 (React의 Modal 느낌을 인라인으로 구현)
    if analyze_btn:
        with st.spinner("AI가 문항을 분석하고 DB와 대조 중입니다..."):
            time.sleep(1.5)
            raw_questions = split_raw_questions(raw_text)
            masked_questions = [
                mask_entities(q, course_name, instructor_name) for q in raw_questions
            ]
            match_results = match_questions(
                masked_questions, st.session_state.question_bank
            )
            st.session_state.last_etl_results = [
                {
                    "status": item["status"],
                    "orig": raw_questions[idx],
                    "clean": masked_questions[idx],
                    "note": (
                        f"기존 문항 일치 (유사도 {item['score']:.2f})"
                        if item["status"] == "existing"
                        else f"유사 문항 발견 (유사도 {item['score']:.2f})"
                        if item["status"] == "similar"
                        else "DB에 없는 신규 문항 (등록 필요)"
                    ),
                    "match_text": item["match_text"],
                    "match_id": item["match_id"],
                    "score": item["score"],
                }
                for idx, item in enumerate(match_results)
            ]
            st.session_state.analysis_result = True

    if st.session_state.analysis_result:
        st.divider()
        st.subheader("🔍 분석 결과 리포트 (DB Match Simulation)")
        
        results = st.session_state.last_etl_results
        
        # 결과 요약
        new_count = len([r for r in results if r['status'] == 'new'])
        total_count = len(results)
        st.warning(f"총 {total_count}개 문항 중 {new_count}개의 새로운 문항이 감지되었습니다.")

        # 리스트 뷰 (React UI 스타일)
        for item in results:
            # 상태별 스타일 정의
            if item['status'] == 'existing':
                badge = '<span class="badge-exist">기존 (Existing)</span>'
                border_color = "#e2e8f0"
                bg_color = "white"
            elif item['status'] == 'similar':
                badge = '<span class="badge-sim">유사 (Similar)</span>'
                border_color = "#fef08a"
                bg_color = "#fefce8"
            else: # new
                badge = '<span class="badge-new">신규 (New)</span>'
                border_color = "#ffedd5"
                bg_color = "#fff7ed"

            st.markdown(f"""
            <div style="border:1px solid {border_color}; background-color:{bg_color}; padding:15px; border-radius:8px; margin-bottom:10px; display:flex; align-items:center;">
                <div style="width:100px;">{badge}</div>
                <div style="flex-grow:1; margin-left:15px;">
                    <div style="font-size:12px; color:#94a3b8; text-decoration:line-through;">{item['orig']}</div>
                    <div style="font-size:15px; font-weight:600; color:#1e293b;">{item['clean']} <span style="font-size:12px; color:#4f46e5;">(Masking OK)</span></div>
                    <div style="font-size:12px; color:#64748b; margin-top:4px;">
                        {item['note']}
                        {f"<br>매칭 문항: {item['match_text']}" if item['match_text'] else ""}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        c1, c2 = st.columns([4, 1])
        with c2:
            if st.button("확인 및 DB 저장"):
                updated_bank, save_summary = update_question_bank(
                    st.session_state.question_bank, results
                )
                st.session_state.question_bank = updated_bank
                st.balloons()
                st.success(
                    f"question_bank 업데이트 완료: 신규 {save_summary['new']}건, 병합 {save_summary['merged']}건"
                )
                st.session_state.analysis_result = None # 초기화

# ==============================================================================
# [MODULE 3] AI 분석
# ==============================================================================
elif "3." in menu:
    if st.session_state.survey_info:
        survey_id_options = [s["survey_id"] for s in st.session_state.survey_info]
        selected_survey_id = st.selectbox("분석 대상 survey_id 선택", survey_id_options)
    else:
        selected_survey_id = None
        st.warning("설문 메타데이터가 없습니다. Module 1에서 설문을 생성하세요.")

    if selected_survey_id:
        filtered_responses = st.session_state.responses[
            st.session_state.responses["survey_id"] == selected_survey_id
        ]
    else:
        filtered_responses = st.session_state.responses.iloc[0:0]

    tab_quant, tab_qual = st.tabs(["📊 정량 데이터 분석", "💬 정성 데이터(AI) 분석"])
    
    with tab_quant:
        st.caption(f"응답 데이터 필터: survey_id = {selected_survey_id}")
        m1, m2, m3, m4 = st.columns(4)
        respondent_count = filtered_responses["respondent_id"].nunique()
        avg_score = (
            filtered_responses["answer_value"].astype(float).mean()
            if not filtered_responses.empty
            else 0
        )
        m1.metric("총 응답자", f"{respondent_count}명", "+12%")
        m2.metric("평균 만족도", f"{avg_score:.1f} / 5.0", "+0.2")
        m3.metric("NPS", "72점", "Excellent")
        m4.metric("응답률", "94%", "+2%")
        
        st.markdown("##### 📌 과정별 만족도 비교")
        chart_data = pd.DataFrame({
            "과정명": ["신임팀장", "승진자", "핵심가치", "DT교육"],
            "만족도": [4.8, 4.2, 4.5, 3.9],
            "목표치": [4.5, 4.5, 4.5, 4.5]
        })
        st.bar_chart(chart_data, x="과정명", y=["만족도", "목표치"], color=["#4e73df", "#eaecf4"])

    with tab_qual:
        st.info("🤖 Gemini AI Analysis: 수백 개의 주관식 코멘트를 읽고 핵심 키워드를 추출합니다.")
        
        col_chat, col_result = st.columns([1, 2])
        with col_chat:
            with st.chat_message("user"):
                st.write("이번 과정 피드백 요약해줘.")
            with st.chat_message("ai", avatar="🤖"):
                st.write("152건 분석 완료. 주요 이슈는 #실무적용과 #시간부족입니다.")
        
        with col_result:
            with st.expander("1. 긍정 피드백 (Positive)", expanded=True):
                st.write("👍 현업 적용성: 당장 쓸 수 있는 툴 제공 (45건)")
            with st.expander("2. 개선 요청 (Negative)", expanded=True):
                st.write("👎 시간 부족: 실습 시간 확대 요망 (20건)")

# ==============================================================================
# [MODULE 4] 리포트 센터
# ==============================================================================
elif "4." in menu:
    col_opt, col_preview = st.columns([1, 2])
    
    with col_opt:
        st.subheader("⚙️ 보고서 설정")
        with st.container(border=True):
            st.selectbox("프로젝트", ["2026 신임팀장 과정", "2025 전사 조직진단"])
            st.radio("포맷", ["PDF (상세)", "PPT (발표)", "Excel"])
            st.checkbox("AI 요약 포함", value=True)
            
            if st.button("다운로드", type="primary"):
                with st.spinner("생성 중..."):
                    time.sleep(1)
                st.success("다운로드 완료!")
    
    with col_preview:
        st.subheader("📄 미리보기")
        st.markdown("""
        <div style="border:1px solid #ddd; padding:40px; background-color:white; box-shadow: 5px 5px 15px rgba(0,0,0,0.1);">
            <h3 style="text-align:center;">2026 신임팀장 리더십 진단 결과</h3>
            <p style="text-align:center; color:#666;">2026.01.15 | HRD팀</p>
            <hr>
            <h4>1. Summary</h4>
            <p style="color:#555;">종합 만족도는 <b>4.5점</b>으로 전년 대비 상승했습니다.</p>
        </div>
        """, unsafe_allow_html=True)
