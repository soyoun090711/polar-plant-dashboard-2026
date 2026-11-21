import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io

st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
    html, body, [class*="css"] {
       font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def read_csv(file):
    data = file.getvalue()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding=enc)
        except Exception:
            pass
    return pd.DataFrame()


def std_cols(df):
    df = df.copy()
    df.columns = [str(c).strip().lstrip("\ufeff") for c in df.columns]
    rename = {}
    for c in df.columns:
        k = c.lower().replace(" ", "")
        if k in ("time", "categories", "시간", "날짜", "datetime", "date"):
            rename[c] = "time"
        elif k in ("temperature", "온도"):
            rename[c] = "temperature"
        elif k in ("humidity", "습도"):
            rename[c] = "humidity"
        elif k == "ph":
            rename[c] = "ph"
        elif k == "ec":
            rename[c] = "ec"
        elif "생중량" in k:
            rename[c] = "생중량"
        elif "잎" in k:
            rename[c] = "잎 수"
        elif "지상부" in k and "길이" in k:
            rename[c] = "지상부 길이"
        elif "지하부" in k and "길이" in k:
            rename[c] = "지하부 길이"
        elif "지상부" in k and ("질량" in k or "무게" in k):
            rename[c] = "지상부 질량"
        elif "지하부" in k and ("질량" in k or "무게" in k):
            rename[c] = "지하부 질량"
        elif "개체" in k:
            rename[c] = "개체번호"
    df = df.rename(columns=rename)
    for c in df.columns:
        if c in ("time", "개체번호"):
            continue
        if not pd.api.types.is_numeric_dtype(df[c]):
            num = pd.to_numeric(
                df[c].astype(str).str.replace(",", "").str.extract(r"(-?\d+\.?\d*)")[0],
                errors="coerce",
            )
            if num.notna().mean() >= 0.5:
                df[c] = num
    if "생중량" not in df.columns and {"지상부 질량", "지하부 질량"} <= set(df.columns):
        df["생중량"] = df["지상부 질량"] + df["지하부 질량"]
    if "time" in df.columns:
        t = df["time"].astype(str).str.strip()
        parsed = pd.to_datetime(t, errors="coerce", format="mixed")
        bad = parsed.isna() & t.str.match(r"^\d{8}_\d{1,2}$")
        if bad.any():
            parts = t[bad].str.split("_", expand=True)
            parsed[bad] = pd.to_datetime(parts[0], format="%Y%m%d") + pd.to_timedelta(parts[1].astype(int), unit="h")
        df["time"] = parsed
    return df


def growth_bar(df, value_col, title):
    if df is None or value_col not in df.columns or "개체번호" not in df.columns:
        st.info(f"'{title}' 데이터를 찾지 못했어요.")
        return
    d = df.dropna(subset=[value_col])
    if len(d) < 2:
        st.info(f"'{title}' 데이터가 2개 미만이에요.")
        return
    avg = d.groupby("개체번호", as_index=False)[value_col].mean()
    avg = avg.sort_values(value_col, ascending=False)
    fig = px.bar(avg, x="개체번호", y=value_col, title=title)
    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"), height=400)
    st.plotly_chart(fig, width="stretch")


env_file = st.sidebar.file_uploader("환경 CSV", type="csv")
growth_file = st.sidebar.file_uploader("생육 CSV", type="csv")

env_df = None
growth_df = None
school_name = "미설정"

if env_file is not None or growth_file is not None:
    with st.spinner("CSV를 읽고 표준화하는 중..."):
        if env_file is not None:
            env_df = read_csv(env_file)
            env_df = std_cols(env_df)
            school_name = env_file.name.replace("\ufeff", "").split(".")[0]
        if growth_file is not None:
            growth_df = read_csv(growth_file)
            growth_df = std_cols(growth_df)

if growth_df is not None:
    growth_items = st.sidebar.multiselect(
        "생육 측정 항목",
        ["생중량", "잎 수", "지상부 길이", "지하부 길이"],
        default=["생중량", "잎 수", "지상부 길이", "지하부 길이"],
    )
else:
    growth_items = []

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

