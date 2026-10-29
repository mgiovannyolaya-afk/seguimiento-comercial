import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Gestión Comercial - Meta 70%", page_icon="📈", layout="wide"
)

st.title("🎯 Control de Oportunidades y Cumplimiento (Meta 70%)")
st.markdown(
    "Tablero conectado para identificar clientes con Venta 0 y cerrar la brecha del 70%."
)

# Opción para subir el archivo directamente o leerlo del repositorio
archivo_subido = st.file_uploader(
    "Sube tu archivo 'SGTO X CANAL.xlsx'", type=["xlsx"]
)

if archivo_subido is not None:
  try:
    df = pd.read_excel(archivo_subido, header=1)
    st.success("¡Archivo cargado con éxito!")
    st.dataframe(df, use_container_width=True)
  except Exception as e:
    st.error(f"Error al leer el archivo subido: {e}")
else:
  try:
    # Intenta leerlo automáticamente de la carpeta del repositorio
    df = pd.read_excel("SGTO X CANAL.xlsx", header=1)
    st.success("Datos cargados automáticamente desde el repositorio.")
    st.dataframe(df, use_container_width=True)
  except Exception as e:
    st.info(
        "Por favor, sube tu archivo 'SGTO X CANAL.xlsx' usando el botón de"
        " arriba para visualizar tu tablero."
    )
