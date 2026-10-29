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
    col_cliente = detectar_columna(['Nombre Cliente', 'Cliente', 'Documento Cliente'], 3)
    col_anio = detectar_columna(['Año', 'Anio', 'Year'], 4)
    col_mes = detectar_columna(['Mes', 'Month'], 5)
    col_valor = detectar_columna(['Ventas Det', 'Venta', 'Valor', 'Total'], 6)

    # Asegurar tipo numérico limpio en la columna de valor global
    df[col_valor] = pd.to_numeric(df[col_valor], errors='coerce').fillna(0)
    df[col_anio] = pd.to_numeric(df[col_anio], errors='coerce')

    # --- BARRA LATERAL: FILTROS PRINCIPALES ---
    st.sidebar.header("🎯 Filtros")

    df_f = df.copy()

    # 1. Código UN (Regional)
    opciones_reg = ["Todos"] + sorted([str(x) for x in df_f[col_regional].dropna().unique()])
    sel_reg = st.sidebar.selectbox("Código UN (Regional)", opciones_reg, index=0)
    if sel_reg != "Todos":
        df_f = df_f[df_f[col_regional].astype(str) == sel_reg]

    # 2. Canal / Tipo de Cliente
    opciones_canal = ["Todos"] + sorted([str(x) for x in df_f[col_canal].dropna().unique()])
    sel_canal = st.sidebar.selectbox("Canal", opciones_canal, index=0)
    if sel_canal != "Todos":
        df_f = df_f[df_f[col_canal].astype(str) == sel_canal]

    # 3. Supervisor / Gerente de Unidad
    opciones_gerente = ["Todos"] + sorted([str(x) for x in df_f[col_gerente].dropna().unique()])
    sel_gerente = st.sidebar.selectbox("Supervisor", opciones_gerente, index=0)
    if sel_gerente != "Todos":
        df_f = df_f[df_f[col_gerente].astype(str) == sel_gerente]

    # --- CUERPO PRINCIPAL: FILTROS DE AÑO Y MESES ARRIBA ---
    st.subheader("📅 Panel de Control Temporal")
    
    col_f1, col_f2 = st.columns([1, 3])
    
    with col_f1:
        anios_disp = sorted(df_f[col_anio].dropna().unique())
        anio_base = st.selectbox("Selecciona el Año Base:", anios_disp, index=len(anios_disp)-1 if anios_disp else 0)

    with col_f2:
        # Orden cronológico estricto para los meses
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
            meses_sel = st.segmented_control("Selecciona los meses activos:", options=meses_disp, default=meses_disp, selection_mode="multi")
        else:
            meses_sel = st.multiselect("Selecciona los meses activos:", options=meses_disp, default=list(meses_disp))

    st.markdown("---")

    if anio_base and meses_sel:
        anio_sel = int(anio_base)
        anio_anterior = anio_sel - 1

        # Filtrado estricto por período seleccionado
        df_actual = df_f[(df_f[col_anio] == anio_sel) & (df_f[col_mes].isin(meses_sel))]
        df_ant = df_f[(df_f[col_anio] == anio_anterior) & (df_f[col_mes].isin(meses_sel))]

        # Cálculos generales para KPIs (sin decimales)
        total_actual = df_actual[col_valor].sum()
        total_anterior = df_ant[col_valor].sum()
        crecimiento_global = ((total_actual / total_anterior) - 1) * 100 if total_anterior > 0 else 0

        # Tarjetas de Métricas principales (sin decimales)
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(label=f"Ventas Total ({anio_sel})", value=f"${total_actual:,.0f}")
        kpi2.metric(label=f"Ventas Total ({anio_anterior})", value=f"${total_anterior:,.0f}", delta=f"{crecimiento_global:,.0f}% YoY")
        kpi3.metric(label="Meses Evaluados", value=f"{len(meses_sel)} mes(es)")

        st.markdown("---")

        # --- GRÁFICOS INTERACTIVOS (BARRAS) ---
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.subheader(f"📊 Ventas por Regional ({anio_sel})")
            if not df_actual.empty:
                df_reg = df_actual.groupby(col_regional)[col_valor].sum().reset_index()
                df_reg = df_reg.sort_values(by=col_valor, ascending=False).head(10)
                
                df_reg['Texto_Moneda'] = df_reg[col_valor].apply(lambda x: f"${x:,.0f}")

                fig_reg = px.bar(
                    df_reg, x=col_valor, y=col_regional, orientation='h',
                    text='Texto_Moneda', color=col_valor, color_continuous_scale='Blues'
                )
                fig_reg.update_traces(
                    texttemplate='%{text}', 
                    textposition='auto',
                    hovertemplate='<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>'
                )
                fig_reg.update_layout(
                    yaxis={'categoryorder':'total ascending'}, 
                    showlegend=False, 
                    xaxis_title="Venta ($)", 
                    yaxis_title="Regional",
                    coloraxis_colorbar=dict(tickformat=",.0f")
                )
                st.plotly_chart(fig_reg, use_container_width=True)
            else:
                st.info("Sin datos para los filtros seleccionados.")

        with col_g2:
            st.subheader("🏆 Top Clientes")
            if not df_actual.empty:
                df_cli_top = df_actual.groupby(col_cliente)[col_valor].sum().reset_index()
                df_cli_top = df_cli_top.sort_values(by=col_valor, ascending=False).head(10)
                
                df_cli_top['Texto_Moneda'] = df_cli_top[col_valor].apply(lambda x: f"${x:,.0f}")

                fig_cli = px.bar(
                    df_cli_top, x=col_valor, y=col_cliente, orientation='h',
                    text='Texto_Moneda', color=col_valor, color_continuous_scale='Greens'
                )
                fig_cli.update_traces(
                    texttemplate='%{text}', 
                    textposition='auto',
                    hovertemplate='<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>'
                )
                fig_cli.update_layout(
                    yaxis={'categoryorder':'total ascending'}, 
                    showlegend=False, 
                    xaxis_title="Venta ($)", 
                    yaxis_title="Cliente",
                    coloraxis_colorbar=dict(tickformat=",.0f")
                )
                st.plotly_chart(fig_cli, use_container_width=True)
            else:
                st.info("Sin datos para los filtros seleccionados.")

        st.markdown("---")

        # --- GRÁFICO DE TENDENCIA MENSUAL (LÍNEAS YoY - ALTURA AJUSTADA) ---
        st.subheader(f"📈 Tendencia Mensual de Ventas ({anio_sel} vs {anio_anterior})")
        df_tendencia = df_f[df_f[col_anio].isin([anio_sel, anio_anterior])]
        if not df_tendencia.empty:
            df_tend = df_tendencia.groupby([col_mes, col_anio])[col_valor].sum().reset_index()
            df_tend['Mes_Orden'] = df_tend[col_mes].apply(obtener_peso_mes)
            df_tend = df_tend.sort_values(by='Mes_Orden')
            df_tend[col_anio] = df_tend[col_anio].astype(str)

            fig_tend = px.line(
                df_tend, x=col_mes, y=col_valor, color=col_anio, markers=True,
                labels={col_mes: "Mes", col_valor: "Venta Total ($)", col_anio: "Año"},
                color_discrete_sequence=['#1f77b4', '#aec7e8']
            )
            fig_tend.update_traces(hovertemplate='<b>Mes: %{x}</b><br>Venta: $%{y:,.0f}<extra></extra>')
            fig_tend.update_layout(
                xaxis_title="Mes", 
                yaxis_title="Venta Total ($)",
                height=350  # <-- Altura optimizada para que luzca proporcionada
            )
            st.plotly_chart(fig_tend, use_container_width=True)
        else:
            st.info("No hay datos suficientes para la tendencia mensual.")

        st.markdown("---")

        # --- TABLA COMPARATIVA DE CLIENTES CON ESTILOS CONDICIONALES Y DESCARGA ---
        st.subheader("📋 Detalle por Cliente (Año Actual vs. Año Anterior)")

        col_busq, col_desc = st.columns([3, 1])
        with col_busq:
            busqueda_tabla = st.text_input("🔍 Escribe el nombre del cliente para buscar en la tabla:", "")

        ventas_actual = df_actual.groupby(col_cliente)[col_valor].sum().reset_index()
        ventas_actual.rename(columns={col_valor: f'Venta {anio_sel}'}, inplace=True)

        ventas_anterior = df_ant.groupby(col_cliente)[col_valor].sum().reset_index()
        ventas_anterior.rename(columns={col_valor: f'Venta {anio_anterior}'}, inplace=True)

        tabla_final = pd.merge(ventas_actual, ventas_anterior, on=col_cliente, how='outer').fillna(0)

        tabla_final['Variación ($)'] = tabla_final[f'Venta {anio_sel}'] - tabla_final[f'Venta {anio_anterior}']
        tabla_final['Variación (%)'] = ((tabla_final[f'Venta {anio_sel}'] / tabla_final[f'Venta {anio_anterior}'].replace(0, 1)) - 1) * 100
        
        tabla_final = tabla_final.sort_values(by=f'Venta {anio_sel}', ascending=False)

        if busqueda_tabla:
            tabla_final = tabla_final[tabla_final[col_cliente].astype(str).str.contains(busqueda_tabla, case=False, na=False)]

        # Botón de descarga CSV
        with col_desc:
            st.write("") 
            csv_data = tabla_final.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descargar CSV",
                data=csv_data,
                file_name=f"detalle_clientes_{anio_sel}.csv",
                mime="text/csv",
            )

        # Función de estilo condicional robusta para verde (crece) y rojo (decrece)
        def color_variacion(val):
            try:
                if isinstance(val, (int, float)):
                    if val > 0:
                        return 'color: #2E7D32; font-weight: bold;'
                    elif val < 0:
                        return 'color: #C62828; font-weight: bold;'
            except:
                pass
            return ''

        # Formatos finales en moneda y porcentajes sin decimales
        format_dict = {
            f'Venta {anio_sel}': '${:,.0f}',
            f'Venta {anio_anterior}': '${:,.0f}',
            'Variación ($)': '${:,.0f}',
            'Variación (%)': '{:,.0f}%'
        }

        tabla_estilizada = (
            tabla_final.style
            .format(format_dict)
            .map(color_variacion, subset=['Variación ($)', 'Variación (%)'])
        )

        st.caption(f"Comparativa activa para: **{', '.join(map(str, meses_sel))}** ({anio_sel} vs. {anio_anterior})")
        st.dataframe(tabla_estilizada, use_container_width=True)

    else:
        st.warning("⚠️ Selecciona un Año Base y al menos un Mes.")

except Exception as e:
    st.error(f"Ocurrió un error al procesar la aplicación: {e}")
