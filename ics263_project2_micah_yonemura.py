
import streamlit as st
import pandas as pd
import plotly.express as px
import glob
import os
from datetime import date # Import date from datetime module
from pathlib import Path
import numpy as np


# Define path (relative, for Streamlit Cloud compatibility)
folder_path = Path(".")  # Current directory; change to Path("data") if you use a subfolder

for file_path in folder_path.iterdir():
    if file_path.is_file():
        print(file_path)


# Use glob to find all matching .csv in folder
file_paths = glob.glob(os.path.join(folder_path, "*.csv"))

# Create list of dataframes
df_list = []
for filename in file_paths:
    df = pd.read_csv(filename)
    # Extract year from filename and add it as a new column
    year = int(os.path.basename(filename).replace('.csv', ''))
    df['Year'] = year
        # Standardize column names
    if 'Happiness Score' in df.columns:
        pass # Already has the desired name
    elif 'Score' in df.columns:
        df.rename(columns={'Score': 'Happiness Score'}, inplace=True)
    elif 'Happiness.Score' in df.columns:
        df.rename(columns={'Happiness.Score': 'Happiness Score'}, inplace=True)

    if 'GDP per capita' in df.columns:
        pass # Already has the desired name
    elif 'Economy (GDP per Capita)' in df.columns:
        df.rename(columns={'Economy (GDP per Capita)': 'GDP per capita'}, inplace=True)
    elif 'Economy..GDP.per.Capita.' in df.columns:
        df.rename(columns={'Economy..GDP.per.Capita.': 'GDP per capita'}, inplace=True)
    
    if 'Health (Life Expectancy)' in df.columns:
        pass # Already has the desired name
    elif 'Healthy life expectancy' in df.columns:
        df.rename(columns={'Healthy life expectancy': 'Health (Life Expectancy)'}, inplace=True);
    elif 'Health..Life.Expectancy.' in df.columns:
        df.rename(columns={'Health..Life.Expectancy.': 'Health (Life Expectancy)'}, inplace=True);


    if 'Country or region' in df.columns:
        df.rename(columns={'Country or region': 'Country'}, inplace=True)

    # Standardize 'Standard Error' for uncertainty if other columns exist
    if 'Standard Error' not in df.columns:
        if 'Lower Confidence Interval' in df.columns and 'Upper Confidence Interval' in df.columns:
            df['Standard Error'] = (df['Upper Confidence Interval'] - df['Lower Confidence Interval']) / 3.92
        elif 'Whisker.high' in df.columns and 'Whisker.low' in df.columns:
            df['Standard Error'] = (df['Whisker.high'] - df['Whisker.low']) / 3.92 # Assuming 95% CI

    df_list.append(df)

# Concatenate all dataframes into one
combined_df = pd.concat(df_list, ignore_index=True)

# Create a country to region mapping from existing data to fill missing regions
country_to_region_map = combined_df.dropna(subset=['Region']).set_index('Country')['Region'].to_dict()
combined_df['Region'] = combined_df.apply(lambda row: country_to_region_map.get(row['Country']) if pd.isna(row['Region']) else row['Region'], axis=1)

# Impute missing Standard error values with the mean of existing ones
mean_standard_error = combined_df['Standard Error'].mean()
combined_df['Standard Error'] = combined_df['Standard Error'].fillna(mean_standard_error)

print(combined_df.head())

# Check length of rows
print(f"Total rows: {len(combined_df)}")

# Input widgets in sidebar
with st.sidebar:
    st.header('Filters')
    
    # Numeric Slider
    happiness_range = st.slider('Happiness Range', min_value=0.0, max_value=10.0, value=(0.0, 10.0))

    # Multi-select dropdown region
    selected_regions = st.multiselect('Select regions', combined_df['Region'].unique())
    if not selected_regions:
        st.warning('No region selected. Showing all data.')

    # Multi-select dropdown country
    selected_countries = st.multiselect('Select countries', combined_df['Country'].unique())
    if not selected_countries:
        st.warning('No country selected. Showing all data.')

    # Date range selector
    min_year = int(combined_df['Year'].min())
    max_year = int(combined_df['Year'].max())
    start_year_selected, end_year_selected = st.slider('Select Year Range', min_value=min_year, max_value=max_year, value=(min_year, max_year))

    # Checkbox or radio button
    show_top_countries = st.checkbox('Show Top Countries')
    if show_top_countries:
        top_countries = combined_df.groupby('Country')['Happiness Score'].mean().sort_values(ascending=False).head(10)

    show_bottom_countries = st.checkbox('Show Bottom Countries')
    if show_bottom_countries:
        bottom_countries = combined_df.groupby('Country')['Happiness Score'].mean().sort_values(ascending=True).head(10)


