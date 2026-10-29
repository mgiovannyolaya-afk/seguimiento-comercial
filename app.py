import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de la página con diseño ancho y moderno
st.set_page_config(
    page_title="Gestión Comercial - Meta 70%", page_icon="🎯", layout="wide"
)

# Estilo visual corporativo limpio
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# Título principal del tablero
st.title("🎯 Control de Oportunidades y Cumplimiento (Meta 70%)")
st.markdown(
    "Monitoreo interactivo de canales, ejecución de impactos, ventas y reserva"
    " actualizada."
)
st.markdown("---")


# Carga de datos optimizada con caché
@st.cache_data
def cargar_datos():
  return pd.read_excel("SGTO X CANAL.xlsx", sheet_name="Export")


try:
  df = cargar_datos()

  # Asegurar formato numérico en columnas clave
  if "IMPACTO" in df.columns:
    df["IMPACTO"] = pd.to_numeric(df["IMPACTO"], errors="coerce").fillna(0)
  if "TOTAL" in df.columns:
    df["TOTAL"] = pd.to_numeric(df["TOTAL"], errors="coerce").fillna(0)
  if "RESERVA DIA" in df.columns:
    df["RESERVA DIA"] = pd.to_numeric(df["RESERVA DIA"], errors="coerce").fillna(
        0
    )

  # --- BARRA LATERAL DE FILTROS INTERACTIVOS ---
  st.sidebar.header("🔍 Filtros de Segmentación")

  # 1. Filtro de Canal (Muestra todos los canales)
  canales = ["Todos"] + sorted(
      df["Canal"].dropna().astype(str).unique().tolist()
  )
  canal_seleccionado = st.sidebar.selectbox("Canal", canales)

  if canal_seleccionado != "Todos":
    df_temp = df[df["Canal"].astype(str) == canal_seleccionado]
  else:
    df_temp = df

  # 2. Filtro de Supervisor
  supervisores = ["Todos"] + sorted(
      df_temp["Supervisor"].dropna().astype(str).unique().tolist()
  )
  sup_seleccionado = st.sidebar.selectbox("Supervisor", supervisores)

  if sup_seleccionado != "Todos":
    df_temp = df_temp[df_temp["Supervisor"].astype(str) == sup_seleccionado]

  # 3. Filtro de Zona
  zonas = ["Todas"] + sorted(
      df_temp["Zona"].dropna().astype(str).unique().tolist()
  )
  zona_seleccionada = st.sidebar.selectbox("Zona", zonas)

  if zona_seleccionada != "Todas":
    df_temp = df_temp[df_temp["Zona"].astype(str) == zona_seleccionada]

  # 4. Filtro de Vendedor
  vendedores = ["Todos"] + sorted(
      df_temp["Vendedor"].dropna().astype(str).unique().tolist()
  )
  vendedor_seleccionado = st.sidebar.selectbox("Vendedor", vendedores)

  if vendedor_seleccionado != "Todos":
    df_filtrado = df_temp[
        df_temp["Vendedor"].astype(str) == vendedor_seleccionado
    ]
  else:
    df_filtrado = df_temp

  # --- CÁLCULO DE MÉTRICAS Y TOTALES ---
  total_clientes = len(df_filtrado)
  impactados_count = (
      int(df_filtrado["IMPACTO"].sum()) if "IMPACTO" in df_filtrado.columns else 0
  )
  oportunidad_count = total_clientes - impactados_count
  porcentaje_ejecucion = (
      (impactados_count / total_clientes * 100) if total_clientes > 0 else 0
  )

  # Totales en pesos (Ventas 'TOTAL' y Reserva actualizada 'RESERVA DIA')
  total_ventas = df_filtrado["TOTAL"].sum()
  total_reserva_dia = df_filtrado["RESERVA DIA"].sum()

  # --- TARJETAS DE MÉTRICAS SUPERIORES (KPIs) ---
  col1, col2, col3, col4, col5 = st.columns(5)

  with col1:
    st.metric(label="📊 Total Clientes", value=f"{total_clientes:,}")
  with col2:
    st.metric(
        label="✅ Clientes Impactados",
        value=f"{impactados_count:,}",
        delta=f"{porcentaje_ejecucion:.1f}% Ejecución",
    )
  with col3:
    st.metric(
        label="⚠️ Con Oportunidad (Falta)", value=f"{oportunidad_count:,}"
    )
  with col4:
    st.metric(label="💰 Venta Total ($)", value=f"${total_ventas:,.0f}")
  with col5:
    st.metric(
        label="🔥 Reserva Día ($)", value=f"${total_reserva_dia:,.0f}"
    )

  # Barra de progreso visual para el porcentaje de ejecución
  st.progress(
      min(max(porcentaje_ejecucion / 100.0, 0.0), 1.0),
      text=f"Progreso de Ejecución de Impactos: {porcentaje_ejecucion:.1f}%",
  )
  st.markdown("---")

  # --- GRÁFICO PEQUEÑO Y COMPACTO DE RESUMEN ---
  if not df_filtrado.empty:
    with st.expander("📊 Ver Gráfico Resumen por Canal", expanded=True):
      df_grafico = (
          df_filtrado.groupby("Canal")[["TOTAL", "RESERVA DIA"]]
          .sum()
          .reset_index()
      )
      fig = px.bar(
          df_grafico,
          x="Canal",
          y=["TOTAL", "RESERVA DIA"],
          labels={"value": "Pesos ($)", "variable": "Métrica"},
          barmode="group",
          height=300,
          color_discrete_sequence=["#1f77b4", "#ff7f0e"],
      )
      fig.update_layout(
          margin=dict(l=20, r=20, t=20, b=20),
          xaxis_tickangle=-25,
          plot_bgcolor="rgba(0,0,0,0)",
          paper_bgcolor="rgba(0,0,0,0)",
      )
      st.plotly_chart(fig, use_container_width=True)

  st.markdown("---")

  # --- PESTAÑAS DE NAVEGACIÓN PRINCIPALES ---
  pestana1, pestana2, pestana3 = st.tabs([
      "🎯 Clientes con Oportunidad (Falta Impactar)",
      "✅ Clientes Impactados (Con Ventas)",
      "📋 Detalle Comercial General",
  ])

  # Columnas clave para mostrar ordenadas
  columnas_principales = [
      "Canal",
      "Supervisor",
      "Zona",
      "Vendedor",
      "Nit Cliente",
      "Nombre Cliente",
      "Ciudad",
      "TOTAL",
      "RESERVA DIA",
      "Total Cartera",
      "%Eje Ppto",
  ]
  cols_disponibles = [
      c for c in columnas_principales if c in df_filtrado.columns
  ]

  with pestana1:
    st.subheader("🔍 Clientes Pendientes por Impactar (Oportunidad)")
    if "IMPACTO" in df_filtrado.columns:
      df_opp = df_filtrado[df_filtrado["IMPACTO"] == 0]
      st.metric(
          label="Clientes Pendientes en este filtro", value=f"{len(df_opp):,}"
      )
      st.dataframe(
          df_opp[cols_disponibles], use_container_width=True, height=420
      )
    else:
      st.info("No se encontró la columna IMPACTO.")

  with pestana2:
    st.subheader("✅ Clientes Impactados Exitosamente")
    if "IMPACTO" in df_filtrado.columns:
      df_imp = df_filtrado[df_filtrado["IMPACTO"] == 1]
      st.metric(
          label="Clientes Impactados en este filtro", value=f"{len(df_imp):,}"
      )
      st.dataframe(
          df_imp[cols_disponibles], use_container_width=True, height=420
      )
    else:
      st.info("No se encontró la columna IMPACTO.")

  with pestana3:
    st.subheader("📋 Base de Datos General (Filtrada)")
    st.dataframe(
        df_filtrado[cols_disponibles], use_container_width=True, height=420
    )

except Exception as e:
  st.error(f"Error al procesar los datos: {e}")
