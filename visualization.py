import plotly.graph_objects as go
import numpy as np


def create_chart(df, zcyc_interp=None, selected_secid=None):
    """
        Create a Plotly scatter chart for bond yields with an optional yield curve.

        The chart includes:
        - Bond points (yield vs. time to maturity)
        - Optional zero-coupon yield curve (ZCYC)
        - Highlighting of a selected bond via `selectedpoints`

        Args:
            df (pd.DataFrame):
                DataFrame containing bond data. Expected columns:
                - 'SECID': Unique bond identifier
                - 'SHORTNAME': Bond display name
                - 'ttm': Time to maturity (in years)
                - 'EFFECTIVEYIELD': Yield (%)
                - 'duration_years': Duration (in years)

            zcyc_interp (Callable, optional):
                Interpolator function for the zero-coupon yield curve.
                Must support:
                - `.x` attribute (array of maturities)
                - callable interface: f(x) -> y

            selected_secid (str, optional):
                SECID of the currently selected bond.
                Used to highlight the corresponding point on the chart.

        Returns:
            plotly.graph_objects.Figure:
                Configured Plotly figure with:
                - Scatter trace for bonds
                - Optional line trace for yield curve
                - Highlighted selected point (if provided)

        Notes:
            - Uses `selectedpoints` for efficient highlighting without duplicating traces
    """

    fig = go.Figure()

    # --- ZCYC LINE ---
    if zcyc_interp:
        # Generate smooth curve using interpolator bounds
        x_smooth = np.linspace(
            zcyc_interp.x.min(),
            zcyc_interp.x.max(),
            300
        )

        y_smooth = zcyc_interp(x_smooth)

        fig.add_trace(go.Scatter(
            x=x_smooth,
            y=y_smooth,
            mode="lines",
            line=dict(color="lightgray", width=1.5),
            name="КБД",
            hovertemplate=(
                    "<b>КБД</b><br>" +
                    "До погашения: %{x:.2f} лет<br>" +
                    "Значение: %{y:.2f}%<extra></extra>"
            ),
        ))

    # --- FIND INDEX OF SELECTED POINT ---
    selected_index = None

    # Plotly `selectedpoints` expects 0-based positional indices, not SECID.
    # Use NumPy to compute the position of the selected SECID, making the logic robust
    # to filtering or non-sequential DataFrame indices.
    if selected_secid:

        matches = np.where(df["SECID"].values == selected_secid)[0]
        selected_index = matches[0] if len(matches) else None

    # --- BOND POINTS (SINGLE TRACE) ---
    fig.add_trace(go.Scatter(
        x=df["ttm"],
        y=df["EFFECTIVEYIELD"],
        mode="markers",

        # Attach extra data for hover & selection handling
        customdata=df[["SECID", 'duration_years']],
        text=df["SHORTNAME"],

        marker=dict(
            size=8,
            color="DeepSkyBlue"
        ),

        # Highlight selected point (if exists)
        selectedpoints=[selected_index] if selected_index is not None else None,

        selected=dict(
            marker=dict(size=14, color="PaleVioletRed")
        ),

        hovertemplate=(
                "<b>%{text}</b><br>" +
                "Дюрация: %{customdata[1]:.2f}<br>" +
                "До погашения: %{x:.2f} лет<br>" +
                "Эффективная доходность: %{y:.2f}%<extra></extra>"
        ),
    ))

    # --- LAYOUT ---
    fig.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None,
        margin=dict(l=20, r=20, t=0, b=0), # l=left, r=right, t=top, b=bottom
    )

    return fig