import datetime
import re
import requests
import streamlit as st

st.set_page_config(
    page_title="학교 급식 알리미", page_icon="🍱", layout="centered"
)

# 1. Streamlit Secrets에서 API 키를 가져오고, 없으면 변수값 사용
if "NEIS_API_KEY" in st.secrets:
    NEIS_API_KEY = st.secrets["NEIS_API_KEY"]
else:
    NEIS_API_KEY = "475158beb13640a08d94b5fa99bb678f"  # 여기에 본인 API 키 입력


def get_school_info(api_key, school_name):
    if api_key == "YOUR_NEIS_API_KEY_HERE" or not api_key:
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
        clean_menu = re.sub(r"\s*\([0-9.]*\)", "", clean_menu).strip()

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

        if real_school_name == "API_KEY_MISSING":
            st.error(
                "🔑 **나이스 API 키가 설정되지 않았습니다!**\n\n`app.py` 파일의 `NEIS_API_KEY` 변수에 발급받은 키를 넣어주세요."
            )
        elif (
            isinstance(real_school_name, str)
            and real_school_name.startswith("API_ERROR")
        ):
            st.error(f"⚠️ **나이스 API 오류:** {real_school_name}")
        elif not office_code:
            st.error(f"❌ '{school_input}' 검색 결과를 찾을 수 없습니다.")
        else:
            # 💡 한국 표준시(KST, UTC+9) 적용
            KST = datetime.timezone(datetime.timedelta(hours=9))
            now = datetime.datetime.now(KST)

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
