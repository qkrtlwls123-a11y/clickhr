import io
import streamlit as st
import pandas as pd
import re
import time
from datetime import datetime

from integrations import gemini, google_forms, reporting, storage

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
if 'analysis_payload' not in st.session_state:
    st.session_state.analysis_payload = []
if "storage_client" not in st.session_state:
    st.session_state.storage_client = storage.get_storage()
if "question_bank_df" not in st.session_state:
    st.session_state.question_bank_df = storage.seed_question_bank(st.session_state.storage_client)
if "survey_info_df" not in st.session_state:
    st.session_state.survey_info_df = st.session_state.storage_client.load_survey_info()
if "responses_df" not in st.session_state:
    st.session_state.responses_df = st.session_state.storage_client.load_responses()
if 'gemini_result' not in st.session_state:
    st.session_state.gemini_result = None
def refresh_storage_cache() -> None:
    st.session_state.question_bank_df = st.session_state.storage_client.load_question_bank()
    st.session_state.survey_info_df = st.session_state.storage_client.load_survey_info()
    st.session_state.responses_df = st.session_state.storage_client.load_responses()


def question_bank_records() -> list[dict]:
    if st.session_state.question_bank_df.empty:
        return []
    return (
        st.session_state.question_bank_df[["question_id", "text"]]
        .rename(columns={"question_id": "id"})
        .to_dict(orient="records")
    )


def normalize_text(text: str) -> str:
    text = re.sub(r"\d+", " ", text)
    text = re.sub(r"[^\w\s가-힣]", " ", text)
    text = text.replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def mask_variables(text: str, course: str, instructor: str) -> str:
    masked = text
    if course:
        masked = re.sub(re.escape(course), "{{COURSE}}", masked)
    if instructor:
        masked = re.sub(re.escape(instructor), "{{INSTRUCTOR}}", masked)
    return masked


