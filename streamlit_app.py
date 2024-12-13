import streamlit as st
import folium
import pandas as pd
import numpy as np
from streamlit_folium import st_folium
import altair as alt

# Data Source for map: https://public.opendatasoft.com/explore/embed/dataset/world-administrative-boundaries-countries/table/
@st.cache_resource
def get_input_data():
    """ Import the original GNESTE datafile in a Pandas Dataframe format
    
    
    Read the data in from Dropbox and load onto the webpage"""
    url = "https://www.dropbox.com/scl/fi/e62t8nrji5ruo99plpxrl/GNESTE_ALL.csv?rlkey=kyueuuql5r4optc3bw0g33tyj&st=t1agotqq&dl=1"

    data_file = pd.read_csv(url)

    return data_file

def display_map(df, technology):
    map = folium.Map(location=[10, 0], zoom_start=1, control_scale=True, scrollWheelZoom=True, tiles='CartoDB positron')
    df = df.rename(columns={"Country code":"iso3_code"})

    choropleth = folium.Choropleth(
        geo_data='./DATA/country_boundaries.geojson',
        data=df,
        columns=('iso3_code', "WACC"),
        key_on='feature.properties.iso3_code',
        line_opacity=0.8,
        highlight=True,
        fill_color="YlGnBu",
        nan_fill_color = "grey",
        legend_name="Weighted Average Cost of Capital (%)"
    )
    choropleth.geojson.add_to(map)


    df_indexed = df.set_index('iso3_code')
    df_indexed = df_indexed.dropna(subset="WACC")
    for feature in choropleth.geojson.data['features']:
        iso3_code = feature['properties']['iso3_code']
        feature['properties'][technology + ' WACC'] = (
        f"{df_indexed.loc[iso3_code, 'WACC']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        feature['properties']["Debt_Share"] = (
        f"{df_indexed.loc[iso3_code, 'Debt_Share']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        feature['properties']["Equity_Cost"] = (
        f"{df_indexed.loc[iso3_code, 'Equity_Cost']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        feature['properties']["Debt_Cost"] = (
        f"{df_indexed.loc[iso3_code, 'Debt_Cost']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        feature['properties']["Tax_Rate"] = (
        f"{df_indexed.loc[iso3_code, 'Tax_Rate']:0.2f}%" if iso3_code in df_indexed.index else "N/A"
    )
        #feature['properties']['GDP'] = 'GDP: ' + '{:,}'.format(df_indexed.loc[country_name, 'State Pop'][0]) if country_name in list(df_indexed.index) else ''

    #choropleth.geojson.add_child(
        #folium.features.GeoJsonTooltip(['english_short'], labels=False)
    #)

    choropleth.geojson.add_child(
    folium.features.GeoJsonTooltip(
        fields=['english_short', technology + ' WACC', "Equity_Cost", "Debt_Cost", "Debt_Share", "Tax_Rate"],  # Display these fields
        aliases=["Country:", technology + ":", "Cost of Equity:", "Cost of Debt:", "Debt Share:", "Tax_Rate"],         # Display names for the fields
        localize=True,
        style="""
        background-color: #F0EFEF;
        border: 2px solid black;
        border-radius: 3px;
        box-shadow: 3px;
    """,
    max_width=400,
    )
)
    
    st_map = st_folium(map, width=700, height=350)

    country_name = ''
    if st_map['last_active_drawing']:
        country_name = st_map['last_active_drawing']['properties']['english_short']
    return country_name

@st.cache_data
def get_sorted_waccs(df, technology):

    if technology == "Solar PV":
        column = "solar_pv_wacc"
    elif technology == "Onshore Wind":
        column = "onshore_wacc"
    elif technology == "Offshore Wind":
        column = "offshore_waccs"

    sorted_df = df.sort_values(by=column, axis=0, ascending=True)
    list = ["solar_pv_wacc", "onshore_wacc", "offshore_wacc"]
    for columns in list:
        if columns == column:
            list.remove(columns)
    sorted_df = sorted_df.drop(labels=list, axis="columns")
    sorted_df = sorted_df.dropna(subset=column)
    sorted_df = sorted_df.rename(columns={column:"WACC"})
    sorted_df["WACC"] = sorted_df["WACC"].round(decimals=2)

    return sorted_df

def sort_waccs(df):

    sorted_df = df.sort_values(by="WACC", axis=0, ascending=True)
    list = ["WACC", "Equity_Cost", "Debt_Cost", "Debt_Share", "Tax_Rate"]
    sorted_df = sorted_df.drop(labels=list, axis="columns")
    
    return sorted_df


@st.cache_data
def get_selected_country(df, country_code):

    selected_wacc = df[df['Country code'] == country_code]

    return selected_wacc


