import os
import streamlit as st
import pandas as pd
from rapidfuzz import process
import ast
from streamlit_cookies_manager import EncryptedCookieManager
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import JsCode
import utitlity
from openai import OpenAI
from docx import Document
from io import BytesIO
import streamlit as st

# Set sidebar state to collapsed
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
hide_sidebar_css = """
    <style>
        ul[data-testid="stSidebarNavItems"] {display: none !important;} /* Hide sidebar page links */
        div[data-testid="stSidebarNavSeparator"] {display: none !important;} /* Hide separator */
    </style>
"""
st.markdown(hide_sidebar_css, unsafe_allow_html=True)
st.markdown("""
    <style>
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)
st.markdown("""
    <style>
        .block-container {
            margin: 0px 15px !important; /* 10px top & bottom, 15px left & right */
            padding: 10px !important;
        }
    </style>
""", unsafe_allow_html=True)


st.markdown("""
    <style>
        /* Hide the entire sidebar */
        section[data-testid="stSidebar"] {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)
st.markdown("""
    <style>
        .st-emotion-cache-1rliy6u {
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.switch_page("hazMat GIS.py")
if st.session_state.logged_in:
    cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
    if not cookies.ready():
        st.stop()
    conn = utitlity.sqlpy()

    if st.button("Go Back"):
        st.session_state.go_to_page = False
        st.switch_page("hazMat GIS.py")
    def load_country_list(file_path):
        """Load the country list from a file."""
        with open(file_path, 'r') as file:
            countries = [line.strip() for line in file.readlines()]
        return countries

    @st.cache_data
    def standardize_country_column(column):
        country_list = load_country_list("worldcountries.txt")
        country_variations = {
            "UAE": "United Arab Emirates",
            "United Arab Emirates": "United Arab Emirates",
            "USA": "United States",
            "United States": "United States",
            "United States of America": "United States",
            "UK": "United Kingdom",
            "United Kingdom": "United Kingdom",
            "Russia": "Russia",
            "Russian Federation": "Russia",
            "South Korea": "South Korea",
            "Republic of Korea": "South Korea"
        }
        def standardize_name(name):
            # Check for known variations
            if name in country_variations:
                return country_variations[name]
            # Fuzzy match if not in variations
            match = process.extractOne(name, country_list)
            return match[0] if match[1] > 80 else 'Unknown'


        # Apply the standardization function
        return column.apply(standardize_name)

    def load_data():
        try:
            dataframes = []
            
            # Iterate over all files in the folder
            for file_name in os.listdir("/var/data"):
                # Build the full file path
                file_path = os.path.join("/var/data", file_name)
                
                # Check if the file is an Excel file
                if file_name.endswith(('.xlsx', '.xls')):
                    # Read the Excel file into a DataFrame and append to the list
                    df = pd.read_excel(file_path)
                    dataframes.append(df)
            if len(dataframes) == 0:
                return None
            # Concatenate all DataFrames into a single DataFrame
            data = pd.concat(dataframes, ignore_index=True)
            data["Date"] = pd.to_datetime(data["Date"]).dt.strftime('%Y-%m-%d')
            data['Country'] = standardize_country_column(data['Country'])
            data["Coordinates"] = data["Coordinates"].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else None)
            data = data.drop_duplicates()
        except Exception as e:
            st.error(f"Error Occured while loading Data: {e}")
            st.stop()
        return data
    @st.cache_data
    def get_gpt_status_from_conn():
        return conn.get_gpt_status()
    def summarize():
        cookies["summarize"] = "True"
        # cookies.save()

    @st.cache_data
    def get_user_gpt_status_from_conn(user_email):
        return conn.get_user_gpt_status(user_email)

    @st.cache_data
    def get_gpt_limit_check_from_conn(user_email):
        return conn.get_gpt_limit_check(user_email)

    def chatgpt_explain(prompt):
        gpt_api_key = os.getenv("gpt_api_key")
        if not gpt_api_key:
            raise ValueError("GPT API key is not set in the environment")
        client = OpenAI(
            api_key=gpt_api_key
        )
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt},
                ],
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"An Error Occured while summarizing: {e}"
    def create_word_file(content):
        doc = Document()
        doc.add_paragraph(content)  # Add the response text as a paragraph
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)  # Reset the buffer position to the start
        return buffer

    @st.fragment
    def render_aggrid_data(df_display, user_type, user_email):
        full_data = df_display.copy()
        gb = GridOptionsBuilder.from_dataframe(df_display, editable=True)
        gb.configure_column("Category")
        gb.configure_column("Title")
        gb.configure_column("Country")
        gb.configure_column("City")
        gb.configure_column("Date")
        gb.configure_column("Impact")
        gb.configure_column("Casuality")
        gb.configure_column("Injuries")
        gb.configure_column("Full Link")
        gb.configure_column("Severity")
        gb.configure_default_column(
            editable=False, groupable=True,flex=1
        )
        if user_type == "admin":
            gb.configure_column("Coordinates")

        gb.configure_selection("single", use_checkbox=True)
        
        if user_type == "admin":
            gb.configure_default_column(editable=True)

        gb.configure_column(
            "Full Link",
            headerName="Link",
            cellRenderer=JsCode(
                """
                class UrlCellRenderer {
                init(params) {
                    this.eGui = document.createElement('a');
                    this.eGui.innerText = 'Link';
                    this.eGui.setAttribute('href', params.value);
                    this.eGui.setAttribute('style', "text-decoration:none");
                    this.eGui.setAttribute('target', "_blank");
                }
                getGui() {
                    return this.eGui;
                }
                }
            """
            ),
        )
        
        grid_options = gb.build()

        grid_response = AgGrid(
            df_display,
            gridOptions=grid_options,
            updateMode=GridUpdateMode.MODEL_CHANGED,
            allow_unsafe_jscode=True,
            height=800,
            theme="streamlit",
            fit_columns_on_grid_load=True,
        )
        
        selected_row = grid_response.get("selected_rows", [])
        chatgpt_status = get_gpt_status_from_conn()
        if user_type!="admin":
            user_gpt_status = get_user_gpt_status_from_conn(user_email)
            gpt_limit_check = get_gpt_limit_check_from_conn(user_email)
        
        if chatgpt_status and (user_type == "admin" or (user_gpt_status and gpt_limit_check)):
            if "summarize" not in st.session_state:
                st.session_state.summarize = None
                cookies["summarize"] = "False"

            if cookies.get("summarize") == "True":
                if selected_row is not None:
                    with st.container(border=True):
                        st.subheader("Summary")
                        url = selected_row["Full Link"][0]
                        title = selected_row["Title"][0]

                        # Placeholder for loader
                        loader_placeholder = st.empty()

                        with loader_placeholder:
                            # Display loading spinner
                            with st.spinner("Generating response, please wait..."):
                                response = conn.get_gpt_response(url)
                                
                                if not response:
                                    if cookies.get(title) is not None:
                                        response = cookies.get(title)
                                    else:
                                        prompt = f"URL: {url} Title: {title} "
                                        with open("prompt.txt", "r") as file:
                                            content = file.read()
                                        prompt = prompt + content
                                        response = chatgpt_explain(prompt)
                                        cookies[title] = response
                                        conn.add_gpt_response(url, response)

                                if user_type != "admin":
                                    conn.increase_gpt(user_email)
                                    conn.add_gpt_history(user_email, url, title)
                            
                        # Clear loader and display response
                        loader_placeholder.empty()
                        word_file = create_word_file(response)
                        st.download_button(
                            label="Download Response",
                            data=word_file,  # File content as a BytesIO object
                            file_name="response.docx",  # File name with .docx extension
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # MIME type for Word files
                        )
                        st.write(response)

                    cookies["summarize"] = "False"
            else:
                if selected_row is not None:
                    st.button("Summarize",on_click=summarize)

    data = load_data()
    if data is not None:
        with st.container():
            render_aggrid_data(data,st.session_state.user_type,st.session_state.user_email)
else:
    st.warning("Please login to see data")