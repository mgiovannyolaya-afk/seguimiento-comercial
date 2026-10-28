import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Gestión Comercial - Meta 70%", page_icon="📈", layout="wide"
)
st.title("🎯 Control de Oportunidades y Cumplimiento (Meta 70%)")
st.markdown(
    "Tablero conectado para identificar clientes con Venta 0 y cerrar la brecha"
    " del 70%."
)


@st.cache_data(ttl=30)
def cargar_datos():
  df = pd.read_excel("SGTO X CANAL.xlsx", sheet_name="Export")
  return df


try:
  df = cargar_datos()
except:
  st.warning(
      "Sube tu archivo 'SGTO X CANAL.xlsx' en la misma carpeta que este código."
  )
  st.stop()

# Filtros
sup = st.sidebar.selectbox(
    "Supervisor", ["Todos"] + list(df["Supervisor"].dropna().unique())
)
df_f = df if sup == "Todos" else df[df["Supervisor"] == sup]

zona = st.sidebar.selectbox(
    "Zona", ["Todas"] + list(df_f["Zona"].dropna().unique())
)
df_f = df_f if zona == "Todas" else df_f[df_f["Zona"] == zona]

solo_0 = st.sidebar.checkbox(
    "🚨 Solo Clientes Sin Venta (Oportunidades)", value=True
)
df_t = df_f[df_f["IMPACTO"] == 0] if solo_0 else df_f

# KPIs
tot = len(df_f)
imp = int(df_f["IMPACTO"].sum())
sin = tot - imp
pct = (imp / tot) * 100 if tot > 0 else 0
fal = max(0, int(tot * 0.70) - imp)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Clientes", f"{tot:,}")
c2.metric("Impactados", f"{imp} ({pct:.1f}%)", delta="Meta: 70%")
c3.metric("Sin Venta", f"{sin}")
c4.metric("Faltantes para 70%", f"{fal} clientes", delta_color="inverse")

st.markdown("---")
if solo_0 and "Prom Ultim Trim" in df_t.columns:
  df_t = df_t.sort_values(by="Prom Ultim Trim", ascending=False)

cols = [
    "Zona",
    "Supervisor",
    "Nit Cliente",
    "Nombre Cliente",
    "Canal",
    "DIA DE VISITA",
    "Prom Ultim Trim",
    "TOTAL",
    "IMPACTO",
]
st.dataframe(
    df_t[[c for c in cols if c in df_t.columns]], use_container_width=True
)

csv = df_t.to_csv(index=False).encode("utf-8")
st.download_button("📥 Descargar Oportunidades en CSV", csv, "oportunidades.csv")
