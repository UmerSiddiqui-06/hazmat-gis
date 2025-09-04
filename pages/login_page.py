import streamlit as st
from db import sqlpy
from components.custom_warnings import custom_error, custom_warning

st.set_page_config(
    page_title="HazMat GIS", page_icon="assets/logo.png", initial_sidebar_state="auto")

# Cache database connection
@st.cache_resource
def get_database_connection():
    """Single cached database connection for the entire app"""
    return sqlpy.sqlpy()

# Cache toast CSS
@st.cache_data
def get_toast_css():
    return """
    <style>
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 15px 25px;
            background-color: #f8d7da;
            color: #842029;
            border: 1px solid #f5c2c7;
            border-radius: 8px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            opacity: 0;
            animation: fadein 2s forwards;
        }
        @keyframes fadein {
            0% { opacity: 0; transform: translate(-50%, 20px); }
            100% { opacity: 1; transform: translate(-50%, 0); }
        }
    </style>
    """

def show_toast(message, duration=2):
    st.markdown(get_toast_css(), unsafe_allow_html=True)
    st.markdown(f'<div class="toast">⚠️ {message}</div>', unsafe_allow_html=True)

# Initialize cookies outside cache
from streamlit_cookies_manager import EncryptedCookieManager
cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()

# Get database connection
conn = get_database_connection()
if not conn or not conn.cursor:
    st.error("🚫 Database is temporarily unavailable due to connection limits.")
    st.info("💡 This usually resolves within 1-2 minutes. Please try refreshing the page.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Retry Connection", key="retry_connection"):
            st.cache_resource.clear()
            st.experimental_rerun()
    with col2:
        if st.button("🏠 Go to Home", key="go_home"):
            st.switch_page("main.py")
    st.stop()

def login_page():
    # Logo and title
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("assets/logo.png", width=300)
        st.header("HazMat GIS - Login")

    # Login form with batch submission
    with st.form(key="login_form", border=True):
        email = st.text_input("Email", key="email_input").lower()
        password = st.text_input("Password", type="password", key="password_input")
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 2.3])
        with col1:
            login_button = st.form_submit_button("Login")
        with col5:
            forget_button = st.form_submit_button("Forget Password")
        
        
        if login_button:
            if not email:
                custom_warning("Please enter email")
            elif not password:
                custom_warning("Please enter password")
            else:
                is_user, is_admin = conn.check_login(email, password)
                print("is_user:", is_user)
                print("is_admin:", is_admin)
                if is_user == "Accepted":
                    # Set session state and cookies
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.user_type = "admin" if is_admin else "user"
                    st.session_state.page = "main_display"
                    st.session_state.sidebar_hidden = False
                    cookies["logged_in"] = "True"
                    cookies["user_type"] = st.session_state.user_type
                    cookies["page"] = "main_display"
                    cookies["user_email"] = email
                    cookies.save()

                    # Show toast for temporary password
                    if conn.is_temporary_password(email):
                        show_toast("Your password is temporary. Please change it immediately!" if not is_admin else "This is a custom toast notification!")
                    
                    if not is_admin:
                        conn.add_new_login(email)
                    st.switch_page("pages/main_display.py")
                elif is_user == "Rejected":
                    st.session_state.page = "Rejected"
                    st.switch_page("pages/rejected_page.py")
                elif is_user == "Pending":
                    st.session_state.page = "Pending"
                    st.switch_page("pages/pending_page.py")
                else:
                    custom_error("Wrong Password, Try Again")

        if forget_button:
            st.session_state.page = "Forget_Password"
            st.switch_page("pages/forget_password.py")

    # Register link
    col1, col2 = st.columns([2.5, 7.5])
    col1.write("Don't have an account?")
    if col2.button("Register", key="register_button"):
        st.session_state.page = "Register"
        st.switch_page("pages/register_page.py")

if __name__ == "__main__":
    login_page()