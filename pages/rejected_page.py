import streamlit as st
from components.custom_warnings import custom_error
from db import sqlpy
st.set_page_config(
    page_title="HazMat GIS", page_icon="assets/logo.png", initial_sidebar_state="auto")

# Cache database connection
@st.cache_resource
def get_database_connection():
    return sqlpy.sqlpy()

# Get database connection
conn = get_database_connection()
if not conn or not conn.cursor:
    st.error("🚫 Database is temporarily unavailable.")
    if st.button("🔄 Retry", key="retry_connection"):
        st.cache_resource.clear()
        st.experimental_rerun()
    st.stop()

def rejected_page():
    # Simplified layout
    col1, col2, col3 = st.columns([2, 6, 2])
    with col2:
        with st.container(border=True):
            st.subheader("Sorry to Say 😔")
            custom_error("Your request was not accepted.")
            if st.button("Back to Login Page", key="back_to_login"):
                st.session_state.page = "Login"
                st.switch_page("pages/login_page.py")

if __name__ == "__main__":
    rejected_page()