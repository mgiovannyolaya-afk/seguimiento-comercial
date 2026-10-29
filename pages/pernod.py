import streamlit as st
import pandas as pd

# Configuración de la ventana
st.set_page_config(page_title="Seguimiento BV Pernod", layout="wide")

st.title("🍾 Seguimiento BV Pernod Toda")
st.write("Vista independiente para el informe de Pernod.")

# Carga del archivo .xlsb
try:
    @st.cache_data
    def cargar_datos():
        return pd.read_excel("BV PERNOD TODA.xlsb", engine="pyxlsb")

    df_pernod = cargar_datos()

    # Muestra la tabla de datos completa
    st.subheader("Base de Datos Pernod")
    st.dataframe(df_pernod, use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar el archivo 'BV PERNOD TODA.xlsb': {e}")
