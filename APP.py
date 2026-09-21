import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime as dt

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Simulador de Forwards & Futuros",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para una UI limpia y atractiva
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e222d;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .metric-title {
        font-size: 0.9rem;
        color: #888;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. BARRA LATERAL - PARÁMETROS DE ENTRADA
# ==========================================
# Cargar el logo desde la carpeta del proyecto
st.sidebar.image("logo_uace.png", use_column_width=True)
st.sidebar.caption("Unidad de Análisis en Ciencias Económicas (UACE)")
st.sidebar.markdown("---")
st.sidebar.title("⚙️ Parámetros de la Estrategia")

# Selección de Activo
st.sidebar.subheader("1. Selección del Activo")
ticker_option = st.sidebar.selectbox(
    "Selecciona un activo o ingresa un Ticker personalizado:",
    ["SPY", "QQQ", "AAPL", "EURUSD=X", "GBPUSD=X", "BTC-USD", "Personalizado"]
)

if ticker_option == "Personalizado":
    ticker_symbol = st.sidebar.text_input("Ingresa el Ticker (ej: MSFT, CL=F, GC=F):", "MSFT").upper()
else:
    ticker_symbol = ticker_option

# Selección de Fechas
st.sidebar.subheader("2. Fechas del Contrato")
default_start = dt.date(2023, 1, 1)
default_end = dt.date(2023, 12, 31)

start_date = st.sidebar.date_input("Fecha de inicio (Compra / Apertura):", value=default_start)
end_date = st.sidebar.date_input("Fecha de fin (Vencimiento / Cierre):", value=default_end)

if start_date >= end_date:
    st.sidebar.error("⚠️ La fecha de inicio debe ser anterior a la fecha de fin.")

# Parámetros del Contrato
st.sidebar.subheader("3. Especificaciones del Contrato")
contract_size = st.sidebar.number_input("Tamaño del contrato / Multiplicador:", min_value=1, value=100, step=1)
num_contracts = st.sidebar.number_input("Número de contratos:", min_value=1, value=1, step=1)

total_units = contract_size * num_contracts

# ==========================================
# 3. CARGA DE DATOS (YFINANCE)
# ==========================================
@st.cache_data(ttl=3600)
def load_data(ticker, start, end):
    try:
        data = yf.download(ticker, start=start, end=end + dt.timedelta(days=1))
        if data.empty:
            return None
        
        # Extracción limpia de la columna de precio de cierre
        if 'Adj Close' in data.columns:
            prices = data['Adj Close']
        elif 'Close' in data.columns:
            prices = data['Close']
        else:
            prices = data.iloc[:, 0]
            
        if isinstance(prices, pd.DataFrame):
            prices = prices.iloc[:, 0]
            
        df_clean = pd.DataFrame({'Close': prices}).dropna()
        return df_clean
    except Exception as e:
        return None

# Título Principal
st.title("📈 Plataforma de Estrategias con Forwards y Futuros")
st.markdown("Analiza y simula el comportamiento de posiciones **Largas (Long)** y **Cortas (Short)** en mercados de derivados financieros.")

# Cargar datos
with st.spinner("Cargando datos del mercado..."):
    df = load_data(ticker_symbol, start_date, end_date)

if df is None or df.empty:
    st.error(f"❌ No se pudieron descargar datos para el ticker **{ticker_symbol}** en el rango de fechas seleccionado. Por favor verifica los parámetros.")
    st.stop()

# ==========================================
# 4. CÁLCULOS GENERALES
# ==========================================
price_start = float(df['Close'].iloc[0])
price_end = float(df['Close'].iloc[-1])
asset_return = ((price_end - price_start) / price_start) * 100

# Retornos diarios y PnL para Futuros
df['Daily_Return'] = df['Close'].pct_change().fillna(0)
df['Price_Change'] = df['Close'].diff().fillna(0)

df['PnL_Long_Daily'] = df['Price_Change'] * total_units
df['PnL_Short_Daily'] = -df['Price_Change'] * total_units

df['Equity_Curve_Long'] = df['PnL_Long_Daily'].cumsum()
df['Equity_Curve_Short'] = df['PnL_Short_Daily'].cumsum()

# ==========================================
# 5. PESTAÑAS (TABS) DE NAVEGACIÓN
# ==========================================
tab_futuros, tab_forwards = st.tabs(["📊 Estrategia con Futuros", "🤝 Estrategia con Forwards"])

# ------------------------------------------
# TAB 1: FUTUROS
# ------------------------------------------
with tab_futuros:
    st.header("Simulación de Contratos de Futuros")
    st.caption("Los futuros tienen liquidación diaria (*Mark-to-Market*). La curva de capital acumulada refleja las ganancias y pérdidas día a día.")

    # Selección de Posición a visualizar
    col_pos, col_blank = st.columns([1, 2])
    with col_pos:
        position = st.radio("Posición de Futuros:", ["Ambas", "Larga (Long)", "Corta (Short)"], horizontal=True)

    # Tarjetas de Métricas
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Precio Incial (Spot)", f"${price_start:,.2f}")
    m2.metric("Precio Final (Spot)", f"${price_end:,.2f}", f"{asset_return:+.2f}%")
    
    pnl_long_final = df['Equity_Curve_Long'].iloc[-1]
    pnl_short_final = df['Equity_Curve_Short'].iloc[-1]
    
    m3.metric("PnL Final (Long)", f"${pnl_long_final:,.2f}", delta_color="normal")
    m4.metric("PnL Final (Short)", f"${pnl_short_final:,.2f}", delta_color="normal")
    m5.metric("Unidades Totales", f"{total_units:,.0f}")

    st.markdown("---")

    # Gráfico interactivo con Plotly
    fig_fut = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.1,
        subplot_titles=(f"Evolución del Precio del Activo Subyacente ({ticker_symbol})", "Curva de Capital Acumulada (Equity Curve)")
    )

    # Gráfico superior: Precio del subyacente
    fig_fut.add_trace(
        go.Scatter(x=df.index, y=df['Close'], mode='lines', name=f'{ticker_symbol} Precio', line=dict(color='#29b6f6', width=2)),
        row=1, col=1
    )

    # Gráfico inferior: Equity Curves
    if position in ["Ambas", "Larga (Long)"]:
        fig_fut.add_trace(
            go.Scatter(x=df.index, y=df['Equity_Curve_Long'], mode='lines', name='Equity Curve (Long)', line=dict(color='#00e676', width=2)),
            row=2, col=1
        )
    if position in ["Ambas", "Corta (Short)"]:
        fig_fut.add_trace(
            go.Scatter(x=df.index, y=df['Equity_Curve_Short'], mode='lines', name='Equity Curve (Short)', line=dict(color='#ff5252', width=2)),
            row=2, col=1
        )

    # Línea de referencia en cero PnL
    fig_fut.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

    fig_fut.update_layout(
        height=600,
        hovermode="x unified",
        template="plotly_dark",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    fig_fut.update_yaxes(title_text="Precio (USD)", row=1, col=1)
    fig_fut.update_yaxes(title_text="Ganancia / Pérdida (USD)", row=2, col=1)

    st.plotly_chart(fig_fut, use_container_width=True)

    # Mostrar Tabla de Datos
    with st.expander("📄 Ver detalle de datos de Futuros"):
        st.dataframe(df[['Close', 'Daily_Return', 'PnL_Long_Daily', 'Equity_Curve_Long', 'PnL_Short_Daily', 'Equity_Curve_Short']].style.format("{:.2f}"))


# ------------------------------------------
# TAB 2: FORWARDS
# ------------------------------------------
with tab_forwards:
    st.header("Simulación de Contratos Forward")
    st.caption("Los contratos Forward son acuerdos OTC que se liquidan al vencimiento. El PnL depende únicamente de la diferencia entre el precio Forward acordado (Strike) y el precio Spot al vencimiento.")

    col_fwd1, col_fwd2 = st.columns([1, 2])

    with col_fwd1:
        st.subheader("Configuración del Forward")
        # El precio forward sugerido es el precio spot inicial
        custom_strike = st.number_input(
            "Precio Forward Acordado (Strike K):", 
            value=float(price_start), 
            format="%.2f",
            help="Precio fijado en el contrato al inicio de la inversión."
        )

        # Cálculos Forward al Vencimiento
        pnl_fwd_long = (price_end - custom_strike) * total_units
        pnl_fwd_short = (custom_strike - price_end) * total_units

        st.markdown("### Resultados al Vencimiento")
        st.metric("Precio Spot al Vencimiento (S_T)", f"${price_end:,.2f}")
        
        color_long = "green" if pnl_fwd_long >= 0 else "red"
        color_short = "green" if pnl_fwd_short >= 0 else "red"

        st.markdown(f"**PnL Long Forward:** <span style='color:{color_long}; font-size: 1.3rem;'>${pnl_fwd_long:,.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"**PnL Short Forward:** <span style='color:{color_short}; font-size: 1.3rem;'>${pnl_fwd_short:,.2f}</span>", unsafe_allow_html=True)

    with col_fwd2:
        st.subheader("Perfil de Payoff al Vencimiento")

        # Generar rango de precios posibles al vencimiento (+/- 30%)
        min_p = min(df['Close'].min(), custom_strike) * 0.7
        max_p = max(df['Close'].max(), custom_strike) * 1.3
        spot_range = np.linspace(min_p, max_p, 100)

        payoff_long = (spot_range - custom_strike) * total_units
        payoff_short = (custom_strike - spot_range) * total_units

        fig_payoff = go.Figure()

        fig_payoff.add_trace(go.Scatter(x=spot_range, y=payoff_long, mode='lines', name='Long Forward Payoff', line=dict(color='#00e676', width=3)))
        fig_payoff.add_trace(go.Scatter(x=spot_range, y=payoff_short, mode='lines', name='Short Forward Payoff', line=dict(color='#ff5252', width=3)))

        # Marcador del precio Spot actual al vencimiento
        fig_payoff.add_vline(x=custom_strike, line_dash="dash", line_color="orange", annotation_text=f"Strike K: ${custom_strike:,.2f}")
        fig_payoff.add_vline(x=price_end, line_dash="dot", line_color="#29b6f6", annotation_text=f"Spot Final: ${price_end:,.2f}")
        fig_payoff.add_hline(y=0, line_color="gray", line_width=1)

        fig_payoff.update_layout(
            title="Diagrama de Payoff al Vencimiento",
            xaxis_title="Precio Spot del Subyacente al Vencimiento ($)",
            yaxis_title="Ganancia / Pérdida ($)",
            template="plotly_dark",
            height=450,
            hovermode="x unified"
        )

        st.plotly_chart(fig_payoff, use_container_width=True)

    st.markdown("---")
    st.subheader("Evolución Temporal: Precio Spot vs. Precio Pactado (Strike)")

    fig_fwd_time = go.Figure()
    fig_fwd_time.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Precio Spot Histórico', line=dict(color='#29b6f6', width=2)))
    fig_fwd_time.add_hline(y=custom_strike, line_dash="dash", line_color="orange", annotation_text=f"Precio Forward Pactado (${custom_strike:,.2f})")

    fig_fwd_time.update_layout(
        title="Precio Spot del Activo vs. Precio Acordado durante el Periodo",
        xaxis_title="Fecha",
        yaxis_title="Precio (USD)",
        template="plotly_dark",
        height=400
    )

    st.plotly_chart(fig_fwd_time, use_container_width=True)

# Footer informativo
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Simulador de Derivados Financieros | Desarrollado para Streamlit Cloud</p>", unsafe_allow_html=True)
