from difflib import SequenceMatcher
import hashlib
import io
import os
import re
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="SEGUIMIENTO PERNOD RICARD", layout="wide")

st.markdown(
    """
    <style>
        [data-testid="stMetricValue"] {
            font-size: 1.35rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🍾 SEGUIMIENTO PERNOD RICARD 🥂")
st.markdown("---")


def _firma_archivo(ruta):
    if not os.path.exists(ruta):
        return "missing"
    stat = os.stat(ruta)
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"{stat.st_size}-{stat.st_mtime_ns}-{h.hexdigest()}"


def _limpiar_clave(val):
    if pd.isna(val):
        return ""
    txt = str(val).strip().lower()
    txt = re.sub(r"\.0$", "", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt


def _normalizar_texto_busqueda(val):
    if pd.isna(val):
        return ""
    txt = str(val).lower()
    txt = re.sub(r"[^a-z0-9\s]+", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


@st.cache_data
def cargar_datos(firma=""):
    xls_path = "BV PERNOD TODA.xlsb"
    xl = pd.ExcelFile(xls_path, engine="pyxlsb")
    nombres_hojas = xl.sheet_names

    nombre_ppto_real = next(
        (h for h in nombres_hojas if "ppto" in str(h).lower()),
        None,
    )
    nombre_marcas_real = next(
        (h for h in nombres_hojas if "marca" in str(h).lower()),
        None,
    )

    hojas_excluidas = {h for h in [nombre_ppto_real, nombre_marcas_real] if h is not None}
    hojas_ventas = [h for h in nombres_hojas if h not in hojas_excluidas]
    if not hojas_ventas:
        hojas_ventas = [nombres_hojas[0]]

    dfs_ventas = [pd.read_excel(xl, sheet_name=h, engine="pyxlsb") for h in hojas_ventas]
    df_ventas = pd.concat(dfs_ventas, ignore_index=True)

    try:
        df_ppto = (
            pd.read_excel(xl, sheet_name=nombre_ppto_real, engine="pyxlsb")
            if nombre_ppto_real is not None
            else pd.DataFrame()
        )
    except Exception:
        df_ppto = pd.DataFrame()

    try:
        df_marcas = (
            pd.read_excel(xl, sheet_name=nombre_marcas_real, engine="pyxlsb")
            if nombre_marcas_real is not None
            else pd.DataFrame()
        )
    except Exception:
        df_marcas = pd.DataFrame()

    return df_ventas, df_ppto, df_marcas


try:
    df, df_ppto, df_marcas = cargar_datos(_firma_archivo("BV PERNOD TODA.xlsb"))
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

    col_regional = detectar_columna(["Código UN", "Cod UN", "Regional", "Región"], 1)
    col_canal = detectar_columna(["Tipo de Cliente", "Tipo cliente", "Canal", "Canal de Venta"], 0)
    col_gerente = detectar_columna(["Gerente Zona", "Gerente Unidad", "Supervisor", "Gerente"], 2)
    col_zona = detectar_columna(["Código Zona", "Codigo Zona", "Cod Zona", "Id Zona"], 3)
    col_cliente = detectar_columna(["Nombre Cliente", "Cliente", "Documento Cliente"], 4)
    col_referencia = detectar_columna(["Referencia", "Artículo", "Articulo", "SKU", "Producto", "Item", "Descripción Item", "Descripcion"], 5)

    col_nombre_producto = next(
        (
            c for c in columnas
            if any(
                k in _normalizar_texto_busqueda(c)
                for k in ["nombre de producto", "nombre producto", "nombre del producto", "nombre item", "descripcion", "descripción"]
            )
        ),
        None,
    )

    col_anio = detectar_columna(["Año", "Anio", "Year"], 6)
    col_mes = detectar_columna(["Mes", "Month"], 7)
    col_valor = detectar_columna(["Ventas Det", "Venta", "Valor", "Total"], 8)

    df[col_valor] = pd.to_numeric(df[col_valor], errors="coerce").fillna(0)
    df[col_anio] = pd.to_numeric(df[col_anio], errors="coerce").fillna(0).astype(int)

    mapa_meses = {
        "ene": "Ene", "enero": "Ene", "1": "Ene", "01": "Ene",
        "feb": "Feb", "febrero": "Feb", "2": "Feb", "02": "Feb",
        "mar": "Mar", "marzo": "Mar", "3": "Mar", "03": "Mar",
        "abr": "Abr", "abril": "Abr", "4": "Abr", "04": "Abr",
        "may": "May", "mayo": "May", "5": "May", "05": "May",
        "jun": "Jun", "junio": "Jun", "6": "Jun", "06": "Jun",
        "jul": "Jul", "julio": "Jul", "7": "Jul", "07": "Jul",
        "ago": "Ago", "agosto": "Ago", "8": "Ago", "08": "Ago",
        "sep": "Sep", "sept": "Sep", "septiembre": "Sep", "9": "Sep", "09": "Sep",
        "oct": "Oct", "octubre": "Oct", "10": "Oct",
        "nov": "Nov", "noviembre": "Nov", "11": "Nov",
        "dic": "Dic", "diciembre": "Dic", "12": "Dic",
    }
    df[col_mes] = (
        df[col_mes]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda x: mapa_meses.get(x, x.capitalize()))
    )

    mapa_cod_marca = {}
    mapa_desc_marca = {}
    marcas_conocidas = []
    pistas_por_marca = {}

    alias_comunes = {
        "ballantine": ["ballant", "ballan", "ballanti", "finest", "leno"],
        "chivas": ["chivas", "12yo", "13yo", "18yo", "sherry", "extra"],
        "glenlivet": ["glenliv", "glenlivet", "founders", "caribean", "caribbean"],
        "something": ["something", "some", "special"],
        "passport": ["passport", "passpor", "pass", "pas", "selection"],
        "olmeca": ["olmeca", "olme", "reposado", "blanco"],
        "absolut": ["absolut", "absolu", "abs"],
        "dubonnet": ["dubonnet", "dubonne", "aperitivo"],
        "beefeater": ["beefeater", "beef"],
        "jameson": ["jameson", "jame"],
        "perrier": ["perrier", "jouet"],
        "mumm": ["mumm"],
        "ricard": ["ricard", "pernod"],
        "ojo de tigre": ["ojo de tigre", "tigre"],
    }

    marcas_base_respaldo = [
        ("Passport", ["passport", "passpor", "pass", "pas"]),
        ("Olmeca", ["olmeca", "olme"]),
        ("Dubonnet", ["dubonnet", "dubonne"]),
        ("Absolut", ["absolut", "absolu", "abs"]),
        ("Ballantine's", ["ballantine", "ballant", "ballan"]),
        ("Chivas Regal", ["chivas"]),
        ("The Glenlivet", ["glenlivet", "glenliv"]),
        ("Something Special", ["something", "some"]),
        ("Beefeater", ["beefeater", "beef"]),
        ("Jameson", ["jameson", "jame"]),
        ("Ojo de Tigre", ["ojo de tigre", "tigre"]),
    ]

    if not df_marcas.empty:
        cols_m = df_marcas.columns.tolist()
        m_marca = next((c for c in cols_m if "marca" in str(c).lower()), cols_m[0])
        m_ean = next((c for c in cols_m if "ean" in str(c).lower() or "codigo" in str(c).lower() or "código" in str(c).lower() or "ref" in str(c).lower()), None)
        m_desc = next((c for c in cols_m if "desc" in str(c).lower() or "nombre" in str(c).lower() or "prod" in str(c).lower()), None)

        marcas_conocidas = sorted(
            [str(x).strip() for x in df_marcas[m_marca].dropna().unique() if str(x).strip() != ""],
            key=len,
            reverse=True,
        )

        for mc in marcas_conocidas:
            mc_norm = _normalizar_texto_busqueda(mc)
            pistas = set()
            for tok in mc_norm.split():
                if len(tok) >= 3 and tok not in {"years", "year", "old", "the", "and", "de", "la", "el"}:
                    pistas.add(tok)
                    if len(tok) >= 5:
                        pistas.add(tok[:5])
            for clave_al, lista_al in alias_comunes.items():
                if clave_al in mc_norm:
                    for al in lista_al:
                        pistas.add(_normalizar_texto_busqueda(al))
            pistas_por_marca[mc] = sorted([p for p in pistas if p], key=len, reverse=True)

        for _, row in df_marcas.iterrows():
            marca_val = str(row[m_marca]).strip() if pd.notna(row[m_marca]) else ""
            if not marca_val:
                continue
            if m_ean and pd.notna(row[m_ean]):
                k_ean = _limpiar_clave(row[m_ean])
                if k_ean and k_ean not in mapa_cod_marca:
                    mapa_cod_marca[k_ean] = marca_val
            if m_desc and pd.notna(row[m_desc]):
                k_desc = _limpiar_clave(row[m_desc])
                if k_desc and k_desc not in mapa_desc_marca:
                    mapa_desc_marca[k_desc] = marca_val

    for nombre_b, pistas_b in marcas_base_respaldo:
        existe_ya = any(nombre_b.lower() in mc.lower() for mc in marcas_conocidas)
        if not existe_ya:
            marcas_conocidas.append(nombre_b)
            pistas_por_marca[nombre_b] = sorted(
                [_normalizar_texto_busqueda(p) for p in pistas_b if p],
                key=len,
                reverse=True,
            )
        else:
            for mc in marcas_conocidas:
                if nombre_b.lower() in mc.lower():
                    actuales = set(pistas_por_marca.get(mc, []))
                    for p in pistas_b:
                        actuales.add(_normalizar_texto_busqueda(p))
                    pistas_por_marca[mc] = sorted([p for p in actuales if p], key=len, reverse=True)

    marcas_conocidas = sorted(
        [m for m in set(marcas_conocidas) if _normalizar_texto_busqueda(m) != "otros"],
        key=len,
        reverse=True,
    )
    marca_respaldo_final = "Otros"

    def _buscar_marca_por_texto(texto_norm):
        if not texto_norm:
            return None
        for mc in marcas_conocidas:
            mc_norm = _normalizar_texto_busqueda(mc)
            if mc_norm and mc_norm in texto_norm:
                return mc
        for mc in marcas_conocidas:
            for pista in pistas_por_marca.get(mc, []):
                if pista and pista in texto_norm:
                    return mc
        mejor_mc = None
        mejor_ratio = 0.0
        for mc in marcas_conocidas:
            mc_norm = _normalizar_texto_busqueda(mc)
            if not mc_norm:
                continue
            for pal in texto_norm.split():
                if len(pal) >= 4:
                    ratio = SequenceMatcher(None, pal, mc_norm).ratio()
                    if ratio > mejor_ratio:
                        mejor_ratio = ratio
                        mejor_mc = mc
                    for tok_m in mc_norm.split():
                        if len(tok_m) >= 4:
                            r2 = SequenceMatcher(None, pal, tok_m).ratio()
                            if r2 > mejor_ratio:
                                mejor_ratio = r2
                                mejor_mc = mc
        if mejor_mc and mejor_ratio >= 0.78:
            return mejor_mc
        return None

    def resolver_marca_y_estado(fila):
        val_ref = fila[col_referencia]
        val_nom_prod = fila[col_nombre_producto] if col_nombre_producto else ""

        clave_ref = _limpiar_clave(val_ref)
        clave_nom = _limpiar_clave(val_nom_prod)

        if clave_ref in mapa_cod_marca:
            return mapa_cod_marca[clave_ref], "En base MARCAS"
        if clave_nom and clave_nom in mapa_desc_marca:
            return mapa_desc_marca[clave_nom], "En base MARCAS (por nombre producto)"
        if clave_ref in mapa_desc_marca:
            return mapa_desc_marca[clave_ref], "En base MARCAS (por desc.)"

        texto_prioritario = _normalizar_texto_busqueda(f"{val_nom_prod} {val_ref}")
        es_kv = bool(re.match(r"^kv(?:\b|[\s\-_:/0-9])", clave_nom)) or bool(
            re.match(r"^kv(?:\b|[\s\-_:/0-9])", clave_ref)
        )

        marca_detectada = _buscar_marca_por_texto(texto_prioritario)
        if marca_detectada:
            if es_kv:
                return marca_detectada, "KV asignado a marca"
            return marca_detectada, "Asignada por nombre de producto"

        if es_kv:
            return marca_respaldo_final, "KV asignado a Otros"

        return marca_respaldo_final, "Clasificada en Otros"

    res_marcas = df.apply(resolver_marca_y_estado, axis=1)
    df["Marca Estrategica"] = [r[0] for r in res_marcas]
    df["Estado Cruce Marca"] = [r[1] for r in res_marcas]

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

    opciones_marca = ["Todos"] + sorted([str(x) for x in df_f["Marca Estrategica"].dropna().unique()])
    sel_marca = st.sidebar.selectbox("Marca Estratégica", opciones_marca, index=0)
    if sel_marca != "Todos":
        df_f = df_f[df_f["Marca Estrategica"].astype(str) == sel_marca]

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard General & Clientes",
        "📦 Análisis de Referencias (YoY)",
        "🎯 Presupuesto & Zonas (PPTO)",
        "🍾 Análisis por Marcas & KV",
        "🔍 Detalle Clientes y Referencias",
    ])

    orden_meses_ref = [
        "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic",
        "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
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
                if val > 0:
                    return "color: #2E7D32; font-weight: bold;"
                elif val < 0:
                    return "color: #C62828; font-weight: bold;"
        except Exception:
            pass
        return ""

    with tab1:
        st.subheader("📅 Panel de Control Temporal")
        col_f1, col_f2 = st.columns([1, 3])

        with col_f1:
            anios_disp = sorted([int(x) for x in df_f[col_anio].dropna().unique() if x > 0])
            anio_base = st.selectbox("Selecciona el Año Base:", anios_disp, index=len(anios_disp) - 1 if anios_disp else 0, key="anio_tab1")

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
            st.subheader("📈 Tendencia Mensual de Ventas (YoY)")
            df_tend_act = df_f[df_f[col_anio] == anio_sel].groupby(col_mes)[col_valor].sum().reset_index()
            df_tend_act["Año"] = str(anio_sel)
            df_tend_ant = df_f[df_f[col_anio] == anio_anterior].groupby(col_mes)[col_valor].sum().reset_index()
            df_tend_ant["Año"] = str(anio_anterior)

            df_tendencia = pd.concat([df_tend_act, df_tend_ant])
            df_tendencia["Mes_Orden"] = df_tendencia[col_mes].apply(obtener_peso_mes)
            df_tendencia = df_tendencia.sort_values(by="Mes_Orden")

            if not df_tendencia.empty:
                fig_tend = px.line(
                    df_tendencia,
                    x=col_mes,
                    y=col_valor,
                    color="Año",
                    markers=True,
                    color_discrete_map={str(anio_sel): "#0066cc", str(anio_anterior): "#94a3b8"},
                )
                fig_tend.update_traces(hovertemplate="<b>Mes:</b> %{x}<br><b>Venta:</b> $%{y:,.0f}<extra></extra>")
                fig_tend.update_layout(xaxis_title="Mes", yaxis_title="Venta Total ($)", legend_title="Año", height=350, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig_tend, use_container_width=True)

            st.markdown("---")
            st.subheader("🌐 Resumen de Variación General por Unidad de Negocio")
            df_global_actual = df_f_global[(df_f_global[col_anio] == anio_sel) & (df_f_global[col_mes].isin(meses_sel))]
            df_global_ant = df_f_global[(df_f_global[col_anio] == anio_anterior) & (df_f_global[col_mes].isin(meses_sel))]

            reg_actual = df_global_actual.groupby(col_regional)[col_valor].sum().reset_index().rename(columns={col_valor: f"Venta {anio_sel}"})
            reg_ant = df_global_ant.groupby(col_regional)[col_valor].sum().reset_index().rename(columns={col_valor: f"Venta {anio_anterior}"})

            tabla_un_final = pd.merge(reg_actual, reg_ant, on=col_regional, how="outer").fillna(0)
            tabla_un_final["Variación ($)"] = tabla_un_final[f"Venta {anio_sel}"] - tabla_un_final[f"Venta {anio_anterior}"]
            tabla_un_final["Variación (%)"] = ((tabla_un_final[f"Venta {anio_sel}"] / tabla_un_final[f"Venta {anio_anterior}"].replace(0, 1)) - 1) * 100
            tabla_un_final["Crecimiento_Tipo"] = tabla_un_final["Variación (%)"].apply(lambda x: "Crecimiento" if x >= 0 else "Decrecimiento")

            col_vis1, col_vis2 = st.columns([1.2, 1])
            with col_vis1:
                fig_un_vis = px.bar(
                    tabla_un_final.sort_values(by="Variación (%)", ascending=True),
                    x="Variación (%)",
                    y=col_regional,
                    orientation="h",
                    color="Crecimiento_Tipo",
                    color_discrete_map={"Crecimiento": "#2E7D32", "Decrecimiento": "#C62828"},
                    text=tabla_un_final.sort_values(by="Variación (%)", ascending=True)["Variación (%)"].apply(lambda x: f"{x:,.0f}%"),
                )
                fig_un_vis.update_traces(textposition="outside", hovertemplate="<b>%{y}</b><br>Variación: %{x:,.1f}%<extra></extra>")
                fig_un_vis.update_layout(xaxis_title="Variación (%)", yaxis_title="", showlegend=False, height=300, margin=dict(l=0, r=0, t=10, b=0))
                st.plotly_chart(fig_un_vis, use_container_width=True)

            with col_vis2:
                format_dict_un = {
                    f"Venta {anio_sel}": "${:,.0f}",
                    f"Venta {anio_anterior}": "${:,.0f}",
                    "Variación ($)": "${:,.0f}",
                    "Variación (%)": "{:,.0f}%",
                }
                tabla_un_estilizada = (
                    tabla_un_final.sort_values(by=f"Venta {anio_sel}", ascending=False)
                    .style.format(format_dict_un)
                    .map(color_variacion, subset=["Variación ($)", "Variación (%)"])
                    .hide(subset=["Crecimiento_Tipo"], axis="columns")
                )
                st.dataframe(tabla_un_estilizada, use_container_width=True, height=280)

            st.markdown("---")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.subheader(f"📊 Ventas por Regional ({anio_sel})")
                if not df_actual.empty:
                    df_reg = df_actual.groupby(col_regional)[col_valor].sum().reset_index().sort_values(by=col_valor, ascending=False).head(10)
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
                    df_cli_top = df_actual.groupby(col_cliente)[col_valor].sum().reset_index().sort_values(by=col_valor, ascending=False).head(10)
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

            ventas_actual = df_actual.groupby(col_cliente)[col_valor].sum().reset_index().rename(columns={col_valor: f"Venta {anio_sel}"})
            ventas_anterior = df_ant.groupby(col_cliente)[col_valor].sum().reset_index().rename(columns={col_valor: f"Venta {anio_anterior}"})

            pedidos_act = df_actual.groupby(col_cliente).size().reset_index(name="Pedidos_Act")
            pedidos_ant = df_ant.groupby(col_cliente).size().reset_index(name="Pedidos_Ant")
            skus_act = df_actual[df_actual[col_valor] > 0].groupby(col_cliente)[col_referencia].nunique().reset_index(name="Portafolio (SKUs)")

            tabla_final = pd.merge(ventas_actual, ventas_anterior, on=col_cliente, how="outer").fillna(0)
            tabla_final = pd.merge(tabla_final, pedidos_act, on=col_cliente, how="left").fillna(1)
            tabla_final = pd.merge(tabla_final, pedidos_ant, on=col_cliente, how="left").fillna(1)
            tabla_final = pd.merge(tabla_final, skus_act, on=col_cliente, how="left").fillna(0)

            tabla_final[f"Ticket Prom. {anio_sel}"] = tabla_final[f"Venta {anio_sel}"] / tabla_final["Pedidos_Act"]
            tabla_final[f"Ticket Prom. {anio_anterior}"] = tabla_final[f"Venta {anio_anterior}"] / tabla_final["Pedidos_Ant"]
            tabla_final["Variación ($)"] = tabla_final[f"Venta {anio_sel}"] - tabla_final[f"Venta {anio_anterior}"]
            tabla_final["Variación (%)"] = ((tabla_final[f"Venta {anio_sel}"] / tabla_final[f"Venta {anio_anterior}"].replace(0, 1)) - 1) * 100

            cols_mostrar = [
                col_cliente, f"Venta {anio_sel}", f"Venta {anio_anterior}",
                "Variación ($)", "Variación (%)", f"Ticket Prom. {anio_sel}", "Portafolio (SKUs)",
            ]
            tabla_final = tabla_final[cols_mostrar].sort_values(by=f"Venta {anio_sel}", ascending=False)

            if busqueda_tabla:
                tabla_final = tabla_final[tabla_final[col_cliente].astype(str).str.contains(busqueda_tabla, case=False, na=False)]

            with col_desc:
                st.write("")
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    tabla_final.to_excel(writer, index=False, sheet_name="Detalle Clientes")
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Descargar Excel",
                    data=excel_data,
                    file_name=f"detalle_avanzado_clientes_{anio_sel}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_excel_tab1",
                )

            format_dict = {
                f"Venta {anio_sel}": "${:,.0f}",
                f"Venta {anio_anterior}": "${:,.0f}",
                "Variación ($)": "${:,.0f}",
                "Variación (%)": "{:,.0f}%",
                f"Ticket Prom. {anio_sel}": "${:,.0f}",
                "Portafolio (SKUs)": "{:,.0f}",
            }
            st.dataframe(tabla_final.style.format(format_dict).map(color_variacion, subset=["Variación ($)", "Variación (%)"]), use_container_width=True, height=400)

            st.markdown("---")
            st.subheader(f"⚠️ Clientes Inactivos (Compraron en {anio_anterior} pero tienen $0 en {anio_sel})")
            ventas_act_num = df_actual.groupby(col_cliente)[col_valor].sum()
            ventas_ant_num = df_ant.groupby(col_cliente)[col_valor].sum()
            clientes_cero = set(ventas_ant_num[ventas_ant_num > 0].index) - set(ventas_act_num[ventas_act_num > 0].index)
            df_inactivos_final = df_ant[df_ant[col_cliente].isin(clientes_cero)].groupby(col_cliente)[col_valor].sum().reset_index()
            df_inactivos_final.rename(columns={col_valor: f"Venta Histórica {anio_anterior}"}, inplace=True)
            df_inactivos_final = df_inactivos_final.sort_values(by=f"Venta Histórica {anio_anterior}", ascending=False)

            if not df_inactivos_final.empty:
                df_inactivos_final[f"Venta Histórica {anio_anterior}"] = df_inactivos_final[f"Venta Histórica {anio_anterior}"].apply(lambda x: f"${x:,.0f}")
                st.dataframe(df_inactivos_final, use_container_width=True)
            else:
                st.success(f"🎉 ¡Excelente noticia! No hay clientes inactivos para los filtros y meses seleccionados entre {anio_anterior} y {anio_sel}.")

        else:
            st.warning("⚠️ Selecciona un Año Base y al menos un Mes.")

    with tab2:
        st.subheader("📦 Análisis Avanzado de Referencias (YoY)")
        col_ref_f1, col_ref_f2, col_ref_f3 = st.columns([1, 2, 1])
        with col_ref_f1:
            anios_ref_disp = sorted([int(x) for x in df_f[col_anio].dropna().unique() if x > 0])
            anio_ref_base = st.selectbox("Año Actual:", anios_ref_disp, index=len(anios_ref_disp) - 1 if anios_ref_disp else 0, key="anio_tab2")
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

            ref_act = df_ref_actual.groupby(col_referencia)[col_valor].sum().reset_index().rename(columns={col_valor: f"Venta {anio_ref_sel}"})
            ref_ant = df_ref_ant.groupby(col_referencia)[col_valor].sum().reset_index().rename(columns={col_valor: f"Venta {anio_ref_ant}"})

            tabla_ref_comp = pd.merge(ref_act, ref_ant, on=col_referencia, how="outer").fillna(0)
            tabla_ref_comp["Variación ($)"] = tabla_ref_comp[f"Venta {anio_ref_sel}"] - tabla_ref_comp[f"Venta {anio_ref_ant}"]
            tabla_ref_comp["Variación (%)"] = ((tabla_ref_comp[f"Venta {anio_ref_sel}"] / tabla_ref_comp[f"Venta {anio_ref_ant}"].replace(0, 1)) - 1) * 100

            if not tabla_ref_comp.empty:
                st.markdown("---")
                st.markdown(f"### 🏆 Top {top_n} Referencias Más y Menos Vendidas ({anio_ref_sel})")
                col_mv1, col_mv2 = st.columns(2)

                df_top_mas = tabla_ref_comp.sort_values(by=f"Venta {anio_ref_sel}", ascending=False).head(top_n)
                df_top_menos = tabla_ref_comp[tabla_ref_comp[f"Venta {anio_ref_sel}"] > 0].sort_values(by=f"Venta {anio_ref_sel}", ascending=True).head(top_n)

                with col_mv1:
                    st.markdown("**🔥 Más Vendidas**")
                    df_top_mas["Texto_Moneda"] = df_top_mas[f"Venta {anio_ref_sel}"].apply(lambda x: f"${x:,.0f}")
                    fig_mas = px.bar(df_top_mas.sort_values(by=f"Venta {anio_ref_sel}", ascending=True), x=f"Venta {anio_ref_sel}", y=col_referencia, orientation="h", text="Texto_Moneda", color=f"Venta {anio_ref_sel}", color_continuous_scale="Greens")
                    fig_mas.update_traces(texttemplate="%{text}", textposition="auto", hovertemplate="<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>")
                    fig_mas.update_layout(showlegend=False, xaxis_title=f"Venta Total ($ {anio_ref_sel})", yaxis_title="Referencia / Producto", height=320)
                    st.plotly_chart(fig_mas, use_container_width=True)

                with col_mv2:
                    st.markdown("**🧊 Menos Vendidas (Bajo Movimiento)**")
                    df_top_menos["Texto_Moneda"] = df_top_menos[f"Venta {anio_ref_sel}"].apply(lambda x: f"${x:,.0f}")
                    fig_menos = px.bar(df_top_menos.sort_values(by=f"Venta {anio_ref_sel}", ascending=True), x=f"Venta {anio_ref_sel}", y=col_referencia, orientation="h", text="Texto_Moneda", color=f"Venta {anio_ref_sel}", color_continuous_scale="Blues")
                    fig_menos.update_traces(texttemplate="%{text}", textposition="auto", hovertemplate="<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>")
                    fig_menos.update_layout(showlegend=False, xaxis_title=f"Venta Total ($ {anio_ref_sel})", yaxis_title="Referencia / Producto", height=320)
                    st.plotly_chart(fig_menos, use_container_width=True)

                st.markdown("---")
                st.markdown("### 📈 Dinámica de Crecimiento y Decrecimiento YoY")
                col_g_inf1, col_g_inf2 = st.columns(2)
                df_top_crece = tabla_ref_comp.sort_values(by="Variación ($)", ascending=False).head(top_n)
                df_top_decrece = tabla_ref_comp.sort_values(by="Variación ($)", ascending=True).head(top_n)

                with col_g_inf1:
                    st.markdown(f"**📈 Top {top_n} Referencias con Mayor Crecimiento ($)**")
                    df_top_crece["Texto_Var"] = df_top_crece["Variación ($)"].apply(lambda x: f"${x:,.0f}")
                    fig_crece = px.bar(df_top_crece.sort_values(by="Variación ($)", ascending=True), x="Variación ($)", y=col_referencia, orientation="h", text="Texto_Var", color="Variación ($)", color_continuous_scale="Greens")
                    fig_crece.update_traces(texttemplate="%{text}", textposition="auto", hovertemplate="<b>%{y}</b><br>Variación: $%{x:,.0f}<extra></extra>")
                    fig_crece.update_layout(showlegend=False, xaxis_title="Crecimiento en Dinero ($)", yaxis_title="Referencia / Producto", height=320)
                    st.plotly_chart(fig_crece, use_container_width=True)

                with col_g_inf2:
                    st.markdown(f"**📉 Top {top_n} Referencias con Mayor Decrecimiento ($)**")
                    df_top_decrece["Texto_Var"] = df_top_decrece["Variación ($)"].apply(lambda x: f"${x:,.0f}")
                    fig_decrece = px.bar(df_top_decrece.sort_values(by="Variación ($)", ascending=True), x="Variación ($)", y=col_referencia, orientation="h", text="Texto_Var", color="Variación ($)", color_continuous_scale="Reds_r")
                    fig_decrece.update_traces(texttemplate="%{text}", textposition="auto", hovertemplate="<b>%{y}</b><br>Variación: $%{x:,.0f}<extra></extra>")
                    fig_decrece.update_layout(showlegend=False, xaxis_title="Decrecimiento en Dinero ($)", yaxis_title="Referencia / Producto", height=320)
                    st.plotly_chart(fig_decrece, use_container_width=True)

                st.markdown("---")
                st.subheader("📋 Tabla Comparativa Completa de Referencias")
                col_b_ref, col_d_ref = st.columns([3, 1])
                with col_b_ref:
                    busq_ref = st.text_input("🔍 Buscar referencia:", "", key="busq_referencia_txt")

                tabla_ref_final = tabla_ref_comp.sort_values(by=f"Venta {anio_ref_sel}", ascending=False)
                if busq_ref:
                    tabla_ref_final = tabla_ref_final[tabla_ref_final[col_referencia].astype(str).str.contains(busq_ref, case=False, na=False)]

                with col_d_ref:
                    st.write("")
                    output_ref = io.BytesIO()
                    with pd.ExcelWriter(output_ref, engine="openpyxl") as writer_ref:
                        tabla_ref_final.to_excel(writer_ref, index=False, sheet_name="Referencias")
                    excel_data_ref = output_ref.getvalue()

                    st.download_button(
                        label="📥 Descargar Excel",
                        data=excel_data_ref,
                        file_name=f"comparativo_referencias_{anio_ref_sel}_vs_{anio_ref_ant}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="dl_ref_excel",
                    )

                format_dict_ref = {
                    f"Venta {anio_ref_sel}": "${:,.0f}",
                    f"Venta {anio_ref_ant}": "${:,.0f}",
                    "Variación ($)": "${:,.0f}",
                    "Variación (%)": "{:,.0f}%",
                }
                st.dataframe(tabla_ref_final.style.format(format_dict_ref).map(color_variacion, subset=["Variación ($)", "Variación (%)"]), use_container_width=True)

            else:
                st.info("No hay datos de referencias.")
        else:
            st.warning("⚠️ Selecciona el año y meses para el análisis de referencias.")

    with tab3:
        st.subheader("🎯 Cumplimiento de Presupuesto y Zonas (PPTO)")
        st.markdown("Evaluación ordenada por zona con cumplimiento de venta, impactos y pedidos YoY independientes por mes.")

        if not df_ppto.empty:
            col_ppto_f1, col_ppto_f2 = st.columns([1, 3])
            with col_ppto_f1:
                anios_ppto_disp = sorted([int(x) for x in df_f[col_anio].dropna().unique() if x > 0])
                anio_ppto_sel = st.selectbox(
                    "Año Presupuesto:",
                    anios_ppto_disp,
                    index=len(anios_ppto_disp) - 1 if anios_ppto_disp else 0,
                    key="anio_ppto_sel",
                )
            with col_ppto_f2:
                meses_ppto_disp = sorted(list(df_f[col_mes].dropna().unique()), key=obtener_peso_mes)
                meses_ppto_sel = st.multiselect(
                    "Meses a evaluar en PPTO:",
                    options=meses_ppto_disp,
                    default=list(meses_ppto_disp),
                    key="meses_ppto_multi",
                )

            st.markdown("---")

            if anio_ppto_sel and meses_ppto_sel:
                anio_p = int(anio_ppto_sel)
                anio_ant_p = anio_p - 1

                col_pdv = next(
                    (
                        c for c in df.columns
                        if any(k in str(c).strip().lower() for k in ["dirección", "direccion", "pdv", "punto de venta", "punto venta", "sucursal", "cod pdv", "código pdv"])
                    ),
                    None,
                )

                cols_ppto = df_ppto.columns.tolist()
                p_gerente_ppto = next((c for c in cols_ppto if "gerente" in str(c).lower() or "supervisor" in str(c).lower()), cols_ppto[1])
                p_zona = next((c for c in cols_ppto if "zona" in str(c).lower()), cols_ppto[2])
                p_ppto = next((c for c in cols_ppto if "presupuesto" in str(c).lower() or "ppto" in str(c).lower()), cols_ppto[3])
                p_maestra = next((c for c in cols_ppto if "maestra" in str(c).lower()), cols_ppto[4] if len(cols_ppto) > 4 else cols_ppto[3])
                p_un = next((c for c in cols_ppto if "un" in str(c).lower() or "regional" in str(c).lower()), None)

                df_ppto_filtrado = df_ppto.copy()
                df_ppto_filtrado[p_zona] = df_ppto_filtrado[p_zona].astype(str).str.strip()
                df_ppto_filtrado[p_gerente_ppto] = df_ppto_filtrado[p_gerente_ppto].astype(str).str.strip()
                if p_un and p_un in df_ppto_filtrado.columns:
                    df_ppto_filtrado[p_un] = df_ppto_filtrado[p_un].astype(str).str.strip()

                df_ppto_filtrado[p_ppto] = pd.to_numeric(df_ppto_filtrado[p_ppto], errors="coerce").fillna(0)
                df_ppto_filtrado[p_maestra] = pd.to_numeric(df_ppto_filtrado[p_maestra], errors="coerce").fillna(0)

                if sel_reg != "Todos" and p_un and p_un in df_ppto_filtrado.columns:
                    df_ppto_filtrado = df_ppto_filtrado[df_ppto_filtrado[p_un] == str(sel_reg).strip()]

                if sel_gerente != "Todos":
                    df_ppto_filtrado = df_ppto_filtrado[df_ppto_filtrado[p_gerente_ppto] == str(sel_gerente).strip()]

                if sel_zona != "Todos":
                    df_ppto_filtrado = df_ppto_filtrado[df_ppto_filtrado[p_zona] == str(sel_zona).strip()]

                df_v_act = df[(df[col_anio] == anio_p) & (df[col_mes].isin(meses_ppto_sel))].copy()
                df_v_ant = df[(df[col_anio] == anio_ant_p) & (df[col_mes].isin(meses_ppto_sel))].copy()

                df_v_act[col_zona] = df_v_act[col_zona].astype(str).str.strip()
                df_v_ant[col_zona] = df_v_ant[col_zona].astype(str).str.strip()

                if sel_reg != "Todos":
                    df_v_act = df_v_act[df_v_act[col_regional].astype(str).str.strip() == str(sel_reg).strip()]
                    df_v_ant = df_v_ant[df_v_ant[col_regional].astype(str).str.strip() == str(sel_reg).strip()]

                if sel_canal != "Todos":
                    df_v_act = df_v_act[df_v_act[col_canal].astype(str).str.strip() == str(sel_canal).strip()]
                    df_v_ant = df_v_ant[df_v_ant[col_canal].astype(str).str.strip() == str(sel_canal).strip()]

                if sel_marca != "Todos":
                    df_v_act = df_v_act[df_v_act["Marca Estrategica"].astype(str).str.strip() == str(sel_marca).strip()]
                    df_v_ant = df_v_ant[df_v_ant["Marca Estrategica"].astype(str).str.strip() == str(sel_marca).strip()]

                zonas_validas = set(df_ppto_filtrado[p_zona].unique())
                if sel_gerente != "Todos" or sel_zona != "Todos":
                    df_v_act = df_v_act[df_v_act[col_zona].isin(zonas_validas)]
                    df_v_ant = df_v_ant[df_v_ant[col_zona].isin(zonas_validas)]

                df_act_imp = df_v_act[df_v_act[col_valor] > 1].copy()
                if col_pdv:
                    df_act_imp["_pdv_clave"] = (
                        df_act_imp[col_cliente].astype(str).str.strip()
                        + " || "
                        + df_act_imp[col_pdv].astype(str).str.strip()
                    )
                else:
                    df_act_imp["_pdv_clave"] = df_act_imp[col_cliente].astype(str).str.strip()

                df_ventas_zona = df_v_act.groupby(col_zona, as_index=False)[col_valor].sum().rename(columns={col_valor: "Venta"})
                df_cli_gt1 = df_act_imp.groupby(col_zona, as_index=False)[col_cliente].nunique().rename(columns={col_cliente: "Impactos"})
                df_imp_pdv = df_act_imp.groupby(col_zona, as_index=False)["_pdv_clave"].nunique().rename(columns={"_pdv_clave": "Impactos PDV/Dir"})
                df_pedidos_act = df_v_act.groupby(col_zona).size().reset_index(name="Pedidos")
                df_pedidos_ant = df_v_ant.groupby(col_zona).size().reset_index(name="Pedidos Ant")

                tabla_cumplimiento = pd.merge(df_ppto_filtrado, df_ventas_zona, left_on=p_zona, right_on=col_zona, how="left")
                if col_zona != p_zona and col_zona in tabla_cumplimiento.columns:
                    tabla_cumplimiento.drop(columns=[col_zona], inplace=True)

                tabla_cumplimiento = pd.merge(tabla_cumplimiento, df_cli_gt1, on=p_zona, how="left")
                tabla_cumplimiento = pd.merge(tabla_cumplimiento, df_imp_pdv, on=p_zona, how="left")
                tabla_cumplimiento = pd.merge(tabla_cumplimiento, df_pedidos_act, on=p_zona, how="left")
                tabla_cumplimiento = pd.merge(tabla_cumplimiento, df_pedidos_ant, on=p_zona, how="left")

                for col_num in ["Venta", "Impactos", "Impactos PDV/Dir", "Pedidos", "Pedidos Ant"]:
                    if col_num not in tabla_cumplimiento.columns:
                        tabla_cumplimiento[col_num] = 0
                    tabla_cumplimiento[col_num] = pd.to_numeric(tabla_cumplimiento[col_num], errors="coerce").fillna(0)

                tabla_cumplimiento["% Cumplimiento Venta"] = (tabla_cumplimiento["Venta"] / tabla_cumplimiento[p_ppto].replace(0, 1)) * 100
                tabla_cumplimiento["% Cumplimiento Impactos"] = (tabla_cumplimiento["Impactos"] / tabla_cumplimiento[p_maestra].replace(0, 1)) * 100
                tabla_cumplimiento["Variación Pedidos"] = tabla_cumplimiento["Pedidos"] - tabla_cumplimiento["Pedidos Ant"]
                tabla_cumplimiento["Var. Pedidos (%)"] = ((tabla_cumplimiento["Pedidos"] / tabla_cumplimiento["Pedidos Ant"].replace(0, 1)) - 1) * 100

                partes_titulo = []
                if sel_reg != "Todos":
                    partes_titulo.append(f"Regional: {sel_reg}")
                if sel_gerente != "Todos":
                    partes_titulo.append(f"Supervisor: {sel_gerente}")
                if sel_zona != "Todos":
                    partes_titulo.append(f"Zona: {sel_zona}")
                if sel_canal != "Todos":
                    partes_titulo.append(f"Canal: {sel_canal}")
                if sel_marca != "Todos":
                    partes_titulo.append(f"Marca: {sel_marca}")
                etiqueta_filtro = " | ".join(partes_titulo) if partes_titulo else "General (Todos los filtros)"

                total_ppto = tabla_cumplimiento[p_ppto].sum()
                total_venta_real = tabla_cumplimiento["Venta"].sum()
                total_maestra = tabla_cumplimiento[p_maestra].sum()
                total_impactos_nit = tabla_cumplimiento["Impactos"].sum()
                total_impactos_pdv = tabla_cumplimiento["Impactos PDV/Dir"].sum()
                total_ped_act = tabla_cumplimiento["Pedidos"].sum()
                total_ped_ant = tabla_cumplimiento["Pedidos Ant"].sum()
                var_ped_num = total_ped_act - total_ped_ant
                var_ped_pct = ((total_ped_act / total_ped_ant) - 1) * 100 if total_ped_ant > 0 else 0

                cump_venta_pct = (total_venta_real / total_ppto) * 100 if total_ppto > 0 else 0
                cump_imp_pct = (total_impactos_nit / total_maestra) * 100 if total_maestra > 0 else 0

                st.markdown(f"### 📌 Resumen Ejecutivo — {etiqueta_filtro}")
                if not col_pdv:
                    st.caption("Nota: No se detectó columna de Dirección/PDV en la base; Impactos PDV/Dir refleja el conteo único por cliente.")

                st.markdown(
                    f"""
                    <div style="display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:14px; margin-bottom:12px;">
                        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:5px solid #0066cc; border-radius:10px; padding:14px;">
                            <div style="font-size:0.82rem; color:#475569; font-weight:600;">💰 PRESUPUESTO VS VENTAS</div>
                            <div style="font-size:1.45rem; font-weight:700; color:#0f172a; margin:4px 0;">{cump_venta_pct:,.1f}% <span style="font-size:0.85rem; font-weight:500; color:#0066cc;">Cumpl.</span></div>
                            <div style="font-size:0.84rem; color:#334155;"><b>Venta:</b> ${total_venta_real:,.0f}</div>
                            <div style="font-size:0.84rem; color:#64748b;"><b>PPTO:</b> ${total_ppto:,.0f}</div>
                        </div>
                        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:5px solid #2e7d32; border-radius:10px; padding:14px;">
                            <div style="font-size:0.82rem; color:#475569; font-weight:600;">🎯 MAESTRA VS IMPACTOS (NIT)</div>
                            <div style="font-size:1.45rem; font-weight:700; color:#0f172a; margin:4px 0;">{cump_imp_pct:,.1f}% <span style="font-size:0.85rem; font-weight:500; color:#2e7d32;">Cumpl.</span></div>
                            <div style="font-size:0.84rem; color:#334155;"><b>Impactos:</b> {total_impactos_nit:,.0f}</div>
                            <div style="font-size:0.84rem; color:#64748b;"><b>Maestra:</b> {total_maestra:,.0f}</div>
                        </div>
                        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:5px solid #7c3aed; border-radius:10px; padding:14px;">
                            <div style="font-size:0.82rem; color:#475569; font-weight:600;">📍 IMPACTOS POR PDV / DIRECCIÓN</div>
                            <div style="font-size:1.45rem; font-weight:700; color:#0f172a; margin:4px 0;">{total_impactos_pdv:,.0f} <span style="font-size:0.85rem; font-weight:500; color:#7c3aed;">PDV / Dir.</span></div>
                            <div style="font-size:0.84rem; color:#334155;"><b>Por Cliente/NIT:</b> {total_impactos_nit:,.0f}</div>
                            <div style="font-size:0.84rem; color:#64748b;"><b>Diferencia Multi-PDV:</b> +{max(0, total_impactos_pdv - total_impactos_nit):,.0f}</div>
                        </div>
                        <div style="background:#f8fafc; border:1px solid #e2e8f0; border-left:5px solid {'#2e7d32' if var_ped_num >= 0 else '#c62828'}; border-radius:10px; padding:14px;">
                            <div style="font-size:0.82rem; color:#475569; font-weight:600;">📦 PEDIDOS VS AÑO ANT. ({anio_p} vs {anio_ant_p})</div>
                            <div style="font-size:1.45rem; font-weight:700; color:#0f172a; margin:4px 0;">{total_ped_act:,.0f} <span style="font-size:0.85rem; font-weight:600; color:{'#2e7d32' if var_ped_num >= 0 else '#c62828'};">({var_ped_num:+,.0f} / {var_ped_pct:+.1f}%)</span></div>
                            <div style="font-size:0.84rem; color:#334155;"><b>Año {anio_p}:</b> {total_ped_act:,.0f} pedidos</div>
                            <div style="font-size:0.84rem; color:#64748b;"><b>Año {anio_ant_p}:</b> {total_ped_ant:,.0f} pedidos</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if sel_reg != "Todos" and sel_zona == "Todos" and not tabla_cumplimiento.empty:
                    resumen_zonas = (
                        tabla_cumplimiento.groupby(p_zona, as_index=False)[[p_ppto, "Venta", p_maestra, "Impactos", "Impactos PDV/Dir", "Pedidos", "Pedidos Ant"]]
                        .sum()
                    )
                    resumen_zonas["% Cumplimiento Venta"] = (resumen_zonas["Venta"] / resumen_zonas[p_ppto].replace(0, 1)) * 100
                    resumen_zonas["% Cumplimiento Impactos"] = (resumen_zonas["Impactos"] / resumen_zonas[p_maestra].replace(0, 1)) * 100
                    resumen_zonas["Variación Pedidos"] = resumen_zonas["Pedidos"] - resumen_zonas["Pedidos Ant"]
                    resumen_zonas["Var. Pedidos (%)"] = ((resumen_zonas["Pedidos"] / resumen_zonas["Pedidos Ant"].replace(0, 1)) - 1) * 100

                    st.markdown(f"**Resumen por Zona ({sel_reg}):**")
                    st.dataframe(
                        resumen_zonas.style.format({
                            p_ppto: "${:,.0f}",
                            "Venta": "${:,.0f}",
                            "% Cumplimiento Venta": "{:,.1f}%",
                            p_maestra: "{:,.0f}",
                            "Impactos": "{:,.0f}",
                            "% Cumplimiento Impactos": "{:,.1f}%",
                            "Impactos PDV/Dir": "{:,.0f}",
                            "Pedidos": "{:,.0f}",
                            "Pedidos Ant": "{:,.0f}",
                            "Variación Pedidos": "{:+,.0f}",
                            "Var. Pedidos (%)": "{:+.1f}%",
                        }),
                        use_container_width=True,
                    )

                st.markdown("---")

                format_dict_ppto = {
                    p_ppto: "${:,.0f}",
                    "Venta": "${:,.0f}",
                    "% Cumplimiento Venta": "{:,.1f}%",
                    p_maestra: "{:,.0f}",
                    "Impactos": "{:,.0f}",
                    "% Cumplimiento Impactos": "{:,.1f}%",
                    "Impactos PDV/Dir": "{:,.0f}",
                    "Pedidos": "{:,.0f}",
                    "Pedidos Ant": "{:,.0f}",
                    "Variación Pedidos": "{:+,.0f}",
                    "Var. Pedidos (%)": "{:+.1f}%",
                }
                st.dataframe(tabla_cumplimiento.style.format(format_dict_ppto, na_rep="0"), use_container_width=True)
            else:
                st.warning("Selecciona año y meses para el presupuesto.")
        else:
            st.info("No se encontró la hoja de presupuesto (PPTO).")

    with tab4:
        st.subheader("🍾 Análisis por Marcas Estratégicas & KV")
        col_m_f1, col_m_f2 = st.columns([1, 3])
        with col_m_f1:
            anios_m_disp = sorted([int(x) for x in df_f[col_anio].dropna().unique() if x > 0])
            anio_m_sel = st.selectbox("Año a analizar:", anios_m_disp, index=len(anios_m_disp) - 1 if anios_m_disp else 0, key="anio_tab4")
        with col_m_f2:
            meses_m_disp = sorted(list(df_f[col_mes].dropna().unique()), key=obtener_peso_mes)
            meses_m_sel = st.multiselect("Meses activos:", options=meses_m_disp, default=list(meses_m_disp), key="meses_tab4")

        st.markdown("---")

        if anio_m_sel and meses_m_sel:
            anio_m = int(anio_m_sel)
            anio_m_ant = anio_m - 1

            df_m_act = df_f[(df_f[col_anio] == anio_m) & (df_f[col_mes].isin(meses_m_sel))]
            df_m_ant = df_f[(df_f[col_anio] == anio_m_ant) & (df_f[col_mes].isin(meses_m_sel))]

            m_act = df_m_act.groupby("Marca Estrategica", as_index=False)[col_valor].sum().rename(columns={col_valor: f"Venta {anio_m}"})
            m_ant = df_m_ant.groupby("Marca Estrategica", as_index=False)[col_valor].sum().rename(columns={col_valor: f"Venta {anio_m_ant}"})

            tabla_marcas = pd.merge(m_act, m_ant, on="Marca Estrategica", how="outer").fillna(0)
            total_m_act = tabla_marcas[f"Venta {anio_m}"].sum()
            tabla_marcas["Participación (%)"] = (tabla_marcas[f"Venta {anio_m}"] / total_m_act * 100) if total_m_act > 0 else 0
            tabla_marcas["Variación ($)"] = tabla_marcas[f"Venta {anio_m}"] - tabla_marcas[f"Venta {anio_m_ant}"]
            tabla_marcas["Variación (%)"] = ((tabla_marcas[f"Venta {anio_m}"] / tabla_marcas[f"Venta {anio_m_ant}"].replace(0, 1)) - 1) * 100
            tabla_marcas = tabla_marcas.sort_values(by=f"Venta {anio_m}", ascending=False)

            st.subheader(f"📊 Ventas y Participación por Marca ({anio_m} vs {anio_m_ant})")
            fig_marcas = px.bar(
                tabla_marcas.sort_values(by=f"Venta {anio_m}", ascending=True),
                x=f"Venta {anio_m}",
                y="Marca Estrategica",
                orientation="h",
                text=tabla_marcas.sort_values(by=f"Venta {anio_m}", ascending=True)[f"Venta {anio_m}"].apply(lambda x: f"${x:,.0f}"),
                color=f"Venta {anio_m}",
                color_continuous_scale="Purples",
            )
            fig_marcas.update_traces(texttemplate="%{text}", textposition="auto", hovertemplate="<b>%{y}</b><br>Venta: $%{x:,.0f}<extra></extra>")
            fig_marcas.update_layout(showlegend=False, xaxis_title=f"Venta Total ($ {anio_m})", yaxis_title="Marca Estratégica", height=360)
            st.plotly_chart(fig_marcas, use_container_width=True)

            st.dataframe(
                tabla_marcas.style.format({
                    f"Venta {anio_m}": "${:,.0f}",
                    f"Venta {anio_m_ant}": "${:,.0f}",
                    "Participación (%)": "{:,.1f}%",
                    "Variación ($)": "${:+,.0f}",
                    "Variación (%)": "{:+.1f}%",
                }).map(color_variacion, subset=["Variación ($)", "Variación (%)"]),
                use_container_width=True,
            )

            st.markdown("---")
            st.subheader("🔎 Referencias asignadas a 'Otros'")
            df_otros = df_m_act[df_m_act["Marca Estrategica"] == "Otros"].copy()

            if not df_otros.empty:
                cols_group_otros = [col_referencia]
                if col_nombre_producto and col_nombre_producto != col_referencia:
                    cols_group_otros.append(col_nombre_producto)
                cols_group_otros.extend(["Marca Estrategica", "Estado Cruce Marca"])

                resumen_otros = (
                    df_otros.groupby(cols_group_otros, as_index=False)
                    .agg(
                        Registros=(col_valor, "count"),
                        Venta_Total=(col_valor, "sum"),
                        Clientes_Unicos=(col_cliente, "nunique"),
                    )
                    .sort_values(by="Venta_Total", ascending=False)
                )
                st.info(f"Se muestran **{len(resumen_otros)}** referencias agrupadas en **Otros** (total **${resumen_otros['Venta_Total'].sum():,.0f}**).")

                out_otros = io.BytesIO()
                with pd.ExcelWriter(out_otros, engine="openpyxl") as writer_otros:
                    resumen_otros.to_excel(writer_otros, index=False, sheet_name="Categoria_Otros")
                st.download_button(
                    label="📥 Descargar referencias en Otros (Excel)",
                    data=out_otros.getvalue(),
                    file_name=f"referencias_otros_{anio_m}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_otros_excel",
                )

                st.dataframe(
                    resumen_otros.style.format({
                        "Registros": "{:,.0f}",
                        "Venta_Total": "${:,.0f}",
                        "Clientes_Unicos": "{:,.0f}",
                    }),
                    use_container_width=True,
                )
            else:
                st.success("No hay referencias en 'Otros' para los filtros seleccionados.")

    with tab5:
        st.subheader("🔍 Detalle de Clientes y Referencias")
        st.markdown("Consulta rápida de transacciones y movimientos filtrados.")
        st.dataframe(df_f, use_container_width=True, height=450)

except Exception as e:
    st.error(f"Error al cargar o procesar los datos: {e}")
