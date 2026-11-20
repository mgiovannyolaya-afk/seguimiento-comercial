import os
import hashlib
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import calendar
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


def _firma_archivo(ruta: str) -> str:
    """Genera una firma única basada en tamaño, fecha de modificación y hash MD5 del archivo."""
    if not os.path.exists(ruta):
        return "missing"
    stat = os.stat(ruta)
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"{stat.st_size}-{stat.st_mtime_ns}-{h.hexdigest()}"


@st.cache_data(show_spinner="Cargando base actualizada...")
def cargar_datos(firma_version: str = ""):
    xls_path = "BV PERNOD TODA.xlsb"
    xl = pd.ExcelFile(xls_path, engine="pyxlsb")
    nombres_hojas = xl.sheet_names

    # Identificar hoja de PPTO y excluirla de ventas para evitar mezclar columnas o ceros
    nombre_ppto_real = next((h for h in nombres_hojas if "ppto" in str(h).lower()), None)
    hojas_ventas = [h for h in nombres_hojas if h != nombre_ppto_real]
    if not hojas_ventas:
        hojas_ventas = [nombres_hojas[0]]

    dfs_ventas = [pd.read_excel(xl, sheet_name=h) for h in hojas_ventas]
    df_ventas = pd.concat(dfs_ventas, ignore_index=True)

    df_ppto = pd.read_excel(xl, sheet_name=nombre_ppto_real) if nombre_ppto_real else pd.DataFrame()
    return df_ventas, df_ppto


MAPA_MESES = {
    "ene": "Ene", "enero": "Ene", "jan": "Ene", "january": "Ene", "1": "Ene", "01": "Ene",
    "feb": "Feb", "febrero": "Feb", "february": "Feb", "2": "Feb", "02": "Feb",
    "mar": "Mar", "marzo": "Mar", "march": "Mar", "3": "Mar", "03": "Mar",
    "abr": "Abr", "abril": "Abr", "apr": "Abr", "april": "Abr", "4": "Abr", "04": "Abr",
    "may": "May", "mayo": "May", "5": "May", "05": "May",
    "jun": "Jun", "junio": "Jun", "june": "Jun", "6": "Jun", "06": "Jun",
    "jul": "Jul", "julio": "Jul", "july": "Jul", "7": "Jul", "07": "Jul",
    "ago": "Ago", "agosto": "Ago", "aug": "Ago", "august": "Ago", "8": "Ago", "08": "Ago",
    "sep": "Sep", "sept": "Sep", "septiembre": "Sep", "setiembre": "Sep", "september": "Sep", "9": "Sep", "09": "Sep",
    "oct": "Oct", "octubre": "Oct", "october": "Oct", "10": "Oct",
    "nov": "Nov", "noviembre": "Nov", "november": "Nov", "11": "Nov",
    "dic": "Dic", "diciembre": "Dic", "dec": "Dic", "december": "Dic", "12": "Dic",
}

PESO_MESES = {
    "Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dic": 12
}


def limpiar_etiqueta_mes(val) -> str:
    if pd.isna(val):
        return ""
    txt = str(val).strip().lower()
    if txt in MAPA_MESES:
        return MAPA_MESES[txt]
    for k, v in MAPA_MESES.items():
        if len(k) >= 3 and k in txt:
            return v
    return str(val).strip().title()


def obtener_peso_mes(m) -> int:
    limpio = limpiar_etiqueta_mes(m)
    return PESO_MESES.get(limpio, 999)


def color_variacion(val):
    try:
        if isinstance(val, (int, float)):
            if val > 0:
                return "color: #2E7D32; font-weight: bold;"
            elif val < 0:
                return "color: #C62828; font-weight: bold;"
    except Exception:
        pass
    return ""