# Apply filters
current_filter = pd.Series(True, index=combined_df.index)

# Happiness Score filter
current_filter = current_filter & (
    (combined_df['Happiness Score'] >= happiness_range[0]) &
    (combined_df['Happiness Score'] <= happiness_range[1]))

# Year filter
current_filter = current_filter & (
    (combined_df['Year'] >= start_year_selected) &
    (combined_df['Year'] <= end_year_selected))

# Combine Country, Region, Top/Bottom selection with OR logic
country_inclusion_filter = pd.Series(False, index=combined_df.index)
any_country_region_selection_made = False

if selected_countries:
    country_inclusion_filter = country_inclusion_filter | (combined_df['Country'].isin(selected_countries))
    any_country_region_selection_made = True

if selected_regions:
    country_inclusion_filter = country_inclusion_filter | (combined_df['Region'].isin(selected_regions))
    any_country_region_selection_made = True

if show_top_countries:
    country_inclusion_filter = country_inclusion_filter | (combined_df['Country'].isin(top_countries.index))
    any_country_region_selection_made = True

if show_bottom_countries:
    country_inclusion_filter = country_inclusion_filter | (combined_df['Country'].isin(bottom_countries.index))
    any_country_region_selection_made = True

# If no specific country/region/top/bottom selections are made, then all countries/regions are selected
if not any_country_region_selection_made:
    country_inclusion_filter = pd.Series(True, index=combined_df.index)

current_filter = current_filter & country_inclusion_filter

filtered = combined_df[current_filter]

# Correlation matrix for filtered country
correlation_matrix = filtered[['Happiness Score', 'Family', 'Health (Life Expectancy)', 'Freedom', 'Generosity', 'GDP per capita']].corr()
fig = px.imshow(correlation_matrix, color_continuous_scale='RdBu', title='Correlation Heatmap for selected countries')
st.plotly_chart(fig)

# Display summary statistics
st.subheader('Summary Statistics')
col1, col2, col3 = st.columns(3)
with col1:
    st.metric('Total Countries', filtered['Country'].nunique())
with col2:
    st.metric('Average Happiness Score', round(filtered['Happiness Score'].mean(), 2))
with col3:
    st.metric('Average GDP', round(filtered['GDP per capita'].mean(), 2))

# Handle edge cases
if len(filtered) == 0:
    st.warning('No data available for selected filters.')
    st.stop()

#
# Time series visualization
fig = px.line(filtered, x='Year', y='Happiness Score', color='Country', title='Happiness Score Over Time')
st.plotly_chart(fig)

# Geospatial visualization
fig = px.choropleth(filtered, locations='Country', locationmode='country names', color='Happiness Score',
                    hover_name='Country', title='Happiness Score by Country')
st.plotly_chart(fig)

# Calculate the mean per region per year for plotting
region_mean = filtered.groupby(['Region', 'Year'])['Happiness Score'].agg(['mean']).reset_index()
region_mean.columns = ['Region', 'Year', 'Region Mean']

# Calculate deviations for asymmetric error bars
filtered['error_pos'] = filtered['Upper Confidence Interval'] - filtered['Happiness Score']
filtered['error_neg'] = filtered['Happiness Score'] - filtered['Lower Confidence Interval']

# Uncertainty Aware Visualization
fig = px.box(filtered, y='Happiness Score', x='Country', color='Region',
                       points='all', # show all actual points
                       title='Distribution of Happiness Score per Country (Box Plot)')
fig.update_layout(xaxis_tickangle=-45) # Rotate country labels for better readability
st.plotly_chart(fig)

