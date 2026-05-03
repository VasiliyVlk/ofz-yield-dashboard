import streamlit as st
from data import get_bonds_data, get_zcyc_interpolator, get_rusfar_value
from visualization import create_chart
from ui import safe_run, render_bond_info, render_bond_selector, format_bond_name, init_session_state, update_widget_key
from i18n import translate as t

# --- PAGE CONFIG ---
# Set page metadata and layout
st.set_page_config(page_title='ofz_yield_map', layout="wide")
st.title(t('main_title'))

# --- INIT ---
init_session_state()

# --- SIDEBAR: GLOBAL SETTINGS ---
with st.sidebar:

    st.header(t('settings'))

    # Stable internal values for coupon type (used in logic and filtering)
    options = ['fix', 'floater']
    # Current value from session state (single source of truth)
    default_value = st.session_state.coupon_type

    # Coupon type selector controls:
    # - which dataset is loaded (ZCYC vs RUSFAR)
    # - which bonds are displayed
    #
    # IMPORTANT:
    # - Uses dynamic widget key (stored in session_state) to force re-creation
    #   when language changes (prevents label/value desynchronization)
    # - `format_func` is used only for UI translation; underlying values remain stable
    selected_coupon = st.segmented_control(
        t('coupon_type_label'),
        options,
        width='stretch',
        key=st.session_state.widget_key,
        default=default_value,
        required=True,
        format_func=t
    )

    # Sync widget output back to session state (explicit update)
    st.session_state.coupon_type = selected_coupon


# --- DATA LOADING ---
# Load benchmark data depending on coupon type:
# - Fixed bonds → ZCYC curve
# - Floating bonds → RUSFAR rate
if selected_coupon == 'fix':
    zcyc_interp, rusfar_value = safe_run(get_zcyc_interpolator), None
else:
    zcyc_interp, rusfar_value = None, safe_run(get_rusfar_value)

# Load bonds dataset (optionally enriched with ZCYC spreads)
bonds_df = safe_run(get_bonds_data, zcyc_interp)
# Filter bonds by selected coupon type
bonds_df = bonds_df.loc[bonds_df['coupon_type'] == selected_coupon]
# Normalize bond names for consistent UI display (i18n-friendly)
bonds_df['display_name'] = bonds_df['SHORTNAME'].apply(format_bond_name)


# --- STATE VALIDATION ---
# Ensure selected SECID is still valid after filtering or data refresh.
# This prevents inconsistencies between UI state and available data.
if st.session_state.selected_secid not in bonds_df["SECID"].values:
    st.session_state.selected_secid = None


# --- UPDATE STATE FROM CHART ---
# Plotly selection is stored in Streamlit session_state under the chart `key`.
# We read it BEFORE rendering the chart to avoid double-click issues.
#
# Structure:
# st.session_state["bond_chart"]["selection"]["points"][0]["customdata"][0]
# → contains SECID passed via `customdata` in the chart
#
# IMPORTANT:
# - Runs before chart rendering
# - Ensures single-click interaction (no manual rerun needed)
# - Keeps chart and sidebar selection in sync via session_state
chart_selection = st.session_state.get("bond_chart", {}).get("selection")

if chart_selection and chart_selection["point_indices"]:
    new_secid = chart_selection["points"][0]["customdata"][0]

    if new_secid != st.session_state.selected_secid:
        st.session_state.selected_secid = new_secid


# --- CHART ---
# Build chart with current selection (used for highlighting selected bond)
fig = create_chart(
    bonds_df,
    zcyc_interp,
    selected_secid=st.session_state.selected_secid
)

# Render Plotly chart.
# The `key` binds chart state (including selection) to session_state,
# allowing us to read user interaction without relying on event callbacks.
event = st.plotly_chart(
    fig,
    on_select="rerun",  # triggers rerun so selection becomes available in session_state
    selection_mode="points",
    config={"scrollZoom": True},
    key="bond_chart"
)


# --- SIDEBAR: BOND SELECTOR AND LANGUAGE WIDGET ---
with st.sidebar:

    # Must be rendered AFTER updating session_state from chart.
    # Otherwise, select box will overwrite the value on rerun
    # since widgets sync their value back to session_state.
    render_bond_selector(bonds_df)

    # `on_change` triggers update_widget_key(), which regenerates the key
    # for the coupon type widget. This forces Streamlit to recreate it,
    # ensuring correct label rendering after language switch (prevents UI desync).
    st.segmented_control(
        t('language'),
        ['Ru', 'En'],
        width='stretch',
        key='lang',
        required=True,
        on_change=update_widget_key
    )

# --- OUTPUT ---
# Render bond details if selection exists
if st.session_state.selected_secid:

    render_bond_info(
        bonds_df,
        st.session_state.selected_secid,
        selected_coupon,
        rusfar_value
    )

else:
    # Fallback UI when nothing is selected
    st.info(t('click_hint'))