import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="SEGUIMIENTO PERNOD RICARD", layout="wide")

# Título llamativo
st.title("🍾 SEGUIMIENTO PERNOD RICARD 🥂")
st.markdown("---")

@st.cache_data
def cargar_datos():
    xls_path = "BV PERNOD TODA.xlsb"
    # Cargamos la base principal de ventas (primera hoja)
    df_ventas = pd.read_excel(xls_path, sheet_name=0, engine="pyxlsb")
    
    try:
        # Cargamos la hoja de presupuestos buscando el nombre que contenga 'ppto' o tomando la segunda hoja
        xl = pd.ExcelFile(xls_path, engine="pyxlsb")
        nombres_hojas = xl.sheet_names
        nombre_ppto_real = next((h for h in nombres_hojas if 'ppto' in h.lower()), nombres_hojas[1] if len(nombres_hojas) > 1 else 0)
        df_ppto = pd.read_excel(xls_path, sheet_name=nombre_ppto_real, engine="pyxlsb")
    except Exception as e:
        df_ppto = pd.DataFrame()
        
    return df_ventas, df_ppto

try:
    df, df_ppto = cargar_datos()
    columnas = df.columns.tolist()

    # Detección automática inteligente de columnas en ventas
    def detectar_columna(palabras_clave, fallback_idx=0):
        for pk in palabras_clave:
            for col in columnas:
                if pk.lower() == str(col).lower():
                    return col
        for pk in palabras_clave:
            for col in columnas:
                if pk.lower() in str(col).lower():
                    return col
        return columnas[fallback_idx] if fallback_idx < len(columnas) else columnas[0]

    col_regional = detectar_columna(['Código UN', 'Cod UN', 'Regional', 'Región'], 1)
    col_canal = detectar_columna(['Tipo de Cliente', 'Tipo cliente', 'Canal', 'Canal de Venta'], 0)
    col_gerente = detectar_columna(['Gerente Zona', 'Gerente Unidad', 'Supervisor', 'Gerente'], 2)
    col_zona = detectar_columna(['Código Zona', 'Codigo Zona', 'Cod Zona', 'Id Zona'], 3)
    col_cliente = detectar_columna(['Nombre Cliente', 'Cliente', 'Documento Cliente'], 4)
    col_referencia = detectar_columna(['Referencia', 'Artículo', 'Articulo', 'SKU', 'Producto', 'Item', 'Descripción Item'], 5)
    col_anio = detectar_columna(['Año', 'Anio', 'Year'], 6)
    col_mes = detectar_columna(['Mes', 'Month'], 7)
    col_valor = detectar_columna(['Ventas Det', 'Venta', 'Valor', 'Total'], 8)

    # Limpieza de datos numéricos
    df[col_valor] = pd.to_numeric(df[col_valor], errors='coerce').fillna(0)
    df[col_anio] = pd.to_numeric(df[col_anio], errors='coerce')

    # --- BARRA LATERAL: FILTROS GLOBALES ---
    st.sidebar.header("🎯 Filtros Globales")
    df_f = df.copy()

    opciones_reg = ["Todos"] + sorted([str(x) for x in df_f[col_regional].dropna().unique()])
    sel_reg = st.sidebar.selectbox("Código UN (Regional)", opciones_reg, index=0)
    df_f_global = df_f.copy()
    if sel_reg != "Todos":
        df_f = df_f[df_f[col_regional].astype(str) == sel_reg]

    opciones_canal = ["Todos"] + sorted([str(x) for x in df_f[col_canal].dropna().unique()])
    sel_canal = st.sidebar.selectbox("Canal", opciones_canal, index=0)
    if sel_canal != "Todos":
        df_f = df_f[df_f[col_canal].astype(str) == sel_canal]
        df_f_global = df_f_global[df_f_global[col_canal].astype(str) == sel_canal]

    opciones_gerente = ["Todos"] + sorted([str(x) for x in df_f[col_gerente].dropna().unique()])
    sel_gerente = st.sidebar.selectbox("Supervisor", opciones_gerente, index=0)
    if sel_gerente != "Todos":
        df_f = df_f[df_f[col_gerente].astype(str) == sel_gerente]
        df_f_global = df_f_global[df_f_global[col_gerente].astype(str) == sel_gerente]

    opciones_zona = ["Todos"] + sorted([str(x) for x in df_f[col_zona].dropna().unique()])
    sel_zona = st.sidebar.selectbox("Código Zona", opciones_zona, index=0)
    if sel_zona != "Todos":
        df_f = df_f[df_f[col_zona].astype(str) == sel_zona]
        df_f_global = df_f_global[df_f_global[col_zona].astype(str) == sel_zona]

    # --- CREACIÓN DE PESTAÑAS PRINCIPALES ---
    tab1, tab2, tab3 = st.tabs([
        "📊 Dashboard General & Clientes", 
        "📦 Análisis de Referencias (YoY)", 
        "🎯 Presupuesto & Zonas (PPTO)"
    ])

    orden_meses_ref = [
        "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic",
        "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    def obtener_peso_mes(m):
        m_lower = str(m).strip().lower()
        for idx, ref in enumerate(orden_meses_ref):
            if ref in m_lower:
                return idx
        return 999

    def color_variacion(val):
        try:
            if isinstance(val, (int, float)):
                if val > 0: return 'color: #2E7D32; font-weight: bold;'
                elif val < 0: return 'color: #C62828; font-weight: bold;'
        except: pass
        return ''

    # ==========================================
    # PESTAÑA 1: DASHBOARD COMERCIAL GENERAL
    # ==========================================
    with tab1:
        st.subheader("📅 Panel de Control Temporal")
        col_f1, col_f2 = st.columns([1, 3])
        
        with col_f1:
            anios_disp = sorted(df_f[col_anio].dropna().unique())
            anio_base = st.selectbox("Selecciona el Año Base:", anios_disp, index=len(anios_disp)-1 if anios_disp else 0, key="anio_tab1")

        with col_f2:
            meses_unicos = df_f[col_mes].dropna().unique()
            meses_disp = sorted(list(meses_unicos), key=obtener_peso_mes)
            meses_sel = st.multiselect("Selecciona los meses activos:", options=meses_disp, default=list(meses_disp), key="meses_tab1_multi")

        st.markdown("---")

        if anio_base and meses_sel:
            anio_sel = int(anio_base)
            anio_anterior = anio_sel - 1

            df_actual = df_f[(df_f[col_anio] == anio_sel) & (df_f[col_mes].isin(meses_sel))]
            df_ant = df_f[(df_f[col_anio] == anio_anterior) & (df_f[col_mes].isin(meses_sel))]

            total_actual = df_actual[col_valor].sum()
            total_anterior = df_ant[col_valor].sum()
            crecimiento_global = ((total_actual / total_anterior) - 1) * 100 if total_anterior > 0 else 0

            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric(label=f"Ventas Total ({anio_sel})", value=f"${total_actual:,.0f}")
            kpi2.metric(label=f"Ventas Total ({anio_anterior})", value=f"${total_anterior:,.0f}", delta=f"{crecimiento_global:,.0f}% YoY")
            kpi3.metric(label="Meses Evaluados", value=f"{len(meses_sel)} mes(es)")

            st.markdown("---")
            st.subheader("🌐 Resumen de Variación General por Unidad de Negocio")

            df_global_actual = df_f_global[(df_f_global[col_anio] == anio_sel) & (df_f_global[col_mes].isin(meses_sel))]
            df_global_ant = df_f_global[(df_f_global[col_anio] == anio_anterior) & (df_f_global[col_mes].isin(meses_sel))]

            reg_actual = df_global_actual.groupby(col_regional)[col_valor].sum().reset_index().rename(columns={col_valor: f'Venta {anio_sel}'})
            reg_ant = df_global_ant.groupby(col_regional)[col_valor].sum().reset_index().rename(columns={col_valor: f'Venta {anio_anterior}'})

            tabla_un_final = pd.merge(reg_actual, reg_ant, on=col_regional, how='outer').fillna(0)
            tabla_un_final['Variación ($)'] = tabla_un_final[f'Venta {anio_sel}'] - tabla_un_final[f'Venta {anio_anterior}']
            tabla_un_final['Variación (%)'] = ((tabla_un_final[f'Venta {anio_sel}'] / tabla_un_final[f'Venta {anio_anterior}'].replace(0, 1)) - 1) * 100
            tabla_un_final['Crecimiento_Tipo'] = tabla_un_final['Variación (%)'].apply(lambda x: 'Crecimiento' if x >= 0 else 'Decrecimiento')

            col_vis1, col_vis2 = st.columns([1.2, 1])
            with col_vis1:
                fig_un_vis = px.bar(
                    tabla_un_final.sort_values(by='Variación (%)', ascending=True),
                    x='Variación (%)', y=col_regional, orientation='h',
                    color='Crecimiento_Tipo', color_discrete_map={'Crecimiento': '#2E7D32', 'Decrecimiento': '#C62828'},
                    text=tabla_un_final.sort_values(by='Variación (%)', ascending=True)['Variación (%)'].apply(lambda x: f"{x:,.0f}%")
                )
                fig_un_vis.update_traces(textposition='outside', hovertemplate='<b>%{y}</b><br>Variación: %{x:,.1f}%<extra></extra>')
                fig_un_vis.update_layout(xaxis_title="Variación (%)", yaxis_title="", showlegend=False, height=300, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_un_vis, use_container_width=True)

            with col_vis2:
                format_dict_un = {f'Venta {anio_sel}': '${:,.0f}', f'Venta {anio_anterior}': '${:,.0f}', 'Variación ($)': '${:,.0f}', 'Variación (%)': '{:,.0f}%'}
                tabla_un_estilizada = (
                    tabla_un_final.sort_values(by=f'Venta {anio_sel}', ascending=False).style
                    .format(format_dict_un)
                    .map(color_variacion, subset=['Variación ($)', 'Variación (%)'])
                    .hide(subset=['Crecimiento_Tipo'], axis='columns')
                )
                st.dataframe(tabla_un_estilizada, use_container_width=True, height=280)

            st.markdown("---")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader(f"📊 Ventas por Regional ({anio_sel})")
                if not df_actual.empty:
                    df_reg = df_actual.groupby(col_regional)[col_valor].sum().reset_index().sort_values(by=col_valor, ascending=False).head(10)
                    df_reg['Texto_Moneda'] = df_reg[col_valor].apply(lambda x: f"${x:,.0f}")
                    fig_reg = px.bar(df_reg, x=col_valor, y=col_regional, orientation='h', text='Texto_Moneda', color=col_valor, color_continuous_scale='Blues')
                    fig_reg.update_traces(texttemplate='%{text}', textposition='auto', hovertemplate='<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>')
                    fig_reg.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, xaxis_title="Venta ($)", yaxis_title="Regional")
                    st.plotly_chart(fig_reg, use_container_width=True)
                else: st.info("Sin datos.")

            with col_g2:
                st.subheader("🏆 Top Clientes")
                if not df_actual.empty:
                    df_cli_top = df_actual.groupby(col_cliente)[col_valor].sum().reset_index().sort_values(by=col_valor, ascending=False).head(10)
                    df_cli_top['Texto_Moneda'] = df_cli_top[col_valor].apply(lambda x: f"${x:,.0f}")
                    fig_cli = px.bar(df_cli_top, x=col_valor, y=col_cliente, orientation='h', text='Texto_Moneda', color=col_valor, color_continuous_scale='Greens')
                    fig_cli.update_traces(texttemplate='%{text}', textposition='auto', hovertemplate='<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>')
                    fig_cli.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, xaxis_title="Venta ($)", yaxis_title="Cliente")
                    st.plotly_chart(fig_cli, use_container_width=True)
                else: st.info("Sin datos.")

            st.markdown("---")
            st.subheader("📋 Detalle por Cliente (Año Actual vs. Año Anterior)")
            col_busq, col_desc = st.columns([3, 1])
            with col_busq: busqueda_tabla = st.text_input("🔍 Buscar cliente:", "", key="busq_cli_tab1")

            ventas_actual = df_actual.groupby(col_cliente)[col_valor].sum().reset_index().rename(columns={col_valor: f'Venta {anio_sel}'})
            ventas_anterior = df_ant.groupby(col_cliente)[col_valor].sum().reset_index().rename(columns={col_valor: f'Venta {anio_anterior}'})
            tabla_final = pd.merge(ventas_actual, ventas_anterior, on=col_cliente, how='outer').fillna(0)
            tabla_final['Variación ($)'] = tabla_final[f'Venta {anio_sel}'] - tabla_final[f'Venta {anio_anterior}']
            tabla_final['Variación (%)'] = ((tabla_final[f'Venta {anio_sel}'] / tabla_final[f'Venta {anio_anterior}'].replace(0, 1)) - 1) * 100
            tabla_final = tabla_final.sort_values(by=f'Venta {anio_sel}', ascending=False)

            if busqueda_tabla:
                tabla_final = tabla_final[tabla_final[col_cliente].astype(str).str.contains(busqueda_tabla, case=False, na=False)]

            with col_desc:
                st.write("")
                st.download_button(label="📥 Descargar CSV", data=tabla_final.to_csv(index=False).encode('utf-8'), file_name=f"detalle_clientes_{anio_sel}.csv", mime="text/csv", key="dl_csv_tab1")

            format_dict = {f'Venta {anio_sel}': '${:,.0f}', f'Venta {anio_anterior}': '${:,.0f}', 'Variación ($)': '${:,.0f}', 'Variación (%)': '{:,.0f}%'}
            st.dataframe(tabla_final.style.format(format_dict).map(color_variacion, subset=['Variación ($)', 'Variación (%)']), use_container_width=True)

            st.markdown("---")
            st.subheader(f"⚠️ Clientes Inactivos (Compraron en {anio_anterior} pero tienen $0 en {anio_sel})")
            ventas_act_num = df_actual.groupby(col_cliente)[col_valor].sum()
            ventas_ant_num = df_ant.groupby(col_cliente)[col_valor].sum()
            clientes_cero = set(ventas_ant_num[ventas_ant_num > 0].index) - set(ventas_act_num[ventas_act_num > 0].index)
            df_inactivos_final = df_ant[df_ant[col_cliente].isin(clientes_cero)].groupby(col_cliente)[col_valor].sum().reset_index()
            df_inactivos_final.rename(columns={col_valor: f'Venta Histórica {anio_anterior}'}, inplace=True)
            df_inactivos_final = df_inactivos_final.sort_values(by=f'Venta Histórica {anio_anterior}', ascending=False
