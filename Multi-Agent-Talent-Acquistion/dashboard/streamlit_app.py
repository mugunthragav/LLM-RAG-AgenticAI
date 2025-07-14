import streamlit as st
import requests
import pandas as pd
from io import BytesIO
import zipfile

# FastAPI backend URL
BACKEND_URL = "http://localhost:8000"

# Streamlit app
st.title("Rasa.ai Labs Talent Acquisition")

# Section to upload resumes
st.header("Upload Resumes")
uploaded_files = st.file_uploader("Upload resume files (PDF/DOCX) or a zip file", accept_multiple_files=True, type=['pdf', 'docx', 'zip'])

if st.button("Process Resumes"):
    if not uploaded_files:
        st.error("Please upload at least one file.")
    else:
        with st.spinner("Uploading and processing resumes..."):
            files = []
            for uploaded_file in uploaded_files:
                if uploaded_file.name.endswith('.zip'):
                    # Extract zip file
                    zip_bytes = uploaded_file.read()
                    with zipfile.ZipFile(BytesIO(zip_bytes), 'r') as zip_ref:
                        for file_info in zip_ref.infolist():
                            if file_info.filename.endswith(('.pdf', '.docx')):
                                with zip_ref.open(file_info) as file:
                                    files.append(("files", (file_info.filename, file.read(), 'application/octet-stream')))
                            else:
                                st.warning(f"Skipping unsupported file in zip: {file_info.filename}")
                else:
                    # Handle individual PDF/DOCX files
                    files.append(("files", (uploaded_file.name, uploaded_file.read(), 'application/octet-stream')))

            if not files:
                st.error("No valid resume files (PDF/DOCX) found.")
            else:
                # Send files to FastAPI backend
                try:
                    response = requests.post(f"{BACKEND_URL}/upload-resumes/", files=files)
                    response.raise_for_status()
                    result = response.json()
                    st.success(f"Processing started! Task ID: {result['task_id']}")
                    st.session_state['task_id'] = result['task_id']
                except requests.exceptions.RequestException as e:
                    st.error(f"Error uploading files: {str(e)}")

# Section to view candidate data
st.header("View Processed Candidates")
task_id = st.text_input("Enter Task ID to View Candidates", value=st.session_state.get('task_id', ''))
if st.button("Fetch Candidates"):
    if not task_id:
        st.error("Please enter a Task ID.")
    else:
        with st.spinner("Fetching candidate data..."):
            try:
                response = requests.get(f"{BACKEND_URL}/candidates/", params={"task_id": task_id})
                response.raise_for_status()
                candidates = response.json()
                if candidates:
                    df = pd.DataFrame(candidates)
                    display_columns = [
                        "file_name", "name", "skills", "experience", "passedout_year", "internships", "sex",
                        "classification", "matched_role", "match_score", "score", "email_sent"
                    ]
                    # Filter columns that exist in the DataFrame
                    display_columns = [col for col in display_columns if col in df.columns]
                    display_df = df[display_columns]
                    st.subheader("Processed Candidates")
                    st.dataframe(display_df)
                else:
                    st.info("No candidates found for this Task ID.")
            except requests.exceptions.RequestException as e:
                st.error(f"Error fetching candidates: {str(e)}")

# Section to reset database
st.header("Reset Database")
if st.button("Reset Database"):
    with st.spinner("Resetting database..."):
        try:
            response = requests.post(f"{BACKEND_URL}/reset-database/")
            response.raise_for_status()
            result = response.json()
            st.success(result["message"])
        except requests.exceptions.RequestException as e:
            st.error(f"Error resetting database: {str(e)}")