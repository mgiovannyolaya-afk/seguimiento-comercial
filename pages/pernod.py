import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página en modo ancho
st.set_page_config(page_title="Seguimiento BV Pernod - Interactivo", layout="wide")

st.title("🍾 Seguimiento BV Pernod - Dashboard Comercial")
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

    # --- BARRA LATERAL: CONFIGURACIÓN Y FILTROS ESTRUCTURALES ---
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
    st.sidebar.header("🎯 Filtros Estructurales")

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

    # 4. Filtro de Años en barra lateral
    anios_disp = sorted(df_f[col_anio].dropna().unique())
    anio_actual_default = [max(anios_disp)] if anios_disp else []
    anios_sel = st.sidebar.multiselect("Selecciona Año(s) base:", anios_disp, default=anio_actual_default)

    # Asegurar formato numérico para cálculos
    df_f[col_valor] = pd.to_numeric(df_f[col_valor], errors='coerce').fillna(0)
    df_f[col_anio] = pd.to_numeric(df_f[col_anio], errors='coerce')

    # --- CUERPO PRINCIPAL: FILTRO DE MESES ARRIBA ---
    st.subheader("📅 Selección de Periodo (Meses)")
    
    # Obtener los meses disponibles según los filtros de la barra lateral
    meses_disp = sorted(df_f[col_mes].dropna().unique())
    
    # Filtro de meses ubicado en la parte superior
    col_m1, col_m2 = st.columns([3, 1])
    with col_m1:
        meses_sel = st.multiselect("Filtra y selecciona uno o varios meses:", meses_disp, default=list(meses_disp))
    with col_m2:
        st.write("")
        st.caption(f"Total meses elegidos: **{len(meses_sel)}**")

    st.markdown("---")

    if anios_sel and meses_sel:
        anio_sel = max(anios_sel)
        anio_anterior = anio_sel - 1

        # Filtrar año actual y meses seleccionados
        df_actual = df_f[(df_f[col_anio] == anio_sel) & (df_f[col_mes].isin(meses_sel))]
        
        # Filtrar año anterior y los mismos meses seleccionados
        df_ant = df_f[(df_f[col_anio] == anio_anterior) & (df_f[col_mes].isin(meses_sel))]

        # Totales para KPIs
        total_actual = df_actual[col_valor].sum()
        total_anterior = df_ant[col_valor].sum()
        crecimiento_global = ((total_actual / total_anterior) - 1) * 100 if total_anterior > 0 else 0

        # Mostrar Tarjetas KPI Superiores
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label=f"Ventas Total ({anio_sel})", value=f"${total_actual:,.0f}")
        kpi2.metric(label=f"Ventas Total ({anio_anterior})", value=f"${total_anterior:,.0f}", delta=f"{crecimiento_global:,.2f}% YoY")
        kpi3.metric(label="Meses Seleccionados Arriba", value=f"{len(meses_sel)} mes(es)")

        st.markdown("---")

        # --- SECCIÓN DE GRÁFICOS INTERACTIVOS ---
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader(f"📊 Top Regionales / Zonas ({anio_sel})")
            if not df_actual.empty:
                df_reg = df_actual.groupby(col_regional)[col_valor].sum().reset_index()
                df_reg = df_reg.sort_values(by=col_valor, ascending=False).head(10)
                fig_reg = px.bar(
                    df_reg, x=col_valor, y=col_regional, orientation='h',
                    text_auto='.2s', color=col_valor,
                    color_continuous_scale='Blues'
                )
                fig_reg.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, xaxis_title="Venta ($)", yaxis_title="Regional / Zona")
                st.plotly_chart(fig_reg, use_container_width=True)
            else:
                st.info("No hay datos para mostrar con los filtros seleccionados.")

        with col_g2:
            st.subheader("🏆 Top 10 Clientes")
            if not df_actual.empty:
                df_cli_top = df_actual.groupby(col_cliente)[col_valor].sum().reset_index()
                df_cli_top = df_cli_top.sort_values(by=col_valor, ascending=False).head(10)
                fig_cli = px.bar(
                    df_cli_top, x=col_valor, y=col_cliente, orientation='h',
                    text_auto='.2s', color=col_valor,
                    color_continuous_scale='Greens'
                )
                fig_cli.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, xaxis_title="Venta ($)", yaxis_title="Cliente")
                st.plotly_chart(fig_cli, use_container_width=True)
            else:
                st.info("No hay datos para mostrar en este gráfico.")

        st.markdown("---")

        # --- TABLA DETALLADA DE CLIENTES (YoY) ---
        st.subheader("📋 Detalle y Crecimiento por Cliente (Año Actual vs. Año Anterior)")

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
        
        # Ordenar de mayor a menor venta actual
        tabla_final = tabla_final.sort_values(by=f'Venta {anio_sel}', ascending=False)

        # Formato moneda para ventas y variación absoluta
        for col_m in [f'Venta {anio_sel}', f'Venta {anio_anterior}', 'Variación ($)']:
            tabla_final[col_m] = tabla_final[col_m].apply(lambda x: f"${x:,.0f}")

        # Formato porcentaje
        tabla_final['Variación (%)'] = tabla_final['Variación (%)'].apply(lambda x: f"{x:,.2f}%")

        st.caption(f"Mostrando comparativa para los meses: **{', '.join(map(str, meses_sel))}** ({anio_sel} vs. {anio_anterior})")
        st.dataframe(tabla_final, use_container_width=True)

    else:
        st.warning("⚠️ Por favor selecciona al menos un Año en la barra lateral y al menos un Mes en el selector superior.")

except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo o las columnas: {e}")
