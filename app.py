import pandas as pd
import streamlit as st

st.set_page_config(page_title="Gestión Comercial - Meta 70%", page_icon="📈", layout="wide")
st.title("🎯 Control de Oportunidades y Cumplimiento (Meta 70%)")

# Opción para subir el archivo directamente o leerlo del repositorio
archivo_subido = st.file_uploader("Sube tu archivo 'SGTO X CANAL.xlsx'", type=["xlsx"])

if archivo_subido is not None:
    df = pd.read_excel(archivo_subido)
    st.success("¡Archivo cargado con éxito!")
    st.dataframe(df)
else:
    try:
        # Intenta leerlo automáticamente de la carpeta del repositorio
        df = pd.read_excel("SGTO X CANAL.xlsx")
        st.success("Datos cargados automáticamente desde el repositorio.")
        st.dataframe(df)
    except Exception as e:
        st.info("Por favor, sube tu archivo 'SGTO X CANAL.xlsx' usando el botón de arriba para visualizar tu tablero.")
