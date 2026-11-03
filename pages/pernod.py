import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="SEGUIMIENTO PERNOD RICARD", layout="wide")

# Estilo CSS para evitar que las métricas largas se recorten con "..."
st.markdown("""
    <style>
        [data-testid="stMetricValue"] {
            font-size: 1.4rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Título llamativo
st.title("🍾 SEGUIMIENTO PERNOD RICARD 🥂")
st.markdown("---")

@st.cache_data
def cargar_datos():
    xls_path = "BV PERNOD TODA.xlsb"
    df_ventas = pd.read_excel(xls_path, sheet_name=0, engine="pyxlsb")
    
    try:
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
            df_inactivos_final = df_inactivos_final.sort_values(by=f'Venta Histórica {anio_anterior}', ascending=False)

            if not df_inactivos_final.empty:
                df_inactivos_final[f'Venta Histórica {anio_anterior}'] = df_inactivos_final[f'Venta Histórica {anio_anterior}'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(df_inactivos_final, use_container_width=True)
            else:
                st.success(f"🎉 ¡Excelente noticia! No hay clientes inactivos para los filtros y meses seleccionados entre {anio_anterior} y {anio_sel}.")

        else:
            st.warning("⚠️ Selecciona un Año Base y al menos un Mes.")

    # ==========================================
    # PESTAÑA 2: ANÁLISIS DE REFERENCIAS (YoY)
    # ==========================================
    with tab2:
        st.subheader("📦 Análisis Avanzado de Referencias (YoY: 2025 vs 2026)")
        col_ref_f1, col_ref_f2, col_ref_f3 = st.columns([1, 2, 1])
        with col_ref_f1:
            anios_ref_disp = sorted(df_f[col_anio].dropna().unique())
            anio_ref_base = st.selectbox("Año Actual:", anios_ref_disp, index=len(anios_ref_disp)-1 if anios_ref_disp else 0, key="anio_tab2")
        with col_ref_f2:
            meses_ref_disp = sorted(list(df_f[col_mes].dropna().unique()), key=obtener_peso_mes)
            meses_ref_sel = st.multiselect("Meses a evaluar:", options=meses_ref_disp, default=list(meses_ref_disp), key="meses_tab2")
        with col_ref_f3:
            top_n = st.selectbox("Cantidad en Top:", [5, 10, 15, 20], index=1, key="top_n_sel")

        if anio_ref_base and meses_ref_sel:
            anio_ref_sel = int(anio_ref_base)
            anio_ref_ant = anio_ref_sel - 1

            df_ref_actual = df_f[(df_f[col_anio] == anio_ref_sel) & (df_f[col_mes].isin(meses_ref_sel))]
            df_ref_ant = df_f[(df_f[col_anio] == anio_ref_ant) & (df_f[col_mes].isin(meses_ref_sel))]

            ref_act = df_ref_actual.groupby(col_referencia)[col_valor].sum().reset_index().rename(columns={col_valor: f'Venta {anio_ref_sel}'})
            ref_ant = df_ref_ant.groupby(col_referencia)[col_valor].sum().reset_index().rename(columns={col_valor: f'Venta {anio_ref_ant}'})

            tabla_ref_comp = pd.merge(ref_act, ref_ant, on=col_referencia, how='outer').fillna(0)
            tabla_ref_comp['Variación ($)'] = tabla_ref_comp[f'Venta {anio_ref_sel}'] - tabla_ref_comp[f'Venta {anio_ref_ant}']
            tabla_ref_comp['Variación (%)'] = ((tabla_ref_comp[f'Venta {anio_ref_sel}'] / tabla_ref_comp[f'Venta {anio_ref_ant}'].replace(0, 1)) - 1) * 100

            if not tabla_ref_comp.empty:
                st.markdown("---")
                st.markdown(f"### 🏆 Top {top_n} Referencias Más y Menos Vendidas ({anio_ref_sel})")
                col_mv1, col_mv2 = st.columns(2)

                df_top_mas = tabla_ref_comp.sort_values(by=f'Venta {anio_ref_sel}', ascending=False).head(top_n)
                df_top_menos = tabla_ref_comp[tabla_ref_comp[f'Venta {anio_ref_sel}'] > 0].sort_values(by=f'Venta {anio_ref_sel}', ascending=True).head(top_n)

                with col_mv1:
                    st.markdown(f"**🔥 Más Vendidas**")
                    df_top_mas['Texto_Moneda'] = df_top_mas[f'Venta {anio_ref_sel}'].apply(lambda x: f"${x:,.0f}")
                    fig_mas = px.bar(df_top_mas.sort_values(by=f'Venta {anio_ref_sel}', ascending=True), x=f'Venta {anio_ref_sel}', y=col_referencia, orientation='h', text='Texto_Moneda', color=f'Venta {anio_ref_sel}', color_continuous_scale='Greens')
                    fig_mas.update_traces(texttemplate='%{text}', textposition='auto', hovertemplate='<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>')
                    fig_mas.update_layout(showlegend=False, xaxis_title=f"Venta Total ($ {anio_ref_sel})", yaxis_title="Referencia / Producto", height=320)
                    st.plotly_chart(fig_mas, use_container_width=True)

                with col_mv2:
                    st.markdown(f"**🧊 Menos Vendidas (Bajo Movimiento)**")
                    df_top_menos['Texto_Moneda'] = df_top_menos[f'Venta {anio_ref_sel}'].apply(lambda x: f"${x:,.0f}")
                    fig_menos = px.bar(df_top_menos.sort_values(by=f'Venta {anio_ref_sel}', ascending=True), x=f'Venta {anio_ref_sel}', y=col_referencia, orientation='h', text='Texto_Moneda', color=f'Venta {anio_ref_sel}', color_continuous_scale='Blues')
                    fig_menos.update_traces(texttemplate='%{text}', textposition='auto', hovertemplate='<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>')
                    fig_menos.update_layout(showlegend=False, xaxis_title=f"Venta Total ($ {anio_ref_sel})", yaxis_title="Referencia / Producto", height=320)
                    st.plotly_chart(fig_menos, use_container_width=True)

                st.markdown("---")
                st.markdown(f"### 📈 Dinámica de Crecimiento y Decrecimiento YoY")
                col_g_inf1, col_g_inf2 = st.columns(2)
                df_top_crece = tabla_ref_comp.sort_values(by='Variación ($)', ascending=False).head(top_n)
                df_top_decrece = tabla_ref_comp.sort_values(by='Variación ($)', ascending=True).head(top_n)

                with col_g_inf1:
                    st.markdown(f"**📈 Top {top_n} Referencias con Mayor Crecimiento ($)**")
                    df_top_crece['Texto_Var'] = df_top_crece['Variación ($)'].apply(lambda x: f"${x:,.0f}")
                    fig_crece = px.bar(df_top_crece.sort_values(by='Variación ($)', ascending=True), x='Variación ($)', y=col_referencia, orientation='h', text='Texto_Var', color='Variación ($)', color_continuous_scale='Greens')
                    fig_crece.update_traces(texttemplate='%{text}', textposition='auto', hovertemplate='<b>%{y}</b><br>Variación: $%{x:,.0f}<extra></extra>')
                    fig_crece.update_layout(showlegend=False, xaxis_title="Crecimiento en Dinero ($)", yaxis_title="Referencia / Producto", height=320)
                    st.plotly_chart(fig_crece, use_container_width=True)

                with col_g_inf2:
                    st.markdown(f"**📉 Top {top_n} Referencias con Mayor Decrecimiento ($)**")
                    df_top_decrece['Texto_Var'] = df_top_decrece['Variación ($)'].apply(lambda x: f"${x:,.0f}")
                    fig_decrece = px.bar(df_top_decrece.sort_values(by='Variación ($)', ascending=True), x='Variación ($)', y=col_referencia, orientation='h', text='Texto_Var', color='Variación ($)', color_continuous_scale='Reds_r')
                    fig_decrece.update_traces(texttemplate='%{text}', textposition='auto', hovertemplate='<b>%{y}</b><br>Variación: $%{x:,.0f}<extra></extra>')
                    fig_decrece.update_layout(showlegend=False, xaxis_title="Decrecimiento en Dinero ($)", yaxis_title="Referencia / Producto", height=320)
                    st.plotly_chart(fig_decrece, use_container_width=True)

                st.markdown("---")
                st.subheader("📋 Tabla Comparativa Completa de Referencias")
                col_b_ref, col_d_ref = st.columns([3, 1])
                with col_b_ref: busq_ref = st.text_input("🔍 Buscar referencia:", "", key="busq_referencia_txt")
                
                tabla_ref_final = tabla_ref_comp.sort_values(by=f'Venta {anio_ref_sel}', ascending=False)
                if busq_ref:
                    tabla_ref_final = tabla_ref_final[tabla_ref_final[col_referencia].astype(str).str.contains(busq_ref, case=False, na=False)]

                with col_d_ref:
                    st.write("")
                    st.download_button(label="📥 Descargar CSV", data=tabla_ref_final.to_csv(index=False).encode('utf-8'), file_name=f"comparativo_referencias_{anio_ref_sel}_vs_{anio_ref_ant}.csv", mime="text/csv", key="dl_ref_csv")

                format_dict_ref = {f'Venta {anio_ref_sel}': '${:,.0f}', f'Venta {anio_ref_ant}': '${:,.0f}', 'Variación ($)': '${:,.0f}', 'Variación (%)': '{:,.0f}%'}
                st.dataframe(tabla_ref_final.style.format(format_dict_ref).map(color_variacion, subset=['Variación ($)', 'Variación (%)']), use_container_width=True)

            else:
                st.info("No hay datos de referencias.")
        else:
            st.warning("⚠️ Selecciona el año y meses para el análisis de referencias.")

    # ==========================================
    # PESTAÑA 3: PRESUPUESTO & ZONAS (PPTO)
    # ==========================================
    with tab3:
        st.subheader("🎯 Cumplimiento de Presupuesto y Zonas (PPTO)")
        st.markdown("Evaluación ordenada por zona con cumplimiento de venta, impactos y pedidos YoY independientes por mes.")

        if not df_ppto.empty:
            col_ppto_f1, col_ppto_f2 = st.columns([1, 3])
            with col_ppto_f1:
                anios_ppto_disp = sorted(df_f[col_anio].dropna().unique())
                anio_ppto_sel = st.selectbox("Año Presupuesto:", anios_ppto_disp, index=len(anios_ppto_disp)-1 if anios_ppto_disp else 0, key="anio_ppto_sel")
            with col_ppto_f2:
                meses_ppto_disp = sorted(list(df_f[col_mes].dropna().unique()), key=obtener_peso_mes)
                meses_ppto_sel = st.multiselect("Meses a evaluar en PPTO:", options=meses_ppto_disp, default=list(meses_ppto_disp), key="meses_ppto_multi")

            st.markdown("---")

            if anio_ppto_sel and meses_ppto_sel:
                anio_p = int(anio_ppto_sel)
                anio_ant_p = anio_p - 1

                df_ppto_ventas_actual = df[(df[col_anio] == anio_p) & (df[col_mes].isin(meses_ppto_sel))]
                df_ppto_ventas_ant = df[(df[col_anio] == anio_ant_p) & (df[col_mes].isin(meses_ppto_sel))]

                cols_ppto = df_ppto.columns.tolist()
                p_gerente_ppto = next((c for c in cols_ppto if 'gerente' in str(c).lower() or 'supervisor' in str(c).lower()), cols_ppto[1])
                p_zona = next((c for c in cols_ppto if 'zona' in str(c).lower()), cols_ppto[2])
                p_ppto = next((c for c in cols_ppto if 'presupuesto' in str(c).lower() or 'ppto' in str(c).lower()), cols_ppto[3])
                p_maestra = next((c for c in cols_ppto if 'maestra' in str(c).lower()), cols_ppto[4] if len(cols_ppto)>4 else cols_ppto[3])
                p_un = next((c for c in cols_ppto if 'un' in str(c).lower() or 'regional' in str(c).lower()), cols_ppto[0])

                df_ppto_filtrado = df_ppto.copy()
                if sel_zona != "Todos":
                    df_ppto_filtrado = df_ppto_filtrado[df_ppto_filtrado[p_zona].astype(str) == sel_zona]
                if sel_gerente != "Todos":
                    df_ppto_filtrado = df_ppto_filtrado[df_ppto_filtrado[p_gerente_ppto].astype(str) == sel_gerente]

                if sel_reg != "Todos":
                    df_ppto_ventas_actual = df_ppto_ventas_actual[df_ppto_ventas_actual[col_regional].astype(str) == sel_reg]
                    df_ppto_ventas_ant = df_ppto_ventas_ant[df_ppto_ventas_ant[col_regional].astype(str) == sel_reg]
                if sel_canal != "Todos":
                    df_ppto_ventas_actual = df_ppto_ventas_actual[df_ppto_ventas_actual[col_canal].astype(str) == sel_canal]
                    df_ppto_ventas_ant = df_ppto_ventas_ant[df_ppto_ventas_ant[col_canal].astype(str) == sel_canal]

                df_ventas_zona = df_ppto_ventas_actual.groupby(col_zona)[col_valor].sum().reset_index().rename(columns={col_valor: 'Venta'})
                df_cli_gt1 = df_ppto_ventas_actual[df_ppto_ventas_actual[col_valor] > 1].groupby(col_zona)[col_cliente].nunique().reset_index().rename(columns={col_cliente: 'Impactos'})
                df_pedidos_act = df_ppto_ventas_actual.groupby(col_zona).size().reset_index(name='Pedidos')
                df_pedidos_ant = df_ppto_ventas_ant.groupby(col_zona).size().reset_index(name='Pedidos Ant')

                df_ppto_filtrado[p_zona] = df_ppto_filtrado[p_zona].astype(str).str.strip()
                df_ventas_zona[col_zona] = df_ventas_zona[col_zona].astype(str).str.strip()
                df_cli_gt1[col_zona] = df_cli_gt1[col_zona].astype(str).str.strip()
                df_pedidos_act[col_zona] = df_pedidos_act[col_zona].astype(str).str.strip()
                df_pedidos_ant[col_zona] = df_pedidos_ant[col_zona].astype(str).str.strip()

                df_ppto_filtrado[p_ppto] = pd.to_numeric(df_ppto_filtrado[p_ppto], errors='coerce').fillna(0)
                df_ppto_filtrado[p_maestra] = pd.to_numeric(df_ppto_filtrado[p_maestra], errors='coerce').fillna(0)

                tabla_cumplimiento = pd.merge(df_ppto_filtrado, df_ventas_zona, left_on=p_zona, right_on=col_zona, how='left').fillna(0)
                tabla_cumplimiento = pd.merge(tabla_cumplimiento, df_cli_gt1, on=col_zona, how='left').fillna(0)
                tabla_cumplimiento = pd.merge(tabla_cumplimiento, df_pedidos_act, on=col_zona, how='left').fillna(0)
                tabla_cumplimiento = pd.merge(tabla_cumplimiento, df_pedidos_ant, on=col_zona, how='left').fillna(0)

                tabla_cumplimiento['% Cumplimiento Venta'] = (tabla_cumplimiento['Venta'] / tabla_cumplimiento[p_ppto].replace(0, 1)) * 100
                tabla_cumplimiento['% Cumplimiento Impactos'] = (tabla_cumplimiento['Impactos'] / tabla_cumplimiento[p_maestra].replace(0, 1)) * 100
                tabla_cumplimiento['Variación Pedidos'] = tabla_cumplimiento['Pedidos'] - tabla_cumplimiento['Pedidos Ant']

                total_ppto = tabla_cumplimiento[p_ppto].sum()
                total_venta_real = tabla_cumplimiento['Venta'].sum()
                cumplimiento_global_ppto = (total_venta_real / total_ppto) * 100 if total_ppto > 0 else 0

                # Clientes únicos globales actuales y anteriores filtrados por la zona/supervisor activo
                zonas_filtradas = tabla_cumplimiento[p_zona].astype(str).unique()
                df_act_sup = df_ppto_ventas_actual[df_ppto_ventas_actual[col_zona].astype(str).isin(zonas_filtradas)]
                df_ant_sup = df_ppto_ventas_ant[df_ppto_ventas_ant[col_zona].astype(str).isin(zonas_filtradas)]

                total_clientes_gt1 = df_act_sup[df_act_sup[col_valor] > 1][col_cliente].nunique()
                total_clientes_ant = df_ant_sup[df_ant_sup[col_valor] > 1][col_cliente].nunique()
                var_clientes_yoy = total_clientes_gt1 - total_clientes_ant

                # Ventas año anterior para métrica superior
                total_venta_ant = df_ant_sup[col_valor].sum()
                var_venta_yoy = ((total_venta_real / total_venta_ant) - 1) * 100 if total_venta_ant > 0 else 0

                total_pedidos_act = int(tabla_cumplimiento['Pedidos'].sum())
                total_pedidos_ant = int(tabla_cumplimiento['Pedidos Ant'].sum())
                var_pedidos_total = total_pedidos_act - total_pedidos_ant

                # Métricas superiores con comparativa YoY completa
                k1, k2, k3 = st.columns(3)
                k1.metric(label="Presupuesto Total (Meta)", value=f"${total_ppto:,.0f}")
                k2.metric(label="Venta Real Acumulada", value=f"${total_venta_real:,.0f}", delta=f"{cumplimiento_global_ppto:,.1f}% Cumpl. ({var_venta_yoy:+.1f}% YoY)")
                k3.metric(label="Zonas Evaluadas", value=f"{len(tabla_cumplimiento)}")

                k4, k5 = st.columns(2)
                k4.metric(label="Clientes Impactados (> $1)", value=f"{total_clientes_gt1:,}", delta=f"{var_clientes_yoy:+d} YoY (Ant: {total_clientes_ant:,})")
                k5.metric(label="Cantidad de Pedidos", value=f"{total_pedidos_act:,}", delta=f"{var_pedidos_total:+d} YoY (Ant: {total_pedidos_ant:,})")

                st.markdown("---")
                st.subheader("📋 Detalle de Ejecución por Zona")

                columnas_deseadas = {
                    p_un: 'Código UN',
                    p_zona: 'Código Zona',
                    p_ppto: 'Presupuesto',
                    'Venta': 'Venta',
                    '% Cumplimiento Venta': '% Cumplimiento Venta',
                    p_maestra: 'Maestra',
                    'Impactos': 'Impactos',
                    '% Cumplimiento Impactos': '% Cumplimiento Impactos',
                    'Pedidos': 'Pedidos',
                    'Pedidos Ant': 'Pedidos Año Anterior',
                    'Variación Pedidos': 'Variación Pedidos'
                }

                cols_finales_validas = [c for c in columnas_deseadas.keys() if c in tabla_cumplimiento.columns]
                tabla_mostrar = tabla_cumplimiento[cols_finales_validas].rename(columns=columnas_deseadas)

                format_dict_ppto = {
                    'Presupuesto': '${:,.0f}',
                    'Venta': '${:,.0f}',
                    '% Cumplimiento Venta': '{:,.1f}%',
                    '% Cumplimiento Impactos': '{:,.1f}%',
                    'Maestra': '{:,.0f}',
                    'Impactos': '{:,.0f}',
                    'Pedidos': '{:,.0f}',
                    'Pedidos Año Anterior': '{:,.0f}',
                    'Variación Pedidos': '{:+,.0f}'
                }

                tabla_ppto_estilizada = (
                    tabla_mostrar.sort_values(by='% Cumplimiento Venta', ascending=False).style
                    .format(format_dict_ppto)
                    .map(color_variacion, subset=['% Cumplimiento Venta', '% Cumplimiento Impactos', 'Variación Pedidos'])
                )
                st.dataframe(tabla_ppto_estilizada, use_container_width=True, height=380)
            else:
                st.warning("⚠️ Selecciona el año y al menos un mes para evaluar el presupuesto.")

        else:
            st.warning("⚠️ No se encontró la hoja 'PPTO' en tu archivo Excel. Asegúrate de que tenga ese nombre exacto.")

except Exception as e:
    st.error(f"Ocurrió un error al procesar la aplicación: {e}")
