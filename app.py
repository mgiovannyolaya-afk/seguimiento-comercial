import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Diagnóstico - Gestión Comercial", page_icon="🔍", layout="wide"
)

st.title("🔍 Diagnóstico del archivo Excel")
st.markdown(
    "Este panel nos mostrará exactamente cómo lee Streamlit tu archivo"
    " 'SGTO X CANAL.xlsx'."
)

try:
  # Revisar las pestañas (hojas) que tiene el archivo Excel
  excel_file = pd.ExcelFile("SGTO X CANAL.xlsx")
  st.success(
      f"¡Archivo encontrado con éxito! Hojas disponibles en el Excel:"
      f" {excel_file.sheet_names}"
  )

  # Leer el archivo en bruto sin modificar nada para ver su estructura real
  df_raw = pd.read_excel("SGTO X CANAL.xlsx", header=None)

  st.subheader("Vista previa de las primeras 10 filas del Excel en bruto:")
  st.dataframe(df_raw.head(10), use_container_width=True)

except Exception as e:
  st.error(f"No se pudo leer el archivo. Detalle del error: {e}")
  st.info(
      "Asegúrate de que el archivo 'SGTO X CANAL.xlsx' esté subido en la raíz"
      " principal de tu repositorio en GitHub."
  )
