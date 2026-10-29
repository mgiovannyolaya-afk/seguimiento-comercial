import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Seguimiento BV Pernod", layout="wide")

st.title("🍾 Seguimiento BV Pernod - Dashboard Comercial")
st.markdown("---")

@st.cache_data
def cargar_datos():
    return pd.read_excel("BV PERNOD TODA.xlsb", engine="pyxlsb")

try:
    df = cargar_datos()
    columnas = df.columns.tolist()

    # Mapeo por palabras clave exactas para evitar que se dupliquen las columnas
    def buscar_columna_exacta(palabras_clave, fallback_index=0):
        for pk in palabras_clave:
            for col in columnas:
                if pk.lower() == str(col).lower():
                    return col
        for pk in palabras_clave:
            for col in columnas:
                if pk.lower() in str(col).lower():
                    return col
        return columnas[fallback_index] if fallback_index < len(columnas) else columnas[0]

    # --- CONFIGURACIÓN EN LA BARRA LATERAL ---
    st.sidebar.header("⚙️ Mapeo de Columnas")
    st.sidebar.caption("Ajusta si los nombres no coinciden exactamente:")

    # Selección explícita con valores por defecto bien buscados
    col_canal = st.sidebar.selectbox("Canal", columnas, index=columnas.index(buscar_columna_exacta(['Canal', 'Canal de Venta'], 0)))
    col_regional = st.sidebar.selectbox("Regional / Zona", columnas, index=columnas.index(buscar_columna_exacta(['Código Zona', 'Regional', 'Zona'], 1)))
    col_gerente = st.sidebar.selectbox("Gerente de Unidad", columnas, index=columnas.index(buscar_columna_exacta(['Gerente Zona', 'Gerente Unidad', 'Gerente'], 2)))
    col_cliente = st.sidebar.selectbox("Cliente", columnas, index=columnas.index(buscar_columna_exacta(['Nombre Cliente', 'Cliente', 'Documento Cliente'], 3)))
    col_anio = st.sidebar.selectbox("Año", columnas, index=columnas.index(buscar_columna_exacta(['Año', 'Anio', 'Year'], 4)))
    col_mes = st.sidebar.selectbox("Mes", columnas, index=columnas.index(buscar_columna_exacta(['Mes', 'Month'], 5)))
    col_valor = st.sidebar.selectbox("Venta / Valor", columnas, index=columnas.index(buscar_columna_exacta(['Ventas Det', 'Venta', 'Valor', 'Total'], 6)))

    st.sidebar.divider()
    st.sidebar.header("🎯 Filtros Estructurales")

    df_f = df.copy()

    # Filtro Canal
    canales_disp = sorted(df_f[col_canal].dropna().unique().astype(str))
    canales_sel = st.sidebar.multiselect("Canal(es):", canales_disp, default=canales_disp)
    if canales_sel:
        df_f = df_f[df_f[col_canal].astype(str).isin(canales_sel)]

    # Filtro Regional
    regional_disp = sorted(df_f[col_regional].dropna().unique().astype(str))
    regional_sel = st.sidebar.multiselect("Regional(es):", regional_disp, default=regional_disp)
    if regional_sel:
        df_f = df_f[df_f[col_regional].astype(str).isin(regional_sel)]

    # Filtro Gerente
    gerente_disp = sorted(df_f[col_gerente].dropna().unique().astype(str))
    gerente_sel = st.sidebar.multiselect("Gerente(s):", gerente_disp, default=gerente_disp)
    if gerente_sel:
        df_f = df_f[df_f[col_gerente].astype(str).isin(gerente_sel)]

    # Filtro Año Base
    anios_disp = sorted(df_f[col_anio].dropna().unique())
    anio_base = st.sidebar.selectbox("Año Base Comparativo:", anios_disp, index=len(anios_disp)-1 if anios_disp else 0)

    # Asegurar tipos de datos numéricos
    df_f[col_valor] = pd.to_numeric(df_f[col_valor], errors='coerce').fillna(0)
    df_f[col_anio] = pd.to_numeric(df_f[col_anio], errors='coerce')

    # --- CUERPO PRINCIPAL: BOTONES INTERACTIVOS DE MESES CON UN CLIC ---
    st.subheader("📅 Filtro de Meses (Un Clic para Seleccionar/Desseleccionar)")

    # Ordenar meses cronológicamente si es posible
    meses_ordenados = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    meses_existentes = df_f[col_mes].dropna().unique()
    meses_disp = [m for m in meses_ordenados if m in meses_existentes] if any(m in meses_existentes for m in meses_ordenados) else sorted(meses_existentes)

    # Botones o Segmented Control para seleccionar con un clic
    if hasattr(st, "segmented_control"):
        meses_sel = st.segmented_control("Selecciona los meses activos:", options=meses_disp, default=meses_disp, selection_mode="multi")
    else:
        meses_sel = st.multiselect("Selecciona los meses activos:", options=meses_disp, default=list(meses_disp))

    st.markdown("---")

    if anio_base and meses_sel:
        anio_sel = int(anio_base)
        anio_anterior = anio_sel - 1

        # Filtrado por período seleccionado arriba
        df_actual = df_f[(df_f[col_anio] == anio_sel) & (df_f[col_mes].isin(meses_sel))]
        df_ant = df_f[(df_f[col_anio] == anio_anterior) & (df_f[col_mes].isin(meses_sel))]

        # Cálculos generales para KPIs
        total_actual = df_actual[col_valor].sum()
        total_anterior = df_ant[col_valor].sum()
        crecimiento_global = ((total_actual / total_anterior) - 1) * 100 if total_anterior > 0 else 0

        # Tarjetas de Métricas principales
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label=f"Ventas Total ({anio_sel})", value=f"${total_actual:,.0f}")
        kpi2.metric(label=f"Ventas Total ({anio_anterior})", value=f"${total_anterior:,.0f}", delta=f"{crecimiento_global:,.2f}% YoY")
        kpi3.metric(label="Meses Evaluados", value=f"{len(meses_sel)} mes(es)")

        st.markdown("---")

        # --- GRÁFICOS INTERACTIVOS ---
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader(f"📊 Ventas por Regional ({anio_sel})")
            if not df_actual.empty:
                df_reg = df_actual.groupby(col_regional)[col_valor].sum().reset_index()
                df_reg = df_reg.sort_values(by=col_valor, ascending=False).head(10)
                fig_reg = px.bar(
                    df_reg, x=col_valor, y=col_regional, orientation='h',
                    text_auto='.2s', color=col_valor, color_continuous_scale='Blues'
                )
                fig_reg.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, xaxis_title="Venta ($)", yaxis_title="Regional")
                st.plotly_chart(fig_reg, use_container_width=True)
            else:
                st.info("Sin datos para los filtros seleccionados.")

        with col_g2:
            st.subheader("🏆 Top 10 Clientes")
            if not df_actual.empty:
                df_cli_top = df_actual.groupby(col_cliente)[col_valor].sum().reset_index()
                df_cli_top = df_cli_top.sort_values(by=col_valor, ascending=False).head(10)
                fig_cli = px.bar(
                    df_cli_top, x=col_valor, y=col_cliente, orientation='h',
                    text_auto='.2s', color=col_valor, color_continuous_scale='Greens'
                )
                fig_cli.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, xaxis_title="Venta ($)", yaxis_title="Cliente")
                st.plotly_chart(fig_cli, use_container_width=True)
            else:
                st.info("Sin datos para los filtros seleccionados.")

        st.markdown("---")

        # --- TABLA COMPARATIVA DE CLIENTES (YoY) ---
        st.subheader("📋 Detalle por Cliente (Año Actual vs. Año Anterior)")

        ventas_actual = df_actual.groupby(col_cliente)[col_valor].sum().reset_index()
        ventas_actual.rename(columns={col_valor: f'Venta {anio_sel}'}, inplace=True)

        ventas_anterior = df_ant.groupby(col_cliente)[col_valor].sum().reset_index()
        ventas_anterior.rename(columns={col_valor: f'Venta {anio_anterior}'}, inplace=True)

        tabla_final = pd.merge(ventas_actual, ventas_anterior, on=col_cliente, how='outer').fillna(0)

        tabla_final['Variación ($)'] = tabla_final[f'Venta {anio_sel}'] - tabla_final[f'Venta {anio_anterior}']
        tabla_final['Variación (%)'] = ((tabla_final[f'Venta {anio_sel}'] / tabla_final[f'Venta {anio_anterior}'].replace(0, 1)) - 1) * 100
        
        tabla_final = tabla_final.sort_values(by=f'Venta {anio_sel}', ascending=False)

        # Formatos finales
        for col_m in [f'Venta {anio_sel}', f'Venta {anio_anterior}', 'Variación ($)']:
            tabla_final[col_m] = tabla_final[col_m].apply(lambda x: f"${x:,.0f}")

        tabla_final['Variación (%)'] = tabla_final['Variación (%)'].apply(lambda x: f"{x:,.2f}%")

        st.caption(f"Comparativa activa para: **{', '.join(map(str, meses_sel))}** ({anio_sel} vs. {anio_anterior})")
        st.dataframe(tabla_final, use_container_width=True)

    else:
        st.warning("⚠️ Selecciona un Año Base y al menos un Mes arriba.")

except Exception as e:
    st.error(f"Ocurrió un error al procesar la aplicación: {e}")
