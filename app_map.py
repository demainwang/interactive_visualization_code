import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

gdp_per_capita = pd.read_csv("gdp-per-capita-worldbank.csv")
population = pd.read_csv("population.csv")
total_co2 = pd.read_csv("annual-co2-emissions-per-country.csv")
oil_production = pd.read_csv("oil-production-by-country.csv")
continents = pd.read_csv("continents-according-to-our-world-in-data.csv")

data = pd.merge(gdp_per_capita, population, on=["Entity", "Year"])
data = pd.merge(data, total_co2, on=["Entity", "Year"])
data["Total_GDP"] = data["GDP per capita, PPP (constant 2017 international $)"] * data["Population - Sex: all - Age: all - Variant: estimates"]
data["CO2_per_GDP"] = (data["Annual CO₂ emissions"] / data["Total_GDP"]) * 1000

data = data.drop(columns=["Code_x", "Code_y"], errors="ignore")
data.rename(columns={"Entity": "Country", "Year": "Year"}, inplace=True)
oil_production.rename(columns={"Entity": "Country"}, inplace=True)
data = pd.merge(data, oil_production, on=["Country", "Year"], how="left")
data.fillna(0, inplace=True)
data["Year"] = data["Year"].astype(int)
data = data.sort_values("Year")

color_min = data["CO2_per_GDP"].min()
color_max = data["CO2_per_GDP"].max()
color_mid = (color_min + color_max) / 2

fig_map = px.choropleth(
    data,
    locations="Country",
    locationmode="country names",
    color="CO2_per_GDP",
    hover_name="Country",
    animation_frame="Year",
    title="CO2 Emissions per GDP Dollar Over Time (kg/$)",
    color_continuous_scale=px.colors.sequential.Reds,
    labels={"CO2_per_GDP": "CO2 per GDP (kg/$)"},
)
fig_map.update_layout(
    geo=dict(
        showframe=False,
        showcoastlines=True,
        projection_type="equirectangular",
    ),
    coloraxis=dict(
        colorbar=dict(
            tickvals=[color_min, color_mid, color_max],
            ticktext=[f"{color_min:.2f}", f"{color_mid:.2f}", f"{color_max:.2f}"],
            title="CO2 per GDP (kg/$)",
        ),
        colorscale=px.colors.sequential.Reds,
        cmin=color_min,
        cmax=color_max,
    )
)

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Div(
        children=[
            html.Div(
                children=[
                    dcc.Graph(id='map', figure=fig_map),
                    dcc.Graph(id='scatterplot', style={'height': '60%'})
                ],
                style={'width': '60%', 'display': 'inline-block', 'padding': '0px'}
            ),
            html.Div(
                children=[
                    dcc.Graph(id='line-graph-1', style={'height': '60%'}),
                    dcc.Graph(id='line-graph-2', style={'height': '60%'})
                ],
                style={'width': '40%', 'display': 'inline-block', 'padding': '0px', 'height': '100%'}
            ),
        ],
        style={'width': '100%', 'display': 'flex', 'height': '700px'}
    ),
    html.Div(
        dcc.Slider(
            id='year-slider',
            min=data['Year'].min(),
            max=data['Year'].max(),
            step=1,
            value=data['Year'].min(),
            marks={year: str(year) for year in range(data['Year'].min(), data['Year'].max() + 1, 5)},
            tooltip={"placement": "bottom", "always_visible": True},
            updatemode='drag'
        ),
        style={'margin-top': '150px', 'margin-left': '5%', 'margin-right': '5%'}
    ),
    dcc.Store(id='selected-countries', data=[])
])


@app.callback(
    Output('selected-countries', 'data'),
    [Input('map', 'clickData')],
    [State('selected-countries', 'data')]
)
def update_selected_countries(click_data, selected_countries):
    if selected_countries is None:
        selected_countries = []
    
    if click_data:
        selected_country = click_data['points'][0]['hovertext']
        
        if selected_country in selected_countries:
            selected_countries.remove(selected_country)
        else:
            selected_countries.append(selected_country)
    
    return selected_countries


