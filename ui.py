import pandas as pd
import streamlit as st
import re
from i18n import translate as t
from typing import Callable, Any


def safe_run(func: Callable, *args: Any, **kwargs: Any) -> Any | None:
    """
    Execute a data-loading function with built-in Streamlit error handling.

    This helper wraps a function that returns a tuple (data, error),
    displays a user-friendly warning message in case of failure,
    and stops further execution of the Streamlit app.

    Args:
        func (typing.Callable): Function to execute. Must return (data, error),
            where `error` is None if execution succeeded.
        *args: Positional arguments passed to `func`.
        **kwargs: Keyword arguments passed to `func`.

    Returns:
        Any: The data returned by `func` if no error occurred.

    Raises:
        streamlit.errors.StopException:
            Raised internally by `st.stop()` to halt app execution
            when an error occurs.
    """

    data, error = func(*args, **kwargs)

    if error:
        st.warning(t('error_msg'))
        st.stop()

    return data


def format_bond_name(name: str) -> str:
    """
    Format bond name for display depending on UI language.

    Converts Russian OFZ prefix to English equivalent for EN locale.
    Does not modify original data.

    Args:
        name (str): Original bond name from MOEX.

    Returns:
        str: Localized display name.
    """

    if st.session_state.get('lang', 'Ru') == 'En':
        return re.sub(r'^ОФЗ', 'OFZ', name)

    return name


def render_bond_info(
        bonds_df: pd.DataFrame,
        selected_secid: str,
        coupon_type: str,
        rusfar_value: float | None
) -> None:
    """
    Render detailed information for a selected bond in a Streamlit dashboard.

    Displays key bond metrics (yield, price, coupon, duration, etc.) and
    calculates spread relative to a benchmark depending on coupon type.

    Args:
        bonds_df (pandas.DataFrame):
            DataFrame containing bond data. Expected columns include:
            - 'SECID', 'display_name'
            - 'EFFECTIVEYIELD', 'PRICE', 'COUPONPERCENT'
            - 'NEXTCOUPON', 'MATDATE'
            - 'ACCRUEDINT', 'COUPONPERIOD'
            - 'duration_years'
            - 'gcurve_spread' (for fixed bonds)

        selected_secid (str):
            Selected bond identifier. Used to filter `bonds_df`.

        coupon_type (str):
            Type of coupon ("Фикс" or "Флоатер").
            Determines which benchmark is used for spread calculation.

        rusfar_value (float | None):
            RUSFAR rate (used for floating bonds).

    Returns:
        None

    Notes:
        - Function is UI-focused and directly renders Streamlit components
        - Assumes that `selected_secid` is managed via session state
        - Handles edge case when selected bond is no longer available
    """

    # Filter selected bond
    bond_df = bonds_df[bonds_df["SECID"] == selected_secid]

    # Handle case when bond is missing (e.g. after filtering or data update)
    if bond_df.empty:
        st.warning(t('bond_info_warning'))
        return

    # Extract single row and replace NaN for UI safety
    bond_info = bond_df.iloc[0].fillna('-')

    # --- SPREAD CALCULATION ---
    # Convert spread to basis points depending on coupon type
    if coupon_type == 'fix':
        delta_value = bond_info['gcurve_spread'] * 100
        benchmark = 'G-Curve'
    else:
        # Spread to RUSFAR (in basis points)
        delta_value = (bond_info['EFFECTIVEYIELD'] - rusfar_value) * 100
        benchmark = 'RUSFAR'

    # --- HEADER ---
    st.subheader(bond_info['display_name'])

    # --- METRICS LAYOUT ---

    # Layout is split into two horizontal containers with different vertical alignment.
    # This is intentional: the first row contains a metric with delta (col1),
    # which increases its vertical size compared to other columns.
    #
    # Using `vertical_alignment='top'` for the first row keeps all metrics aligned at the top,
    # while `vertical_alignment='bottom'` for the second row ensures visual balance
    # between rows despite uneven element heights.
    first_row = st.container(horizontal=True, vertical_alignment='top')
    second_row = st.container(horizontal=True, vertical_alignment='bottom')

    # --- FIRST ROW ---
    with first_row:
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            t('yield'),
            f"{bond_info['EFFECTIVEYIELD']:.2f}",
            delta=f"{delta_value:.2f}",
            delta_description=t('spread_format', benchmark=benchmark)
        )
        col2.metric(t('price'), bond_info['PRICE'])
        col3.metric(t('coupon_val'), bond_info['COUPONPERCENT'])
        col4.metric(t('next_coupon'), bond_info['NEXTCOUPON'])

    # --- SECOND ROW ---
    with second_row:
        col1, col2, col3, col4 = st.columns(4)

        col1.metric(t('duration'), f'{bond_info['duration_years']:.2f}')
        col2.metric(t('aci'), bond_info['ACCRUEDINT'])
        col3.metric(t('frequency'), bond_info['COUPONPERIOD'])
        col4.metric(t('maturity_date'), bond_info['MATDATE'])