with tab1:
    try:
        st.subheader("연구 배경 및 목적")
        st.write("우리 학교 극지식물의 개체별 생육 차이를 환경 조건과 함께 분석합니다.")
        st.write("온도·습도 같은 환경 요인이 개체별 생중량 차이로 이어지는지, 그래프와 표로 확인해 보세요.")

        rows = []
        if env_df is not None and not env_df.empty:
            period = env_df["time"].dropna()
            period_str = f"{period.min().strftime('%Y-%m-%d')} ~ {period.max().strftime('%Y-%m-%d')}" if len(period) else "측정 기간 없음"
            rows.append(["환경 데이터", len(env_df), period_str, "온도·습도·pH·EC"])
        if growth_df is not None and not growth_df.empty:
            rows.append(["생육 결과", len(growth_df), "-", "개체번호·잎 수·생체중 등"])
        if rows:
            st.subheader("데이터 요약")
            st.dataframe(pd.DataFrame(rows, columns=["데이터", "개체 수", "측정 기간", "측정 항목"]), width="stretch")
        else:
            st.info("환경 데이터 CSV와 생육 결과 CSV를 업로드해 주세요.")

        st.subheader("주요 지표")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if growth_df is not None and "생중량" in growth_df.columns:
                w = growth_df["생중량"].dropna()
                st.metric("총 개체수", f"{len(w)}개체" if len(w) else "0개체")
            else:
                st.metric("총 개체수", "측정 없음")
        with c2:
            if env_df is not None and "temperature" in env_df.columns:
                t = env_df["temperature"].dropna()
                st.metric("평균 온도", f"{t.mean():.1f}°C" if len(t) else "측정 없음")
            else:
                st.metric("평균 온도", "측정 없음")
        with c3:
            if env_df is not None and "humidity" in env_df.columns:
                h = env_df["humidity"].dropna()
                st.metric("평균 습도", f"{h.mean():.1f}%" if len(h) else "측정 없음")
            else:
                st.metric("평균 습도", "측정 없음")
        with c4:
            if growth_df is not None and "생중량" in growth_df.columns:
                w = growth_df["생중량"].dropna()
                st.metric("평균 생중량", f"{w.mean():.2f}g" if len(w) else "측정 없음")
            else:
                st.metric("평균 생중량", "측정 없음")
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")

with tab2:
    try:
        if env_df is not None and not env_df.empty:
            st.subheader("환경 요약")
            sum_rows = []
            for col, label in [("temperature", "온도 (°C)"), ("humidity", "습도 (%)"), ("ph", "pH"), ("ec", "EC (mS/cm)")]:
                if col in env_df.columns:
                    s = env_df[col].dropna()
                    if len(s):
                        sum_rows.append({"항목": label, "평균": f"{s.mean():.2f}", "최소": f"{s.min():.2f}", "최대": f"{s.max():.2f}"})
            if sum_rows:
                st.dataframe(pd.DataFrame(sum_rows), width="stretch")
            else:
                st.info("환경 데이터에서 온도·습도·pH·EC 열을 찾지 못했어요.")

            st.subheader("날짜별 시계열")
            d = env_df.dropna(subset=["time"])
            if len(d):
                dd = d.copy()
                dd["date"] = dd["time"].dt.date
                daily = dd.groupby("date").mean(numeric_only=True).reset_index()
                daily["time"] = pd.to_datetime(daily["date"])

                if "temperature" in daily.columns:
                    fig = px.line(daily, x="time", y="temperature", title="온도 변화 (일별 평균)")
                    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
                    st.plotly_chart(fig, width="stretch")
                if "humidity" in daily.columns:
                    fig = px.line(daily, x="time", y="humidity", title="습도 변화 (일별 평균)")
                    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
                    st.plotly_chart(fig, width="stretch")
                ph_ec = [c for c in ["ph", "ec"] if c in daily.columns]
                if ph_ec:
                    fig = px.line(daily, x="time", y=ph_ec, title="pH·EC 변화 (일별 평균)")
                    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
                    st.plotly_chart(fig, width="stretch")
            else:
                st.info("환경 데이터의 시간을 읽지 못했어요.")

            with st.expander("환경 데이터 원본"):
                st.dataframe(env_df, width="stretch")
                csv = env_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("환경 데이터 CSV 다운로드", csv, file_name="환경데이터.csv", mime="text/csv")
        else:
            st.info("환경 데이터 CSV를 업로드하면 날짜별 그래프와 요약을 볼 수 있어요.")
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")