try:
    ruta_base = "BV PERNOD TODA.xlsb"
    df, df_ppto = cargar_datos(_firma_archivo(ruta_base))
    columnas = df.columns.tolist()

    def detectar_columna(palabras_clave, fallback_idx=0):
        for pk in palabras_clave:
            for col in columnas:
                if pk.lower() == str(col).strip().lower():
                    return col
        for pk in palabras_clave:
            for col in columnas:
                if pk.lower() in str(col).strip().lower():
                    return col
        return columnas[fallback_idx] if fallback_idx < len(columnas) else columnas[0]

    col_regional = detectar_columna(["Código UN", "Cod UN", "Regional", "Región"], 1)
    col_canal = detectar_columna(["Tipo de Cliente", "Tipo cliente", "Canal", "Canal de Venta"], 0)
    col_gerente = detectar_columna(["Gerente Zona", "Gerente Unidad", "Supervisor", "Gerente"], 2)
    col_zona = detectar_columna(["Código Zona", "Codigo Zona", "Cod Zona", "Id Zona"], 3)
    col_cliente = detectar_columna(["Nombre Cliente", "Cliente", "Documento Cliente"], 4)
    col_referencia = detectar_columna(["Referencia", "Artículo", "Articulo", "SKU", "Producto", "Item", "Descripción Item"], 5)
    col_anio = detectar_columna(["Año", "Anio", "Year"], 6)
    col_mes = detectar_columna(["Mes", "Month"], 7)
    col_valor = detectar_columna(["Ventas Det", "Venta", "Valor", "Total"], 8)

    df[col_valor] = pd.to_numeric(
        df[col_valor].astype(str).str.replace(r"[\$\s]", "", regex=True),
        errors="coerce"
    ).fillna(0)
    df[col_anio] = pd.to_numeric(df[col_anio], errors="coerce").fillna(0).astype(int)
    df[col_mes] = df[col_mes].apply(limpiar_etiqueta_mes)
    df = df[df[col_mes] != ""]

    st.sidebar.header("🎯 Filtros Globales")
    df_f = df.copy()
    df_f_global = df.copy()

    opciones_reg = ["Todos"] + sorted([str(x) for x in df_f[col_regional].dropna().unique()])
    sel_reg = st.sidebar.selectbox("Código UN (Regional)", opciones_reg, index=0)
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

    meses_ordenados_base = sorted(
        [m for m in df_f[col_mes].dropna().unique() if str(m).strip() != ""],
        key=obtener_peso_mes
    )
    anios_base_disp = sorted([int(x) for x in df_f[col_anio].dropna().unique() if int(x) > 0])

    # Detectar automáticamente cualquier mes nuevo agregado en una base actualizada
    if "meses_conocidos" not in st.session_state:
        st.session_state["meses_conocidos"] = list(meses_ordenados_base)

    nuevos_meses = [m for m in meses_ordenados_base if m not in st.session_state["meses_conocidos"]]
    if nuevos_meses:
        st.session_state["meses_conocidos"] = list(meses_ordenados_base)
        for key_ms in ["meses_tab1_multi", "meses_tab2", "meses_ppto_multi"]:
            if key_ms in st.session_state:
                st.session_state[key_ms] = sorted(
                    list(set(st.session_state[key_ms]) | set(nuevos_meses)),
                    key=obtener_peso_mes
                )

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard General & Clientes",
        "📦 Análisis de Referencias (YoY)",
        "🎯 Presupuesto & Zonas (PPTO)",
        "🔍 Detalle Clientes y Referencias"
    ])

    with tab1:
        st.subheader("📅 Panel de Control Temporal")
        col_f1, col_f2 = st.columns([1, 3])

        with col_f1:
            anio_base = st.selectbox(
                "Selecciona el Año Base:",
                anios_base_disp,
                index=len(anios_base_disp) - 1 if anios_base_disp else 0,
                key="anio_tab1"
            )

        with col_f2:
            if "meses_tab1_multi" not in st.session_state:
                st.session_state["meses_tab1_multi"] = list(meses_ordenados_base)
            else:
                st.session_state["meses_tab1_multi"] = [
                    m for m in st.session_state["meses_tab1_multi"] if m in meses_ordenados_base
                ]
            meses_sel = st.multiselect(
                "Selecciona los meses activos:",
                options=meses_ordenados_base,
                key="meses_tab1_multi"
            )

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
            st.subheader("📈 Tendencia Mensual de Ventas (YoY)")
            df_tend_act = df_f[df_f[col_anio] == anio_sel].groupby(col_mes, as_index=False)[col_valor].sum()
            df_tend_act["Año"] = str(anio_sel)
            df_tend_ant = df_f[df_f[col_anio] == anio_anterior].groupby(col_mes, as_index=False)[col_valor].sum()
            df_tend_ant["Año"] = str(anio_anterior)

            df_tendencia = pd.concat([df_tend_act, df_tend_ant], ignore_index=True)
            df_tendencia["Mes_Orden"] = df_tendencia[col_mes].apply(obtener_peso_mes)
            df_tendencia = df_tendencia.sort_values(by="Mes_Orden")

            if not df_tendencia.empty:
                fig_tend = px.line(
                    df_tendencia, x=col_mes, y=col_valor, color="Año", markers=True,
                    color_discrete_map={str(anio_sel): "#0066cc", str(anio_anterior): "#94a3b8"}
                )
                fig_tend.update_traces(hovertemplate="<b>Mes:</b> %{x}<br><b>Venta:</b> $%{y:,.0f}<extra></extra>")
                fig_tend.update_layout(xaxis_title="Mes", yaxis_title="Venta Total ($)", legend_title="Año", height=350, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig_tend, use_container_width=True)

            st.markdown("---")
            st.subheader("🌐 Resumen de Variación General por Unidad de Negocio")
            df_global_actual = df_f_global[(df_f_global[col_anio] == anio_sel) & (df_f_global[col_mes].isin(meses_sel))]
            df_global_ant = df_f_global[(df_f_global[col_anio] == anio_anterior) & (df_f_global[col_mes].isin(meses_sel))]

            reg_actual = df_global_actual.groupby(col_regional, as_index=False)[col_valor].sum().rename(columns={col_valor: f"Venta {anio_sel}"})
            reg_ant = df_global_ant.groupby(col_regional, as_index=False)[col_valor].sum().rename(columns={col_valor: f"Venta {anio_anterior}"})

            tabla_un_final = pd.merge(reg_actual, reg_ant, on=col_regional, how="outer").fillna(0)
            tabla_un_final["Variación ($)"] = tabla_un_final[f"Venta {anio_sel}"] - tabla_un_final[f"Venta {anio_anterior}"]
            tabla_un_final["Variación (%)"] = ((tabla_un_final[f"Venta {anio_sel}"] / tabla_un_final[f"Venta {anio_anterior}"].replace(0, 1)) - 1) * 100
            tabla_un_final["Crecimiento_Tipo"] = tabla_un_final["Variación (%)"].apply(lambda x: "Crecimiento" if x >= 0 else "Decrecimiento")

            col_vis1, col_vis2 = st.columns([1.2, 1])
            with col_vis1:
                orden_vis = tabla_un_final.sort_values(by="Variación (%)", ascending=True)
                fig_un_vis = px.bar(
                    orden_vis,
                    x="Variación (%)", y=col_regional, orientation="h",
                    color="Crecimiento_Tipo", color_discrete_map={"Crecimiento": "#2E7D32", "Decrecimiento": "#C62828"},
                    text=orden_vis["Variación (%)"].apply(lambda x: f"{x:,.0f}%")
                )
                fig_un_vis.update_traces(textposition="outside", hovertemplate="<b>%{y}</b><br>Variación: %{x:,.1f}%<extra></extra>")
                fig_un_vis.update_layout(xaxis_title="Variación (%)", yaxis_title="", showlegend=False, height=300, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_un_vis, use_container_width=True)

            with col_vis2:
                format_dict_un = {
                    f"Venta {anio_sel}": "${:,.0f}",
                    f"Venta {anio_anterior}": "${:,.0f}",
                    "Variación ($)": "${:,.0f}",
                    "Variación (%)": "{:,.0f}%"
                }
                tabla_un_estilizada = (
                    tabla_un_final.sort_values(by=f"Venta {anio_sel}", ascending=False).style
                    .format(format_dict_un)
                    .map(color_variacion, subset=["Variación ($)", "Variación (%)"])
                    .hide(subset=["Crecimiento_Tipo"], axis="columns")
                )
                st.dataframe(tabla_un_estilizada, use_container_width=True, height=280)

            st.markdown("---")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader(f"📊 Ventas por Regional ({anio_sel})")
                if not df_actual.empty:
                    df_reg = df_actual.groupby(col_regional, as_index=False)[col_valor].sum().sort_values(by=col_valor, ascending=False).head(10)
                    df_reg["Texto_Moneda"] = df_reg[col_valor].apply(lambda x: f"${x:,.0f}")
                    fig_reg = px.bar(df_reg, x=col_valor, y=col_regional, orientation="h", text="Texto_Moneda", color=col_valor, color_continuous_scale="Blues")
                    fig_reg.update_traces(texttemplate="%{text}", textposition="auto", hovertemplate="<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>")
                    fig_reg.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False, xaxis_title="Venta ($)", yaxis_title="Regional")
                    st.plotly_chart(fig_reg, use_container_width=True)
                else:
                    st.info("Sin datos.")

            with col_g2:
                st.subheader("🏆 Top Clientes")
                if not df_actual.empty:
                    df_cli_top = df_actual.groupby(col_cliente, as_index=False)[col_valor].sum().sort_values(by=col_valor, ascending=False).head(10)
                    df_cli_top["Texto_Moneda"] = df_cli_top[col_valor].apply(lambda x: f"${x:,.0f}")
                    fig_cli = px.bar(df_cli_top, x=col_valor, y=col_cliente, orientation="h", text="Texto_Moneda", color=col_valor, color_continuous_scale="Greens")
                    fig_cli.update_traces(texttemplate="%{text}", textposition="auto", hovertemplate="<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>")
                    fig_cli.update_layout(yaxis={"categoryorder": "total ascending"}, showlegend=False, xaxis_title="Venta ($)", yaxis_title="Cliente")
                    st.plotly_chart(fig_cli, use_container_width=True)
                else:
                    st.info("Sin datos.")

            st.markdown("---")
            st.subheader("📋 Detalle Avanzado por Cliente (Ventas, Ticket Promedio y Portafolio)")
            col_busq, col_desc = st.columns([3, 1])
            with col_busq:
                busqueda_tabla = st.text_input("🔍 Buscar cliente:", "", key="busq_cli_tab1")

            ventas_actual = df_actual.groupby(col_cliente, as_index=False)[col_valor].sum().rename(columns={col_valor: f"Venta {anio_sel}"})
            ventas_anterior = df_ant.groupby(col_cliente, as_index=False)[col_valor].sum().rename(columns={col_valor: f"Venta {anio_anterior}"})

            pedidos_act = df_actual.groupby(col_cliente).size().reset_index(name="Pedidos_Act")
            pedidos_ant = df_ant.groupby(col_cliente).size().reset_index(name="Pedidos_Ant")
            skus_act = df_actual[df_actual[col_valor] > 0].groupby(col_cliente)[col_referencia].nunique().reset_index(name="Portafolio (SKUs)")

            tabla_final = pd.merge(ventas_actual, ventas_anterior, on=col_cliente, how="outer").fillna(0)
            tabla_final = pd.merge(tabla_final, pedidos_act, on=col_cliente, how="left").fillna({"Pedidos_Act": 1})
            tabla_final = pd.merge(tabla_final, pedidos_ant, on=col_cliente, how="left").fillna({"Pedidos_Ant": 1})
            tabla_final = pd.merge(tabla_final, skus_act, on=col_cliente, how="left").fillna({"Portafolio (SKUs)": 0})

            tabla_final[f"Ticket Prom. {anio_sel}"] = tabla_final[f"Venta {anio_sel}"] / tabla_final["Pedidos_Act"].replace(0, 1)
            tabla_final[f"Ticket Prom. {anio_anterior}"] = tabla_final[f"Venta {anio_anterior}"] / tabla_final["Pedidos_Ant"].replace(
