import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import time
import pandas as pd
import os
from pages.db_path import db_path
import utitlity

@st.cache_resource
def get_database_connection():
    return utitlity.sqlpy()

conn = get_database_connection()

# Check if connection worked
if not conn or not conn.cursor:
    st.error("🚫 Database is temporarily unavailable.")
    if st.button("🔄 Retry"):
        st.cache_resource.clear()
        st.rerun()
    st.stop()
st.set_page_config(
    page_title="HazMat GIS", page_icon="logo1.png", initial_sidebar_state="collapsed",layout="wide")
from streamlit_cookies_manager import EncryptedCookieManager
cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()
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
PATH = db_path()
def render_aggrid(df_display,filename="temp"):
    if st.button("Go Back"):
        st.session_state.page = "admin_panel"
        cookies["page"] = "admin_panel"
        cookies.save()
        st.switch_page("pages/admin_panel.py")
    df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.strftime('%Y-%m-%d')
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

    gb.configure_column("Coordinates")

    gb.configure_selection("single", use_checkbox=True)

    gb.configure_default_column(editable=True)
    # gb.configure_default_column(flex=1)
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
    gb.configure_default_column(
    flex=1,
    minWidth=100,
    maxWidth=500000,
    resizable=True,
)
    grid_options = gb.build()

    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        updateMode=GridUpdateMode.MODEL_CHANGED,
        allow_unsafe_jscode=True,
        height=800,
        theme="streamlit",
        fit_columns_on_grid_load=False,
    )

    if grid_response['data'] is not None:
        updated_df = pd.DataFrame(grid_response['data'])
        original_data = df_display.reset_index(drop=True)
        updated_data = updated_df.reset_index(drop=True)
        if not updated_data.equals(original_data): 
            if st.button("Save Changes"):
                
                # Update only the modified rows and cells
                for index, row in updated_data.iterrows():
                    if not row.equals(original_data.loc[index]):  # Check if the row has changed
                        for col in updated_data.columns:
                            if row[col] != original_data.loc[index, col]:  # Check specific cell changes
                                # Find the corresponding index in the full_data DataFrame
                                full_index = full_data.index[original_data.index[index]]
                                full_data.loc[full_index, col] = row[col]
                
                # Save back the updated Excel file
                full_data.to_excel(f"data/{filename}", index=False)
                st.success("Data saved to Excel successfully!")
                df_display = updated_df
                time.sleep(1)
                st.rerun()

    return grid_response.get("selected_rows", [])
@st.cache_data
def load_excel_files():
    excel_files = {}
    for file_name in os.listdir(f"{PATH}"):
        if file_name.endswith((".xlsx", ".xls")):
            file_path = os.path.join(f"{PATH}", file_name)
            excel_files[file_name] = pd.read_excel(file_path)
    return excel_files
st.session_state.user_type = cookies.get("user_type")
if "user_type" in st.session_state and st.session_state.user_type=="admin":
    st.session_state.filename = cookies.get("filename")
    excel_files = load_excel_files()
    st.session_state.selected_file = excel_files[st.session_state.filename]
    
    render_aggrid(st.session_state.selected_file,st.session_state.filename)
else:
    st.switch_page("pages/login.py")