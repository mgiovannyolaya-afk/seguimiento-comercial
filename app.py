import pandas as pd
import streamlit as st

# Configuración de la página con diseño ancho y moderno
st.set_page_config(
    page_title="Gestión Comercial - Meta 70%", page_icon="🎯", layout="wide"
)

# Estilo visual limpio y corporativo
st.markdown("""
    <style>
        .main { background-color: #f8f9fa; }
        .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# Título principal del tablero
st.title("🎯 Control de Oportunidades y Cumplimiento (Meta 70%)")
st.markdown("Monitoreo comercial interactivo basado en la hoja de control operativo.")
st.markdown("---")

# Carga de datos optimizada desde la hoja 'Export'
@st.cache_data
def cargar_datos():
    df = pd.read_excel("SGTO X CANAL.xlsx", sheet_name="Export")
    return df

try:
    with st.spinner("Cargando base de datos comercial..."):
        df = cargar_datos()

    # --- BARRA LATERAL DE FILTROS INTERACTIVOS ---
    st.sidebar.header("🔍 Filtros de Segmentación")
    
    # Filtro de Supervisor
    supervisores = ["Todos"] + sorted(df["Supervisor"].dropna().unique().tolist())
    sup_seleccionado = st.sidebar.selectbox("Supervisor", supervisores)

    # Filtro de Zona basado en la selección
    if sup_seleccionado != "Todos":
        df_temp = df[df["Supervisor"] == sup_seleccionado]
    else:
        df_temp = df

    zonas = ["Todas"] + sorted(df_temp["Zona"].dropna().unique().tolist())
    zona_seleccionada = st.sidebar.selectbox("Zona", zonas)

    if zona_seleccionada != "Todas":
        df_temp = df_temp[df_temp["Zona"] == zona_seleccionada]

    # Filtro de Vendedor
    vendedores = ["Todos"] + sorted(df_temp["Vendedor"].dropna().unique().tolist())
    vendedor_seleccionado = st.sidebar.selectbox("Vendedor", vendedores)

    # Aplicar filtros finales
    df_filtrado = df_temp.copy()
    if vendedor_seleccionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Vendedor"] == vendedor_seleccionado]

    # --- TARJETAS DE MÉTRICAS SUPERIORES (KPIs) ---
    col1, col2, col3, col4 = st.columns(4)

    total_clientes = len(df_filtrado)
    total_reserva = pd.to_numeric(df_filtrado["Reserva"], errors="coerce").sum()
    total_cartera = pd.to_numeric(df_filtrado["Total Cartera"], errors="coerce").sum()
    prom_cumplimiento = 70.0  # Meta establecida

    with col1:
        st.metric(label="📊 Clientes / Registros", value=f"{total_clientes:,}")
    with col2:
        st.metric(label="🎯 Meta Comercial", value=f"{prom_cumplimiento}%")
    with col3:
        st.metric(label="💰 Total Reserva", value=f"${total_reserva:,.0f}")
    with col4:
        st.metric(label="⚠️ Cartera Total", value=f"${total_cartera:,.0f}")

    st.markdown("---")

    # --- PESTAÑAS DE NAVEGACIÓN ---
    pestana1, pestana2, pestana3 = st.tabs(["📋 Detalle Comercial", "🔍 Clientes y Oportunidades", "📈 Resumen por Zona"])

    with pestana1:
        st.subheader("Base de Datos Filtrada")
        # Selector de columnas clave para una visualización limpia
        columnas_principales = [
            'Supervisor', 'Zona', 'Vendedor', 'Nit Cliente', 'Nombre Cliente', 
            'Ciudad', 'Canal', 'Reserva', 'Total Cartera', '%Eje Ppto'
        ]
        cols_disponibles = [c for c in columnas_principales if c in df_filtrado.columns]
        
        st.dataframe(df_filtrado[cols_disponibles], use_container_width=True, height=450)

    with pestana2:
        st.subheader("Análisis de Oportunidades y Venta 0")
        # Mostrar clientes con baja ejecución o potencial de reserva
        if 'Reserva' in df_filtrado.columns:
            df_oportunidad = df_filtrado[['Nombre Cliente', 'Canal', 'Vendedor', 'Reserva', 'Cupo']].sort_values(by='Reserva', ascending=False)
            st.dataframe(df_oportunidad, use_container_width=True, height=450)
        else:
            st.info("No se encontró la columna de reserva para este análisis.")

    with pestana3:
        st.subheader("Consolidado por Zona y Vendedor")
        if 'Zona' in df_filtrado.columns and 'Reserva' in df_filtrado.columns:
            resumen_zona = df_filtrado.groupby(['Zona', 'Vendedor'])['Reserva'].sum().reset_index()
            st.dataframe(resumen_zona, use_container_width=True, height=450)
        else:
            st.info("Datos insuficientes para agrupar por zona.")

except Exception as e:
    st.error(f"Error al procesar la hoja 'Export': {e}")
    st.info("Asegúrate de que el archivo 'SGTO X CANAL.xlsx' está actualizado en el repositorio con la pestaña 'Export'.")
