import streamlit as st
import folium
import pandas as pd
import numpy as np
from streamlit_folium import st_folium
import altair as alt
import plotly.express as px
from scipy import stats
from github import Github
from datetime import datetime
import os

# GitHub token and repository details
REPO_NAME = "LukeHatton21/gneste_data"

# Data Source for map: https://public.opendatasoft.com/explore/embed/dataset/world-administrative-boundaries-countries/table/
@st.cache_resource
def get_details():
    with open('https://www.dropbox.com/scl/fi/diux1pan2w692rqpw5ol7/Github-Access-Code.rtf?rlkey=t97t2tqly3q3irfbij1i8fxc1&st=k3l2mtb4&dl=1', 'r') as file:
        text = file.read()
    token = text

    return token



@st.cache_resource
def get_input_data():
    """ Import the original GNESTE datafile in a Pandas Dataframe format
    
    
    Read the data in from Dropbox and load onto the webpage"""
    url = "https://www.dropbox.com/scl/fi/e62t8nrji5ruo99plpxrl/GNESTE_ALL.csv?rlkey=kyueuuql5r4optc3bw0g33tyj&st=t1agotqq&dl=1"

    data_file = pd.read_csv(url)

    return data_file

def display_map(df, variable, variable_name, count=None):
    map = folium.Map(location=[10, 0], zoom_start=1, control_scale=True, scrollWheelZoom=True, tiles='CartoDB positron')
    df = df.rename(columns={"ISO3":"iso3_code"})
    if count is not None:
        threshold_scale = [1, 5, 15, 50, 100, max(df[variable])]
    else:
        threshold_scale=None
    choropleth = folium.Choropleth(
        geo_data='./DATA/country_boundaries.geojson',
        data=df,
        columns=('iso3_code', variable),
        key_on='feature.properties.iso3_code',
        line_opacity=0.8,
        highlight=True,
        fill_color="YlGnBu",
        nan_fill_color = "grey",
        legend_name="Datapoints",
        threshold_scale=threshold_scale,
    )
    choropleth.geojson.add_to(map)

    df_indexed = df.set_index('iso3_code')
    df_indexed = df_indexed.dropna(subset=variable)
    df_indexed = df_indexed[~df_indexed.index.duplicated(keep='first')]  # Remove duplicates

    for feature in choropleth.geojson.data['features']:
        iso3_code = feature['properties']['iso3_code']
        feature['properties'][variable] = (
            f"{df_indexed.loc[iso3_code, variable]:0.0f}" if iso3_code in df_indexed.index else "N/A"
        )


    choropleth.geojson.add_child(
    folium.features.GeoJsonTooltip(
        fields=['english_short', variable],  # Display these fields
        aliases=["Country:", variable_name],         # Display names for the fields
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

def display_count_map(df, variable, variable_name, count=None):
    map = folium.Map(location=[10, 0], zoom_start=1, control_scale=True, scrollWheelZoom=True, tiles='CartoDB positron')
    df = df.rename(columns={"ISO3":"iso3_code"})
    if count is not None:
        threshold_scale = [1, 5, 15, 50, 100, max(df[variable])]
    else:
        threshold_scale=None
    choropleth = folium.Choropleth(
        geo_data='./DATA/country_boundaries.geojson',
        data=df,
        columns=('iso3_code', variable),
        key_on='feature.properties.iso3_code',
        line_opacity=0.8,
        highlight=True,
        fill_color="YlGnBu",
        nan_fill_color = "grey",
        legend_name="Datapoints",
        threshold_scale=threshold_scale,
    )
    choropleth.geojson.add_to(map)

    df_indexed = df.set_index('iso3_code')
    df_indexed = df_indexed.dropna(subset=variable)
    df_indexed = df_indexed[~df_indexed.index.duplicated(keep='first')]  # Remove duplicates

    for feature in choropleth.geojson.data['features']:
        iso3_code = feature['properties']['iso3_code']
        feature['properties'][variable] = (
            f"{df_indexed.loc[iso3_code, variable]:0.0f}" if iso3_code in df_indexed.index else "N/A"
        )


    choropleth.geojson.add_child(
    folium.features.GeoJsonTooltip(
        fields=['english_short', variable],  # Display these fields
        aliases=["Country:", variable_name],         # Display names for the fields
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

def create_benchmark_boxplot(data, assumption, label):

    # Extract values from the data
    y_max = np.nanmax(data['value'])
    renamed_data = data.rename(columns={"value":label})

    # Create a boxplot
    fig = px.box(renamed_data, x="Continent", y=label, points="all")
    fig.add_hline(y=assumption, line_width=3, line_dash="dash", line_color="red")
    fig.update_yaxes(range=[0, y_max])
    
     
    # Add in the assumption as a red line     
    event = st.plotly_chart(fig, key="iris", on_select="rerun")

def upload_to_github(repository, new_file, commit_message):

    """ Upload the updated GNESTE database to the specified Github repository
    
    Inputs:
        repository: Repository name to upload to
        github_token: Personal Access Token to use
        altered_df: Updated dataframe with modifications to upload
        commit_message: Commit message to use"""
    
    # Specify filename
    file_name = "GNESTE_ALL.csv"

    # Get Github locations and access token
    token = get_details()
    g = Github(token)
    repo = g.get_repo(repository)
    

    # Get file content
    content = new_file.to_csv(index=False)

    # Upload updated file
    try:
        existing_file = repo.get_contents(file_name)
        

        # If it exists, update the file
        repo.update_file(existing_file.path, commit_message,content, existing_file.sha)
        st.success(f"Updated the GNESTE database")
    except:
        # If it doesn't exist, create a new file
        repo.create_file(file_name, commit_message, content)
        st.success(f"Uploaded new file to the repository")

## Read in Datafile
gneste_datafile = get_input_data()

## Get country data
country_counts = gneste_datafile['Country'].value_counts().reset_index()
country_counts = pd.merge(country_counts, gneste_datafile[['Country', 'ISO3']], on="Country", how="left")


# Text and Formatting
style_heading = 'text-align: center'
style_image = 'display: block; margin-left: auto; margin-right: auto;' 

st.markdown(f"<h1 style='{style_heading}'>The Global and National Energy Systems Techno-Economic (GNESTE) Database</h1>", unsafe_allow_html=True)
st.header("")
tab1, tab2, tab3, tab4, tab5, tab6, tab7= st.tabs(["🌐 Coverage", "🏭Technology CAPEX", "📊Benchmarking", "🔎Data Mapping", "💻Upload", "📝Changelog", "ℹ️About"])



with tab1:
    st.header("Data Coverage")

    # Create map for data counts
    display_count_map(country_counts, "count", "Datapoints:", count="True")
with tab2:
    st.header("Mean National CAPEX")
    technology = st.selectbox("Technology", ["Solar", "Wind", "Hydro", "Nuclear","Batteries", "Gas",  "Coal"], key="CAPEX_technology")
    start_year, end_year = st.select_slider(
    "Select a range of years",
    options=["2020", "2021", "2022", "2023", "2024"],
    value=("2020", "2024"))


    # Select the technology and year
    gneste_extract = gneste_datafile.loc[gneste_datafile["Technology"] == technology].loc[gneste_datafile['Code']=="CAPEX"]

    # Select the corresponding years
    years_range = np.arange(int(start_year), int(end_year)+1, 1).tolist()
    variables = years_range.insert(0, "ISO3")
    list_string = map(str, years_range)
    years_data = gneste_extract[list_string]
    melted_years = pd.melt(years_data, id_vars=['ISO3'])

    mean_data = melted_years.groupby(['ISO3']).mean(numeric_only=True).rename(columns={"value":"mean"}).reset_index()
    #min_data = melted_years.groupby(['ISO3']).min(numeric_only=True).rename(columns={"value":"min"})
    #max_data = melted_years.groupby(['ISO3']).max(numeric_only=True).rename(columns={"value":"max"})

    #combined_df = pd.merge(mean_data, min_data, how="left", on="ISO3")
    #combined_df = pd.merge(combined_df, max_data, how="left", on="ISO3")
    #st.write(combined_df)
    display_map(mean_data, "mean", "US$/kW (2023):")
    

with tab3:
    st.header("Comparison to International Ranges")
    technology_bench = st.selectbox("Technology", ["Solar", "Wind", "Hydro", "Nuclear","Batteries", "Gas",  "Coal"], index=0)
    start_year_bench, end_year_bench = st.select_slider(
    "Select a range of years",
    options=["2020", "2021", "2022", "2023", "2024"],
    value=("2020", "2024"), key="BENCH_YEAR")
    parameter = st.selectbox("Variable", ["CAPEX", "OPEX_T", "OPEX_F", "OPEX_V", "WACC", 
    "LIFETIME", "BUILDTIME", "FUEL_PRICE", "EFFICIENCY"], index=0)


    # Extract benchmarking data
    gneste_benchmark = gneste_datafile.loc[gneste_datafile["Technology"] == technology_bench].loc[gneste_datafile['Code']==parameter]

    # Get units 
    units = gneste_benchmark['Unit'].values[0]
    
    # Input assumption for testing
    assumption = st.number_input("Assumption for benchmarking", value=1000)
 

    # Extract given years
    years_range_bench = np.arange(int(start_year), int(end_year)+1, 1).tolist()
    variables_bench  = years_range_bench.insert(0, "Continent")
    list_string_bench  = map(str, years_range_bench)
    benchmark_data = gneste_benchmark[list_string_bench].dropna(axis=0, how="all")

    # Melt data and aggregate
    melted_benchmark = pd.melt(benchmark_data, id_vars=['Continent']).dropna(axis=0, how="any")

    # Create assumption marking
    percentile = stats.percentileofscore(melted_benchmark['value'].values, assumption)
    st.write(f"The assumption of **{str(assumption)}** " + f"**{units}** is at the {percentile:0.2f}% percentile of the data collected")

    # Create a boxplot
    create_benchmark_boxplot(melted_benchmark, assumption, f"{parameter} ({units})")

with tab4:
    st.header("Data Mapping")
    # Get data table
    data_mapping = pd.read_csv("./DATA/GNESTE_Mapping.csv")
    st.table(data_mapping.set_index(data_mapping.columns[0]))
with tab5:
    st.header("Data Upload: WIP DO NOT USE")
    st.write("Additional datapoints can be added to the GNESTE database here, either manually by specifying the corresponding parameters or through an upload of a CSV or Excel file")


    # Get dataframe for updating
    new_file = gneste_datafile

    # Get date and time for commit message
    now = datetime.now()
    date_time = now.strftime("%m/%d/%Y, %H:%M:%S")





    # File uploader
    st.subheader("File Upload")
    st.write("Uploaded file must be in CSV format and specify the following in its columns: Technology, Country, Variable, Unit, Category, Source, and Year")
    uploaded_file = st.file_uploader("Choose a file to upload", type=["csv", "xlsx"])

    if uploaded_file:
        # Display the file name
        st.write(f"Uploaded file: {uploaded_file.name}")

        # Process the file as a DataFrame
        try:
            # Example: Loading as a DataFrame (assume CSV here, add other cases as needed)
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            elif uploaded_file.name.endswith(".xlsx"):
                df = pd.read_excel(uploaded_file)
            else:
                st.error("Unsupported file format.")
                df = None
            
            if df is not None:
                
                # Reset file pointer to read the raw content
                uploaded_file.seek(0)
                
                # Read raw content to upload
                raw_content = uploaded_file.read()

                if st.button("Upload to GitHub"):
                    try:
                        # Upload the file to GitHub
                        upload_to_github(REPO_NAME, new_file, date_time)
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")



    # Manual upload
    st.subheader("Manual Upload")
    st.write("Specify the corresponding parameters:")
    
    technology_upload = st.multiselect("Technology", options=["Solar", "Wind", "Hydro", "Nuclear","Batteries", "Gas",  "Coal"])
    country_upload = st.multiselect("Country", options=["United Kingdom", "United States"])
    variable_upload = st.multiselect("Variable", options=["Capital Cost", "Fixed O&M","Variable O&M", "Total O&M", "Fuel Price", "Efficiency", "Construction Time", "Lifetime", "Cost of Capital"])
    year_upload = st.multiselect("Year", options=["2020", "2021", "2022", "2023", "2024", "2025", "2030", "2040", "2050"])
    
    # Replace with processed dataframe
    manual_dataframe = gneste_datafile

    # Call file processor
    if st.button("Store and Add Additional Manual Upload"):
        st.write("Data Preview:")
         # Display the DataFrame
        st.dataframe(manual_dataframe) 


    # Call github updater
    if st.button("Manual Upload to GNESTE"):
        try:
            # Upload the file to GitHub
            upload_to_github(REPO_NAME, new_file, date_time)
        except Exception as e:
            st.error(f"An error occurred: {e}")
    

with tab6:
    st.header("Changelog")
    changelog = pd.read_csv("./DATA/Changelog.csv")
    st.table(changelog.set_index(changelog.columns[0]))
with tab7:
    st.header("About")
    st.write("Data and assumptions relating to the cost and performance of electricity generation and storage technologies are key input parameters to energy system modelling tools."+
             "Despite the ubiquity and importance of these parameters, there is no standardised database which collates the variety of values from across the literature, so modellers" +
             "must collect them independently each time they populate or update model inputs, leading to duplicated efforts and inconsistencies which can profoundly influence model results." +
             "Technology cost and performance also varies between countries, regions and over time, meaning that data must be country- or region-specific and frequently updated.")
    st.write("The GNESTE database aims to address these challenges by collating historical, current, and future cost and performance data and assumptions for the six most prominent "+
             "electricity generation technologies; coal, gas, hydroelectric, nuclear, solar photovoltaic (PV) and wind power, which together accounted for over 92 % of installed generation capacity in 2022.")
    st.header("Methods")
    st.write("The GNESTE database is global in scope but with regional and national specificity, covers the years 2015 through to 2050, and spans 5518 datapoints collated from 56 sources. " +
             "The full list of sources alongside the academic write up of the collation can be found in Data in Brief: https://doi.org/10.1016/j.dib.2024.110669.")
    st.header("Funding")
    st.write("The GNESTE database was created using funding from the South African-driven Modeling Capacity and Communication (ADMeCC) project" +
             " and the Climate Compatible Growth (CCG) programme. Both CCG and ADMeCC are funded by the Foreign, Commonwealth and Development Office (FCDO) of the UK government." +
             "The CCG programme brings together leading research organisations and is led out of the STEER centre, Loughborough University.")
    st.write("The GNESTE visualisation here was developed by Luke Hatton at Imperial College London. Contact by email: l.hatton23@imperial.ac.uk")
    st.header("License and Data Use Permissions")
    st.write("The data available here is licensed as Creative Commons Attribution-NonCommercial International (CC BY-NC 4.0), which means you are free to copy, " + 
             "redistribute and adapt it for non-commercial purposes, provided you give appropriate credit. If you wish to use the data for commercial purposes, " +
             "please get in touch to discuss commercial license pricing.")