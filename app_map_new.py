import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# [Previous data loading code remains the same until app layout]

app = dash.Dash(__name__)

app.layout = html.Div([
    # Top row with map and scatterplot
    html.Div(
        children=[
            html.Div(
                children=[dcc.Graph(id='map')],
                style={'width': '50%', 'display': 'inline-block', 'padding': '10px'}
            ),
            html.Div(
                children=[dcc.Graph(id='scatterplot')],
                style={'width': '50%', 'display': 'inline-block', 'padding': '10px'}
            ),
        ],
        style={'width': '100%', 'display': 'flex'}
    ),
    # Bottom row with line graphs
    html.Div(
        children=[
            html.Div(
                children=[dcc.Graph(id='line-graph-1')],
                style={'width': '50%', 'display': 'inline-block', 'padding': '10px'}
            ),
            html.Div(
                children=[dcc.Graph(id='line-graph-2')],
                style={'width': '50%', 'display': 'inline-block', 'padding': '10px'}
            ),
        ],
        style={'width': '100%', 'display': 'flex'}
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
        style={'margin-top': '20px', 'margin-left': '5%', 'margin-right': '5%'}
    ),
    dcc.Store(id='selected-countries', data=[])
])

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

    # Update map hover template
    fig_map_year = px.choropleth(
        year_data,
        locations="Country",
        locationmode="country names",
        color="CO2_per_GDP",
        hover_name="Country",
        color_continuous_scale=px.colors.sequential.Reds,
        labels={"CO2_per_GDP": "CO2 per GDP (kg/$)"},
    )
    
    # Add custom hover template
    hover_text = []
    for idx, row in year_data.iterrows():
        hover_text.append(
            f"<b>{row['Country']}</b><br>" +
            f"CO2 per GDP: {row['CO2_per_GDP']:.2f} kg/$<br>" +
            f"Oil Production: {row['Oil production (TWh)']:.1f} TWh<br>"
        )
    
    fig_map_year.update_traces(
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover_text
    )
    
    # Update map layout
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

    # Add oil production bubbles
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

    # Line graphs with averages
    fig_line_1 = go.Figure()
    fig_line_2 = go.Figure()

    # Calculate and add average lines
    avg_gdp = data.groupby('Year')['GDP per capita, PPP (constant 2017 international $)'].mean()
    avg_co2 = data.groupby('Year').apply(
        lambda x: x['Annual CO₂ emissions'].sum() / x['Population - Sex: all - Age: all - Variant: estimates'].sum()
    )

    fig_line_1.add_trace(go.Scatter(
        x=avg_gdp.index,
        y=avg_gdp.values,
        mode='lines',
        name='Global Average',
        line=dict(color='grey', dash='dash')
    ))

    fig_line_2.add_trace(go.Scatter(
        x=avg_co2.index,
        y=avg_co2.values,
        mode='lines',
        name='Global Average',
        line=dict(color='grey', dash='dash')
    ))

    # Add selected countries
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

    # Add Paris Agreement vertical line (2015)
    fig_line_2.add_vline(
        x=2015,
        line_dash="dash",
        line_color="green",
        annotation_text="Paris Agreement",
        annotation_position="top right"
    )

    # Update line graphs layout
    y_max_line_1 = max([max(trace.y) for trace in fig_line_1.data]) * 1.1 if fig_line_1.data else 1
    y_max_line_2 = max([max(trace.y) for trace in fig_line_2.data]) * 1.1 if fig_line_2.data else 1

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

    # Update scatterplot
    fig_scatter = go.Figure()

    if selected_countries:
        selected_data = year_data[year_data['Country'].isin(selected_countries)]
        
        fig_scatter.add_trace(go.Scatter(
            x=selected_data['GDP per capita, PPP (constant 2017 international $)'],
            y=selected_data['Annual CO₂ emissions'] / selected_data['Population - Sex: all - Age: all - Variant: estimates'],
            mode='markers',
            text=selected_data['Country'],
            marker=dict(
                size=selected_data['Population - Sex: all - Age: all - Variant: estimates'] / 10000000,
                sizemin=10,  # Minimum size for better visibility
                sizeref=2.*max(selected_data['Population - Sex: all - Age: all - Variant: estimates'])/10000000/(40.**2),
                sizemode='area'
            ),
            hovertemplate="<b>%{text}</b><br>" +
                         "GDP per Capita: %{x:,.0f}<br>" +
                         "CO2 per Capita: %{y:.2f}<br>" +
                         "<extra></extra>"
        ))

        fig_scatter.update_layout(
            title="CO2 Emissions per Capita vs GDP per Capita",
            xaxis_title="GDP per Capita (PPP)",
            yaxis_title="CO2 Emissions per Capita (tonnes)",
            plot_bgcolor='white',
            xaxis=dict(
                showgrid=True,
                gridcolor='lightgrey',
                zeroline=True,
                zerolinecolor='lightgrey',
                type='log'  # Log scale for better distribution
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='lightgrey',
                zeroline=True,
                zerolinecolor='lightgrey',
                type='log'  # Log scale for better distribution
            )
        )

    return fig_map_year, fig_line_1, fig_line_2, fig_scatter

if __name__ == '__main__':
    app.run_server(debug=True)