@app.callback(
    [Output('map', 'figure'),
     Output('line-graph-1', 'figure'),
     Output('line-graph-2', 'figure'),
     Output('scatterplot', 'figure')],
    [Input('year-slider', 'value'),
     Input('selected-countries', 'data')]
)
def update_content(year, selected_countries):
    year_data = data[data['Year'] == year]

    fig_map_year = px.choropleth(
        year_data,
        locations="Country",
        locationmode="country names",
        color="CO2_per_GDP",
        hover_name="Country",
        color_continuous_scale=px.colors.sequential.Reds,
        labels={"CO2_per_GDP": "CO2 per GDP (kg/$)"},
    )
    fig_map_year.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type="equirectangular",
        ),
        coloraxis=dict(
            colorbar=dict(
                tickvals=[color_min, color_mid, color_max],
                ticktext=[f"{color_min:.2f}", f"{color_mid:.2f}", f"{color_max:.2f}"],
                title="CO2 per GDP (kg/$)",
            ),
            colorscale=px.colors.sequential.Reds,
            cmin=color_min,
            cmax=color_max,
        )
    )
    fig_bubbles = px.scatter_geo(
        year_data,
        locations="Country",
        locationmode="country names",
        size="Oil production (TWh)",
        hover_name="Country",
        size_max=50,
        labels={"Oil production (TWh)": "Oil Production (TWh)"},
    )
    fig_bubbles.update_traces(marker=dict(color="black"))
    for trace in fig_bubbles.data:
        fig_map_year.add_trace(trace)

    fig_line_1 = go.Figure()
    fig_line_2 = go.Figure()

    for country in selected_countries:
        country_data = data[data['Country'] == country]

        fig_line_1.add_trace(go.Scatter(
            x=country_data['Year'],
            y=country_data['GDP per capita, PPP (constant 2017 international $)'],
            mode='lines',
            name=country
        ))

        fig_line_2.add_trace(go.Scatter(
            x=country_data['Year'],
            y=country_data['Annual CO₂ emissions'] / country_data['Population - Sex: all - Age: all - Variant: estimates'],
            mode='lines',
            name=country
        ))

    y_max_line_1 = max([max(fig_line_1.data[i].y) for i in range(len(fig_line_1.data))]) * 1.1 if fig_line_1.data else 1
    y_max_line_2 = max([max(fig_line_2.data[i].y) for i in range(len(fig_line_2.data))]) * 1.1 if fig_line_2.data else 1

    moving_line_1 = max([max(fig_line_1.data[0].y), 1])
    moving_line_2 = max([max(fig_line_2.data[0].y), 1])

    fig_line_1.add_shape(
        type='line',
        x0=year,
        x1=year,
        y0=0, 
        y1=moving_line_1, 
        line=dict(color='grey')
    )
    fig_line_2.add_shape(
        type='line',
        x0=year,
        x1=year,
        y0=0, 
        y1=moving_line_2, 
        line=dict(color='grey')
    )

    fig_line_1.update_layout(
        title="GDP per Capita Over Time",
        xaxis_title="Year",
        yaxis_title="GDP per Capita (PPP)",
        plot_bgcolor='white',
        xaxis=dict(showgrid=False, gridcolor='lightgrey', zeroline=True, zerolinecolor='lightgrey'),
        yaxis=dict(showgrid=True, gridcolor='lightgrey', zeroline=True, zerolinecolor='lightgrey', range=[0, y_max_line_1])
    )

    fig_line_2.update_layout(
        title="CO2 Emissions per Capita Over Time",
        xaxis_title="Year",
        yaxis_title="CO2 Emissions per Capita (tonnes)",
        plot_bgcolor='white',
        xaxis=dict(showgrid=False, gridcolor='lightgrey', zeroline=True, zerolinecolor='lightgrey'),
        yaxis=dict(showgrid=True, gridcolor='lightgrey', zeroline=True, zerolinecolor='lightgrey', range=[0, y_max_line_2])
    )
    
    fig_scatter = go.Figure()

    if selected_countries:
        for country in selected_countries:
            country_data = year_data[year_data['Country'] == country]

            fig_scatter.add_trace(go.Scatter(
                x=country_data['GDP per capita, PPP (constant 2017 international $)'],
                y=country_data['Annual CO₂ emissions'] / country_data['Population - Sex: all - Age: all - Variant: estimates'],
                mode='markers',
                name=country,
                marker=dict(
                    size=country_data['Population - Sex: all - Age: all - Variant: estimates'] / 10000000
                )
            ))

        selected_data = data[data['Country'].isin(selected_countries)]
        
        x_min = selected_data['GDP per capita, PPP (constant 2017 international $)'].min()
        x_max = selected_data['GDP per capita, PPP (constant 2017 international $)'].max()
        
        y_min = (selected_data['Annual CO₂ emissions'] / selected_data['Population - Sex: all - Age: all - Variant: estimates']).min()
        y_max = (selected_data['Annual CO₂ emissions'] / selected_data['Population - Sex: all - Age: all - Variant: estimates']).max()

        fig_scatter.update_layout(
            title="CO2 per GDP vs GDP per Capita",
            xaxis_title="GDP per Capita (PPP)",
            yaxis_title="CO2 per GDP (kg/$)",
            plot_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='lightgrey', zeroline=True, zerolinecolor='lightgrey', range=[0, x_max+10000]),
            yaxis=dict(showgrid=True, gridcolor='lightgrey', zeroline=True, zerolinecolor='lightgrey', range=[0, y_max+2])
        )

    return fig_map_year, fig_line_1, fig_line_2, fig_scatter



if __name__ == '__main__':
    app.run_server(debug=True)
