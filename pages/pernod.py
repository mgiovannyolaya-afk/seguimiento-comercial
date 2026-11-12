import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="SEGUIMIENTO PERNOD RICARD", layout="wide")

st.markdown("""
    <style>
        [data-testid="stMetricValue"] {
            font-size: 1.35rem !important;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🍾 SEGUIMIENTO PERNOD RICARD 🥂")
st.markdown("---")

@st.cache_data
def cargar_datos():
    xls_path = "BV PERNOD TODA.xlsb"
    dfs_dict = pd.read_excel(xls_path, sheet_name=None, engine="pyxlsb")
    df_ventas = pd.concat(dfs_dict.values(), ignore_index=True)
    
    try:
        xl = pd.ExcelFile(xls_path, engine="pyxlsb")
        nombres_hojas = xl.sheet_names
        nombre_ppto_real = next((h for h in nombres_hojas if 'ppto' in h.lower()), nombres_hojas[1] if len(nombres_hojas) > 1 else 0)
        df_ppto = pd.read_excel(xls_path, sheet_name=nombre_ppto_real, engine="pyxlsb")
    except Exception:
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
    df[col_anio] = pd.to_numeric(df[col_anio], errors='coerce').fillna(0).astype(int)

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

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard General & Clientes", 
        "📦 Análisis de Referencias (YoY)", 
        "🎯 Presupuesto & Zonas (PPTO)",
        "🔍 Detalle Clientes y Referencias"
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

    with tab1:
        st.subheader("📅 Panel de Control Temporal")
        col_f1, col_f2 = st.columns([1, 3])
        
        with col_f1:
            anios_disp = sorted([int(x) for x in df_f[col_anio].dropna().unique() if x > 0])
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

            cli_unicos_act = df_actual[df_actual[col_valor] > 1][col_cliente].nunique()
            cli_unicos_ant = df_ant[df_ant[col_valor] > 1][col_cliente].nunique()

            ticket_prom_act = total_actual / cli_unicos_act if cli_unicos_act > 0 else 0
            ticket_prom_ant = total_anterior / cli_unicos_ant if cli_unicos_ant > 0 else 0
            var_ticket = ((ticket_prom_act / ticket_prom_ant) - 1) * 100 if ticket_prom_ant > 0 else 0

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric(label=f"Ventas Total ({anio_sel})", value=f"${total_actual:,.0f}")
            kpi2.metric(label=f"Ventas Total ({anio_anterior})", value=f"${total_anterior:,.0f}", delta=f"{crecimiento_global:,.0f}% YoY")
            kpi3.metric(label="Ticket Promedio / Cliente", value=f"${ticket_prom_act:,.0f}", delta=f"{var_ticket:+,.1f}% YoY")
            kpi4.metric(label="Meses Evaluados", value=f"{len(meses_sel)} mes(es)")

            st.markdown("---")
            st.subheader("📋 Detalle Avanzado por Cliente")
            col_busq, col_desc = st.columns([3, 1])
            with col_busq: busqueda_tabla = st.text_input("🔍 Buscar cliente:", "", key="busq_cli_tab1")

            ventas_actual = df_actual.groupby(col_cliente)[col_valor].sum().reset_index().rename(columns={col_valor: f'Venta {anio_sel}'})
            ventas_anterior = df_ant.groupby(col_cliente)[col_valor].sum().reset_index().rename(columns={col_valor: f'Venta {anio_anterior}'})
            
            pedidos_act = df_actual.groupby(col_cliente).size().reset_index(name='Pedidos_Act')
            pedidos_ant = df_ant.groupby(col_cliente).size().reset_index(name='Pedidos_Ant')
            skus_act = df_actual[df_actual[col_valor] > 0].groupby(col_cliente)[col_referencia].nunique().reset_index(name='Portafolio (SKUs)')

            tabla_final = pd.merge(ventas_actual, ventas_anterior, on=col_cliente, how='outer').fillna(0)
            tabla_final = pd.merge(tabla_final, pedidos_act, on=col_cliente, how='left').fillna(1)
            tabla_final = pd.merge(tabla_final, pedidos_ant, on=col_cliente, how='left').fillna(1)
            tabla_final = pd.merge(tabla_final, skus_act, on=col_cliente, how='left').fillna(0)

            tabla_final[f'Ticket Prom. {anio_sel}'] = tabla_final[f'Venta {anio_sel}'] / tabla_final['Pedidos_Act']
            tabla_final[f'Ticket Prom. {anio_anterior}'] = tabla_final[f'Venta {anio_anterior}'] / tabla_final['Pedidos_Ant']
            tabla_final['Variación ($)'] = tabla_final[f'Venta {anio_sel}'] - tabla_final[f'Venta {anio_anterior}']
            tabla_final['Variación (%)'] = ((tabla_final[f'Venta {anio_sel}'] / tabla_final[f'Venta {anio_anterior}'].replace(0, 1)) - 1) * 100

            cols_mostrar = [
                col_cliente, f'Venta {anio_sel}', f'Venta {anio_anterior}', 
                'Variación ($)', 'Variación (%)', f'Ticket Prom. {anio_sel}', 'Portafolio (SKUs)'
            ]
            tabla_final = tabla_final[cols_mostrar].sort_values(by=f'Venta {anio_sel}', ascending=False)

            if busqueda_tabla:
                tabla_final = tabla_final[tabla_final[col_cliente].astype(str).str.contains(busqueda_tabla, case=False, na=False)]

            with col_desc:
                st.write("")
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    tabla_final.to_excel(writer, index=False, sheet_name='Detalle Clientes')
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Descargar Excel", 
                    data=excel_data, 
                    file_name=f"detalle_avanzado_clientes_{anio_sel}.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                    key="dl_excel_tab1"
                )

            format_dict = {
                f'Venta {anio_sel}': '${:,.0f}', f'Venta {anio_anterior}': '${:,.0f}', 
                'Variación ($)': '${:,.0f}', 'Variación (%)': '{:,.0f}%',
                f'Ticket Prom. {anio_sel}': '${:,.0f}', 'Portafolio (SKUs)': '{:,.0f}'
            }
            st.dataframe(tabla_final.style.format(format_dict).map(color_variacion, subset=['Variación ($)', 'Variación (%)']), use_container_width=True, height=400)
        else:
            st.warning("⚠️ Selecciona un Año Base y al menos un Mes.")

except Exception as e:
    st.error(f"⚠️ Ocurrió un error al procesar los datos o las columnas del archivo: {e}")
