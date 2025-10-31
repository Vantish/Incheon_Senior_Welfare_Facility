***

# 🏢 인천광역시 노인복지시설 위치기반 POI 추천 애플리케이션

본 리포지토리는 인천광역시의 노인복지시설 데이터를 중심으로, 사용자의 위치 입력을 받아
가장 적합한 노인복지시설을 추천하고 주변 맛집, 여가·체육시설, 버스정류장 등 관련 POI를 함께 제공하는
Streamlit 기반 위치기반 추천(POI recommendation) 애플리케이션입니다.


***

##  연구 목적 및 개요

- **목표**  
  도로명 주소를 위도·경도로 정밀 지오코딩(Geocoding) 후,  
  반경 10km 이내에서 인천 지역 내 노인복지시설과 연계된 다중 POI를 사용자 맞춤형으로 추천  

- **부가 기능**  
    gemini 2.5 flash -geminiAI를 이용한 자연어처리 챗봇으로 건강과 맛집 추천 하는 AI챗봇

- **주요 대상**  
  노인복지 커뮤니티 이용자, 노인 가구가 있는 보호자, 지방자치단체 정책 담당자, 일반 사용자 등

***

## 🏗️ 시스템 아키텍처 및 핵심 알고리즘

- **지리정보 처리**  
  Kakao Maps REST API 및 로컬 좌표 변환 모듈을 활용한 정밀 주소-좌표 변환 수행  

- **근접도 분석**  
  Haversine 공식 기반
  osmnx와 networks를 통한 도로기반 거리탐색

- **다중 POI 융합**  
  버스 정류장, 식음료 위생시설, 문화·체육 인프라 등 POI 데이터 통합 및 다중 기준 다중 대상 추천 시스템 구축  

- **공간 시각화 및 UI/UX**  
  Folium과 branca를 활용한 지리공간 데이터 시각화와  


***

## 🛠️ 핵심 기술 스택

- 언어: Python 3.10+  
- 웹 프레임워크: Streamlit (대화형 대시보드 및 사용자 인터페이스)  
- 데이터 처리: pandas, numpy  
- 거리 연산 및 분석 : osmnx, networkx, Haversine
- 머신러닝/추천: gemini 2.5 flash
- 시각화: folium, branca , st_aggrid, Streamlit, polyline
- API 통신: requests  
- 배포 및 환경관리: Docker (선택), pip + requirements.txt  

*상기 기술들은 코드베이스 내 사용되거나 권장되는 라이브러리이며, 자세한 의존성은 `requirements.txt` 참고*

***

##  데이터 소스 및 취득 방법

- 내부 데이터셋: 로컬 CSV(`data/` 폴더) 내 인천 노인복지시설, 식당, 버스정류장 등  
- 외부 연동: Kakao 지도 API (지오코딩), 공공데이터포털 오픈 API 활용  

***

## ⚙️ 설치 및 배포

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
streamlit run app_main.py
```

- 앱 진입점: `app_main.py` 혹은 필요 시 `app_home.py`, `app_map.py` 등 실행 가능

***

##  활용 시나리오

- 사용자 입력 기반 실시간 위경도 변환 및 근접 노인복지시설 도출  
- 시설별 주소 및 주변 맛집, 버스정류장 등 POI 정보 제공  
- 고령자 친화적 UX/UI로 직관적 지도 인터페이스 제공

***

## 🤝 기여 및 확장

- 데이터 정합성 강화(중복 제거, 표준화) 및 신규 POI(의료기관, 약국 등) 통합  
- 자동화 배포 파이프라인(Docker, 클라우드 서비스) 구축 관련 PR 환영  

***

## 📄 라이선스 및 출처

- 데이터 출처: 인천광역시 공공 데이터 포털 및 현지 수집 데이터  
- 라이선스: 별도 명시가 없을 시 MIT 라이선스 준용 권장  

***

