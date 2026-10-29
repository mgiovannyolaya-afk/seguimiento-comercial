import streamlit as st
import pandas as pd

# Configuración de la página en modo ancho
st.set_page_config(page_title="Seguimiento BV Pernod", layout="wide")

st.title("🍾 Seguimiento BV Pernod - Análisis Comercial y Crecimiento YoY")
st.markdown("---")

# Función optimizada para cargar el archivo .xlsb
@st.cache_data
def cargar_datos():
    return pd.read_excel("BV PERNOD TODA.xlsb", engine="pyxlsb")

try:
    df = cargar_datos()
    columnas = df.columns.tolist()

    # Función inteligente para encontrar índices sin mezclar columnas
    def buscar_indice(palabras_clave, posicion_por_defecto):
        for palabra in palabras_clave:
            for idx, col in enumerate(columnas):
                if palabra.lower() in str(col).lower():
                    return idx
        return min(posicion_por_defecto, len(columnas) - 1)

    # --- BARRA LATERAL: CONFIGURACIÓN Y FILTROS ---
    st.sidebar.header("⚙️ Configuración de Columnas")
    st.sidebar.caption("Verifica y asigna cada campo con su columna:")
    
    col_canal = st.sidebar.selectbox("Canal", columnas, index=buscar_indice(['canal'], 0))
    col_regional = st.sidebar.selectbox("Regional / Zona", columnas, index=buscar_indice(['regional', 'zona', 'reg'], 1))
    col_gerente = st.sidebar.selectbox("Gerente de Unidad", columnas, index=buscar_indice(['gerente', 'unidad', 'jefe'], 2))
    col_cliente = st.sidebar.selectbox("Cliente", columnas, index=buscar_indice(['cliente', 'tercero', 'nombre'], 3))
    col_anio = st.sidebar.selectbox("Año", columnas, index=buscar_indice(['año', 'anio', 'year'], 4))
    col_mes = st.sidebar.selectbox("Mes", columnas, index=buscar_indice(['mes', 'month'], 5))
    col_valor = st.sidebar.selectbox("Venta / Valor", columnas, index=buscar_indice(['venta', 'valor', 'total', 'neto'], 6))

    st.sidebar.divider()
    st.sidebar.header("🎯 Filtros Interactivos")

    df_f = df.copy()

    # 1. Filtro Canal
    canales_disp = sorted(df_f[col_canal].dropna().unique().astype(str))
    canales_sel = st.sidebar.multiselect("Selecciona Canal(es):", canales_disp, default=canales_disp)
    if canales_sel:
        df_f = df_f[df_f[col_canal].astype(str).isin(canales_sel)]

    # 2. Filtro Regional
    regional_disp = sorted(df_f[col_regional].dropna().unique().astype(str))
    regional_sel = st.sidebar.multiselect("Selecciona Regional(es):", regional_disp, default=regional_disp)
    if regional_sel:
        df_f = df_f[df_f[col_regional].astype(str).isin(regional_sel)]

    # 3. Filtro Gerente de Unidad
    gerente_disp = sorted(df_f[col_gerente].dropna().unique().astype(str))
    gerente_sel = st.sidebar.multiselect("Selecciona Gerente(s):", gerente_disp, default=gerente_disp)
    if gerente_sel:
        df_f = df_f[df_f[col_gerente].astype(str).isin(gerente_sel)]

    # 4. Filtro de Años y Meses
    anios_disp = sorted(df_f[col_anio].dropna().unique())
    anio_actual_default = [max(anios_disp)] if anios_disp else []
    anios_sel = st.sidebar.multiselect("Selecciona Año(s) base:", anios_disp, default=anio_actual_default)
    
    meses_disp = df_f[col_mes].dropna().unique()
    meses_sel = st.sidebar.multiselect("Selecciona Mes(es):", meses_disp, default=list(meses_disp))

    # Asegurar formato numérico para cálculos
    df_f[col_valor] = pd.to_numeric(df_f[col_valor], errors='coerce').fillna(0)
    df_f[col_anio] = pd.to_numeric(df_f[col_anio], errors='coerce')

    # --- CUERPO PRINCIPAL ---
    st.subheader("📋 Comparativa de Ventas por Cliente (Año Actual vs. Año Anterior)")

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

        # Unir tablas por cliente de forma limpia
        tabla_final = pd.merge(ventas_actual, ventas_anterior, on=col_cliente, how='outer').fillna(0)

        # Calcular variaciones absolutas y porcentuales
        tabla_final['Variación ($)'] = tabla_final[f'Venta {anio_sel}'] - tabla_final[f'Venta {anio_anterior}']
        tabla_final['Variación (%)'] = ((tabla_final[f'Venta {anio_sel}'] / tabla_final[f'Venta {anio_anterior}'].replace(0, 1)) - 1) * 100
        
        # Aplicar formato de moneda a las columnas financieras
        for col_m in [f'Venta {anio_sel}', f'Venta {anio_anterior}', 'Variación ($)']:
            tabla_final[col_m] = tabla_final[col_m].apply(lambda x: f"${x:,.0f}")

        # Formato de porcentaje
        tabla_final['Variación (%)'] = tabla_final['Variación (%)'].apply(lambda x: f"{x:,.2f}%")

        st.info(f"Mostrando comparativa para los meses: **{', '.join(map(str, meses_sel))}** ({anio_sel} vs. {anio_anterior})")
        st.dataframe(tabla_final, use_container_width=True)
    else:
        st.warning("⚠️ Por favor selecciona al menos un Año y un Mes en la barra lateral para generar la comparativa.")

except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo o las columnas: {e}")
