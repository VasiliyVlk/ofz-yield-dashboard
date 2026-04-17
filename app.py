import streamlit as st
from data import get_bonds_data, get_zcyc_interpolator, get_rusfar_value
from visualization import create_chart
from ui import safe_run, render_bond_info, render_bond_selector

# --- PAGE CONFIG ---
# Set page metadata and layout
st.set_page_config(page_title="Карта доходности ОФЗ", layout="wide")
st.title("Карта доходности ОФЗ 🧠")

# --- INIT ---
# Initialize selected SECID in session state.
# This acts as a single source of truth for selection across:
# - chart clicks
# - sidebar selectbox
if "selected_secid" not in st.session_state:
    st.session_state.selected_secid = None


# --- SIDEBAR: GLOBAL SETTINGS ---
with st.sidebar:

    st.header("Настройки")

    # Coupon type selector controls:
    # - which dataset is loaded (ZCYC vs RUSFAR)
    # - which bonds are displayed
    coupon_type = st.segmented_control(
        'Тип купона:',
        ['Флоатер', 'Фикс'],
        default='Фикс',
        width='stretch'
    )


# --- DATA LOADING ---
# Load benchmark data depending on coupon type:
# - Fixed bonds → ZCYC curve
# - Floating bonds → RUSFAR rate
if coupon_type == 'Фикс':
    zcyc_interp, rusfar_value = safe_run(get_zcyc_interpolator, name="КБД"), None
else:
    zcyc_interp, rusfar_value = None, safe_run(get_rusfar_value, name="RUSFAR")

# Load bonds dataset (optionally enriched with ZCYC spreads)
bonds_df = safe_run(get_bonds_data, zcyc_interp, name='облигациям')
# Filter bonds by selected coupon type
bonds_df = bonds_df.loc[bonds_df['BONDTYPE'] == coupon_type]


# --- STATE VALIDATION ---
# Ensure selected SECID is still valid after filtering or data refresh.
# This prevents inconsistencies between UI state and available data.
if st.session_state.selected_secid not in bonds_df["SECID"].values:
    st.session_state.selected_secid = None


# --- CHART ---
# Build chart with current selection (used for highlighting)
fig = create_chart(
    bonds_df,
    zcyc_interp,
    selected_secid=st.session_state.selected_secid
)

# Render Plotly chart with click/selection support.
# `on_select="rerun"` triggers Streamlit rerun on point click.
event = st.plotly_chart(
    fig,
    on_select="rerun",
    selection_mode="points",
    config={"scrollZoom": True}
)


# --- UPDATE STATE FROM CHART ---
# Plotly returns selected points via event["selection"].
# We extract SECID from `customdata` (passed in chart as df[["SECID", ...]]).
# points[0] → first selected point, customdata[0] → SECID.
#
# IMPORTANT:
# - Must run BEFORE selectbox
# - Keeps chart and sidebar in sync via session_state
if event and event["selection"]["point_indices"]:
    clicked = event["selection"]["points"][0]["customdata"][0]

    # Update only if selection changed to avoid unnecessary reruns
    if clicked != st.session_state.selected_secid:
        st.session_state.selected_secid = clicked

        # Force immediate rerun so UI updates in a single click
        # (otherwise requires double click due to Streamlit execution order)
        st.rerun()


# --- SIDEBAR: BOND SELECTOR ---
# Must be rendered AFTER updating session_state from chart.
# Otherwise, selectbox will overwrite the value on rerun
# since widgets sync their value back to session_state.
with st.sidebar:
    render_bond_selector(bonds_df)


# --- OUTPUT ---
# Render bond details if selection exists
if st.session_state.selected_secid:

    render_bond_info(
        bonds_df,
        st.session_state.selected_secid,
        coupon_type,
        rusfar_value
    )

else:
    # Fallback UI when nothing is selected
    st.info("Для вывода подробной информации нажмите на точку или выберите выпуск в списке")