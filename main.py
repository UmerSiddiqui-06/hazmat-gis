import streamlit as st
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
    page_title="HazMat GIS", page_icon="assets/logo.png", initial_sidebar_state="auto"
)
hide_sidebar_css = """
    <style>
        ul[data-testid="stSidebarNavItems"] {display: none !important;} /* Hide sidebar page links */
        div[data-testid="stSidebarNavSeparator"] {display: none !important;} /* Hide separator */
    </style>
"""
st.markdown(hide_sidebar_css, unsafe_allow_html=True)


# Hide Streamlit warnings using markdown and CSS
hide_warning = """
    <style>
        [data-testid="stAlertContainer"] {
            display: none !important;
        }
    </style>
"""
st.markdown(hide_warning, unsafe_allow_html=True)

from streamlit_cookies_manager import EncryptedCookieManager
import warnings


cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()

warnings.filterwarnings("ignore")

def main():

    if "page" not in st.session_state:
        st.session_state.page = "Login"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_type" not in st.session_state:
        st.session_state.user_type = None
    if "code" not in st.session_state:
        st.session_state.code = None
    if "reg_email" not in st.session_state:
        st.session_state.reg_email = None
    if "reg_password" not in st.session_state:
        st.session_state.reg_password = None
    if "selected_tab" not in st.session_state:
        st.session_state.selected_tab = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "go_to_page" not in st.session_state:
        st.session_state.go_to_page = False
    if "admin_data" not in st.session_state:
        st.session_state.admin_data = False
    if st.session_state.go_to_page:
        st.switch_page("pages/data.py")
    if st.session_state.admin_data:
        st.switch_page("pages/admin_data.py")
    if st.session_state.page == "Forget_Password":
        st.switch_page("pages/forget_password.py")

    elif st.session_state.page == "change_password":
        st.switch_page("pages/change_password.py")
        # change_password(st.session_state.user_email)

    elif st.session_state.page == "code_verification":
        st.switch_page("pages/code_verification.py")
        # code_verification(
        #     st.session_state.code,
        #     st.session_state.reg_email,
        #     st.session_state.reg_password,
        # )

    elif st.session_state.page == "Rejected":
        st.switch_page("pages/rejected_page.py")

    elif st.session_state.page == "Pending":
        st.switch_page("pages/pending_page.py")

    elif (
        st.session_state.logged_in == True
        and st.session_state.user_email
        and st.session_state.page not in ["change_password", "admin_panel"]
    ):
        st.switch_page("pages/main_display.py")
    else:
        if cookies.get("logged_in") == "True":
            st.session_state.logged_in = True
            st.session_state.page = cookies.get("page")
        else:
            st.session_state.logged_in = False

        if not st.session_state.logged_in:
            if st.session_state.page == "Login":
                st.switch_page("pages/login_page.py")
            if st.session_state.page == "Register":
                st.switch_page("pages/register_page.py")
        else:
            if st.session_state.page == "admin_panel":
                st.switch_page("pages/admin_panel.py")
            else:
                if cookies.get("user_type") == "admin":
                    st.session_state.user_type = "admin"
                elif cookies.get("user_type") == "user":
                    st.session_state.user_type = "user"
                st.session_state.user_email = cookies.get("user_email", None)
                if st.session_state.user_email == "False":
                    st.session_state.user_email = None
                st.switch_page("pages/main_display.py")


if __name__ == "__main__":
    main()
