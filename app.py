import datetime
import re
import requests
import streamlit as st

# ---------------------------------------------------------
# [필수] 나이스 오픈 API 인증키 설정
# Streamlit Secrets를 사용하거나 직접 키를 입력하세요.
# ---------------------------------------------------------
NEIS_API_KEY = "475158beb13640a08d94b5fa99bb678f"

st.set_page_config(
    page_title="학교 급식 알리미", page_icon="🍱", layout="centered"
)


def get_school_info(api_key, school_name):
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
        school_list = data["schoolInfo"][1]["row"]
        school = school_list[0]
        return (
            school["ATPT_OFCDC_SC_CODE"],
            school["SD_SCHUL_CODE"],
            school["SCHUL_NM"],
        )
    except (KeyError, IndexError):
        return None, None, None


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
        clean_menu = raw_menu.replace("<br/>", "\n")
        clean_menu = re.sub(r"[0-9.]+", "", clean_menu).strip()

        cal_info = meal_info.get("CAL_INFO", "정보 없음")
        raw_ntr = meal_info.get("NTR_INFO", "")
        clean_ntr = raw_ntr.replace("<br/>", ", ").strip()

        return {
            "menu": clean_menu,
            "cal_info": cal_info,
            "ntr_info": clean_ntr if clean_ntr else "영양 정보 없음",
        }
    except (KeyError, IndexError):
        return None


def get_current_meal_target(now):
    now_hour = now.hour
    if now_hour < 7:
        return now, "1", "오늘의 조식 메뉴"
    elif 7 <= now_hour < 9:
        return now, "1", "오늘의 조식 메뉴"
    elif 9 <= now_hour < 13:
        return now, "2", "오늘의 중식 메뉴"
    elif 13 <= now_hour < 19:
        return now, "3", "오늘의 석식 메뉴"
    else:
        return now + datetime.timedelta(days=1), "1", "내일의 조식 메뉴"


# --- Streamlit UI 구성 ---
st.title("🍱 우리 학교 급식 알리미")
st.write("현재 시각에 맞춰 조식, 중식, 석식 메뉴 및 건강 정보를 보여줍니다.")

school_input = st.text_input("학교 이름을 입력하세요", placeholder="예: 서울고등학교")

if st.button("급식 조회하기") or school_input:
    if not school_input.strip():
        st.warning("학교 이름을 입력해 주세요.")
    else:
        office_code, school_code, real_school_name = get_school_info(
            NEIS_API_KEY, school_input
        )

        if not office_code:
            st.error(f"'{school_input}' 검색 결과를 찾을 수 없습니다.")
        else:
            now = datetime.datetime.now()
            target_date, meal_code, meal_title = get_current_meal_target(now)
            date_str = target_date.strftime("%Y%m%d")
            date_formatted = target_date.strftime("%Y년 %m월 %d일")

            st.success(
                f"🏫 **{real_school_name}** | 🕒 현재 시각: {now.strftime('%H시 %M분')}"
            )
            st.subheader(f"{meal_title} ({date_formatted})")

            meal_data = get_meal_info(
                NEIS_API_KEY, office_code, school_code, date_str, meal_code
            )

            if meal_data:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### 🥗 오늘의 메뉴")
                    st.text(meal_data["menu"])

                with col2:
                    st.markdown("### 🌱 건강 & 영양 정보")
                    st.info(f"**열량**: {meal_data['cal_info']}")
                    st.caption(f"**영양 성분**\n{meal_data['ntr_info']}")
            else:
                st.info("해당 날짜의 급식 정보가 없거나 주말/휴업일입니다.")
