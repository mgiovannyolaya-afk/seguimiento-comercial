import streamlit as st
import pandas as pd

st.set_page_config(page_title="Seguimiento BV Pernod", layout="wide")

st.title("🍾 Seguimiento BV Pernod - Análisis de Clientes y Crecimiento YoY")

@st.cache_data
def cargar_datos():
    return pd.read_excel("BV PERNOD TODA.xlsb", engine="pyxlsb")

try:
    df = cargar_datos()
    columnas = df.columns.tolist()

    # Función auxiliar para detectar columnas automáticamente
    def buscar_col(palabras):
        for p in palabras:
            for c in columnas:
                if p.lower() in str(c).lower():
                    return c
        return columnas[0]

    st.sidebar.header("⚙️ Configuración de Columnas")
    st.sidebar.caption("Verifica y ajusta si el nombre difiere en tu Excel:")
    
    col_canal = st.sidebar.selectbox("Columna de Canal", columnas, index=columnas.index(buscar_col(['canal'])))
    col_regional = st.sidebar.selectbox("Columna de Regional", columnas, index=columnas.index(buscar_col(['regional', 'zona', 'reg'])))
    col_gerente = st.sidebar.selectbox("Columna de Gerente de Unidad", columnas, index=columnas.index(buscar_col(['gerente', 'unidad', 'jefe'])))
    col_cliente = st.sidebar.selectbox("Columna de Cliente", columnas, index=columnas.index(buscar_col(['cliente', 'tercero', 'nombre'])))
    col_anio = st.sidebar.selectbox("Columna de Año", columnas, index=columnas.index(buscar_col(['año', 'anio', 'year'])))
    col_mes = st.sidebar.selectbox("Columna de Mes", columnas, index=columnas.index(buscar_col(['mes', 'month'])))
    col_valor = st.sidebar.selectbox("Columna de Venta / Valor", columnas, index=columnas.index(buscar_col(['venta', 'valor', 'total', 'neto'])))

    st.sidebar.divider()
    st.sidebar.header("🎯 Filtros Interactivos")

    # 1. Filtro Canal
    canales_disp = sorted(df[col_canal].dropna().unique().astype(str))
    canales_sel = st.sidebar.multiselect("Selecciona Canal(es):", canales_disp, default=canales_disp)
    df_f = df[df[col_canal].astype(str).isin(canales_sel)]

    # 2. Filtro Regional
    regional_disp = sorted(df_f[col_regional].dropna().unique().astype(str))
    regional_sel = st.sidebar.multiselect("Selecciona Regional(es):", regional_disp, default=regional_disp)
    df_f = df_f[df_f[col_regional].astype(str).isin(regional_sel)]

    # 3. Filtro Gerente de Unidad
    gerente_disp = sorted(df_f[col_gerente].dropna().unique().astype(str))
    gerente_sel = st.sidebar.multiselect("Selecciona Gerente(s) de Unidad:", gerente_disp, default=gerente_disp)
    df_f = df_f[df_f[col_gerente].astype(str).isin(gerente_sel)]

    # 4. Filtro de Años y Meses
    anios_disp = sorted(df_f[col_anio].dropna().unique())
    anio_actual_default = [max(anios_disp)] if anios_disp else []
    anios_sel = st.sidebar.multiselect("Selecciona Año(s) base:", anios_disp, default=anio_actual_default)
    
    meses_disp = df_f[col_mes].dropna().unique()
    meses_sel = st.sidebar.multiselect("Selecciona Mes(es):", meses_disp, default=list(meses_disp))

    # Asegurar valores numéricos
    df_f[col_valor] = pd.to_numeric(df_f[col_valor], errors='coerce').fillna(0)
    df_f[col_anio] = pd.to_numeric(df_f[col_anio], errors='coerce')

    st.divider()
    st.subheader("📋 Comparativa de Ventas por Cliente (Año Actual vs Año Anterior)")

    if anios_sel and meses_sel:
        anio_sel = max(anios_sel)
        anio_anterior = anio_sel - 1

        # Filtrar año actual y meses seleccionados
        df_actual = df_f[(df_f[col_anio] == anio_sel) & (df_f[col_mes].isin(meses_sel))]
        
        # Filtrar año anterior y los mismos meses
        df_ant = df_f[(df_f[col_anio] == anio_anterior) & (df_f[col_mes].isin(meses_sel))]

        # Agrupar ventas por cliente
        ventas_actual = df_actual.groupby(col_cliente)[col_valor].sum().reset_index()
        ventas_actual.rename(columns={col_valor: f'Venta {anio_sel}'}, inplace=True)

        ventas_anterior = df_ant.groupby(col_cliente)[col_valor].sum().reset_index()
        ventas_anterior.rename(columns={col_valor: f'Venta {anio_anterior}'}, inplace=True)

        # Unir tablas por cliente
        tabla_final = pd.merge(ventas_actual, ventas_anterior, on=col_cliente, how='outer').fillna(0)

        # Calcular variaciones
        tabla_final['Variación ($)'] = tabla_final[f'Venta {anio_sel}'] - tabla_final[f'Venta {anio_anterior}']
        tabla_final['Variación (%)'] = ((tabla_final[f'Venta {anio_sel}'] / tabla_final[f'Venta {anio_anterior}'].replace(0, 1)) - 1) * 100
        
        # Formato moneda para ventas y variación absoluta
        for col_m in [f'Venta {anio_sel}', f'Venta {anio_anterior}', 'Variación ($)']:
            tabla_final[col_m] = tabla_final[col_m].apply(lambda x: f"${x:,.0f}")

        # Formato porcentaje
        tabla_final['Variación (%)'] = tabla_final['Variación (%)'].apply(lambda x: f"{x:,.2f}%")

        st.caption(f"Mostrando comparativa para los meses: **{', '.join(map(str, meses_sel))}** ({anio_sel} vs {anio_anterior})")
        st.dataframe(tabla_final, use_container_width=True)
    else:
        st.info("💡 Por favor selecciona al menos un Año y un Mes en la barra lateral para generar la tabla comparativa.")

except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo: {e}")
