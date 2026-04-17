import pandas as pd
import requests
import streamlit as st
from scipy.interpolate import PchipInterpolator

@st.cache_data(ttl=600, show_spinner=False)
def fetch_moex_blocks(url, params, blocks):
    """
    Fetch multiple data blocks from a MOEX ISS API endpoint.

    This function sends a request to the MOEX ISS API, validates the response,
    and converts specified JSON blocks into pandas DataFrames.

    The MOEX ISS API returns data in a structured format:
    each block contains 'data' and 'columns', which are used to construct
    DataFrames.

    Caching:
        Results are cached for 600 seconds (10 minutes) to:
        - Reduce redundant API calls
        - Prevent UI resets and session state loss on reruns

        Note: MOEX market data is typically delayed by ~15 minutes.

    Args:
        url (str):
            API endpoint URL.

        params (dict):
            Query parameters for the request.

        blocks (list[str]):
            List of block names to extract from the response
            (e.g., ["marketdata", "securities"]).

    Returns:
        tuple[dict[str, pd.DataFrame] | None, str | None]:
            - dict of DataFrames (key = block name), if successful
            - None and error message, if any error occurs

    Raises:
        None:
            All exceptions are caught and returned as error messages.
    """

    try:
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()

        data_json = response.json()

        result = {}

        for block in blocks:
            # Ensure requested block exists in response
            if block not in data_json:
                return None, f"Missing block: {block}"

            block_data = data_json[block]

            # Construct DataFrame from MOEX ISS structure
            df = pd.DataFrame(
                data=block_data.get('data', []),
                columns=block_data.get('columns', [])
            )

            # Validate that block contains data
            if df.empty:
                return None, f'Missing data in block: {block}'

            result[block] = df

        return result, None

    except Exception as e:
        # Return None and the exception message if the request fails
        return None, str(e)


def get_bonds_data(zcyc_interp=None):
    """
    Fetch and process government bond data from the MOEX TQOB board.

    Combines static bond attributes (securities) with market data
    (yields, price, duration), and optionally enriches the dataset
    with Zero-Coupon Yield Curve (ZCYC) derived metrics.

    Args:
        zcyc_interp (scipy.interpolate.PchipInterpolator | None):
            Interpolator for the Zero-Coupon Yield Curve.
            If provided, used to calculate theoretical yields and
            G-spreads for fixed-coupon bonds.

    Returns:
        tuple[pd.DataFrame | None, str | None]:
            - Processed DataFrame on success
            - None and error message on failure

    Notes:
        - Only RUB-denominated bonds (FACEUNIT == 'SUR') are included
        - Time-to-maturity (TTM) and duration are converted to years
        - ZCYC-based metrics are added only if interpolator is provided
    """

    # MOEX ISS endpoint for government bonds (OFZ) on the TQOB board
    url = 'https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities.json'

    # Limit response to required fields to reduce payload size
    params = {
        'iss.meta': 'off',
        'iss.only': 'securities,marketdata_yields',
        'securities.columns': 'SECID,SHORTNAME,BONDTYPE,NEXTCOUPON,ACCRUEDINT,MATDATE,FACEUNIT,COUPONPERIOD,COUPONPERCENT',
        'marketdata_yields.columns': 'SECID,PRICE,EFFECTIVEYIELD,DURATION'
    }

    # Fetch data using the generic helper function
    data, error = fetch_moex_blocks(
        url,
        params,
        blocks=['securities', 'marketdata_yields']
    )

    if error:
        return None, error

    securities_df = data['securities']
    marketdata_yields_df = data['marketdata_yields']

    # Simplify bond type labels for easier filtering/display
    securities_df.replace(
        {'Фикс с известным купоном': 'Фикс', 'Линкер/облигации с индексируемым': 'Линкер'},
        inplace=True
    )

    # Merge static and market data
    # Filter to RUB bonds only (exclude CNY-denominated instruments)
    all_data = marketdata_yields_df.merge(
        securities_df.loc[securities_df['FACEUNIT'] == 'SUR'], how='inner', on='SECID'
    )

    # Current date for time-based calculations
    today = pd.Timestamp.today().normalize()

    # Convert maturity to datetime and compute:
    # - TTM (time to maturity, years)
    # - duration in years
    # Using 365.25 accounts for leap years
    all_data['ttm'] = (pd.to_datetime(all_data['MATDATE']) - today) / pd.Timedelta(days=365.25)
    all_data['duration_years'] = all_data['DURATION'] / 365.25

    # Apply ZCYC interpolation if provided (for fixed-coupon bonds)
    if zcyc_interp is not None:
        # Avoid extrapolation by clipping TTM to interpolation bounds
        all_data['ttm_clipped'] = all_data['ttm'].clip(
            lower=zcyc_interp.x.min(),
            upper=zcyc_interp.x.max()
        )

        # Compute theoretical yield (G-curve) and yield spread
        all_data['gcurve_yield'] = zcyc_interp(all_data['ttm_clipped'])
        all_data['gcurve_spread'] = all_data['EFFECTIVEYIELD'] - all_data['gcurve_yield']

    return all_data, None


