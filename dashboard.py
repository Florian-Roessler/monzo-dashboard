# -*- coding: utf-8 -*-
import dash
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
import dash_table_experiments as dte
import pandas as pd
import numpy as np
import os

app = dash.Dash(__name__)

# dataframe loading
df = pd.read_csv("monzo_processed.csv", index_col=0)
df.index = pd.to_datetime(df.index)
df_not_monzo = df[df['category'] != "monzo"]
cols = ['created', 'amount', 'category', 'description']


app.layout = html.Div([
    html.Div([
        html.Div([
            dcc.DatePickerRange(
                id='date-picker-range',
                start_date=df.index[0],
                min_date_allowed=df.index[0],
                end_date=df.index[-1],
                max_date_allowed=df.index[-1],
                calendar_orientation='vertical',
            ),
        ], style={'width': '49%', 'display': 'inline-block'}),

        html.Div([
            dcc.RangeSlider(
                id='amount-range'
            ),
        ], style={'width': '49%', 'float': 'right', 'display': 'inline-block'})
    ], style={
        'borderBottom': 'thin lightgrey solid',
        'backgroundColor': 'rgb(250, 250, 250)',
        'padding': '10px 5px'
    }),

    html.Div([
        dcc.Graph(
            id='pie'
        )
    ], style={'width': '49%', 'display': 'inline-block', 'padding': '0 20'}),
    html.Div([
        dcc.Graph(
                    id='map-graph',
                )
    ], style={'display': 'inline-block', 'width': '49%'}),

    html.Div([
        dte.DataTable(
            rows=df_not_monzo.reset_index()[cols].to_dict('records'),

            row_selectable=True,
            filterable=True,
            sortable=True,
            selected_row_indices=[],
            id='datatable-monzo'
            )
    ])
])


@app.callback(Output('amount-range', 'min'),
              [Input('date-picker-range', 'start_date'),
              Input('date-picker-range', 'end_date')])
def set_low(start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    mask = (df_not_monzo.index > start_date) & (df_not_monzo.index <= end_date)
    return np.floor(df_not_monzo.loc[mask, 'amount'].min() / 50) * 50


@app.callback(Output('amount-range', 'max'),
              [Input('date-picker-range', 'start_date'),
              Input('date-picker-range', 'end_date')])
def set_high(start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    mask = (df_not_monzo.index > start_date) & (df_not_monzo.index <= end_date)
    return np.ceil(df_not_monzo.loc[mask, 'amount'].max() / 50) * 50


@app.callback(Output('amount-range', 'marks'),
              [Input('date-picker-range', 'start_date'),
              Input('date-picker-range', 'end_date')])
def set_marks(start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    mask = (df_not_monzo.index > start_date) & (df_not_monzo.index <= end_date)
    low = np.floor(df_not_monzo.loc[mask, 'amount'].min() / 50) * 50
    high = np.ceil(df_not_monzo.loc[mask, 'amount'].max() / 50) * 50
    return {int(i): '%s' % int(i) for i in np.arange(low, high+1, 50)}


@app.callback(Output('amount-range', 'value'),
              [Input('date-picker-range', 'start_date'),
              Input('date-picker-range', 'end_date')])
def set_value(start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    mask = (df_not_monzo.index > start_date) & (df_not_monzo.index <= end_date)
    low = np.floor(df_not_monzo.loc[mask, 'amount'].min() / 50) * 50
    high = np.ceil(df_not_monzo.loc[mask, 'amount'].max() / 50) * 50
    return [low, high]


@app.callback(Output('datatable-monzo', 'rows'),
              [Input('amount-range', 'value'),
               Input('date-picker-range', 'start_date'),
               Input('date-picker-range', 'end_date')])
def update_table(inp1, start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    mask = (df_not_monzo.index > start_date) & (df_not_monzo.index <= end_date)
    temp = df_not_monzo.loc[mask]
    temp = temp[(temp['amount'] > inp1[0]) & (temp['amount'] < inp1[1])]
    return temp.reset_index()[cols].to_dict('records')


@app.callback(Output('pie', 'figure'),
              [Input('amount-range', 'value'),
               Input('date-picker-range', 'start_date'),
               Input('date-picker-range', 'end_date'),
               Input('map-graph', 'selectedData')])
def update_output(inp1, start_date, end_date, selected_points):

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    mask = (df_not_monzo.index > start_date) & (df_not_monzo.index <= end_date)
    temp = df_not_monzo.loc[mask]
    if selected_points:
        # TODO: Fix rounding error for selection
        avail_lon = [x['lon'] for x in selected_points['points']]
        avail_lat = [x['lat'] for x in selected_points['points']]
        loc_mask = temp[temp['long'].isin(avail_lon)]
        loc_mask = temp[temp['lat'].isin(avail_lat)]

    sum_by_cat = np.abs(temp[(temp['amount'] > inp1[0])
                             & (temp['amount'] < inp1[1])]
                        .groupby("category")['amount'].sum()).to_dict()
    fig = {
      "data": [
        {
          "values": [np.floor(i) for i in sum_by_cat.values()],
          "labels": list(sum_by_cat.keys()),
          "hoverinfo":"label+value",
          "hole": .4,
          "type": "pie"
        }],
      "layout": {
            "title": "Expenses by Category",
            "annotations": [
                {
                    "font": {
                        "size": 16
                    },
                    "showarrow": False,
                    "text": "Expenses"
                }
            ]
        }
    }
    return fig


@app.callback(Output('map-graph', 'figure'),
              [Input('amount-range', 'value'),
               Input('date-picker-range', 'start_date'),
               Input('date-picker-range', 'end_date')])
def update_map_graph(inp1, start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    mask = (df_not_monzo.index > start_date) & (df_not_monzo.index <= end_date)
    temp = df_not_monzo.loc[mask]
    temp = temp[(temp['amount'] > inp1[0]) & (temp['amount'] < inp1[1])]

    for_viz = temp.loc[df["long"].notnull(), ["lat", "long", "description", "amount"]]
    for_viz["lat-long"] = for_viz["lat"].map(str) + for_viz["long"].map(str)
    grouped = for_viz.groupby("lat-long").sum().reset_index()
    for_viz = for_viz.merge(grouped, left_on="lat-long", right_on="lat-long")
    for_viz_no_dups = for_viz.drop_duplicates("lat-long")

    fig = {
        'data': [{
            'lat': for_viz_no_dups['lat'],
            'lon': for_viz_no_dups['long_x'],
            'mode': 'markers',
            'hoverinfo': 'text',
            'text': ["%s: %s" % (x, int(y)) for x, y in
                     for_viz_no_dups[['description', 'amount_y']].values],
            'type': 'scattermapbox'
        }],
        'layout': {
            'mapbox': {
                'accesstoken': (os.environ['MAPBOXAPI']),
                'center': {
                    'lat': 52,
                    'lon': -0.44},
                'zoom': '5'
            },
            'margin': {
                'l': 0, 'r': 0, 'b': 0, 't': 0
            },
        }
    }
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
