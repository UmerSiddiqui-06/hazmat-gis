import streamlit as st
from custom_warnings import custom_error
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
    page_title="HazMat GIS", page_icon="logo1.png", initial_sidebar_state="auto")
def rejected_page():
    columns = st.columns((2, 6, 2))
    with columns[1]:
        with st.container(border=True):
            st.subheader("Sorry to Say 😔")
            custom_error("Your request was not accepted.")
            if st.button("Back to Login Page"):
                st.switch_page("pages/login_page.py")
rejected_page()
