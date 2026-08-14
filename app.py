import datetime
import re
import requests
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="급식 알리미",
    page_icon="🍱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------
# [디자인] 커스텀 CSS (다크모드 지원 및 상단 회색 커버 카드)
# ---------------------------------------------------------
st.markdown(
    """
    <style>
    .hero-card {
        background-color: var(--background-secondary-color, #f0f2f6);
        color: var(--text-color, #000000);
        padding: 24px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid rgba(0, 0, 0, 0.08);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0;
        padding: 0;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        opacity: 0.8;
        margin-top: 8px;
    }
    .menu-card {
        background-color: var(--background-secondary-color, #f8f9fa);
        border-left: 5px solid #4CAF50;
        padding: 16px 20px;
        border-radius: 8px;
        font-size: 1.05rem;
        line-height: 1.8;
        margin-bottom: 15px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# API 키 설정
if "NEIS_API_KEY" in st.secrets:
    NEIS_API_KEY = st.secrets["475158beb13640a08d94b5fa99bb678f"]
else:
    NEIS_API_KEY = "475158beb13640a08d94b5fa99bb678f"


def get_school_info(api_key, school_name):
    if api_key == "475158beb13640a08d94b5fa99bb678f" or not api_key:
        return None, None, "API_KEY_MISSING"

    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 10,
        "SCHUL_NM": school_name,
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "RESULT" in data:
            return None, None, f"API_ERROR: {data['RESULT']['MESSAGE']}"

        school_list = data["schoolInfo"][1]["row"]
        school = school_list[0]
        return (
            school["ATPT_OFCDC_SC_CODE"],
            school["SD_SCHUL_CODE"],
            school["SCHUL_NM"],
        )
    except Exception as e:
        return None, None, f"ERROR: {str(e)}"


def format_nutrition_with_emojis(raw_ntr):
    """영양 정보 한 줄씩 정렬 및 이모지 적용"""
    if not raw_ntr:
        return "영양 정보 없음"

    emoji_map = {
        "탄수화물": "🍚 탄수화물",
        "단백질": "🥩 단백질",
        "지방": "🥑 지방",
        "비타민A": "🥦 비타민A",
        "비타민C": "🥦 비타민C",
        "칼슘": "🥛 칼슘",
        "철분": "🥬 철분",
        "나트륨": "🧂 나트륨",
    }

    raw_clean = raw_ntr.replace("<br/>", "\n").replace(" • ", "\n").replace("·", "\n")
    items = raw_clean.split("\n")

    formatted_items = []
    for item in items:
        item_str = item.strip()
        if not item_str:
            continue

        replaced = False
        for key, val in emoji_map.items():
            if key in item_str:
                formatted_items.append(f"• {item_str.replace(key, val)}")
                replaced = True
                break

        if not replaced:
            formatted_items.append(f"• 🔹 {item_str}")

    return "\n".join(formatted_items)


def get_meal_info(api_key, office_code, school_code, date_str, meal_code):
    url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
    params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 10,
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MLSV_YMD": date_str,
        "MMEAL_SC_CODE": meal_code,
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        meal_info = data["mealServiceDietInfo"][1]["row"][0]

        raw_menu = meal_info.get("DDISH_NM", "")
        clean_menu = raw_menu.replace("<br/>", "\n").strip()

        cal_info = meal_info.get("CAL_INFO", "정보 없음")
        raw_ntr = meal_info.get("NTR_INFO", "")
        formatted_ntr = format_nutrition_with_emojis(raw_ntr)

        return {
            "menu": clean_menu,
            "cal_info": cal_info,
            "ntr_info": formatted_ntr,
        }
    except (KeyError, IndexError):
        return None


def get_current_meal_target(now):
    now_hour = now.hour
    if now_hour < 7:
        return now.date(), "1", "오늘의 조식"
    elif 7 <= now_hour < 9:
        return now.date(), "1", "오늘의 조식"
    elif 9 <= now_hour < 13:
        return now.date(), "2", "오늘의 중식"
    elif 13 <= now_hour < 19:
        return now.date(), "3", "오늘의 석식"
    else:
        return (now + datetime.timedelta(days=1)).date(), "1", "내일의 조식"


# 상단 커버 카드 헤더
st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title">🍱 급식 알리미</div>
        <div class="hero-subtitle">실시간 맞춤 급식 메뉴와 세부 영양 정보를 확인해 보세요!</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# KST 기준 현재 시각
KST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(KST)

# 최근 검색 학교 기억 기능 (Session State)
if "history" not in st.session_state:
    st.session_state.history = []

if "search_query" not in st.session_state:
    st.session_state.search_query = ""


def update_search():
    st.session_state.search_query = st.session_state.input_field


col_input, col_check = st.columns([2, 1])

with col_input:
    school_input = st.text_input(
        "🏫 학교 이름",
        placeholder="예: 서울고등학교",
        key="input_field",
        on_change=update_search,
    )
    if st.session_state.search_query:
        school_input = st.session_state.search_query

with col_check:
    use_custom_date = st.checkbox("📅 날짜 직접 선택")

# 최근 검색 학교 칩(버튼) 표시
if st.session_state.history:
    st.caption("🕒 최근 검색한 학교:")
    cols = st.columns(len(st.session_state.history) + 1)
    for idx, recent_sch in enumerate(st.session_state.history):
        if cols[idx].button(recent_sch, key=f"hist_{idx}"):
            st.session_state.search_query = recent_sch
            st.rerun()

# 날짜/식사 직접 선택 UI
if use_custom_date:
    col_d, col_m = st.columns(2)
    with col_d:
        selected_date = st.date_input("조회할 날짜", value=now.date())
    with col_m:
        meal_option = st.selectbox("식사 구분", ["조식", "중식", "석식"])
        meal_code_map = {"조식": "1", "중식": "2", "석식": "3"}
        meal_code = meal_code_map[meal_option]
        meal_title = f"{selected_date.strftime('%Y년 %m월 %d일')} {meal_option}"
    target_date_str = selected_date.strftime("%Y%m%d")
else:
    auto_date, meal_code, auto_title = get_current_meal_target(now)
    target_date_str = auto_date.strftime("%Y%m%d")
    meal_title = f"{auto_title} ({auto_date.strftime('%Y년 %m월 %d일')})"

# 급식 정보 조회 및 화면 출력
if school_input.strip():
    office_code, school_code, real_school_name = get_school_info(
        NEIS_API_KEY, school_input
    )

    if real_school_name == "API_KEY_MISSING":
        st.error(
            "🔑 **API 키가 설정되지 않았습니다!**\n\n`app.py` 내 `NEIS_API_KEY`에 키를 넣어주세요."
        )
    elif (
        isinstance(real_school_name, str)
        and real_school_name.startswith("API_ERROR")
    ):
        st.error(f"⚠️ **API 오류:** {real_school_name}")
    elif not office_code:
        st.error(f"❌ '{school_input}' 검색 결과를 찾을 수 없습니다.")
    else:
        if real_school_name not in st.session_state.history:
            st.session_state.history.insert(0, real_school_name)
            st.session_state.history = st.session_state.history[:4]

        st.info(
            f"🏫 **{real_school_name}** | 🕒 현재 시각: **{now.strftime('%H시 %M분')}**"
        )
        st.subheader(f"🍽️ {meal_title}")

        meal_data = get_meal_info(
            NEIS_API_KEY, office_code, school_code, target_date_str, meal_code
        )

        if meal_data:
            col_menu, col_info = st.columns([3, 2])

            with col_menu:
                st.markdown("### 🥗 오늘의 메뉴 (알레르기 번호)")
                formatted_menu = meal_data["menu"].replace("\n", "<br/>")
                st.markdown(
                    f'<div class="menu-card">{formatted_menu}</div>',
                    unsafe_allow_html=True,
                )

            with col_info:
                st.markdown("### 📊 건강 정보")
                st.metric(label="🔥 총 예상 열량", value=meal_data["cal_info"])

                with st.expander("🌱 **세부 영양 성분 보기**", expanded=True):
                    st.markdown(meal_data["ntr_info"])

            st.markdown("---")
            with st.expander("⚠️ **알레르기 유발물질 번호 안내**"):
                st.caption(
                    """
                    1.난류 2.우유 3.메밀 4.땅콩 5.대두 6.밀 7.고등어 8.게 9.새우 10.돼지고기  
                    11.복숭아 12.토마토 13.아황산류 14.호두 15.닭고기 16.쇠고기 17.오징어 18.조개류 19.잣
                    """
                )
        else:
            st.warning("😅 해당 날짜/식사의 급식 정보가 없거나 휴업일(주말)입니다.")
