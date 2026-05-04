import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os

# 1. 페이지 기본 설정 (웹 브라우저 탭 이름과 레이아웃 설정)
st.set_page_config(page_title="따릉이 분석 대시보드", page_icon="🚲", layout="wide")

st.title("🚲 서울시 따릉이 자치구별 이용 경향성 분석")
st.markdown("공공데이터를 활용하여 서울시 자치구별 따릉이 이용 패턴을 분석한 대시보드입니다.")

# 2. 데이터베이스 연결 및 오류 처리
db_path = "bicycle.db"

# 파일이 없는 경우 친절한 에러 메시지 출력 후 실행 중단
if not os.path.exists(db_path):
    st.error("🚨 앗! `bicycle.db` 파일이 같은 폴더에 없어요. 데이터를 준비한 후 다시 실행해주세요!")
    st.stop()

# 3. 데이터 불러오기 함수 (캐싱을 통해 속도 최적화)
@st.cache_data
def load_data(query):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.divider()

# ==========================================
# 📊 차트 1: 1회 이용 당 이동거리 (이용 목적 분석)
# ==========================================
st.header("1️⃣ 1회 이용 당 이동거리 (이용 목적 분석)")

sql_1 = """
SELECT 
    s.자치구, 
    CAST(SUM(u.이동거리) AS FLOAT) / SUM(u.이용건수) AS 평균이동거리
FROM 이용정보 u
JOIN 대여소 s ON u.대여소번호 = s.대여소번호
GROUP BY s.자치구
ORDER BY 평균이동거리 DESC
"""
df_1 = load_data(sql_1)

# ① 시각화
fig_1 = px.bar(df_1, x='자치구', y='평균이동거리', 
               title="자치구별 1회 이용 당 평균 이동거리 (m)",
               color='평균이동거리', color_continuous_scale='Blues')
st.plotly_chart(fig_1, use_container_width=True)

# ② 사용한 SQL
with st.expander("🛠 사용한 SQL 쿼리 보기"):
    st.code(sql_1, language="sql")

# ③ 인사이트
st.info("""
💡 **인사이트**
* 평균 이동거리가 짧은 자치구는 지하철역-집 등 **'단거리 출퇴근/통학(라스트마일)'** 목적의 수요가 높다고 볼 수 있습니다.
* 반면, 이동거리가 긴 자치구는 한강공원이나 하천을 따라 **'레저 및 운동'** 목적으로 이용하는 패턴이 두드러집니다.
""")

st.divider()

# ==========================================
# 📊 차트 2: 자치구별 수요 밀도
# ==========================================
st.header("2️⃣ 자치구별 수요 밀도 (대여소 당 이용건수)")

# 대여소 수와 총 이용건수를 비교하여 밀도를 구합니다.
sql_2 = """
SELECT 
    s.자치구, 
    SUM(u.이용건수) AS 총이용건수,
    COUNT(DISTINCT s.대여소번호) AS 대여소수,
    CAST(SUM(u.이용건수) AS FLOAT) / COUNT(DISTINCT s.대여소번호) AS 수요밀도
FROM 이용정보 u
JOIN 대여소 s ON u.대여소번호 = s.대여소번호
GROUP BY s.자치구
ORDER BY 수요밀도 DESC
"""
df_2 = load_data(sql_2)

# ① 시각화
fig_2 = px.scatter(df_2, x='대여소수', y='총이용건수', text='자치구', size='수요밀도',
                   title="자치구별 대여소 수 vs 총 이용건수 (원 크기: 수요 밀도)",
                   color='수요밀도', color_continuous_scale='Reds')
fig_2.update_traces(textposition='top center')
st.plotly_chart(fig_2, use_container_width=True)

# ② 사용한 SQL
with st.expander("🛠 사용한 SQL 쿼리 보기"):
    st.code(sql_2, language="sql")

# ③ 인사이트
st.info("""
💡 **인사이트**
* 수요 밀도(원 크기)가 큰 자치구는 대여소 인프라 대비 따릉이를 찾는 사람이 매우 많아 **자전거 및 대여소 확충이 시급**한 지역입니다.
* 대여소는 많지만 이용건수가 낮아 밀도가 떨어지는 곳은 자전거 재배치 시 자전거를 빼서 수요가 높은 곳으로 옮기는 **재분배 전략**이 필요합니다.
""")

st.divider()

# ==========================================
# 📊 차트 3: 온도와 강수량에 따른 자치구별 이용건수
# ==========================================
st.header("3️⃣ 기상 조건(온도/강수량)에 따른 이용건수 변화")

# 날씨 데이터(기온, 강수량)는 여러 지점이 있을 수 있으므로 월별로 평균을 내어 조인합니다.
sql_3 = """
WITH Weather AS (
    SELECT 
        t.년월, 
        AVG(t.평균기온) AS 평균기온, 
        AVG(IFNULL(p.강수량, 0)) AS 강수량
    FROM 기온 t
    LEFT JOIN 강수량 p ON t.년월 = p.년월 AND t.지점 = p.지점
    GROUP BY t.년월
)
SELECT 
    s.자치구,
    u.대여일자 AS 년월,
    w.평균기온,
    w.강수량,
    SUM(u.이용건수) AS 총이용건수
FROM 이용정보 u
JOIN 대여소 s ON u.대여소번호 = s.대여소번호
JOIN Weather w ON u.대여일자 = w.년월
GROUP BY s.자치구, u.대여일자, w.평균기온, w.강수량
"""
df_3 = load_data(sql_3)

# ① 시각화 (산점도: x는 온도, y는 이용건수, 색상은 강수량)
fig_3 = px.scatter(df_3, x='평균기온', y='총이용건수', color='강수량',
                   hover_data=['자치구', '년월'],
                   title="평균기온과 강수량에 따른 이용건수 (색상이 진할수록 비가 많이 옴)",
                   color_continuous_scale='Teal')
st.plotly_chart(fig_3, use_container_width=True)

# ② 사용한 SQL
with st.expander("🛠 사용한 SQL 쿼리 보기"):
    st.code(sql_3, language="sql")

# ③ 인사이트
st.info("""
💡 **인사이트**
* 온도가 너무 춥거나 더운 시기보다는 **따뜻한 봄/가을 기온(15~20도)**일 때 이용건수가 폭발적으로 증가하는 계절성을 보입니다.
* 같은 온도 조건이더라도 **강수량이 많은 달(진한 색상)**에는 야외 활동의 제약으로 인해 따릉이 이용건수가 급감하는 것을 알 수 있습니다.
""")