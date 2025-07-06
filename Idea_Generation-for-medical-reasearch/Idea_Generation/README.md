# Clinical Research Idea Chatbot

This project consists of a Dash frontend and a FastAPI backend, designed to help generate clinical research ideas using the FutureHouse Platform API.

## Installation and Setup

Follow these steps to set up and run the project locally.

### Prerequisites

* **Python 3.11 or higher** (Python 3.10 and earlier are not supported by `futurehouse-client`).
    You can download Python from [python.org](https://www.python.org/downloads/). Ensure it's added to your system's PATH during installation.

### Steps

1.  **Clone the Repository:**
    ```bash
    Extract the zip file 
    cd Idea_Generation # Or the name of your project directory
    ```

2.  **Create a Virtual Environment with Python 3.11+:**
    It's crucial to use Python 3.11 or 3.12 for this project. Replace `venv` with your preferred virtual environment name (e.g., `ideavenv`).

    ```bash
    # On Windows, using 'py -3.11' if it's in your PATH
    python -m venv venv

    # Or explicitly provide the path to your Python 3.11/3.12 executable
    # "C:\Path\To\Python311\python.exe" -m venv venv
    ```

3.  **Activate the Virtual Environment:**

    * **Windows:**
        ```bash
        venv\Scripts\activate
        ```
    * **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```
    (Your prompt should now show `(venv)` or `(ideavenv)`).

4.  **Install `uv` (Recommended Installer):**
    `uv` is a very fast Python package installer and resolver.

    ```bash
    pip install uv
    ```

5. **Install Project Dependencies: `futurehouse-client` using `uv**

```bash

    uv pip install futurehouse-client    
```
5. **Install Project Dependencies:**

    ```bash
     pip install -r requirements.txt
    ```

6.  **Create and Configure `.env` File:**
    You need to obtain an API key for the FutureHouse Platform. Create a file named `.env` in the root directory of your project (`D:\Idea_Generation\.env`) and add your API key:


  You need an API key to access the FutureHouse Platform API.

  Go to the FutureHouse Platform website (check your documentation for the exact URL).
  Log in or sign up.
  Navigate to your profile or API settings page.
  Generate and obtain your API key.

    ```
    FUTUREHOUSE_API_KEY=your_futurehouse_api_key_here
    ```
    **Replace `your_futurehouse_api_key_here` with your actual API key.**

7.  **Ensure Correct Backend/Frontend Port Configuration:**
    * **FastAPI Backend Port:** The `fastapi_backend.py` file is configured to run on port `8001`.
    * **Dash Frontend Port:** The `app.py` file is configured to run on port `8051`.
    * **Client-side JavaScript:** Ensure your `assets/dash_clientside.js` file correctly points to the FastAPI backend's endpoint:
        ```javascript
        const fastapiEndpoint = '[http://127.0.0.1:8001/api/research_summary](http://127.0.0.1:8001/api/research_summary)';
        ```
        (Make sure there are no `[]` or `()` around the URL in the JavaScript file!)

### Running the Applications

You will need to run the FastAPI backend and the Dash frontend in separate terminal windows.

1.  **Start the FastAPI Backend:**
    In one terminal (with your virtual environment activated):

    ```bash
    set PYTHONUTF8=1	
    uvicorn fastapi_backend:app --reload --port 8001
    ```
    You should see output indicating the server is running on `http://127.0.0.1:8001`. You can verify it by visiting `http://127.0.0.1:8001/docs` in your browser.

2.  **Start the Dash Frontend:**
    In a separate terminal (with your virtual environment activated):

    ```bash
    python app.py
    ```
    You should see output indicating the Dash app is running, typically on `http://127.0.0.1:8051`.

Now, open your web browser and navigate to the address provided by the Dash app (e.g., `http://127.0.0.1:8051`) to interact with the chatbot.