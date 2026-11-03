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
    return pd.read_excel("BV PERNOD TODA.xlsb", engine="pyxlsb")

try:
    df = cargar_datos()
    columnas = df.columns.tolist()

    # Detección automática inteligente de columnas
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

    # Asignación automática de columnas
    col_regional = detectar_columna(['Código UN', 'Cod UN', 'Regional', 'Región'], 1)
    col_canal = detectar_columna(['Tipo de Cliente', 'Tipo cliente', 'Canal', 'Canal de Venta'], 0)
    col_gerente = detectar_columna(['Gerente Zona', 'Gerente Unidad', 'Supervisor', 'Gerente'], 2)
    col_zona = detectar_columna(['Código Zona', 'Codigo Zona', 'Cod Zona', 'Id Zona'], 3)
    col_cliente = detectar_columna(['Nombre Cliente', 'Cliente', 'Documento Cliente'], 4)
    
    # Detección específica para referencias / productos / artículos
    col_referencia = detectar_columna(['Referencia', 'Artículo', 'Articulo', 'SKU', 'Producto', 'Item', 'Descripción Item'], 5)
    
    col_anio = detectar_columna(['Año', 'Anio', 'Year'], 6)
    col_mes = detectar_columna(['Mes', 'Month'], 7)
    col_valor = detectar_columna(['Ventas Det', 'Venta', 'Valor', 'Total'], 8)

    # Asegurar tipo numérico limpio en la columna de valor global
    df[col_valor] = pd.to_numeric(df[col_valor], errors='coerce').fillna(0)
    df[col_anio] = pd.to_numeric(df[col_anio], errors='coerce')

    # --- BARRA LATERAL: FILTROS PRINCIPALES ---
    st.sidebar.header("🎯 Filtros Globales")

    df_f = df.copy()

    # 1. Código UN (Regional)
    opciones_reg = ["Todos"] + sorted([str(x) for x in df_f[col_regional].dropna().unique()])
    sel_reg = st.sidebar.selectbox("Código UN (Regional)", opciones_reg, index=0)
    
    df_f_global = df_f.copy()

    if sel_reg != "Todos":
        df_f = df_f[df_f[col_regional].astype(str) == sel_reg]

    # 2. Canal / Tipo de Cliente
    opciones_canal = ["Todos"] + sorted([str(x) for x in df_f[col_canal].dropna().unique()])
    sel_canal = st.sidebar.selectbox("Canal", opciones_canal, index=0)
    if sel_canal != "Todos":
        df_f = df_f[df_f[col_canal].astype(str) == sel_canal]
        df_f_global = df_f_global[df_f_global[col_canal].astype(str) == sel_canal]

    # 3. Supervisor / Gerente de Unidad
    opciones_gerente = ["Todos"] + sorted([str(x) for x in df_f[col_gerente].dropna().unique()])
    sel_gerente = st.sidebar.selectbox("Supervisor", opciones_gerente, index=0)
    if sel_gerente != "Todos":
        df_f = df_f[df_f[col_gerente].astype(str) == sel_gerente]
        df_f_global = df_f_global[df_f_global[col_gerente].astype(str) == sel_gerente]

    # 4. Filtro de Código Zona
    opciones_zona = ["Todos"] + sorted([str(x) for x in df_f[col_zona].dropna().unique()])
    sel_zona = st.sidebar.selectbox("Código Zona", opciones_zona, index=0)
    if sel_zona != "Todos":
        df_f = df_f[df_f[col_zona].astype(str) == sel_zona]
        df_f_global = df_f_global[df_f_global[col_zona].astype(str) == sel_zona]

    # --- CREACIÓN DE PESTAÑAS PRINCIPALES ---
    tab1, tab2 = st.tabs(["📊 Dashboard General & Clientes", "📦 Análisis de Referencias (Top & Bajo Movimiento)"])

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

            meses_disp = sorted(list(meses_unicos), key=obtener_peso_mes)

            if hasattr(st, "segmented_control"):
                meses_sel = st.segmented_control("Selecciona los meses activos:", options=meses_disp, default=meses_disp, selection_mode="multi", key="meses_tab1")
            else:
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

            # Resumen de Variación General por Unidad de Negocio
            st.subheader("🌐 Resumen de Variación General por Unidad de Negocio")
            st.caption("Vista rápida de ventas y crecimiento por regional (independiente del filtro lateral de Código UN).")

            df_global_actual = df_f_global[(df_f_global[col_anio] == anio_sel) & (df_f_global[col_mes].isin(meses_sel))]
            df_global_ant = df_f_global[(df_f_global[col_anio] == anio_anterior) & (df_f_global[col_mes].isin(meses_sel))]

            reg_actual = df_global_actual.groupby(col_regional)[col_valor].sum().reset_index()
            reg_actual.rename(columns={col_valor: f'Venta {anio_sel}'}, inplace=True)

            reg_ant = df_global_ant.groupby(col_regional)[col_valor].sum().reset_index()
            reg_ant.rename(columns={col_valor: f'Venta {anio_anterior}'}, inplace=True)

            tabla_un_final = pd.merge(reg_actual, reg_ant, on=col_regional, how='outer').fillna(0)
            tabla_un_final['Variación ($)'] = tabla_un_final[f'Venta {anio_sel}'] - tabla_un_final[f'Venta {anio_anterior}']
            tabla_un_final['Variación (%)'] = ((tabla_un_final[f'Venta {anio_sel}'] / tabla_un_final[f'Venta {anio_anterior}'].replace(0, 1)) - 1) * 100
            tabla_un_final['Crecimiento_Tipo'] = tabla_un_final['Variación (%)'].apply(lambda x: 'Crecimiento' if x >= 0 else 'Decrecimiento')

            col_vis1, col_vis2 = st.columns([1.2, 1])

            with col_vis1:
                fig_un_vis = px.bar(
                    tabla_un_final.sort_values(by='Variación (%)', ascending=True),
                    x='Variación (%)',
                    y=col_regional,
                    orientation='h',
                    color='Crecimiento_Tipo',
                    color_discrete_map={'Crecimiento': '#2E7D32', 'Decrecimiento': '#C62828'},
                    text=tabla_un_final.sort_values(by='Variación (%)', ascending=True)['Variación (%)'].apply(lambda x: f"{x:,.0f}%")
                )
                fig_un_vis.update_traces(textposition='outside', hovertemplate='<b>%{y}</b><br>Variación: %{x:,.1f}%<extra></extra>')
                fig_un_vis.update_layout(xaxis_title="Variación (%)", yaxis_title="", showlegend=False, height=300, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_un_vis, use_container_width=True)

            with col_vis2:
                def color_variacion(val):
                    try:
                        if isinstance(val, (int, float)):
                            if val > 0: return 'color: #2E7D32; font-weight: bold;'
                            elif val < 0: return 'color: #C62828; font-weight: bold;'
                    except: pass
                    return ''

                format_dict_un = {f'Venta {anio_sel}': '${:,.0f}', f'Venta {anio_anterior}': '${:,.0f}', 'Variación ($)': '${:,.0f}', 'Variación (%)': '{:,.0f}%'}
                tabla_un_estilizada = (
                    tabla_un_final.sort_values(by=f'Venta {anio_sel}', ascending=False).style
                    .format(format_dict_un)
                    .map(color_variacion, subset=['Variación ($)', 'Variación (%)'])
                    .hide(subset=['Crecimiento_Tipo'], axis='columns')
                )
                st.dataframe(tabla_un_estilizada, use_container_width=True, height=280)

            st.markdown("---")

            # Gráficos Regional y Top Clientes
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

            # Detalle por Cliente
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

        else:
            st.warning("⚠️ Selecciona un Año Base y al menos un Mes.")

    # ==========================================
    # PESTAÑA 2: ANÁLISIS DE REFERENCIAS (TOP & BAJO MOVIMIENTO)
    # ==========================================
    with tab2:
        st.subheader("📦 Análisis Avanzado de Referencias y Productos")
        st.markdown("Consulta rápida de las referencias más vendidas (Top comerciales) y las de menor rotación para optimización de inventarios y portafolio.")

        col_ref_f1, col_ref_f2, col_ref_f3 = st.columns([1, 2, 1])
        with col_ref_f1:
            anios_ref_disp = sorted(df_f[col_anio].dropna().unique())
            anio_ref_base = st.selectbox("Año a evaluar:", anios_ref_disp, index=len(anios_ref_disp)-1 if anios_ref_disp else 0, key="anio_tab2")
        with col_ref_f2:
            meses_ref_disp = sorted(list(df_f[col_mes].dropna().unique()), key=obtener_peso_mes)
            meses_ref_sel = st.multiselect("Meses a evaluar:", options=meses_ref_disp, default=list(meses_ref_disp), key="meses_tab2")
        with col_ref_f3:
            top_n = st.selectbox("Cantidad a mostrar en Top:", [5, 10, 15, 20], index=1, key="top_n_sel")

        if anio_ref_base and meses_ref_sel:
            df_ref_eval = df_f[(df_f[col_anio] == int(anio_ref_base)) & (df_f[col_mes].isin(meses_ref_sel))]

            if not df_ref_eval.empty:
                # Agrupación por referencia
                df_ref_group = df_ref_eval.groupby(col_referencia)[col_valor].sum().reset_index()
                df_ref_group = df_ref_group.sort_values(by=col_valor, ascending=False)

                # Top más vendidas
                df_top_mas = df_ref_group.head(top_n)
                # Menos vendidas (con venta mayor a 0 o todas)
                df_top_menos = df_ref_group[df_ref_group[col_valor] > 0].tail(top_n).sort_values(by=col_valor, ascending=True)

                st.markdown("---")
                
                # Visuales en dos columnas
                col_m1, col_m2 = st.columns(2)

                with col_m1:
                    st.markdown(f"### 🔥 Top {top_n} Referencias Más Vendidas")
                    df_top_mas['Texto_Moneda'] = df_top_mas[col_valor].apply(lambda x: f"${x:,.0f}")
                    fig_mas = px.bar(
                        df_top_mas, x=col_valor, y=col_referencia, orientation='h',
                        text='Texto_Moneda', color=col_valor, color_continuous_scale='Greens'
                    )
                    fig_mas.update_traces(texttemplate='%{text}', textposition='auto', hovertemplate='<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>')
                    fig_mas.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, xaxis_title="Venta Total ($)", yaxis_title="Referencia / Producto")
                    st.plotly_chart(fig_mas, use_container_width=True)

                with col_m2:
                    st.markdown(f"### 🧊 Top {top_n} Referencias Menos Vendidas (Bajo Movimiento)")
                    df_top_menos['Texto_Moneda'] = df_top_menos[col_valor].apply(lambda x: f"${x:,.0f}")
                    fig_menos = px.bar(
                        df_top_menos, x=col_valor, y=col_referencia, orientation='h',
                        text='Texto_Moneda', color=col_valor, color_continuous_scale='Reds_r'
                    )
                    fig_menos.update_traces(texttemplate='%{text}', textposition='auto', hovertemplate='<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>')
                    fig_menos.update_layout(yaxis={'categoryorder':'total descending'}, showlegend=False, xaxis_title="Venta Total ($)", yaxis_title="Referencia / Producto")
                    st.plotly_chart(fig_menos, use_container_width=True)

                st.markdown("---")
                st.subheader("📋 Consolidado Completo de Referencias")
                
                # Buscador y descarga
                col_b_ref, col_d_ref = st.columns([3, 1])
                with col_b_ref:
                    busq_ref = st.text_input("🔍 Buscar referencia específica:", "", key="busq_referencia_txt")
                
                df_tabla_ref = df_ref_group.copy()
                df_tabla_ref.rename(columns={col_referencia: "Referencia / Producto", col_valor: f"Venta Total ({anio_ref_base})"}, inplace=True)
                
                if busq_ref:
                    df_tabla_ref = df_tabla_ref[df_tabla_ref["Referencia / Producto"].astype(str).str.contains(busq_ref, case=False, na=False)]

                with col_d_ref:
                    st.write("")
                    st.download_button(
                        label="📥 Descargar Referencias CSV",
                        data=df_tabla_ref.to_csv(index=False).encode('utf-8'),
                        file_name=f"analisis_referencias_{anio_ref_base}.csv",
                        mime="text/csv",
                        key="dl_ref_csv"
                    )

                df_tabla_ref[f"Venta Total ({anio_ref_base})"] = df_tabla_ref[f"Venta Total ({anio_ref_base})"].apply(lambda x: f"${x:,.0f}")
                st.dataframe(df_tabla_ref, use_container_width=True, height=350)

            else:
                st.info("No hay datos de referencias para los filtros seleccionados.")
        else:
            st.warning("⚠️ Selecciona el año y meses para el análisis de referencias.")

except Exception as e:
    st.error(f"Ocurrió un error al procesar la aplicación: {e}")
