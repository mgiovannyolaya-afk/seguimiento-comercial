import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de la página con diseño ancho y moderno
st.set_page_config(
    page_title="Gestión Comercial - Meta 70%", page_icon="🎯", layout="wide"
)

# Estilo visual corporativo y tarjetas personalizadas con no-wrap
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
        .summary-box {
            background-color: #e8f4fd;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #b6d4fe;
            text-align: center;
            font-weight: 600;
            color: #084298;
            margin-bottom: 15px;
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
            white-space: nowrap;
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


# Carga de datos local desde el repositorio (actualizado mediante subida manual)
@st.cache_data(ttl=60)
def cargar_datos():
  return pd.read_excel("SGTO X CANAL.xlsx", sheet_name="Export")


try:
  df = cargar_datos()

  # Limpiar nombres de columnas por si tienen espacios ocultos
  df.columns = df.columns.str.strip()

  # Asegurar formato numérico en columnas clave
  for col in ["IMPACTO", "TOTAL", "RESERVA DIA"]:
    if col in df.columns:
      df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

  # Buscar columnas de presupuesto y la nueva columna de % Eje Mes
  col_ppto = next(
      (
          c
          for c in df.columns
          if "ppto" in c.lower()
          or "presupuesto" in c.lower()
          or "pto" in c.lower()
      ),
      None,
  )
  col_eje_mes = next(
      (
          c
          for c in df.columns
          if ("eje" in c.lower() and "mes" in c.lower())
          or ("%" in c and "mes" in c.lower())
      ),
      None,
  )
  if not col_eje_mes:  # Respaldo por si se llama diferente
    col_eje_mes = next(
        (c for c in df.columns if "%" in c or "cumplimiento" in c.lower()), None
    )

  if col_ppto:
    df[col_ppto] = pd.to_numeric(df[col_ppto], errors="coerce").fillna(0)
  if col_eje_mes:
    df[col_eje_mes] = pd.to_numeric(df[col_eje_mes], errors="coerce").fillna(0)

  # --- BARRA LATERAL DE FILTROS Y GRÁFICO ---
  st.sidebar.header("🔍 Filtros de Segmentación")

  df_temp = df.copy()

  # 1. Filtro de Código UN (Regional: DIBOG, DICAL, DIMED)
  col_un_candidatas = [
      c for c in df.columns if "un" in c.lower() or "codigo" in c.lower()
  ]
  col_un = col_un_candidatas[0] if col_un_candidatas else None

  if col_un and col_un in df.columns:
    un_opciones = ["Todos"] + sorted(
        df_temp[col_un].dropna().astype(str).unique().tolist()
    )
    un_sel = st.sidebar.selectbox("Código UN (Regional)", un_opciones)
    if un_sel != "Todos":
      df_temp = df_temp[df_temp[col_un].astype(str) == un_sel]

  # 2. Filtro de Canal
  if "Canal" in df.columns:
    canales = ["Todos"] + sorted(
        df_temp["Canal"].dropna().astype(str).unique().tolist()
    )
    canal_sel = st.sidebar.selectbox("Canal", canales)
    if canal_sel != "Todos":
      df_temp = df_temp[df_temp["Canal"].astype(str) == canal_sel]

  # 3. Filtro de Supervisor
  if "Supervisor" in df.columns:
    supervisores = ["Todos"] + sorted(
        df_temp["Supervisor"].dropna().astype(str).unique().tolist()
    )
    sup_sel = st.sidebar.selectbox("Supervisor", supervisores)
    if sup_sel != "Todos":
      df_temp = df_temp[df_temp["Supervisor"].astype(str) == sup_sel]

  # 4. Filtro de Zona
  if "Zona" in df.columns:
    zonas = ["Todas"] + sorted(
        df_temp["Zona"].dropna().astype(str).unique().tolist()
    )
    zona_sel = st.sidebar.selectbox("Zona", zonas)
    if zona_sel != "Todas":
      df_temp = df_temp[df_temp["Zona"].astype(str) == zona_sel]

  # 5. Filtro de Vendedor
  if "Vendedor" in df.columns:
    vendedores = ["Todos"] + sorted(
        df_temp["Vendedor"].dropna().astype(str).unique().tolist()
    )
    vend_sel = st.sidebar.selectbox("Vendedor", vendedores)
    if vend_sel != "Todos":
      df_filtrado = df_temp[df_temp["Vendedor"].astype(str) == vend_sel]
    else:
      df_filtrado = df_temp
  else:
    df_filtrado = df_temp

  # --- GRÁFICO PEQUEÑO EN LA BARRA LATERAL ---
  st.sidebar.markdown("---")
  st.sidebar.subheader("📊 Resumen Visual")
  if not df_filtrado.empty and "Canal" in df_filtrado.columns:
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

  # --- CÁLCULO DE MÉTRICAS Y TOTALES GENERALES ---
  total_clientes = len(df_filtrado)
  impactados_count = (
      int(df_filtrado["IMPACTO"].sum()) if "IMPACTO" in df_filtrado.columns else 0
  )
  oportunidad_count = total_clientes - impactados_count
  porcentaje_ejecucion = (
      (impactados_count / total_clientes * 100) if total_clientes > 0 else 0
  )

  total_ventas = (
      df_filtrado["TOTAL"].sum() if "TOTAL" in df_filtrado.columns else 0
  )
  total_reserva_dia = (
      df_filtrado["RESERVA DIA"].sum()
      if "RESERVA DIA" in df_filtrado.columns
      else 0
  )

  str_ventas = f"${total_ventas:,.0f}"
  str_reserva = f"${total_reserva_dia:,.0f}"

  # --- TARJETAS SUPERIORES ---
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

  # Barra de progreso visual
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

  # Columnas seleccionadas incluyendo la nueva col_eje_mes
  columnas_tabla = [
      col_un,
      "Canal",
      "Zona",
      "Nit Cliente",
      "Nombre Cliente",
      col_ppto,
      "TOTAL",
      "RESERVA DIA",
      col_eje_mes,
  ]
  cols_disponibles = [
      c
      for c in columnas_tabla
      if c is not None and c in df_filtrado.columns
  ]


  # Función para formatear valores monetarios y porcentajes en la vista
  def formatear_dataframe(df_in):
    df_out = df_in.copy()
    cols_moneda = [c for c in ["TOTAL", "RESERVA DIA", col_ppto] if c in df_out.columns]
    for col in cols_moneda:
      df_out[col] = df_out[col].apply(
          lambda x: f"${x:,.0f}" if pd.notnull(x) and x != 0 else "$0"
      )
    if col_eje_mes and col_eje_mes in df_out.columns:
      df_out[col_eje_mes] = df_out[col_eje_mes].apply(
          lambda x: f"{x * 100:.1f}%" if pd.notnull(x) else "0.0%"
      )
    return df_out


  # Función para renderizar los totales superiores de la tabla
  def mostrar_totales_superiores(df_sub):
    t_ppto = df_sub[col_ppto].sum() if col_ppto and col_ppto in df_sub.columns else 0
    t_venta = df_sub["TOTAL"].sum() if "TOTAL" in df_sub.columns else 0
    t_reserva = df_sub["RESERVA DIA"].sum() if "RESERVA DIA" in df_sub.columns else 0
    
    # Promedio ponderado o promedio simple de ejecución del mes
    t_eje = 0
    if col_eje_mes and col_eje_mes in df_sub.columns and len(df_sub) > 0:
      t_eje = df_sub[col_eje_mes].mean() * 100

    c1, c2, c3, c4 = st.columns(4)
    with c1:
      st.markdown(f"<div class='summary-box'>📦 Total Presupuesto<br><b>${t_ppto:,.0f}</b></div>", unsafe_allow_html=True)
    with c2:
      st.markdown(f"<div class='summary-box'>💰 Total Venta<br><b>${t_venta:,.0f}</b></div>", unsafe_allow_html=True)
    with c3:
      st.markdown(f"<div class='summary-box'>🔥 Total Reserva Día<br><b><b>${t_reserva:,.0f}</b></div>", unsafe_allow_html=True)
    with c4:
      st.markdown(f"<div class='summary-box'>📈 Promedio % Eje Mes<br><b>{t_eje:.1f}%</b></div>", unsafe_allow_html=True)


  with pestana1:
    st.subheader("🔍 Clientes Pendientes por Impactar (Oportunidad)")
    if "IMPACTO" in df_filtrado.columns:
      df_opp = df_filtrado[df_filtrado["IMPACTO"] == 0]
      st.metric(label="Clientes Pendientes en este filtro", value=f"{len(df_opp):,}")
      mostrar_totales_superiores(df_opp)
      st.dataframe(
          formatear_dataframe(df_opp[cols_disponibles]),
          use_container_width=True,
          height=420,
      )
    else:
      st.info("No se encontró la columna IMPACTO.")

  with pestana2:
    st.subheader("✅ Clientes Impactados Exitosamente")
    if "IMPACTO" in df_filtrado.columns:
      df_imp = df_filtrado[df_filtrado["IMPACTO"] == 1]
      st.metric(label="Clientes Impactados en este filtro", value=f"{len(df_imp):,}")
      mostrar_totales_superiores(df_imp)
      st.dataframe(
          formatear_dataframe(df_imp[cols_disponibles]),
          use_container_width=True,
          height=420,
      )
    else:
      st.info("No se encontró la columna IMPACTO.")

  with pestana3:
    st.subheader("📋 Base de Datos General (Filtrada)")
    mostrar_totales_superiores(df_filtrado)
    st.dataframe(
        formatear_dataframe(df_filtrado[cols_disponibles]),
        use_container_width=True,
        height=420,
    )

except Exception as e:
  st.error(
      f"Ocurrió un error al cargar los datos: {e}. Verifica que el archivo"
      " tenga la pestaña 'Export'."
  )
