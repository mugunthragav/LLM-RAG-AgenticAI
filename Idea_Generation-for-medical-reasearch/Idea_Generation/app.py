import dash
from dash import dcc, html, Input, Output, State, ClientsideFunction, callback
import dash_bootstrap_components as dbc

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

app.layout = dbc.Container([
    dbc.Row(dbc.Col(html.H1("Clinical Research Idea Chatbot", className="text-center my-4 text-primary"))),

    dbc.Row(dbc.Col(
        dbc.Card([
            dbc.CardHeader(html.H5("Chat History", className="mb-0 text-white")),
            dbc.CardBody(
                id="chat-output",
                style={"height": "60vh", "overflowY": "auto", "backgroundColor": "#e6eff6", "padding": "15px"}
            )
        ], className="mb-3 shadow-lg rounded-3 border-0"),
    )),

    dbc.Row(dbc.Col(
        dbc.InputGroup([
            dbc.Input(id="user-input", type="text", placeholder="Type your research idea...", n_submit=0),
            dbc.Button("Submit", id="submit-button", color="primary", className="ms-2")
        ], className="shadow-sm mb-4 rounded-3")
    )),

    dcc.Store(id='query-store'),
    dcc.Store(id='response-store'),
    dcc.Loading(id="loading-spinner", type="default", children=html.Div(id="loading-text"))
], fluid=True)


@callback(
    Output("query-store", "data"),
    Output("chat-output", "children", allow_duplicate=True),
    Output("user-input", "value"),
    Output("loading-text", "children"),
    Input("submit-button", "n_clicks"),
    Input("user-input", "n_submit"),
    State("user-input", "value"),
    State("chat-output", "children"),
    prevent_initial_call=True
)
def handle_user_input(n_clicks, n_submit, user_message, chat_history_elements):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if not user_message or ("submit-button" not in changed_id and "user-input" not in changed_id):
        return dash.no_update, dash.no_update, "", ""

    if chat_history_elements is None:
        chat_history_elements = []
    elif not isinstance(chat_history_elements, list):
        chat_history_elements = [chat_history_elements]

    chat_history_elements.append(
        dbc.Alert(html.Div([html.Strong("You: "), html.Span(user_message)]),
                  color="secondary", className="mb-2 rounded-pill px-4 py-2")
    )
    return {"query": user_message}, chat_history_elements, "", "Processing your query..."


app.clientside_callback(
    ClientsideFunction(namespace='clientside', function_name='make_api_call'),
    Output('response-store', 'data'),
    Input('query-store', 'data'),
    prevent_initial_call=True
)


@callback(
    Output("chat-output", "children", allow_duplicate=True),
    Output("loading-text", "children", allow_duplicate=True),
    Input("response-store", "data"),
    State("chat-output", "children"),
    prevent_initial_call=True
)
def update_chat_with_bot_response(response_data, chat_history_elements):
    if response_data is None:
        return dash.no_update, dash.no_update

    bot_response = response_data.get("summary", "An unknown error occurred.")
    status = response_data.get("status", "error")

    if chat_history_elements is None:
        chat_history_elements = []
    elif not isinstance(chat_history_elements, list):
        chat_history_elements = [chat_history_elements]

    alert_color = "info" if status == "success" else "warning" if status == "no_answer" else "danger"

    chat_history_elements.append(
        dbc.Alert(html.Div([html.Strong("Bot: "), html.Span(bot_response)]),
                  color=alert_color, className="mb-2 rounded-pill px-4 py-2")
    )
    return chat_history_elements, ""


if __name__ == "__main__":
    app.run(debug=True, port=8051)
