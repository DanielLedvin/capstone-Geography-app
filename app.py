import streamlit as st
import geopandas as gpd
import pandas as pd
from streamlit_folium import st_folium
import json
import visualizations as viz


# --- Page Configuration ---
st.set_page_config(layout='wide',
                   page_title='Sub-Saharan Crop Forecast Viewer')
st.title('Sub-Saharan Africa Crop Forecast Viewer')


# --- Data Loading Function ---
@st.cache_data
def load_data():
    '''
    Function:
    - Reads in cape_eo and crop production datasets as well as shapefile for mapping
    - Formats DataFrames for use in the interactive map

    Return:
    - cape_eo = Cape EO observations
    - viewer_yield = Yield values for Maize. columns are only fnid, year, and yield
    - gdf = Shapefile for mapping Sub-Saharan Africa

    Note:
    - cape_eo predictors are the same for the XGB and LR models, so I arbitrarily chose
        the rows from the XGB model not to have repeating predictor values
    '''
    # Read in files from 'data/' folder
    cape_eo = pd.read_parquet('./data/cape_eo_formatted.parquet')
    viewer_yield = pd.read_parquet('./data/viewer_yield.parquet')
    yield_fcst = pd.read_parquet('./data/viewer_yield_fcst_error.parquet')

    # Load gdf for lookups
    gdf = gpd.read_file('./data/gscd_shape_simplified.gpkg',
                        layer='gscd_shape_simplified',
                        engine='pyogrio')

    # Load GeoJSON
    with open('./data/gscd_shape.geojson') as f:
        geojson = json.load(f)

    return cape_eo, viewer_yield, yield_fcst, gdf, geojson


# --- Load Data ---
cape_eo, viewer_yield, yield_fcst, gdf, geojson = load_data()
eo_vars = ['ndvi', 'prcp', 'pdry', 'etos', 'tavg', 'gdd', 'kdd']


# --- Page Selection ---
page = st.sidebar.radio("Page", ["Yield & Climate", "Historical Forecasts"])


# --- Page 1: Current Conditions ---
if page == "Yield & Climate":

    # --- Build Map ---
    st.markdown('### Click a region to view EO and crop data')

    m = viz.build_base_map(geojson)
    map_output = st_folium(m, width=900, height=600)

    fnid = None
    
    # --- Display Data ---
    if map_output and map_output.get('last_active_drawing'):
        fnid = map_output['last_active_drawing']['properties']['fnid']

        # Use gdf for lookup
        region_row = gdf[gdf['fnid'] == fnid].iloc[0]
        region_name = f"{region_row['admin0']} - {region_row['admin1']}"
        st.success(f'Selected Region: {region_name}')


    if fnid:
        # Filter by region
        crop_yield = viewer_yield[viewer_yield['fnid'] == fnid]
        eo_df = cape_eo[cape_eo['fnid'] == fnid]

        if not eo_df.empty:
            # Select what EO to display
            selected_eo_var = st.selectbox(
                label='Select EO variables to plot',
                options=eo_vars,
                index=0
            )
        
        yield_col, eo_col = st.columns(2)

        # Yield graph
        with yield_col:
            if crop_yield.empty:
                st.warning('No yield data available for this region.')
            else:
                fig_yield = viz.plot_yield_obs(crop_yield)
                st.pyplot(fig_yield)

        # EO predictor graph
        with eo_col:
            if not eo_df.empty:
                fig_eo = viz.plot_eo_var(eo_df, selected_eo_var)
                st.pyplot(fig_eo)
            else:
                st.warning('No EO data available for this region.') 

    else:
        st.info('Click a region on the map to begin.')


# --- Page 2: Historical Forecasts ---
if page== "Historical Forecasts":
    st.markdown("### View Historical Forecast and Error")

    if "choropleth_fig" not in st.session_state:
        st.session_state.choropleth_fig = None

    var_col, country_col, season_col, years_col, model_col, lead_col = st.columns(6)

    with var_col:
        variables = [col for col in yield_fcst.columns if col not in ['fnid', 'country', 'admin1', 'admin2', 'season', 'year', 'model', 'lead']]
        selected_variable = st.selectbox('Variable', variables)
    
    with country_col:
        # Country selection
        countries = sorted(yield_fcst['country'].unique())
        selected_country = st.selectbox('Country', countries)
        country_fnids = yield_fcst[yield_fcst['country'] == selected_country]['fnid'].unique().tolist()

    with season_col:
        # Select season
        seasons = yield_fcst[yield_fcst['fnid'].isin(country_fnids)]['season'].unique()
        selected_season = st.selectbox('Season', seasons)

    with years_col:
        # Find available years for country fnids
        yrs = yield_fcst.loc[((yield_fcst['fnid'].isin(country_fnids)) 
                              & (yield_fcst['season']==selected_season)), 
                              'year'].dropna()
        if yrs.empty:
            st.warning("No forecast years available for the selected conditions.")
            st.stop()
        min_year, max_year = int(yrs.min()), int(yrs.max())
        year_range = list(range(min_year, max_year + 1))
        selected_year = st.selectbox('Year', year_range)

    # Parameter selection
    with model_col:
        models = sorted(yield_fcst["model"].unique())
        selected_model = st.selectbox("Model", models)

    with lead_col:
        leads  = sorted(yield_fcst["lead"].unique())
        selected_lead  = st.selectbox("Lead",  leads)

    # --- Create Apply Button ---
    update = st.button("Update Map")

    if update:

        fig = viz.create_map(yield_fcst, 
                             geojson, 
                             gdf,
                             selected_variable,
                             country_fnids, 
                             selected_country,
                             selected_season, 
                             selected_year, 
                             selected_model, 
                             selected_lead)
        
        st.session_state.choropleth_fig = fig

    if st.session_state.choropleth_fig is not None:
        st.plotly_chart(st.session_state.choropleth_fig, use_container_width=True)