def render_bond_selector(bonds_df: pd.DataFrame) -> None:
    """
        Render a Streamlit selectbox for choosing a bond by SECID.

        The widget displays a human-readable label (display_name)
        while internally storing the selected SECID in `st.session_state["selected_secid"]`.

        Args:
            bonds_df (pandas.DataFrame):
                DataFrame containing bond data. Expected columns:
                - 'SECID': Unique bond identifier (used as value)
                - 'display_name': Bond name (used for display formatting)

        Returns:
            None

        Notes:
            - Uses `format_func` to decouple displayed label from actual value
            - Selection is persisted automatically via Streamlit session state
            - Assumes 'selected_secid' key is managed outside this function
        """

    # List of available bond identifiers (used as selectbox values)
    secid_list = bonds_df["SECID"].tolist()

    # Map SECID → display label
    secid_to_name = dict(
        zip(bonds_df["SECID"], bonds_df["display_name"])
    )

    # `key` binds the widget to Streamlit session state.
    # The selected SECID is stored in st.session_state["selected_secid"],
    # allowing persistence across reruns and synchronization with chart interactions.
    st.selectbox(
        t('bond_label'),
        secid_list,
        key="selected_secid",
        placeholder=t('placeholder'),
        format_func=lambda x: secid_to_name.get(x, x)
    )


def init_session_state() -> None:
    """
    Initialize default values in Streamlit session state.

    Ensures all required keys are present before UI rendering.
    Prevents KeyError and maintains consistent state across reruns.

    Session keys:
        lang (str):
            Current UI language ('Ru' or 'En').

        selected_secid (str | None):
            Selected bond identifier (SECID).
            Acts as a single source of truth for both chart and sidebar.

        coupon_type (str):
            Selected bond type filter:
            - 'fix' for fixed-coupon bonds (ZCYC-based analysis)
            - 'floater' for floating-rate bonds (RUSFAR-based analysis)

        widget_key (str):
            Dynamic key for coupon type widget.
            Depends on language to force widget re-creation on change,
            preventing UI desynchronization.
    """

    # --- LANGUAGE ---
    if 'lang' not in st.session_state:
        st.session_state.lang = 'Ru'

    # --- SELECTED BOND ---
    if "selected_secid" not in st.session_state:
        st.session_state.selected_secid = None

    # --- COUPON TYPE ---
    if "coupon_type" not in st.session_state:
        st.session_state.coupon_type = 'fix'

    # --- WIDGET KEY ---
    if 'widget_key' not in st.session_state:
        st.session_state.widget_key = f"coupon_{st.session_state.lang}"


def update_widget_key() -> None:
    """
    Update widget key for coupon type selector based on current language.

    Used as an `on_change` callback for the language widget.
    Changing the key forces Streamlit to recreate the coupon selector,
    preventing UI desynchronization when labels change.
    """

    st.session_state.widget_key = f"coupon_{st.session_state.lang}"
