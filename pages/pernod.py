import streamlit as st
import pandas as pd

st.set_page_config(page_title="Seguimiento BV Pernod", layout="wide")

st.title("🍾 Seguimiento BV Pernod - Vista de Clientes")

@st.cache_data
def cargar_datos():
    return pd.read_excel("BV PERNOD TODA.xlsb", engine="pyxlsb")

try:
    df = cargar_datos()
    
    columnas = df.columns.tolist()
    
    def buscar_col(palabras):
        for p in palabras:
            for c in columnas:
                if p.lower() in str(c).lower():
                    return c
        return columnas[0]

    col_canal = buscar_col(['canal'])
    col_cliente = buscar_col(['cliente', 'tercero', 'nombre'])
    col_mes = buscar_col(['mes', 'month'])

    st.sidebar.header("🎯 Filtros Interactivos")

    # 1. Filtro por Canales
    canales_disp = df[col_canal].dropna().unique()
    canales_sel = st.sidebar.multiselect("Selecciona Canal(es):", canales_disp, default=list(canales_disp))
    df_filtrado = df[df[col_canal].isin(canales_sel)]

    # 2. Filtro por Clientes
    clientes_disp = df_filtrado[col_cliente].dropna().unique()
    clientes_sel = st.sidebar.multiselect("Selecciona Cliente(s):", clientes_disp, default=list(clientes_disp))
    if clientes_sel:
        df_filtrado = df_filtrado[df_filtrado[col_cliente].isin(clientes_sel)]

    # 3. Filtro por Meses
    if col_mes in df_filtrado.columns:
        meses_disp = df_filtrado[col_mes].dropna().unique()
        meses_sel = st.sidebar.multiselect("Selecciona Mes(es):", meses_disp, default=list(meses_disp))
        if meses_sel:
            df_filtrado = df_filtrado[df_filtrado[col_mes].isin(meses_sel)]

    # --- EXCLUSIÓN DE COLUMNAS NO DESEADAS ---
    palabras_excluir = [
        'año', 'anio', 'proveedor', 'gerente', 'vendedor', 
        'origen', 'ciudad', 'departamento', 'ean', 'producto', 
        'árbol', 'arbol', 'grupo', 'marca', 'línea', 'linea', 
        'unidades', 'cajas'
    ]

    cols_a_mostrar = []
    for col in df_filtrado.columns:
        col_lower = str(col).lower()
        if not any(exc in col_lower for exc in palabras_excluir):
            cols_a_mostrar.append(col)

    df_visualizacion = df_filtrado[cols_a_mostrar]

    st.subheader("📋 Detalle de Clientes y Datos Relevantes")
    st.dataframe(df_visualizacion, use_container_width=True)

except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
