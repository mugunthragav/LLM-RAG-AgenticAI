window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        make_api_call: async function(queryStoreData) {
            if (!queryStoreData || !queryStoreData.query) {
                return null;
            }

            try {
                const response = await fetch("http://localhost:8001/api/research_summary", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(queryStoreData)
                });

                if (!response.ok) {
                    return { summary: "Error from backend.", status: "error" };
                }

                const data = await response.json();
                return data;
            } catch (error) {
                console.error("API fetch failed:", error);
                return { summary: "Backend not reachable.", status: "error" };
            }
        }
    }
});
