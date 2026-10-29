import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Gestión Comercial - Meta 70%", page_icon="📈", layout="wide"
)

st.title("🎯 Control de Oportunidades y Cumplimiento (Meta 70%)")
st.markdown(
    "Tablero conectado para identificar clientes con Venta 0 y cerrar la brecha"
    " del 70%."
)


# Función para cargar y limpiar el Excel automáticamente
def cargar_datos(origen):
  df_raw = pd.read_excel(origen, header=None)
  # Buscar automáticamente la fila que contiene "GU" para usarla como encabezado
  fila_encabezado = 0
  for index, row in df_raw.iterrows():
    if "GU" in row.values:
      fila_encabezado = index
      break

  # Recargar con el encabezado correcto y limpiar filas vacías
  df = pd.read_excel(origen, header=fila_encabezado)
  df = df.dropna(how="all")  # Eliminar filas completamente vacías
  return df


# Opción para subir archivo o leer del repositorio
archivo_subido = st.file_uploader(
    "Sube tu archivo 'SGTO X CANAL.xlsx'", type=["xlsx"]
)

if archivo_subido is not None:
  try:
    df = cargar_datos(archivo_subido)
    st.success("¡Archivo cargado con éxito!")
    st.dataframe(df, use_container_width=True)
  except Exception as e:
    st.error(f"Error al leer el archivo subido: {e}")
else:
  try:
    df = cargar_datos("SGTO X CANAL.xlsx")
    st.success("Datos cargados automáticamente desde el repositorio.")
    st.dataframe(df, use_container_width=True)
  except Exception as e:
    st.info(
        "Por favor, sube tu archivo 'SGTO X CANAL.xlsx' usando el botón de"
        " arriba para visualizar tu tablero."
    )
