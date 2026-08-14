Python 3.14.7 (tags/v3.14.7:823f032, Aug  5 2026, 10:51:32) [MSC v.1944 64 bit (AMD64)] on win32
Enter "help" below or click "Help" above for more information.
import datetime
import re
import requests

# ---------------------------------------------------------
# [필수] 나이스 오픈 API 인증키 설정
# ---------------------------------------------------------
NEIS_API_KEY = "475158beb13640a08d94b5fa99bb678f"


def get_school_info(api_key, school_name):
    """학교 이름을 검색하여 시도교육청코드와 행정표준코드(학교코드)를 반환합니다."""
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
    """지정한 날짜와 식사 구분(1:조식, 2:중식, 3:석식)의 메뉴 및 건강/영양 정보를 가져옵니다."""
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

        # 1. 급식 메뉴 정제
        raw_menu = meal_info.get("DDISH_NM", "")
        clean_menu = raw_menu.replace("<br/>", "\n")
        clean_menu = re.sub(r"[0-9.]+", "", clean_menu).strip()

        # 2. 건강 및 영양 정보 추출
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
    """현재 시각을 기준으로 대상 날짜, 급식 코드, 타이틀을 결정합니다.

    - 00시 ~ 07시 미만: 당일 조식 (코드 1)
    - 07시 ~ 09시 미만: 당일 조식 (코드 1)
    - 09시 ~ 13시 미만: 당일 중식 (코드 2)
    - 13시 ~ 19시 미만: 당일 석식 (코드 3)
    - 19시 ~ 24시 미만: 다음 날 조식 (코드 1)
    """
    now_hour = now.hour

    if now_hour < 7:
        # 07시 이전 -> 당일 조식
        target_date = now
        meal_code = "1"
        meal_title = "오늘의 조식 메뉴"
    elif 7 <= now_hour < 9:
        # 07시 ~ 09시 -> 당일 조식
        target_date = now
        meal_code = "1"
        meal_title = "오늘의 조식 메뉴"
    elif 9 <= now_hour < 13:
        # 09시 ~ 13시 -> 당일 중식
        target_date = now
        meal_code = "2"
        meal_title = "오늘의 중식 메뉴"
    elif 13 <= now_hour < 19:
        # 13시 ~ 19시 -> 당일 석식
        target_date = now
        meal_code = "3"
        meal_title = "오늘의 석식 메뉴"
    else:
        # 19시 이후 -> 다음 날 조식
        target_date = now + datetime.timedelta(days=1)
        meal_code = "1"
        meal_title = "내일의 조식 메뉴"

    return target_date, meal_code, meal_title


def main():
    school_name = input("학교 이름을 입력하세요 (예: 서울고등학교): ").strip()

    if not school_name:
        print("학교 이름을 정확하게 입력해 주세요.")
        return

    # 1. 학교 코드 조회
    office_code, school_code, real_school_name = get_school_info(
        NEIS_API_KEY, school_name
    )

...     if not office_code:
...         print(f"❌ '{school_name}' 검색 결과를 찾을 수 없습니다.")
...         return
... 
...     # 2. 현재 시각 기준으로 조회 날짜 및 급식 종류 계산
...     now = datetime.datetime.now()
...     target_date, meal_code, meal_title = get_current_meal_target(now)
...     date_str = target_date.strftime("%Y%m%d")
...     date_formatted = target_date.strftime("%Y-%m-%d")
... 
...     print("\n" + "=" * 50)
...     print(
...         f"🏫 학교: {real_school_name} | 🕒 현재 시각: {now.strftime('%H시 %M분')}"
...     )
...     print("=" * 50)
... 
...     # 3. 급식 및 건강 정보 조회
...     meal_data = get_meal_info(
...         NEIS_API_KEY, office_code, school_code, date_str, meal_code
...     )
... 
...     print(f"🍱 [{meal_title}] ({date_formatted})")
...     print("-" * 50)
... 
...     if meal_data:
...         print("[식단 메뉴]")
...         print(meal_data["menu"])
...         print("\n" + "-" * 50)
...         print("🌱 [건강 & 영양 정보]")
...         print(f"• 열량: {meal_data['cal_info']}")
...         print(f"• 영양 성분: {meal_data['ntr_info']}")
...     else:
...         print("해당 날짜의 급식 정보가 없거나 주말/휴업일입니다.")
... 
...     print("=" * 50)
... 
... 
... if __name__ == "__main__":
