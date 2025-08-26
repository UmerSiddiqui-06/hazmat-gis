import streamlit as st
from components.custom_warnings import custom_warning
from db import sqlpy

@st.cache_resource
def get_database_connection():
    return sqlpy.sqlpy()

conn = get_database_connection()

# Check if connection worked
if not conn or not conn.cursor:
    st.error("🚫 Database is temporarily unavailable.")
    if st.button("🔄 Retry"):
        st.cache_resource.clear()
        st.rerun()
    st.stop()
st.set_page_config(
    page_title="HazMat GIS", page_icon="assets/logo.png", initial_sidebar_state="auto")
def pending_page():
    columns = st.columns((2, 6, 2))
    with columns[1]:
        with st.container(border=True):
            st.subheader("Please Wait ⏳")
            custom_warning("Your request has not been accepted yet.")
            if st.button("Back to Login Page"):
                st.switch_page("pages/login_page.py")
pending_page()
