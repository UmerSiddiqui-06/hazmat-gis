import streamlit as st
from db import sqlpy
from streamlit_cookies_manager import EncryptedCookieManager
import warnings
# Cache CSS to avoid re-rendering
@st.cache_data
def get_css():
    return """
    <style>
        ul[data-testid="stSidebarNavItems"], div[data-testid="stSidebarNavSeparator"], [data-testid="stAlertContainer"] {
            display: none !important;
        }
    </style>
    """

# # Cache cookie manager to initialize only once
# @st.cache_resource
def init_cookies():
    return EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")

# Cache database connection
@st.cache_resource
def get_database_connection():
    return sqlpy.sqlpy()

# Apply page config only once
if "page_config_set" not in st.session_state:
    st.set_page_config(page_title="HazMat GIS", page_icon="assets/logo.png", initial_sidebar_state="auto")
    st.session_state.page_config_set = True

# Apply cached CSS
st.markdown(get_css(), unsafe_allow_html=True)

# Initialize cookies and database connection
cookies = init_cookies()
conn = get_database_connection()

# Check if connection worked
if not conn or not conn.cursor:
    st.error("🚫 Database is temporarily unavailable.")
    if st.button("🔄 Retry"):
        st.cache_resource.clear()
        st.experimental_rerun()
    st.stop()

# Suppress warnings
warnings.filterwarnings("ignore")

# Define page routes
PAGE_ROUTES = {
    "Login": "pages/login_page.py",
    "Register": "pages/register_page.py",
    "Forget_Password": "pages/forget_password.py",
    "change_password": "pages/change_password.py",
    "code_verification": "pages/code_verification.py",
    "Rejected": "pages/rejected_page.py",
    "Pending": "pages/pending_page.py",
    "admin_panel": "pages/admin_panel.py",
    "go_to_page": "pages/data.py",
    "admin_data": "pages/admin_data.py",
    "default": "pages/main_display.py"
}

def initialize_session_state():
    """Initialize session state variables with defaults if not set."""
    defaults = {
        "page": "Login",
        "logged_in": False,
        "user_type": None,
        "code": None,
        "reg_email": None,
        "reg_password": None,
        "selected_tab": None,
        "user_email": None,
        "go_to_page": False,
        "admin_data": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def navigate():
    """Handle navigation based on session state and cookies."""
    # Initialize session state
    initialize_session_state()

    # Check cookie-based login
    if cookies.get("logged_in") == "True" and not st.session_state.logged_in:
        st.session_state.logged_in = True
        st.session_state.page = cookies.get("page", "default")
        st.session_state.user_type = cookies.get("user_type")
        st.session_state.user_email = cookies.get("user_email") if cookies.get("user_email") != "False" else None

    # Determine page to navigate to
    if st.session_state.go_to_page:
        target_page = "go_to_page"
    elif st.session_state.admin_data:
        target_page = "admin_data"
    elif st.session_state.page in PAGE_ROUTES:
        target_page = st.session_state.page
    elif st.session_state.logged_in and st.session_state.user_email and st.session_state.page not in ["change_password", "admin_panel"]:
        target_page = "default"
    else:
        target_page = "Login" if not st.session_state.logged_in else "default"
        

    # Navigate to the target page
    st.switch_page(PAGE_ROUTES[target_page])

def main():
    if not cookies.ready():
        st.stop()
    navigate()

if __name__ == "__main__":
    main()