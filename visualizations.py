import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import folium
import streamlit as st


def build_base_map(geojson):

    m = folium.Map(location=[0, 20], zoom_start=3)

    # Draw map from GeoJSON
    folium.GeoJson(
        geojson,
        tooltip=folium.GeoJsonTooltip(
            fields=['admin0', 'admin1', 'admin2'],
            aliases=['Country: ', 'admin1: ', 'admin2:'],
            localize=True
        )
    ).add_to(m)

    return m


@st.cache_resource
def plot_yield_obs(crop_yield):

    fig, ax = plt.subplots()

    sns.lineplot(
        data=crop_yield,
        x='year',
        y='yield_obs',
        ax=ax,
        marker='o'
    )

    ax.set_xlabel('Year')
    ax.set_ylabel('Yield (t/ha)')
    ax.set_title('Maize Yield Over Time')
    fig.tight_layout()
    
    return fig

@st.cache_resource
def plot_eo_var(eo_df, selected_eo):

    fig, ax = plt.subplots()
    sns.lineplot(
        data=eo_df,
        x='date',
        y=selected_eo,
        ax=ax,
        marker='o'
    )

    ax.set_xlabel('Year')
    ax.set_ylabel(selected_eo)
    ax.set_title(f'{selected_eo} Over Time (Pre-Harvest)')
    fig.autofmt_xdate()
    fig.tight_layout()

    return fig


@st.cache_resource
def create_map(yield_fcst, geojson, _gdf, selected_variable, country_fnids, selected_country, selected_season, selected_year, selected_model, selected_lead):

    # Dictionary for mapping variables:
    label_map = {
        "yield_fcst":         ("Forecast Yield",    "t/ha"),
        "yield_fcst_error":   ("Forecast Error",    "t/ha"),
        "yield_fcst_perror":  ("Percent Error",     "%"),
    }

    var_label, var_unit = label_map.get(selected_variable, (selected_variable, ""))
    
    # Filter for selection
    df_filt = yield_fcst.query(
        "fnid in @country_fnids " 
        "& season==@selected_season "
        "& year==@selected_year "
        "& model==@selected_model "
        "& lead==@selected_lead",
        engine="python"
    )

    # --- Build two-layer map ---
    # Layer 1: color every region gray in case of missing data
    # Layer 2: Overlay only region with data

    fig = go.Figure()

    # # --- Layer 1 ---
    # fig.add_trace(go.Choroplethmapbox(
    #     geojson=geojson,
    #     locations=country_fnids,
    #     z=[0]*len(country_fnids),
    #     featureidkey="properties.fnid",
    #     colorscale=[[0, "lightgray"], [1, "lightgray"]],
    #     showscale=False,
    #     marker_line_width=0.5,
    #     marker_line_color="black"
    # ))

    # --- Layer 2 ---
    if not df_filt.empty:
        fig.add_trace(go.Choroplethmapbox(
            geojson=geojson,
            locations=df_filt["fnid"],
            z=df_filt[selected_variable],
            featureidkey="properties.fnid",
            colorscale="RdYlBu",
            marker_line_width=0.5,
            colorbar_title=var_label,
            text=df_filt['admin1'],
            hovertemplate=(
                "<b>%{text}</b><br>"
                f"{var_label}: "+"%{z:.2f} "+var_unit+"<extra></extra>"
            )
        ))
    
    # --- Layout ---
    # center on the country’s centroid
    country_gdf = _gdf[_gdf["admin0"] == selected_country]
    lat0 = country_gdf.centroid_lat.mean()
    lon0 = country_gdf.centroid_lon.mean()

    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=4,
        mapbox_center={"lat": lat0, "lon": lon0},
        margin={"r":0,"t":0,"l":0,"b":0}
    )

    return fig