def plot_ranking_table(raw_df, country_codes):

    # Select countries
    df = raw_df[raw_df["Country code"].isin(country_codes)]

    
    # Melt dataframe
    df = df.rename(columns={"Risk_Free":" Risk Free", "Country_Risk":"Country Risk", "Technology_Risk":"Technology Risk"})
    data_melted = df.melt(id_vars="Country code", var_name="Factor", value_name="Value")

    # Set order
    category_order = [' Risk Free', 'Country Risk', 'Equity Risk', 'Lenders Margin', 'Technology Risk']

    # Create chart
    chart = alt.Chart(data_melted).mark_bar().encode(
        x=alt.X('sum(Value):Q', stack='zero', title='Weighted Average Cost of Capital (%)'),
        y=alt.Y('Country code:O', sort="x", title='Country'),  # Sort countries by total value descending
        color=alt.Color('Factor:N', title='Factor'),
        order=alt.Order('Factor:O', sort="ascending"),  # Color bars by category
).properties(width=700)

    # Add x-axis to the top
    x_axis_top = chart.encode(
        x=alt.X('sum(Value):Q', stack='zero', title='Weighted Average Cost of Capital (%)', axis=alt.Axis(orient='top'))
    )

    # Combine the original chart and the one with the top axis
    chart_with_double_x_axis = alt.layer(
        chart,
        x_axis_top
    )

    st.write(chart_with_double_x_axis)

def display_count_map(df):
    map = folium.Map(location=[10, 0], zoom_start=1, control_scale=True, scrollWheelZoom=True, tiles='CartoDB positron')
    df = df.rename(columns={"ISO3":"iso3_code"})

    choropleth = folium.Choropleth(
        geo_data='./DATA/country_boundaries.geojson',
        data=df,
        columns=('iso3_code', "count"),
        key_on='feature.properties.iso3_code',
        line_opacity=0.8,
        highlight=True,
        fill_color="YlGnBu",
        nan_fill_color = "grey",
        legend_name="Datapoints",
        threshold_scale=[1, 5, 15, 50, 100, max(df['count'])],
    )
    choropleth.geojson.add_to(map)

    print(f"Minimum count: {df['count'].min()}, Maximum count: {df['count'].max()}")
    df_indexed = df.set_index('iso3_code')
    df_indexed = df_indexed.dropna(subset="count")
    df_indexed = df_indexed[~df_indexed.index.duplicated(keep='first')]  # Remove duplicates

    for feature in choropleth.geojson.data['features']:
        iso3_code = feature['properties']['iso3_code']
        feature['properties']['count'] = (
            f"{df_indexed.loc[iso3_code, 'count']:0.0f}" if iso3_code in df_indexed.index else "N/A"
        )


    choropleth.geojson.add_child(
    folium.features.GeoJsonTooltip(
        fields=['english_short', "count"],  # Display these fields
        aliases=["Country:", "Datapoints:"],         # Display names for the fields
        localize=True,
        style="""
        background-color: #F0EFEF;
        border: 2px solid black;
        border-radius: 3px;
        box-shadow: 3px;
    """,
    max_width=400,
    )
)
    
    st_map = st_folium(map, width=700, height=350)

    country_name = ''
    if st_map['last_active_drawing']:
        country_name = st_map['last_active_drawing']['properties']['english_short']
    return country_name


def plot_comparison_chart(df):
   # Melt dataframe
    df = df.rename(columns={"Risk_Free":" Risk Free", "Country_Risk":"Country Risk", "Technology_Risk":"Technology Risk"})
    data_melted = df.melt(id_vars="Year", var_name="Factor", value_name="Value")

    # Set order
    category_order = [' Risk Free', 'Country Risk', 'Equity Risk', 'Lenders Margin', 'Technology Risk']

    # Create chart
    chart = alt.Chart(data_melted).mark_bar().encode(
        x=alt.X('sum(Value):Q', stack='zero', title='Weighted Average Cost of Capital (%)'),
        y=alt.Y('Year:O', title='Country'),  # Sort countries by total value descending
        color=alt.Color('Factor:N', title='Factor'),
        order=alt.Order('Factor:O', sort="ascending"),  # Color bars by category
).properties(width=700)
    st.write(chart)
    

## Read in Datafile
gneste_datafile = get_input_data()

## Get country data
country_counts = gneste_datafile['Country'].value_counts().reset_index()
print(country_counts)
country_counts = pd.merge(country_counts, gneste_datafile[['Country', 'ISO3']], on="Country", how="left")


# Text and Formatting
style_heading = 'text-align: center'
style_image = 'display: block; margin-left: auto; margin-right: auto;' 

st.markdown(f"<h1 style='{style_heading}'>The Global and National Energy Systems Techno-Economic (GNESTE) Database</h1>", unsafe_allow_html=True)
st.header("")
tab1, tab2, tab3, tab4, tab5= st.tabs(["🌐 Global Coverage", "🏭 Technology", "ℹ️ Benchmarking Tool", "🔭 Projections", "📝 About"])



with tab1:
    st.header("Data Coverage")
    display_count_map(country_counts)
with tab2:
    st.header("Global Ranges")

with tab3:
    st.header("Comparison to International Ranges")
with tab4:
    st.header("XX")
with tab5:
    st.header("About")
    st.header("Methods")
    st.header("License and Data Use Permissions")