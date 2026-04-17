import streamlit as st


def safe_run(func, *args, name="облигациям", **kwargs):
    """
    Execute a data-loading function with built-in Streamlit error handling.

    This helper wraps a function that returns a tuple (data, error),
    displays a user-friendly warning message in case of failure,
    and stops further execution of the Streamlit app.

    Args:
        func (Callable): Function to execute. Must return (data, error),
            where `error` is None if execution succeeded.
        *args: Positional arguments passed to `func`.
        name (str, optional): Human-readable name of the data being loaded.
            Used in the error message. Defaults to "облигациям".
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
        st.warning(f"Не удалось загрузить данные по {name}")
        st.stop()

    return data


def render_bond_info(bonds_df, selected_secid, coupon_type, rusfar_value):
    """
    Render detailed information for a selected bond in a Streamlit dashboard.

    Displays key bond metrics (yield, price, coupon, duration, etc.) and
    calculates spread relative to a benchmark depending on coupon type.

    Args:
        bonds_df (pd.DataFrame):
            DataFrame containing bond data. Expected columns include:
            - 'SECID', 'SHORTNAME'
            - 'EFFECTIVEYIELD', 'PRICE', 'COUPONPERCENT'
            - 'NEXTCOUPON', 'MATDATE'
            - 'ACCRUEDINT', 'COUPONPERIOD'
            - 'duration_years'
            - 'gcurve_spread' (for fixed bonds)

        selected_secid (str or None):
            Selected bond identifier. Used to filter `bonds_df`.

        coupon_type (str):
            Type of coupon ("Фикс" or "Флоатер").
            Determines which benchmark is used for spread calculation.

        rusfar_value (float):
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
        st.warning('Не удалось загрузить информацию о выбранной облигации, возможно, она недоступна')
        return

    # Extract single row and replace NaN for UI safety
    bond_info = bond_df.iloc[0].fillna('-')

    # --- SPREAD CALCULATION ---
    # Convert spread to basis points depending on coupon type
    if coupon_type == 'Фикс':
        delta_value = bond_info['gcurve_spread'] * 100
        delta_description = 'Спред к КБД'
    else:
        # Spread to RUSFAR (in basis points)
        delta_value = (bond_info['EFFECTIVEYIELD'] - rusfar_value) * 100
        delta_description = 'Спред к RUSFAR'

    # --- HEADER ---
    st.subheader(f"{bond_info['SHORTNAME']}")

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
            "Доходность, %",
            f"{bond_info['EFFECTIVEYIELD']:.2f}",
            delta=f"{delta_value:.2f} б.п.",
            delta_description=delta_description
        )
        col2.metric("Цена, %", bond_info['PRICE'])
        col3.metric("Купон, %", bond_info['COUPONPERCENT'])
        col4.metric("Дата следующего купона", bond_info['NEXTCOUPON'])

    # --- SECOND ROW ---
    with second_row:
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Дюрация, годы", f'{bond_info['duration_years']:.2f}')
        col2.metric("НКД, ₽", bond_info['ACCRUEDINT'])
        col3.metric("Периодичность выплат, дни", bond_info['COUPONPERIOD'])
        col4.metric("Дата погашения", bond_info['MATDATE'])


def render_bond_selector(bonds_df):
    """
        Render a Streamlit selectbox for choosing a bond by SECID.

        The widget displays a human-readable label (derived from SHORTNAME)
        while internally storing the selected SECID in `st.session_state["selected_secid"]`.

        Args:
            bonds_df (pd.DataFrame):
                DataFrame containing bond data. Expected columns:
                - 'SECID': Unique bond identifier (used as value)
                - 'SHORTNAME': Bond name (used for display formatting)

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
    # Here we extract only numeric part from SHORTNAME (e.g. "ОФЗ 26238" → "26238")
    # to keep the UI compact and readable
    secid_to_name = dict(
        zip(bonds_df["SECID"], bonds_df["SHORTNAME"].str.replace(r'[^\d]+', '', regex=True))
    )

    # `key` binds the widget to Streamlit session state.
    # The selected SECID is stored in st.session_state["selected_secid"],
    # allowing persistence across reruns and synchronization with chart interactions.
    st.selectbox(
        "Облигация:",
        secid_list,
        key="selected_secid",
        placeholder='ОФЗ .....',
        format_func=lambda x: secid_to_name.get(x, x)
    )
