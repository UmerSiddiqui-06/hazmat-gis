import streamlit as st
from db import sqlpy
import re
from components.custom_warnings import custom_warning
# Cache database connection
@st.cache_resource
def get_database_connection():
    return sqlpy.sqlpy()

# Initialize cookies outside cache
from streamlit_cookies_manager import EncryptedCookieManager
cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()

# Get database connection
conn = get_database_connection()
if not conn or not conn.cursor:
    st.error("🚫 Database is temporarily unavailable.")
    if st.button("🔄 Retry", key="retry_connection"):
        st.cache_resource.clear()
        st.experimental_rerun()
    st.stop()
st.set_page_config(
    page_title="HazMat GIS", page_icon="assets/logo.png", initial_sidebar_state="auto"
)

def valid_password(password):
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
    )

def change_password(email):
    # Layout for title
    col1, col2, col3 = st.columns([1, 8, 1])
    with col2:
        st.subheader("Change Password")
        with st.form(key="change_password_form", border=True):
            current_password = st.text_input("Current Password", type="password", key="current_password")
            new_password = st.text_input("New Password", type="password", key="new_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            col1, col2, col3 = st.columns([2.7, 4, 1.5])
            with col1:
                update_password = st.form_submit_button("Update Password")
            with col3:
                go_back = st.form_submit_button("Go Back")
            
            if update_password:
                is_present = conn.check_login(email, current_password)
                if not is_present:
                    custom_warning("Wrong Password. Try Again")
                elif new_password != confirm_password:
                    custom_warning("Passwords do not match!")
                elif not valid_password(new_password):
                    custom_warning(
                        "Password must include 1 uppercase, 1 lowercase, 1 number, and be at least 8 characters."
                    )
                else:
                    conn.update_password(email, new_password)
                    st.success("Password updated successfully!")
                    st.session_state.page = "main_display"
                    st.switch_page("pages/main_display.py")

            if go_back:
                st.session_state.logged_in = True
                st.session_state.page = "main_display"
                st.switch_page("pages/main_display.py")

def main():
    # Check login status
    if cookies.get("logged_in") == "True" or ("logged_in" in st.session_state and st.session_state.logged_in):
        st.session_state.logged_in = True
        st.session_state.user_email = cookies.get("user_email")
        if st.session_state.user_email:
            change_password(st.session_state.user_email)
        else:
            st.session_state.page = "Login"
            st.switch_page("pages/login_page.py")
    else:
        st.session_state.page = "Login"
        st.switch_page("pages/login_page.py")

if __name__ == "__main__":
    main()