with tab3:
    try:
        if growth_df is not None and not growth_df.empty:
            st.subheader("핵심 결과")
            if "생중량" in growth_df.columns:
                w = growth_df["생중량"].dropna()
                if len(w):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("평균 생중량", f"{w.mean():.2f}g")
                    with c2:
                        max_i = w.idxmax()
                        st.metric("최대 개체", f"개체 {growth_df.loc[max_i, '개체번호']}")
                    with c3:
                        min_i = w.idxmin()
                        st.metric("최소 개체", f"개체 {growth_df.loc[min_i, '개체번호']}")

            st.subheader("개체별 생육 비교")
            if "생중량" in growth_items:
                growth_bar(growth_df, "생중량", "평균 생중량 (⭐ 가장 중요)")
            if "잎 수" in growth_items:
                growth_bar(growth_df, "잎 수", "평균 잎 수")
            if "지상부 길이" in growth_items:
                growth_bar(growth_df, "지상부 길이", "평균 지상부 길이")
            if "지하부 길이" in growth_items:
                growth_bar(growth_df, "지하부 길이", "평균 지하부 길이")

            st.subheader("생중량 분포")
            if "생중량" in growth_df.columns:
                d = growth_df.dropna(subset=["생중량"])
                if len(d) >= 2:
                    fig = px.box(d, y="생중량", title="생중량 분포 (박스플롯)")
                    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"), height=450)
                    st.plotly_chart(fig, width="stretch")
                else:
                    st.info("생중량 데이터를 찾지 못했어요.")

            st.subheader("상관관계 분석")
            if "생중량" in growth_df.columns and "잎 수" in growth_df.columns:
                d = growth_df.dropna(subset=["생중량", "잎 수"])
                if len(d) >= 2:
                    corr = d["생중량"].corr(d["잎 수"])
                    fig = px.scatter(d, x="잎 수", y="생중량", title="잎 수 vs 생중량")
                    fig.update_traces(marker=dict(opacity=0.6))
                    x = d["잎 수"].values
                    y = d["생중량"].values
                    slope, intercept = np.polyfit(x, y, 1)
                    fig.add_trace(go.Scatter(x=x, y=slope * x + intercept, mode="lines", name="추세선", line=dict(color="red", dash="dash")))
                    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"), height=450)
                    st.plotly_chart(fig, width="stretch")
                    st.caption(f"상관계수: {corr:.3f}")
                else:
                    st.info("잎 수와 생중량의 상관관계를 계산할 데이터가 부족해요.")
            if "생중량" in growth_df.columns and "지상부 길이" in growth_df.columns:
                d = growth_df.dropna(subset=["생중량", "지상부 길이"])
                if len(d) >= 2:
                    corr = d["생중량"].corr(d["지상부 길이"])
                    fig = px.scatter(d, x="지상부 길이", y="생중량", title="지상부 길이 vs 생중량")
                    fig.update_traces(marker=dict(opacity=0.6))
                    x = d["지상부 길이"].values
                    y = d["생중량"].values
                    slope, intercept = np.polyfit(x, y, 1)
                    fig.add_trace(go.Scatter(x=x, y=slope * x + intercept, mode="lines", name="추세선", line=dict(color="red", dash="dash")))
                    fig.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"), height=450)
                    st.plotly_chart(fig, width="stretch")
                    st.caption(f"상관계수: {corr:.3f}")
                else:
                    st.info("지상부 길이와 생중량의 상관관계를 계산할 데이터가 부족해요.")

            with st.expander("생육 데이터 원본"):
                st.dataframe(growth_df, width="stretch")
                csv = growth_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("생육 데이터 CSV 다운로드", csv, file_name="생육결과데이터.csv", mime="text/csv")
        else:
            st.info("생육 결과 CSV를 업로드하면 개체별 생육 비교와 상관관계 분석을 볼 수 있어요.")
    except Exception as e:
        st.warning(f"⚠️ 이 부분은 데이터 형식 때문에 표시하지 못했어요: {e}")
