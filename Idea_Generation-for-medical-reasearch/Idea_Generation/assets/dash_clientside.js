// assets/dash_clientside.js

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        make_api_call: function(query_data) {
            if (!query_data || !query_data.query) {
                // Return null or an empty object if no valid query data
                return null;
            }

            const userQuery = query_data.query;
            const fastapiEndpoint = 'http://127.0.0.1:8001/api/research_summary'; // Ensure this matches your FastAPI URL

            // Return a Promise so Dash knows to wait for this asynchronous operation
            return fetch(fastapiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: userQuery })
            })
            .then(response => {
                if (!response.ok) {
                    // If response is not OK (e.g., 400, 500), try to parse error message
                    return response.json().then(errorData => {
                        const errorMessage = errorData.detail || `HTTP error! status: ${response.status}`;
                        throw new Error(errorMessage);
                    }).catch(() => {
                        // Fallback if errorData is not JSON or not present
                        throw new Error(`HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                // Return the data received from FastAPI to the 'response-store'
                return data;
            })
            .catch(error => {
                console.error('Error fetching from FastAPI:', error);
                // Return an error message to the 'response-store' so the UI can display it
                // Using a 'status' field to indicate error or no_answer, for distinct UI handling
                return { status: "error", summary: `Failed to get response from backend: ${error.message}` };
            });
        }
    }
});