def levenshtein_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    prev_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        curr_row = [i]
        for j, char_b in enumerate(b, start=1):
            insertions = prev_row[j] + 1
            deletions = curr_row[j - 1] + 1
            substitutions = prev_row[j - 1] + (char_a != char_b)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def similarity_ratio(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    distance = levenshtein_distance(a, b)
    max_len = max(len(a), len(b))
    return 1 - (distance / max_len) if max_len else 0.0


def find_question_match(cleaned: str, question_bank: list[dict]) -> dict:
    best_match = None
    best_score = 0.0
    for question in question_bank:
        normalized_question = normalize_text(question["text"])
        score = similarity_ratio(cleaned, normalized_question)
        if score > best_score:
            best_score = score
            best_match = question
    return {"match": best_match, "score": best_score}


def analyze_questions(raw_text: str, course: str, instructor: str, question_bank: list[dict]) -> list[dict]:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    results = []
    for line in lines:
        normalized = normalize_text(line)
        masked = mask_variables(normalized, course, instructor)
        match_info = find_question_match(masked, question_bank)
        match = match_info["match"]
        score = match_info["score"]

        if match and score >= 0.95:
            status = "existing"
            note = "기존 문항 일치 (자동 병합)"
        elif match and score >= 0.8:
            status = "similar"
            note = f"유사 문항 발견: '{match['text']}'"
        else:
            status = "new"
            note = "DB에 없는 신규 문항 (등록 필요)"

        results.append(
            {
                "status": status,
                "orig": line,
                "clean": masked,
                "note": note,
                "match_id": match["id"] if match else None,
                "score": score,
            }
        )
    return results

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
            q_data = st.session_state.question_bank_df.copy()
            if q_data.empty:
                q_data = storage.DEFAULT_QUESTION_BANK.copy()
            q_data = q_data.reindex(columns=["question_id", "category", "text"])
            q_data["category"] = q_data["category"].fillna("기타")
            q_data = q_data.rename(
                columns={
                    "question_id": "ID",
                    "text": "문항",
                    "category": "카테고리",
                }
            )
            q_data.insert(0, "선택", False)
            edited_df = st.data_editor(
                q_data,
                column_config={
                    "선택": st.column_config.CheckboxColumn(required=True),
                    "문항": st.column_config.TextColumn(width="large")
                },
                hide_index=True,
                use_container_width=True
            )
            if st.button("💾 질문은행 저장", type="secondary"):
                edited_df = edited_df.copy()
                if "ID" in edited_df.columns:
                    missing_ids = edited_df["ID"].isna() | (edited_df["ID"].astype(str).str.strip() == "")
                    if missing_ids.any():
                        base_index = len(st.session_state.question_bank_df) + 1
                        new_ids = [f"QB-{base_index + i:03d}" for i in range(missing_ids.sum())]
                        edited_df.loc[missing_ids, "ID"] = new_ids
                standardized = storage.standardize_question_bank(edited_df)
                st.session_state.storage_client.save_question_bank(standardized)
                refresh_storage_cache()
                st.toast("질문은행이 저장되었습니다.", icon="✅")
            
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
                    questions = selected_rows["문항"].tolist()
                    form_result = google_forms.create_google_form(form_title, questions)
                survey_id = form_result.get("form_id") or f"SUR-{datetime.now().strftime('%Y%m%d%H%M%S')}-{count}"
                survey_record = pd.DataFrame(
                    [
                        {
                            "survey_id": survey_id,
                            "title": form_title,
                            "question_count": count,
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "form_url": form_result.get("form_url"),
                            "status": form_result.get("status"),
                        }
                    ]
                )
                st.session_state.storage_client.append_survey_info(
                    storage.standardize_survey_info(survey_record)
                )
                refresh_storage_cache()
                st.toast("설문지가 생성되었습니다!", icon="✅")
                if form_result.get("form_url"):
                    st.success(f"[링크 생성 완료]\n\n{form_result['form_url']}")
                else:
                    st.warning("폼 링크를 가져오지 못했습니다. 상태를 확인하세요.")
                if form_result.get("message"):
                    st.caption(form_result["message"])
                st.success(f"발급된 설문 ID: {survey_id}")

    with survey_meta_container:
        st.subheader("🗂️ 설문 메타데이터 저장소 (survey_info)")
        if not st.session_state.survey_info_df.empty:
            st.dataframe(st.session_state.survey_info_df, use_container_width=True, hide_index=True)
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
            if not st.session_state.survey_info_df.empty:
                survey_id_options = st.session_state.survey_info_df["survey_id"].tolist()
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
                required_cols = {"survey_id", "respondent_id", "question_id", "answer_value"}
                missing = required_cols.difference(incoming.columns)
                if missing:
                    st.error(f"필수 컬럼 누락: {', '.join(sorted(missing))}")
                else:
                    standardized = storage.standardize_responses(incoming)
                    st.session_state.storage_client.append_responses(standardized)
                    refresh_storage_cache()
                    st.success(f\"{len(incoming)}건의 응답이 responses에 적재되었습니다.\")

            st.markdown("**Sheets 연결 (시뮬레이션)**")
            sheets_url = st.text_input("Google Sheets URL", placeholder="https://docs.google.com/spreadsheets/...")
            if st.button("Sheets 연결 및 적재", disabled=(selected_survey_id is None)):
                simulated = pd.DataFrame([
                    {
                        "survey_id": selected_survey_id,
                        "respondent_id": "R-001",
                        "question_id": "L-001",
                        "answer_value": 5,
                    },
                    {
                        "survey_id": selected_survey_id,
                        "respondent_id": "R-002",
                        "question_id": "L-002",
                        "answer_value": 4,
                    },
                ])
                st.session_state.storage_client.append_responses(
                    storage.standardize_responses(simulated)
                )
                refresh_storage_cache()
                st.success("Sheets 연결 완료: 2건의 샘플 응답이 적재되었습니다.")

            if not st.session_state.responses_df.empty:
                st.markdown("**현재 responses 데이터**")
                st.dataframe(st.session_state.responses_df, use_container_width=True, hide_index=True)

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
            st.session_state.analysis_payload = analyze_questions(
                raw_text=raw_text,
                course=course_name,
                instructor=instructor_name,
                question_bank=question_bank_records(),
            )
            st.session_state.analysis_result = True
            
    if st.session_state.analysis_result:
        st.divider()
        st.subheader("🔍 분석 결과 리포트 (DB Match Simulation)")
        
        results = st.session_state.analysis_payload
        
        # 결과 요약
        new_count = len([r for r in results if r['status'] == 'new'])
        st.warning(f"총 {len(results)}개 문항 중 {new_count}개의 새로운 문항이 감지되었습니다.")

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
                    <div style="font-size:12px; color:#64748b; margin-top:4px;">{item['note']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        c1, c2 = st.columns([4, 1])
        with c2:
            if st.button("확인 및 DB 저장"):
                new_questions = [r for r in results if r["status"] == "new"]
                if new_questions:
                    existing_count = len(st.session_state.question_bank_df)
                    new_rows = []
                    for offset, item in enumerate(new_questions):
                        new_rows.append(
                            {
                                "question_id": f"NEW-{existing_count + offset + 1:03d}",
                                "text": item["clean"],
                                "category": "신규",
                                "created_at": storage.utc_now(),
                                "updated_at": storage.utc_now(),
                            }
                        )
                    if new_rows:
                        st.session_state.storage_client.append_question_bank(pd.DataFrame(new_rows))
                        refresh_storage_cache()
                st.balloons()
                st.success("데이터베이스에 성공적으로 반영되었습니다.")
                st.session_state.analysis_result = None # 초기화

# ==============================================================================
# [MODULE 3] AI 분석
# ==============================================================================
elif "3." in menu:
    if not st.session_state.survey_info_df.empty:
        survey_id_options = st.session_state.survey_info_df["survey_id"].tolist()
        selected_survey_id = st.selectbox("분석 대상 survey_id 선택", survey_id_options)
    else:
        selected_survey_id = None
        st.warning("설문 메타데이터가 없습니다. Module 1에서 설문을 생성하세요.")

    if selected_survey_id:
        filtered_responses = st.session_state.responses_df[
            st.session_state.responses_df["survey_id"] == selected_survey_id
        ]
    else:
        filtered_responses = st.session_state.responses_df.iloc[0:0]

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
            st.markdown("**정성 코멘트 입력**")
            comment_upload = st.file_uploader("텍스트/CSV 업로드", type=["txt", "csv"])
            raw_comments = st.text_area(
                "코멘트 직접 입력",
                height=200,
                value=(
                    "현업 적용성이 높아서 좋았습니다.\n"
                    "시간이 조금 더 있었으면 합니다.\n"
                    "강사의 사례가 풍부해서 도움이 되었어요."
                )
            )
            if st.button("Gemini 분석 실행", type="primary"):
                comments = []
                if comment_upload is not None:
                    content = comment_upload.read().decode("utf-8")
                    if comment_upload.name.endswith(".csv"):
                        csv_df = pd.read_csv(io.StringIO(content))
                        if "comment" in csv_df.columns:
                            comments.extend(csv_df["comment"].dropna().astype(str).tolist())
                        else:
                            comments.extend(content.splitlines())
                    else:
                        comments.extend(content.splitlines())

                comments.extend([line for line in raw_comments.splitlines() if line.strip()])
                analysis = gemini.analyze_comments(comments)
                st.session_state.gemini_result = analysis
                if analysis["status"] in {"success", "simulated"}:
                    st.toast("Gemini 분석 완료", icon="✅")
                else:
                    st.error(analysis["message"])
        
        with col_result:
            if st.session_state.gemini_result:
                result_payload = st.session_state.gemini_result
                result = result_payload.get("result")
                if result:
                    with st.expander("1. 감정 요약", expanded=True):
                        st.write(f"감정 분류: {result.get('sentiment', '-')}")
                        st.caption(result_payload.get("message"))
                    with st.expander("2. 키워드", expanded=True):
                        keywords = result.get("keywords", [])
                        if keywords:
                            st.write(", ".join(keywords))
                        else:
                            st.write("키워드가 없습니다.")
                    with st.expander("3. 요약", expanded=True):
                        st.write(result.get("summary"))
                else:
                    st.warning("분석 결과가 없습니다.")
            else:
                with st.expander("예시 요약", expanded=True):
                    st.write("분석을 실행하면 Gemini 결과가 표시됩니다.")

# ==============================================================================
# [MODULE 4] 리포트 센터
# ==============================================================================
elif "4." in menu:
    col_opt, col_preview = st.columns([1, 2])
    
    with col_opt:
        st.subheader("⚙️ 보고서 설정")
        with st.container(border=True):
            project = st.selectbox("프로젝트", ["2026 신임팀장 과정", "2025 전사 조직진단"])
            report_format = st.radio("포맷", ["PPT (발표)"])
            include_ai = st.checkbox("AI 요약 포함", value=True)
            summary_input = st.text_area(
                "요약 문장",
                value=(
                    "종합 만족도는 4.5점으로 상승했습니다.\n"
                    "신임팀장 과정의 실무 연계성이 높게 평가되었습니다."
                ),
                height=120,
            )
            highlight_input = st.text_area(
                "하이라이트",
                value=(
                    "강의 콘텐츠: 실습 비중 확대 요청\n"
                    "운영 지원: 사전 안내 개선 필요"
                ),
                height=100,
            )
            
            if st.button("PPT 생성", type="primary"):
                with st.spinner("PPT 렌더링 중..."):
                    summary_lines = [line for line in summary_input.splitlines() if line.strip()]
                    highlight_lines = [line for line in highlight_input.splitlines() if line.strip()]
                    pptx_bytes = reporting.build_pptx_report(
                        title=project,
                        summary_lines=summary_lines,
                        highlights=highlight_lines,
                    )
                st.success("PPT 생성 완료")
                st.download_button(
                    label="PPT 다운로드",
                    data=pptx_bytes,
                    file_name=f"{project}_report.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )
    
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
