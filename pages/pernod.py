import streamlit as st
import pandas as pd

st.set_page_config(page_title="Seguimiento BV Pernod", layout="wide")

st.title("🍾 Seguimiento BV Pernod - Análisis Comercial y Crecimiento")

@st.cache_data
def cargar_datos():
    return pd.read_excel("BV PERNOD TODA.xlsb", engine="pyxlsb")

try:
    df = cargar_datos()
    
    st.success("¡Base de datos de Pernod cargada con éxito!")
    
    # Expandible para ver las columnas originales del Excel por si necesitas identificarlas
    with st.expander("🔍 Ver nombres de columnas disponibles en tu Excel"):
        st.write(df.columns.tolist())

    st.sidebar.header("⚙️ Mapeo de Columnas")
    st.sidebar.caption("Asegúrate de que coincidan con las de tu Excel si difieren:")
    
    columnas = df.columns.tolist()
    
    # Intentar detectar nombres comunes automáticamente o permitir seleccionarlos
    def buscar_columna_sugerida(lista, palabras_clave):
        for palabra in palabras_clave:
            for col in lista:
                if palabra.lower() in str(col).lower():
                    return col
        return lista[0] if lista else None

    col_canal = st.sidebar.selectbox("Columna de Canal", columnas, index=columnas.index(buscar_columna_sugerida(columnas, ['canal'])))
    col_cliente = st.sidebar.selectbox("Columna de Cliente", columnas, index=columnas.index(buscar_columna_sugerida(columnas, ['cliente', 'tercero', 'nombre'])))
    col_anio = st.sidebar.selectbox("Columna de Año", columnas, index=columnas.index(buscar_columna_sugerida(columnas, ['año', 'anio', 'year'])))
    col_mes = st.sidebar.selectbox("Columna de Mes", columnas, index=columnas.index(buscar_columna_sugerida(columnas, ['mes', 'month'])))
    col_valor = st.sidebar.selectbox("Columna de Venta / Valor", columnas, index=columnas.index(buscar_columna_sugerida(columnas, ['venta', 'valor', 'total', 'monto', 'neto'])))

    st.sidebar.divider()
    st.sidebar.subheader("🎯 Filtros Interactivos")

    # 1. Filtro por Canales (Selección múltiple)
    canales_disp = df[col_canal].dropna().unique()
    canales_sel = st.sidebar.multiselect("Selecciona Canal(es):", canales_disp, default=list(canales_disp))
    df_filtrado = df[df[col_canal].isin(canales_sel)]

    # 2. Filtro por Clientes (dependiente del canal seleccionado)
    clientes_disp = df_filtrado[col_cliente].dropna().unique()
    clientes_sel = st.sidebar.multiselect("Selecciona Cliente(s):", clientes_disp, default=list(clientes_disp))
    if clientes_sel:
        df_filtrado = df_filtrado[df_filtrado[col_cliente].isin(clientes_sel)]

    # 3. Filtro por Años
    anios_disp = sorted(df_filtrado[col_anio].dropna().unique())
    anios_sel = st.sidebar.multiselect("Selecciona Año(s):", anios_disp, default=anios_disp)
    if anios_sel:
        df_filtrado = df_filtrado[df_filtrado[col_anio].isin(anios_sel)]

    # 4. Filtro por Meses (Selección múltiple)
    meses_disp = df_filtrado[col_mes].dropna().unique()
    meses_sel = st.sidebar.multiselect("Selecciona Mes(es):", meses_disp, default=list(meses_disp))
    if meses_sel:
        df_filtrado = df_filtrado[df_filtrado[col_mes].isin(meses_sel)]

    # Mostrar tabla filtrada principal
    st.subheader("📋 Detalle de Datos Filtrados")
    st.dataframe(df_filtrado, use_container_width=True)

    st.divider()
    st.subheader("📈 Análisis Financiero: Promedios y Crecimiento Interanual (YoY)")

    if not df_filtrado.empty:
        # Asegurar que la columna de valor sea numérica
        df_filtrado[col_valor] = pd.to_numeric(df_filtrado[col_valor], errors='coerce').fillna(0)

        # Agrupar para obtener totales por Año y Mes
        resumen = df_filtrado.groupby([col_anio, col_mes])[col_valor].sum().reset_index()
        resumen = resumen.sort_values(by=[col_anio, col_mes])
        
        # Calcular Promedio Móvil de 3 meses
        resumen['Promedio_3_Meses'] = resumen[col_valor].rolling(window=3, min_periods=1).mean()

        # Tabla pivote para comparar Años vs Meses (Ej: Mayo 2025 vs Mayo 2026)
        pivote_anual = df_filtrado.pivot_table(index=col_mes, columns=col_anio, values=col_valor, aggfunc='sum')

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📊 Totales y Promedio Móvil (3 Meses)")
            st.dataframe(resumen, use_container_width=True)

        with col2:
            st.markdown("### 🔄 Comparativa de Crecimiento (YoY)")
            anos_cols = sorted([c for c in pivote_anual.columns])
            
            if len(anos_cols) >= 2:
                # Tomamos los últimos dos años disponibles en los filtros para la comparativa rápida
                col_reciente = anos_cols[-1]
                col_anterior = anos_cols[-2]
                
                pivote_anual['Diferencia Absoluta'] = pivote_anual[col_reciente] - pivote_anual[col_anterior]
                pivote_anual['% Crecimiento (YoY)'] = ((pivote_anual[col_reciente] / pivote_anual[col_anterior]) - 1) * 100
                
                st.caption(f"Comparando: **{col_reciente} vs {col_anterior}**")
                st.dataframe(pivote_anual, use_container_width=True)
            else:
                st.dataframe(pivote_anual, use_container_width=True)
                st.info("💡 Selecciona al menos dos años en el filtro lateral para calcular automáticamente el porcentaje de crecimiento interanual.")

except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo o las columnas: {e}")
