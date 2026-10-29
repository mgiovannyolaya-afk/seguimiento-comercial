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
    
    # Selectores manuales en la barra lateral para evitar errores de detección
    st.sidebar.header("⚙️ Configuración de Columnas")
    st.sidebar.caption("Selecciona la columna correcta para cada filtro:")
    
    col_canal = st.sidebar.selectbox("Columna de Canal", columnas, index=0)
    col_cliente_nombre = st.sidebar.selectbox("Columna de Nombre de Cliente", columnas, index=min(1, len(columnas)-1))
    col_mes = st.sidebar.selectbox("Columna de Mes", columnas, index=min(2, len(columnas)-1))

    st.sidebar.divider()
    st.sidebar.header("🎯 Filtros Interactivos")

    # 1. Filtro por Canales
    canales_disp = df[col_canal].dropna().unique()
    canales_sel = st.sidebar.multiselect("Selecciona Canal(es):", canales_disp, default=list(canales_disp))
    df_filtrado = df[df[col_canal].isin(canales_sel)]

    # 2. Filtro por Nombre de Cliente (Texto limpio)
    clientes_disp = sorted(df_filtrado[col_cliente_nombre].dropna().unique().astype(str))
    clientes_sel = st.sidebar.multiselect("Selecciona Nombre(s) de Cliente:", clientes_disp)
    if clientes_sel:
        df_filtrado = df_filtrado[df_filtrado[col_cliente_nombre].astype(str).isin(clientes_sel)]

    # 3. Filtro por Meses
    if col_mes in df_filtrado.columns:
        meses_disp = df_filtrado[col_mes].dropna().unique()
        meses_sel = st.sidebar.multiselect("Selecciona Mes(es):", meses_disp, default=list(meses_disp))
        if meses_sel:
            df_filtrado = df_filtrado[df_filtrado[col_mes].isin(meses_sel)]

    # --- EXCLUSIÓN DE COLUMNAS (Quitar Fecha, Año, Códigos, etc.) ---
    palabras_excluir = [
        'fecha', 'año', 'anio', 'proveedor', 'gerente', 'vendedor', 
        'origen', 'ciudad', 'departamento', 'ean', 'producto', 
        'árbol', 'arbol', 'grupo', 'marca', 'línea', 'linea', 
        'unidades', 'cajas', 'código un', 'codigo un', 'cod un'
    ]

    cols_a_mostrar = []
    for col in df_filtrado.columns:
        col_lower = str(col).lower()
        if not any(exc in col_lower for exc in palabras_excluir):
            cols_a_mostrar.append(col)

    df_visualizacion = df_filtrado[cols_a_mostrar].copy()

    # --- CONVERTIR COLUMNAS DE VENTas/VALORES A MONEDA ---
    for col in df_visualizacion.columns:
        if any(p in col.lower() for p in ['venta', 'valor', 'total', 'monto', 'neto', 'precio']):
            df_visualizacion[col] = pd.to_numeric(df_visualizacion[col], errors='coerce').fillna(0)
            df_visualizacion[col] = df_visualizacion[col].apply(lambda x: f"${x:,.0f}")

    st.subheader("📋 Detalle de Clientes y Datos Relevantes")
    st.dataframe(df_visualizacion, use_container_width=True)

except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
