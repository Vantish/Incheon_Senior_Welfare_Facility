import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime

def get_welfare_news(service_key, page_no=1, num_of_rows=10, age=None, ctpv_nm=None, search_wrd=None):
    base_url = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations/LcgvWelfarelist"
    params = {
        'serviceKey': service_key,
        'pageNo': str(page_no),
        'numOfRows': str(num_of_rows),
    }
    if age:
        params['age'] = str(age)
    if ctpv_nm:
        params['ctpvNm'] = ctpv_nm
    if search_wrd:
        params['searchWrd'] = search_wrd

    response = requests.get(base_url, params=params)
    news_list = []

    if response.status_code == 429:
        st.error("데이터 호출 제한에 도달했습니다. 잠시 후 다시 시도해 주세요.")
    elif response.status_code == 200:
        try:
            root = ET.fromstring(response.content)
            result_code = root.findtext('.//resultCode')
            result_msg = root.findtext('.//resultMessage')
            if result_code == '0':
                for serv in root.findall('.//servList'):
                    news_list.append({
                        'servNm': serv.findtext('servNm', default='N/A'),
                        'servDgst': serv.findtext('servDgst', default='설명없음'),
                        'servDtlLink': serv.findtext('servDtlLink', default=''),
                        'bizChrDeptNm': serv.findtext('bizChrDeptNm', default=''),
                        'ctpvNm': serv.findtext('ctpvNm', default=''),
                        'lastModYmd': serv.findtext('lastModYmd', default=''),
                    })
            elif result_code == '40':
                st.warning('검색된 데이터가 없습니다.')
            else:
                st.error(f'오류 발생 - 코드: {result_code}, 메시지: {result_msg}')
        except Exception as e:
            st.error(f"XML 파싱 중 오류 발생: {e}")
    else:
        st.error(f'데이터 요청 실패, 상태 코드: {response.status_code}')

    return news_list

def format_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d')
    except Exception:
        return date_str

def fetch_news(ctpv, search_list, free_text, rows, page):
    combined_search = search_list.copy()
    if free_text.strip():
        combined_search.append(free_text.strip())
    search_wrd = ",".join(combined_search) if combined_search else None
    with st.spinner('검색 중...'):
        return get_welfare_news(st.secrets["NEWS_API_KEY"], page, rows, None, ctpv, search_wrd)

def run_news():
    st.title('복지 지원 서비스 알림 게시판📝')

    if "page_no" not in st.session_state:
        st.session_state.page_no = 1

    left_col, right_col = st.columns([1, 3])

    with left_col:
        st.header("정보 입력")
        ctpv_nm = st.text_input('지역을 입력해 주세요: 예) 인천', '')
        options = ['노년', '중장년', '건강', '복지', '저소득', '보훈대상자', '긴급지원', '선택안함']
        search_wrd_list = st.multiselect('지원대상의 정보를 선택하세요', options)
        free_text_search = st.text_input('찾고 싶은 내용을 입력하세요', '')
        num_of_rows = st.number_input('한 페이지 출력 건수', min_value=1, max_value=50, value=10)

        page_no = st.session_state.page_no

        if st.button('복지 서비스 조회'):
            st.session_state.page_no = 1
            st.session_state.news_cache = fetch_news(ctpv_nm, search_wrd_list, free_text_search, num_of_rows, 1)

    with right_col:
        news = st.session_state.get("news_cache", [])
        if news:
            for item in news:
                formatted_date = format_date(item['lastModYmd'])
                st.markdown(f"""
<div style="
    border:1px solid #ddd; 
    padding:15px; 
    border-radius:10px; 
    margin-bottom:10px; 
    box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    background:#f9f9f9;">
    <h4 style="margin-bottom:5px;">{item['servNm']}</h4>
    <p style="color:#555; margin-top:0;">📅 {formatted_date}</p>
    <p>소관 부서: {item['bizChrDeptNm']}</p>
    <p>지역: {item['ctpvNm']}</p>
    <p>{item['servDgst']}</p>
    <a href="{item['servDtlLink']}" target="_blank">상세보기 바로가기</a>
</div>
""", unsafe_allow_html=True)
        else:
            st.info('조건에 맞는 복지 서비스가 없습니다.')

    # 페이지 맨 아래에 이전, 다음 페이지 버튼 배치
    if news:
        col1, col2 = st.columns(2)
        with col1:
            if st.button('이전 페이지'):
                if st.session_state.page_no > 1:
                    st.session_state.page_no -= 1
                    page_no = st.session_state.page_no
                    st.session_state.news_cache = fetch_news(ctpv_nm, search_wrd_list, free_text_search, num_of_rows, page_no)
                else:
                    st.warning("첫 페이지입니다.")
        with col2:
            if st.button('다음 페이지'):
                st.session_state.page_no += 1
                page_no = st.session_state.page_no
                st.session_state.news_cache = fetch_news(ctpv_nm, search_wrd_list, free_text_search, num_of_rows, page_no)

if __name__ == '__main__':
    run_news()