def get_zcyc_interpolator():
    """
    Fetch the Zero-Coupon Yield Curve (ZCYC) from MOEX and build an interpolator.

    The ZCYC represents a benchmark yield curve used to evaluate bond yields
    and calculate G-spreads. Since MOEX provides yields only for discrete
    standard maturities, interpolation is required to estimate yields for
    arbitrary time-to-maturity values.

    Returns:
        tuple[scipy.interpolate.PchipInterpolator | None, str | None]:
            - Interpolator object on success
            - None and error message on failure

    Notes:
        - 'period' represents time to maturity (in years)
        - 'value' represents yield (in percent)
        - PCHIP interpolation is used to preserve monotonicity and avoid
          unrealistic oscillations in the yield curve
    """

    # MOEX ISS endpoint for the Zero-Coupon Yield Curve
    url = 'https://iss.moex.com/iss/engines/stock/zcyc.json'
    params = {
        'iss.meta': 'off',
        'iss.only': 'yearyields'
    }

    # Fetch data block 'yearyields' which contains the curve points
    data, error = fetch_moex_blocks(url, params, ['yearyields'])

    if error:
        return None, error

    zcyc = data['yearyields']

    # Ensure data is sorted by maturity (required for interpolation)
    zcyc.sort_values('period', inplace=True)

    # Extract curve axes:
    # X → time to maturity (years)
    # Y → yield (%)
    curve_x = zcyc["period"].values
    curve_y = zcyc["value"].values

    # Build interpolator:
    # PCHIP preserves shape and monotonicity of the curve,
    # avoiding overshooting typical for spline interpolation
    interp = PchipInterpolator(curve_x, curve_y)

    return interp, None


def get_rusfar_value():
    """
    Fetch the latest RUSFAR (Russian Funding Alternative Rate) value.

    RUSFAR is used as a benchmark for floating-rate bonds. While OFZ floaters
    are typically linked to RUONIA, RUSFAR is used here for consistency
    as it is available via MOEX ISS. Both rates are typically highly correlated.

    Returns:
        tuple[float | None, str | None]:
            - RUSFAR value (float) on success
            - None and error message on failure
    """

    # MOEX ISS endpoint for the RUSFAR index
    url = 'https://iss.moex.com/iss/engines/stock/markets/index/securities/RUSFAR.json'
    params = {
        'iss.meta': 'off',
        'iss.only': 'marketdata',
        'marketdata.columns': 'LASTVALUE'
    }

    # Fetch 'marketdata' block using the generic helper
    data, error = fetch_moex_blocks(url, params, ['marketdata'])

    if error:
        return pd.DataFrame(), error

    df = data['marketdata']
    value = df.loc[0, 'LASTVALUE']

    return value, None
