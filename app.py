import pandas as pd
import streamlit as st

# Configuración de la página con diseño ancho y moderno
st.set_page_config(
    page_title="Gestión Comercial - Meta 70%", page_icon="🎯", layout="wide"
)

# Título principal del tablero
st.title("🎯 Control de Oportunidades y Cumplimiento (Meta 70%)")
st.markdown(
    "Monitoreo comercial interactivo basado en la hoja de control operativo."
)
st.markdown("---")


# Carga de datos con caché de Streamlit para máxima velocidad
@st.cache_data
def cargar_datos():
  return pd.read_excel("SGTO X CANAL.xlsx", sheet_name="Export")


try:
  df = cargar_datos()

  # --- BARRA LATERAL DE FILTROS INTERACTIVOS ---
  st.sidebar.header("🔍 Filtros de Segmentación")

  # Filtro de Supervisor
  supervisores = ["Todos"] + sorted(
      df["Supervisor"].dropna().astype(str).unique().tolist()
  )
  sup_seleccionado = st.sidebar.selectbox("Supervisor", supervisores)

  if sup_seleccionado != "Todos":
    df_temp = df[df["Supervisor"].astype(str) == sup_seleccionado]
  else:
    df_temp = df

  # Filtro de Zona
  zonas = ["Todas"] + sorted(
      df_temp["Zona"].dropna().astype(str).unique().tolist()
  )
  zona_seleccionada = st.sidebar.selectbox("Zona", zonas)

  if zona_seleccionada != "Todas":
    df_temp = df_temp[df_temp["Zona"].astype(str) == zona_seleccionada]

  # Filtro de Vendedor
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

  # --- TARJETAS DE MÉTRICAS SUPERIORES (KPIs) ---
  col1, col2, col3, col4 = st.columns(4)

  total_clientes = len(df_filtrado)
  total_reserva = pd.to_numeric(
      df_filtrado["Reserva"], errors="coerce"
  ).sum()
  total_cartera = pd.to_numeric(
      df_filtrado["Total Cartera"], errors="coerce"
  ).sum()

  with col1:
    st.metric(label="📊 Clientes / Registros", value=f"{total_clientes:,}")
  with col2:
    st.metric(label="🎯 Meta Comercial", value="70%")
  with col3:
    st.metric(label="💰 Total Reserva", value=f"${total_reserva:,.0f}")
  with col4:
    st.metric(label="⚠️ Cartera Total", value=f"${total_cartera:,.0f}")

  st.markdown("---")

  # --- PESTAÑAS DE NAVEGACIÓN ---
  pestana1, pestana2, pestana3 = st.tabs([
      "📋 Detalle Comercial",
      "🔍 Clientes y Oportunidades",
      "📈 Resumen por Zona",
  ])

  with pestana1:
    st.subheader("Base de Datos Filtrada")
    columnas_principales = [
        "Supervisor",
        "Zona",
        "Vendedor",
        "Nit Cliente",
        "Nombre Cliente",
        "Ciudad",
        "Canal",
        "Reserva",
        "Total Cartera",
        "%Eje Ppto",
    ]
    cols_disponibles = [
        c for c in columnas_principales if c in df_filtrado.columns
    ]
    st.dataframe(
        df_filtrado[cols_disponibles], use_container_width=True, height=450
    )

  with pestana2:
    st.subheader("Análisis de Oportunidades y Venta")
    if "Reserva" in df_filtrado.columns:
      df_oportunidad = df_filtrado[
          ["Nombre Cliente", "Canal", "Vendedor", "Reserva", "Cupo"]
      ].sort_values(by="Reserva", ascending=False)
      st.dataframe(df_oportunidad, use_container_width=True, height=450)
    else:
      st.info("No se encontró la columna de reserva para este análisis.")

  with pestana3:
    st.subheader("Consolidado por Zona y Vendedor")
    if "Zona" in df_filtrado.columns and "Reserva" in df_filtrado.columns:
      resumen_zona = (
          df_filtrado.groupby(["Zona", "Vendedor"])["Reserva"]
          .sum()
          .reset_index()
      )
      st.dataframe(resumen_zona, use_container_width=True, height=450)
    else:
      st.info("Datos insuficientes para agrupar por zona.")

except Exception as e:
  st.error(f"Error al procesar los datos: {e}")
