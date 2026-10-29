import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de la página con diseño ancho y moderno
st.set_page_config(
    page_title="Gestión Comercial - Meta 70%", page_icon="🎯", layout="wide"
)

# Estilo visual corporativo y tarjetas personalizadas con no-wrap para evitar saltos de línea
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .metric-card {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
            border: 1px solid #e9ecef;
        }
        .metric-title {
            font-size: 14px;
            color: #6c757d;
            font-weight: 600;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 20px;
            color: #212529;
            font-weight: 700;
            white-space: nowrap; /* Evita que el número se parta en varias líneas */
        }
        .metric-delta {
            font-size: 12px;
            color: #28a745;
            margin-top: 5px;
        }
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

  # --- BARRA LATERAL DE FILTROS Y GRÁFICO ---
  st.sidebar.header("🔍 Filtros de Segmentación")

  # 1. Filtro de Canal
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

  # --- GRÁFICO PEQUEÑO EN LA BARRA LATERAL (Debajo de los filtros) ---
  st.sidebar.markdown("---")
  st.sidebar.subheader("📊 Resumen Visual")
  if not df_filtrado.empty:
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
        height=260,
        color_discrete_sequence=["#1f77b4", "#ff7f0e"],
    )
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_tickangle=-45,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
    )
    st.sidebar.plotly_chart(fig, use_container_width=True)

  # --- CÁLCULO DE MÉTRICAS Y TOTALES ---
  total_clientes = len(df_filtrado)
  impactados_count = (
      int(df_filtrado["IMPACTO"].sum()) if "IMPACTO" in df_filtrado.columns else 0
  )
  oportunidad_count = total_clientes - impactados_count
  porcentaje_ejecucion = (
      (impactados_count / total_clientes * 100) if total_clientes > 0 else 0
  )

  # Totales completos en pesos (redondeados a enteros para mayor limpieza)
  total_ventas = df_filtrado["TOTAL"].sum()
  total_reserva_dia = df_filtrado["RESERVA DIA"].sum()

  str_ventas = f"${total_ventas:,.0f}"
  str_reserva = f"${total_reserva_dia:,.0f}"

  # --- TARJETAS SUPERIORES CON HTML PERSONALIZADO ---
  col1, col2, col3, col4, col5 = st.columns(5)

  with col1:
    st.markdown(
        f"""
            <div class="metric-card">
                <div class="metric-title">📊 Total Clientes</div>
                <div class="metric-value">{total_clientes:,}</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

  with col2:
    st.markdown(
        f"""
            <div class="metric-card">
                <div class="metric-title">✅ Clientes Impactados</div>
                <div class="metric-value">{impactados_count:,}</div>
                <div class="metric-delta">{porcentaje_ejecucion:.1f}% Ejecución</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

  with col3:
    st.markdown(
        f"""
            <div class="metric-card">
                <div class="metric-title">⚠️ Con Oportunidad</div>
                <div class="metric-value">{oportunidad_count:,}</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

  with col4:
    st.markdown(
        f"""
            <div class="metric-card">
                <div class="metric-title">💰 Venta Total ($)</div>
                <div class="metric-value">{str_ventas}</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

  with col5:
    st.markdown(
        f"""
            <div class="metric-card">
                <div class="metric-title">🔥 Reserva Día ($)</div>
                <div class="metric-value">{str_reserva}</div>
            </div>
        """,
        unsafe_allow_html=True,
    )

  # Barra de progreso visual para el porcentaje de ejecución
  st.markdown("<br>", unsafe_allow_html=True)
  st.progress(
      min(max(porcentaje_ejecucion / 100.0, 0.0), 1.0),
      text=f"Progreso de Ejecución de Impactos: {porcentaje_ejecucion:.1f}%",
  )
  st.markdown("---")

  # --- PESTAÑAS DE NAVEGACIÓN PRINCIPALES ---
  pestana1, pestana2, pestana3 = st.tabs([
      "🎯 Clientes con Oportunidad (Falta Impactar)",
      "✅ Clientes Impactados (Con Ventas)",
      "📋 Detalle Comercial General",
  ])

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
          df_opp[cols_disponibles], use_container_width=True, height=450
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
          df_imp[cols_disponibles], use_container_width=True, height=450
      )
    else:
      st.info("No se encontró la columna IMPACTO.")

  with pestana3:
    st.subheader("📋 Base de Datos General (Filtrada)")
    st.dataframe(
        df_filtrado[cols_disponibles], use_container_width=True, height=450
    )

except Exception as e:
  st.error(f"Ocurrió un error al procesar los datos: {e}")
