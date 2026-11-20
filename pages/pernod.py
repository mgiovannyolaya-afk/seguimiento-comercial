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


def _limpiar_clave(val):
    if pd.isna(val):
        return ""
    txt = str(val).strip().lower()
    txt = re.sub(r"\.0$", "", txt)
    return re.sub(r"\s+", " ", txt)


def _normalizar_texto(val):
    if pd.isna(val):
        return ""
    txt = str(val).lower()
    txt = (
        txt.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    txt = re.sub(r"[^a-z0-9\s]+", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def _es_desconocido_o_vacio(val):
    if pd.isna(val):
        return True
    txt = _normalizar_texto(val)
    return txt in {
        "",
        "nan",
        "none",
        "null",
        "desconocido",
        "sin marca",
        "sin identificar",
        "kv sin identificar",
        "otros",
    }


def _limpiar_marca_visible(val):
    if pd.isna(val):
        return "Otros"
    txt = re.sub(r"\s+", " ", str(val).strip())
    if _es_desconocido_o_vacio(txt):
        return "Otros"
    return txt


def _clasificar_por_nombre(texto_norm):
    if not texto_norm:
        return None

    reglas = [
        ("Ojo de Tigre", ["ojo de tigre", "tigre"]),
        ("The Glenlivet", ["glenlivet", "glenliv", "founders", "caribean", "caribbean"]),
        ("Chivas Regal", ["chivas", "12yo", "13yo", "18yo", "sherry", "chivas crist"]),
        ("Something Special", ["something", "some", "specia"]),
        ("Ballantine's", ["ballantine", "ballant", "ballan", "finest"]),
        ("Olmeca", ["olmeca", "olme", "altos", "reposado", "blanco"]),
        ("Avión", ["avion", "reserva", "reser cris"]),
        ("Passport", ["passport", "passpor", "selection"]),
        ("Absolut", ["absolut", "absolu", "vodka"]),
        ("Dubonnet", ["dubonnet", "dubonne", "aperitivo"]),
        ("Beefeater", ["beefeater", "beef"]),
        ("Jameson", ["jameson", "jame"]),
        ("Perrier-Jouët", ["perrier", "jouet"]),
        ("Mumm", ["mumm"]),
        ("Ricard", ["ricard"]),
    ]

    for marca_oficial, pistas in reglas:
        if any(p in texto_norm for p in pistas):
            return marca_oficial
    return None


def _detectar_columna(columnas, palabras_clave, fallback_idx=0):
    for pk in palabras_clave:
        pk_l = pk.lower()
        for col in columnas:
            if pk_l == str(col).lower():
                return col
    for pk in palabras_clave:
        pk_l = pk.lower()
        for col in columnas:
            if pk_l in str(col).lower():
                return col
    return columnas[fallback_idx] if fallback_idx < len(columnas) else columnas[0]


def _motor_xlsb():
    try:
        import python_calamine  # noqa: F401
        return "calamine"
    except Exception:
        return "pyxlsb"


@st.cache_data(show_spinner="Cargando hojas de BV PERNOD TODA.xlsb...")
def listar_hojas_xlsb():
    xls_path = "BV PERNOD TODA.xlsb"
    if not os.path.exists(xls_path):
        raise FileNotFoundError(f"No se encontró '{xls_path}'.")
    motor = _motor_xlsb()
    with pd.ExcelFile(xls_path, engine=motor) as xl:
        hojas = xl.sheet_names
    hoja_ppto = next((h for h in hojas if "ppto" in str(h).lower()), None)
    hoja_marcas = next((h for h in hojas if "marca" in str(h).lower()), None)
    excluidas = {h for h in [hoja_ppto, hoja_marcas] if h is not None}
    hojas_ventas = [h for h in hojas if h not in excluidas] or [hojas[0]]
    return hojas_ventas, hoja_ppto, hoja_marcas, motor


@st.cache_data(show_spinner="Procesando datos y clasificando marcas...")
def cargar_datos_rapido(hojas_sel, hoja_ppto, hoja_marcas, motor):
    xls_path = "BV PERNOD TODA.xlsb"
    hojas_a_leer = list(hojas_sel) if hojas_sel else []
    if not hojas_a_leer:
        return pd.DataFrame(), pd.DataFrame(), {}

    with pd.ExcelFile(xls_path, engine=motor) as xl:
        frames = []
        for h in hojas_a_leer:
            df_h = pd.read_excel(xl, sheet_name=h, engine=motor)
            if not df_h.empty:
                frames.append(df_h)
        df_ventas = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        df_ppto = pd.read_excel(xl, sheet_name=hoja_ppto, engine=motor) if hoja_ppto else pd.DataFrame()
        df_marcas = pd.read_excel(xl, sheet_name=hoja_marcas, engine=motor) if hoja_marcas else pd.DataFrame()

    if df_ventas.empty:
        return df_ventas, df_ppto, {}

    cols = df_ventas.columns.tolist()
    col_regional = _detectar_columna(cols, ["Código UN", "Cod UN", "Regional", "Región"], 1)
    col_canal = _detectar_columna(cols, ["Tipo de Cliente", "Tipo cliente", "Canal", "Canal de Venta"], 0)
    col_gerente = _detectar_columna(cols, ["Gerente Zona", "Gerente Unidad", "Supervisor", "Gerente"], 2)
    col_zona = _detectar_columna(cols, ["Código Zona", "Codigo Zona", "Cod Zona", "Id Zona"], 3)
    col_cliente = _detectar_columna(cols, ["Nombre Cliente", "Cliente", "Documento Cliente"], 4)
    col_referencia = _detectar_columna(
        cols,
        ["Referencia", "Artículo", "Articulo", "SKU", "Producto", "Item", "Descripción Item", "Descripcion"],
        5,
    )
    col_nombre_producto = next(
        (
            c for c in cols
            if any(
                k in _normalizar_texto(c)
                for k in ["producto", "nombre de producto", "nombre producto", "nombre del producto", "nombre item", "descripcion"]
            )
            and c != col_referencia
        ),
        None,
    )
    col_unidades = next(
        (
            c for c in cols
            if any(
                k in _normalizar_texto(c)
                for k in ["unidades", "unidad", "cantidad", "cant", "und", "cajas"]
            )
        ),
        None,
    )
    col_anio = _detectar_columna(cols, ["Año", "Anio", "Year"], 6)
    col_mes = _detectar_columna(cols, ["Mes", "Month"], 7)
    col_valor = _detectar_columna(cols, ["Ventas Det", "Venta", "Valor", "Total"], 8)

    df_ventas[col_valor] = pd.to_numeric(df_ventas[col_valor], errors="coerce").fillna(0)
    df_ventas[col_anio] = pd.to_numeric(df_ventas[col_anio], errors="coerce").fillna(0).astype(int)
    if col_unidades:
        df_ventas[col_unidades] = pd.to_numeric(df_ventas[col_unidades], errors="coerce").fillna(0)

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
    df_ventas[col_mes] = (
        df_ventas[col_mes]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(lambda x: mapa_meses.get(x, x.capitalize()))
    )

    mapa_ean_marca = {}
    mapa_prod_marca = {}

    if not df_marcas.empty:
        cm = df_marcas.columns.tolist()
        m_marca = next((c for c in cm if "marca" in _normalizar_texto(c)), cm[0])
        m_ean = next((c for c in cm if any(k in _normalizar_texto(c) for k in ["ean", "codigo", "ref"])), None)
        m_prod = next((c for c in cm if any(k in _normalizar_texto(c) for k in ["producto", "nombre", "desc", "item"])), None)

        for _, row in df_marcas.iterrows():
            marca_raw = row[m_marca] if m_marca in row else None
            prod_raw = row[m_prod] if (m_prod and m_prod in row) else ""
            ean_raw = row[m_ean] if (m_ean and m_ean in row) else ""

            if not _es_desconocido_o_vacio(marca_raw):
                marca_resuelta = _limpiar_marca_visible(marca_raw)
            else:
                marca_resuelta = _clasificar_por_nombre(_normalizar_texto(prod_raw))

            if marca_resuelta and marca_resuelta != "Otros":
                ke = _limpiar_clave(ean_raw)
                kp = _limpiar_clave(prod_raw)
                if ke and ke not in mapa_ean_marca:
                    mapa_ean_marca[ke] = marca_resuelta
                if kp and kp not in mapa_prod_marca:
                    mapa_prod_marca[kp] = marca_resuelta

    serie_ref = df_ventas[col_referencia]
    serie_prod = df_ventas[col_nombre_producto] if col_nombre_producto else pd.Series([""] * len(df_ventas))
    pares_unicos = pd.DataFrame({"r": serie_ref, "p": serie_prod}).drop_duplicates()

    mapa_par = {}
    for r_val, p_val in zip(pares_unicos["r"], pares_unicos["p"]):
        kr = _limpiar_clave(r_val)
        kp = _limpiar_clave(p_val)

        if kr and kr in mapa_ean_marca:
            mapa_par[(r_val, p_val)] = mapa_ean_marca[kr]
            continue
        if kp and kp in mapa_ean_marca:
            mapa_par[(r_val, p_val)] = mapa_ean_marca[kp]
            continue
        if kp and kp in mapa_prod_marca:
            mapa_par[(r_val, p_val)] = mapa_prod_marca[kp]
            continue
        if kr and kr in mapa_prod_marca:
            mapa_par[(r_val, p_val)] = mapa_prod_marca[kr]
            continue

        texto_combinado = _normalizar_texto(f"{p_val} {r_val}")
        detectada = _clasificar_por_nombre(texto_combinado)
        mapa_par[(r_val, p_val)] = detectada if detectada else "Otros"

    df_ventas["Marca Estrategica"] = [
        _limpiar_marca_visible(mapa_par[(r, p)]) for r, p in zip(serie_ref, serie_prod)
    ]

    for c_cat in [col_regional, col_canal, col_gerente, col_zona, col_mes, "Marca Estrategica"]:
        if c_cat in df_ventas.columns:
            df_ventas[c_cat] = df_ventas[c_cat].astype(str).str.strip().astype("category")

    meta = {
        "col_regional": col_regional,
        "col_canal": col_canal,
        "col_gerente": col_gerente,
        "col_zona": col_zona,
        "col_cliente": col_cliente,
        "col_referencia": col_referencia,
        "col_nombre_producto": col_nombre_producto,
        "col_unidades": col_unidades,
        "col_anio": col_anio,
        "col_mes": col_mes,
        "col_valor": col_valor,
    }
    return df_ventas, df_ppto, meta


try:
    hojas_ventas, hoja_ppto, hoja_marcas, motor = listar_hojas_xlsb()
    st.sidebar.header("📂 Hojas de Ventas")
    hojas_sel = st.sidebar.multiselect(
        "Hojas a cargar:",
        options=hojas_ventas,
        default=hojas_ventas[:1],
        help="Selecciona 1 hoja para carga instantánea o varias para consolidar.",
    )

    df, df_ppto, meta = cargar_datos_rapido(tuple(hojas_sel), hoja_ppto, hoja_marcas, motor)
    if df.empty or not meta:
        st.warning("Selecciona al menos una hoja de ventas para mostrar el tablero.")
        st.stop()

    col_regional = meta["col_regional"]
    col_canal = meta["col_canal"]
    col_gerente = meta["col_gerente"]
    col_zona = meta["col_zona"]
    col_cliente = meta["col_cliente"]
    col_referencia = meta["col_referencia"]
    col_nombre_producto = meta["col_nombre_producto"]
    col_unidades = meta["col_unidades"]
    col_anio = meta["col_anio"]
    col_mes = meta["col_mes"]
    col_valor = meta["col_valor"]

    st.sidebar.header("🎯 Filtros Globales")
    df_f = df.copy()

    def _filtro_cat(col_name, label):
        vals = sorted([
            _limpiar_marca_visible(x) if col_name == "Marca Estrategica" else str(x).strip()
            for x in df_f[col_name].dropna().unique().tolist()
            if str(x).strip() not in ("", "nan", "None")
        ])
        vals = sorted(set(vals))
        return st.sidebar.selectbox(label, ["Todos"] + vals, index=0)

    sel_reg = _filtro_cat(col_regional, "Código UN (Regional)")
    if sel_reg != "Todos":
        df_f = df_f[df_f[col_regional].astype(str) == sel_reg]

    sel_canal = _filtro_cat(col_canal, "Canal")
    if sel_canal != "Todos":
        df_f = df_f[df_f[col_canal].astype(str) == sel_canal]

    sel_gerente = _filtro_cat(col_gerente, "Supervisor")
    if sel_gerente != "Todos":
        df_f = df_f[df_f[col_gerente].astype(str) == sel_gerente]

    sel_zona = _filtro_cat(col_zona, "Código Zona")
    if sel_zona != "Todos":
        df_f = df_f[df_f[col_zona].astype(str) == sel_zona]

    sel_marca = _filtro_cat("Marca Estrategica", "Marca Estratégica")
    if sel_marca != "Todos":
        df_f = df_f[df_f["Marca Estrategica"].astype(str).map(_limpiar_marca_visible) == sel_marca]

    orden_meses_ref = [
        "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic",
        "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]

    def obtener_peso_mes(m):
        m_l = str(m).strip().lower()
        for idx, ref in enumerate(orden_meses_ref):
            if ref in m_l:
                return idx
        return 999

    def color_variacion(val):
        if isinstance(val, (int, float)):
            if val > 0:
                return "color: #2E7D32; font-weight: bold;"
            if val < 0:
                return "color: #C62828; font-weight: bold;"
        return ""

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard General & Clientes",
        "📦 Análisis de Referencias (YoY)",
        "🎯 Presupuesto & Zonas (PPTO)",
        "🍾 Análisis por Marcas & KV",
    ])

    anios_disp = sorted([int(x) for x in df_f[col_anio].dropna().unique() if x > 0])
    meses_disp = sorted(
        [m for m in df_f[col_mes].dropna().unique().tolist() if str(m).strip() not in ("", "nan", "None")],
        key=obtener_peso_mes,
    )

    with tab1:
        st.subheader("📅 Panel de Control Temporal")
        c1, c2 = st.columns([1, 3])
        with c1:
            anio_base = st.selectbox("Selecciona el Año Base:", anios_disp, index=len(anios_disp) - 1 if anios_disp else 0, key="a1")
        with c2:
            meses_sel = st.multiselect("Selecciona los meses activos:", meses_disp, default=meses_disp, key="m1")

        if anio_base and meses_sel:
            a_sel = int(anio_base)
            a_ant = a_sel - 1
            df_act = df_f[(df_f[col_anio] == a_sel) & (df_f[col_mes].astype(str).isin(meses_sel))]
            df_ant = df_f[(df_f[col_anio] == a_ant) & (df_f[col_mes].astype(str).isin(meses_sel))]

            tot_act = df_act[col_valor].sum()
            tot_ant = df_ant[col_valor].sum()
            crec = ((tot_act / tot_ant) - 1) * 100 if tot_ant > 0 else 0

            cli_act = df_act[df_act[col_valor] > 1][col_cliente].nunique()
            cli_ant = df_ant[df_ant[col_valor] > 1][col_cliente].nunique()
            tkt_act = tot_act / cli_act if cli_act > 0 else 0
            tkt_ant = tot_ant / cli_ant if cli_ant > 0 else 0
            var_tkt = ((tkt_act / tkt_ant) - 1) * 100 if tkt_ant > 0 else 0

            k1, k2, k3, k4 = st.columns(4)
            k1.metric(f"Ventas Total ({a_sel})", f"${tot_act:,.0f}")
            k2.metric(f"Ventas Total ({a_ant})", f"${tot_ant:,.0f}", f"{crec:,.0f}% YoY")
            k3.metric("Ticket Promedio / Cliente", f"${tkt_act:,.0f}", f"{var_tkt:+,.1f}% YoY")
            k4.metric("Meses Evaluados", f"{len(meses_sel)} mes(es)")

            # Gráfica comparativa mensual de año completo (Ene - Dic)
            st.markdown("---")
            st.subheader(f"📈 Comparativa Mensual Año Completo ({a_sel} vs {a_ant})")

            orden_12_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
            df_anual_act = df_f[df_f[col_anio] == a_sel].groupby(col_mes, observed=False, as_index=False)[col_valor].sum()
            df_anual_ant = df_f[df_f[col_anio] == a_ant].groupby(col_mes, observed=False, as_index=False)[col_valor].sum()

            map_act = dict(zip(df_anual_act[col_mes].astype(str), df_anual_act[col_valor]))
            map_ant = dict(zip(df_anual_ant[col_mes].astype(str), df_anual_ant[col_valor]))

            df_comp_anual = pd.DataFrame({
                "Mes": orden_12_meses,
                f"Venta {a_sel}": [float(map_act.get(m, 0.0)) for m in orden_12_meses],
                f"Venta {a_ant}": [float(map_ant.get(m, 0.0)) for m in orden_12_meses],
            })

            fig_comp = px.line(
                df_comp_anual,
                x="Mes",
                y=[f"Venta {a_sel}", f"Venta {a_ant}"],
                markers=True,
                title=f"Trayectoria Mensual Comparativa: {a_sel} vs {a_ant}",
            )
            fig_comp.update_layout(
                height=350,
                xaxis_title="Mes",
                yaxis_title="Ventas ($)",
                legend_title="Año",
                hovermode="x unified",
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            # Distribución por Canal / Regional y Top Clientes en el periodo activo
            st.markdown("---")
            g_col1, g_col2 = st.columns(2)
            with g_col1:
                st.subheader(f"🏢 Ventas por Canal ({a_sel})")
                df_canal = (
                    df_act.groupby(col_canal, observed=False, as_index=False)[col_valor]
                    .sum()
                    .sort_values(col_valor, ascending=True)
                )
                if not df_canal.empty:
                    fig_can = px.bar(
                        df_canal.tail(10),
                        x=col_valor,
                        y=col_canal,
                        orientation="h",
                        color=col_valor,
                        color_continuous_scale="Blues",
                    )
                    fig_can.update_layout(height=300, showlegend=False, xaxis_title="Ventas ($)", yaxis_title="")
                    st.plotly_chart(fig_can, use_container_width=True)

            with g_col2:
                st.subheader(f"🏆 Top 10 Clientes ({a_sel})")
                df_top_cli = (
                    df_act.groupby(col_cliente, observed=False, as_index=False)[col_valor]
                    .sum()
                    .sort_values(col_valor, ascending=False)
                    .head(10)
                    .sort_values(col_valor, ascending=True)
                )
                if not df_top_cli.empty:
                    fig_tcli = px.bar(
                        df_top_cli,
                        x=col_valor,
                        y=col_cliente,
                        orientation="h",
                        color=col_valor,
                        color_continuous_scale="Teal",
                    )
                    fig_tcli.update_layout(height=300, showlegend=False, xaxis_title="Ventas ($)", yaxis_title="")
                    st.plotly_chart(fig_tcli, use_container_width=True)

            st.markdown("---")
            st.subheader("📋 Detalle Avanzado por Cliente")
            busq_c = st.text_input("🔍 Buscar cliente:", "", key="bc1")
            v_act = df_act.groupby(col_cliente, observed=False)[col_valor].sum().reset_index().rename(columns={col_valor: f"Venta {a_sel}"})
            v_ant = df_ant.groupby(col_cliente, observed=False)[col_valor].sum().reset_index().rename(columns={col_valor: f"Venta {a_ant}"})
            p_act = df_act.groupby(col_cliente, observed=False).size().reset_index(name="Pedidos_Act")
            skus = df_act[df_act[col_valor] > 0].groupby(col_cliente, observed=False)[col_referencia].nunique().reset_index(name="Portafolio (SKUs)")

            t_cli = pd.merge(v_act, v_ant, on=col_cliente, how="outer").fillna(0)
            t_cli = pd.merge(t_cli, p_act, on=col_cliente, how="left").fillna(1)
            t_cli = pd.merge(t_cli, skus, on=col_cliente, how="left").fillna(0)
            t_cli["Variación ($)"] = t_cli[f"Venta {a_sel}"] - t_cli[f"Venta {a_ant}"]
            t_cli["Variación (%)"] = ((t_cli[f"Venta {a_sel}"] / t_cli[f"Venta {a_ant}"].replace(0, 1)) - 1) * 100
            t_cli[f"Ticket Prom. {a_sel}"] = t_cli[f"Venta {a_sel}"] / t_cli["Pedidos_Act"]
            t_cli = t_cli[[col_cliente, f"Venta {a_sel}", f"Venta {a_ant}", "Variación ($)", "Variación (%)", f"Ticket Prom. {a_sel}", "Portafolio (SKUs)"]].sort_values(by=f"Venta {a_sel}", ascending=False)
            if busq_c:
                t_cli = t_cli[t_cli[col_cliente].astype(str).str.contains(busq_c, case=False, na=False)]

            st.dataframe(
                t_cli.style.format({
                    f"Venta {a_sel}": "${:,.0f}",
                    f"Venta {a_ant}": "${:,.0f}",
                    "Variación ($)": "${:,.0f}",
                    "Variación (%)": "{:,.0f}%",
                    f"Ticket Prom. {a_sel}": "${:,.0f}",
                    "Portafolio (SKUs)": "{:,.0f}",
                }).map(color_variacion, subset=["Variación ($)", "Variación (%)"]),
                use_container_width=True,
                height=380,
            )

    with tab2:
        st.subheader("📦 Análisis Avanzado de Referencias (YoY)")
        r1, r2, r3 = st.columns([1, 2, 1])
        with r1:
            a_ref = st.selectbox("Año Actual:", anios_disp, index=len(anios_disp) - 1 if anios_disp else 0, key="a2")
        with r2:
            m_ref = st.multiselect("Meses a evaluar:", meses_disp, default=meses_disp, key="m2")
        with r3:
            top_n = st.selectbox("Cantidad en Top:", [5, 10, 15, 20], index=1, key="t2")

        if a_ref and m_ref:
            a_s = int(a_ref)
            a_p = a_s - 1
            df_ra = df_f[(df_f[col_anio] == a_s) & (df_f[col_mes].astype(str).isin(m_ref))]
            df_rp = df_f[(df_f[col_anio] == a_p) & (df_f[col_mes].astype(str).isin(m_ref))]

            ra = df_ra.groupby(col_referencia, observed=False)[col_valor].sum().reset_index().rename(columns={col_valor: f"Venta {a_s}"})
            rp = df_rp.groupby(col_referencia, observed=False)[col_valor].sum().reset_index().rename(columns={col_valor: f"Venta {a_p}"})
            t_ref = pd.merge(ra, rp, on=col_referencia, how="outer").fillna(0)
            t_ref["Variación ($)"] = t_ref[f"Venta {a_s}"] - t_ref[f"Venta {a_p}"]
            t_ref["Variación (%)"] = ((t_ref[f"Venta {a_s}"] / t_ref[f"Venta {a_p}"].replace(0, 1)) - 1) * 100
            t_ref = t_ref.sort_values(by=f"Venta {a_s}", ascending=False)

            busq_r = st.text_input("🔍 Buscar referencia:", "", key="br2")
            if busq_r:
                t_ref = t_ref[t_ref[col_referencia].astype(str).str.contains(busq_r, case=False, na=False)]

            top_df = t_ref.head(top_n)
            if not top_df.empty:
                fig_r = px.bar(
                    top_df.sort_values(by=f"Venta {a_s}", ascending=True),
                    x=f"Venta {a_s}",
                    y=col_referencia,
                    orientation="h",
                    color=f"Venta {a_s}",
                    color_continuous_scale="Greens",
                )
                fig_r.update_layout(height=320, showlegend=False)
                st.plotly_chart(fig_r, use_container_width=True)

            st.dataframe(
                t_ref.style.format({
                    f"Venta {a_s}": "${:,.0f}",
                    f"Venta {a_p}": "${:,.0f}",
                    "Variación ($)": "${:,.0f}",
                    "Variación (%)": "{:,.0f}%",
                }).map(color_variacion, subset=["Variación ($)", "Variación (%)"]),
                use_container_width=True,
            )

    with tab3:
        st.subheader("🎯 Cumplimiento de Presupuesto y Zonas (PPTO)")
        if not df_ppto.empty:
            p1, p2 = st.columns([1, 3])
            with p1:
                a_pp = st.selectbox("Año Presupuesto:", anios_disp, index=len(anios_disp) - 1 if anios_disp else 0, key="a3")
            with p2:
                m_pp = st.multiselect("Meses a evaluar en PPTO:", meses_disp, default=meses_disp, key="m3")

            if a_pp and m_pp:
                ap = int(a_pp)
                cp = df_ppto.columns.tolist()
                p_zona = next((c for c in cp if "zona" in str(c).lower()), cp[2] if len(cp) > 2 else cp[0])
                p_ppto = next((c for c in cp if "presupuesto" in str(c).lower() or "ppto" in str(c).lower()), cp[3] if len(cp) > 3 else cp[-1])
                p_maestra = next((c for c in cp if "maestra" in str(c).lower()), cp[4] if len(cp) > 4 else p_ppto)

                pp_f = df_ppto.copy()
                pp_f[p_zona] = pp_f[p_zona].astype(str).str.strip()
                pp_f[p_ppto] = pd.to_numeric(pp_f[p_ppto], errors="coerce").fillna(0)
                pp_f[p_maestra] = pd.to
