import pandas as pd
import streamlit as st

# Configuración de la página con diseño ancho
st.set_page_config(
    page_title="Gestión Comercial - Meta 70%", page_icon="🎯", layout="wide"
)

# Título principal del tablero
st.title("🎯 Control de Oportunidades y Cumplimiento (Meta 70%)")
st.markdown(
    "Monitoreo ejecutivo de ventas, identificación de clientes y control de"
    " brechas comerciales."
)
st.markdown("---")


# Función para cargar y limpiar los datos del Excel
@st.cache_data
def cargar_y_limpiar_datos(origen):
  df_raw = pd.read_excel(origen, header=None)
  fila_encabezado = 0
  for index, row in df_raw.iterrows():
    if "GU" in row.values:
      fila_encabezado = index
      break

  df = pd.read_excel(origen, header=fila_encabezado)

  # Limpiar columnas basura (Unnamed o vacías)
  df = df.loc[
      :, ~df.columns.astype(str).str.contains("^Unnamed", case=False, na=False)
  ]
  df = df.dropna(how="all", axis=1)
  df = df.dropna(how="all")

  return df


# Cargar datos desde el repositorio de forma automática
try:
  df = cargar_y_limpiar_datos("SGTO X CANAL.xlsx")

  # --- MÉTRICAS SUPERIORES (KPIs) ---
  col1, col2, col3 = st.columns(3)

  total_registros = len(df)
  # Intentar sumar la columna de reserva/venta si existe
  col_reserva = [c for c in df.columns if "RESERVA" in str(c).upper()]

  with col1:
    st.metric(
        label="📊 Total Registros / Clientes", value=f"{total_registros:,}"
    )

  with col2:
    st.metric(label="🎯 Meta de Cumplimiento", value="70%")

  with col3:
    if col_reserva:
      total_venta = df[col_reserva[0]].sum()
      st.metric(
          label="💰 Valor Total Acumulado", value=f"${total_venta:,.2f}"
      )
    else:
      st.metric(label="estado del Canal", value="Activo")

  st.markdown("---")

  # --- FILTROS Y BUSCADOR ---
  st.subheader("🔍 Filtros de Consulta")
  col_filtro1, col_filtro2 = st.columns(2)

  busqueda = col_filtro1.text_input(
      "Buscar cliente o valor específico:", ""
  )

  if busqueda:
    # Filtrar el DataFrame si escriben algo
    df_filtrado = df[
        df.astype(str)
        .apply(lambda x: x.str.contains(busqueda, case=False))
        .any(axis=1)
    ]
  else:
    df_filtrado = df

  # --- VISUALIZACIÓN DE LA TABLA ---
  st.subheader("📋 Detalle de Oportunidades")
  st.dataframe(df_filtrado, use_container_width=True)

except Exception as e:
  st.error(
      "No se pudo cargar el archivo 'SGTO X CANAL.xlsx' automáticamente. Por"
      f" favor verifica que esté en el repositorio. Detalle: {e}"
  )
