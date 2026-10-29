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


# Carga optimizada y rápida usando header directo
@st.cache_data
def cargar_datos(origen):
  # Lee directamente desde la fila de encabezados correcta
  df = pd.read_excel(origen, header=1)

  # Eliminar columnas basura o vacías (que dicen Unnamed)
  df = df.loc[
      :, ~df.columns.astype(str).str.contains("^Unnamed", case=False, na=False)
  ]
  df = df.dropna(how="all", axis=1)
  df = df.dropna(how="all")
  return df


try:
  # Cargar datos de forma automática desde el repositorio
  df = cargar_datos("SGTO X CANAL.xlsx")

  # --- TARJETAS DE MÉTRICAS (KPIs) ---
  col1, col2, col3 = st.columns(3)

  total_registros = len(df)
  col_reserva = [c for c in df.columns if "RESERVA" in str(c).upper()]

  with col1:
    st.metric(
        label="📊 Total Registros / Clientes", value=f"{total_registros:,}"
    )

  with col2:
    st.metric(label="🎯 Meta de Cumplimiento", value="70%")

  with col3:
    if col_reserva:
      # Limpiar y sumar numéricamente
      total_venta = pd.to_numeric(df[col_reserva[0]], errors="coerce").sum()
      st.metric(
          label="💰 Valor Total Acumulado", value=f"${total_venta:,.2f}"
      )
    else:
      st.metric(label="Estado del Sistema", value="Activo")

  st.markdown("---")

  # --- VISUALIZACIÓN DE LA TABLA ---
  st.subheader("📋 Detalle de Oportunidades")
  st.dataframe(df, use_container_width=True)

except Exception as e:
  st.error(f"No se pudo cargar el archivo automáticamente. Detalle: {e}")
  st.info(
      "Verifica que el archivo 'SGTO X CANAL.xlsx' esté en la misma carpeta"
      " principal de GitHub."
  )
