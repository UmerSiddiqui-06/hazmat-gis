import streamlit as st
from db import sqlpy
import yagmail
import json
from components.custom_warnings import custom_error
st.set_page_config(
    page_title="HazMat GIS", page_icon="assets/logo.png", initial_sidebar_state="auto")

# Cache database connection
@st.cache_resource
def get_database_connection():
    return sqlpy.sqlpy()

# Cache email template
@st.cache_data
def load_email_template():
    with open("Texts/email_code.json", "r") as file:
        return json.load(file)

# Cache warning CSS
@st.cache_data
def get_warning_css():
    return """
    <style>
        .custom-warning {
            display: flex;
            align-items: center;
            background-color: #fff3cd;
            color: #856404;
            padding: 10px 16px;
            border-radius: 4px;
            border: 1px solid #ffeeba;
            font-weight: 700;
            font-size: 16px;
        }
        .custom-warning svg {
            margin-right: 10px;
            flex-shrink: 0;
        }
    </style>
    """

def custom_warning(message):
    st.markdown(get_warning_css(), unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="custom-warning">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 16 16">
                <path d="M7.002 1.316a1.5 1.5 0 0 1 1.996 0l6.857 6.195a1.5 1.5 0 0 1 0 2.26l-6.857 6.195a1.5 1.5 0 0 1-1.996 0L.145 9.771a1.5 1.5 0 0 1 0-2.26L7.002 1.316zM8 5.5a.75.75 0 0 0-.75.75v3.5a.75.75 0 0 0 1.5 0v-3.5A.75.75 0 0 0 8 5.5zm0 6.25a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5z"/>
            </svg>
            {message}
        </div>
        """,
        unsafe_allow_html=True,
    )

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

def send_request_to_admin(user_email):
    email = "HazMat.GIS@gmail.com"
    email_password = "edlxeiepcyjasoqg"
    admin_email = "HazMat.GIS@gmail.com"
    try:
        yag = yagmail.SMTP(email, email_password)
        request_admin = load_email_template()
        subject = request_admin["subject"]
        body = request_admin["contents"].replace("[user_email]", user_email)
        yag.send(to=admin_email, subject=subject, contents=body)
        return True
    except Exception as e:
        custom_error("Failed to send verification code")
        return False

def code_verification(code, email, password):
    # Layout for title
    col1, col2, col3 = st.columns([1, 8, 1])
    with col2:
        with st.form(key="code_verification_form", border=True):
            st.subheader("Enter Verification Code")
            passcode = st.text_input("Enter 6-digit verification code: ", key="passcode_input")
            col1, col2, col3 = st.columns([2, 6, 3.2])
            with col1:
                verify_button = st.form_submit_button("Verify")
            with col3:
                back_button = st.form_submit_button("Back to Register")

            if verify_button:
                if not passcode:
                    custom_warning("Please enter valid passcode")
                elif str(code) == passcode:
                    conn.register_user(email, password)
                    if send_request_to_admin(email):
                        st.success("Your Registration Request has been submitted.")
                        st.session_state.page = "Login"
                        st.switch_page("pages/login_page.py")
                else:
                    custom_error("Wrong Code")

            if back_button:
                st.session_state.page = "Register"
                st.switch_page("pages/register_page.py")

def main():
    # Check for required session state/cookies
    if (cookies.get("code") and cookies.get("reg_email") and cookies.get("reg_password") and
        "code" in st.session_state and "reg_email" in st.session_state and "reg_password" in st.session_state):
        st.session_state["code"] = cookies.get("code")
        st.session_state["reg_email"] = cookies.get("reg_email")
        st.session_state["reg_password"] = cookies.get("reg_password")
        code_verification(st.session_state.code, st.session_state.reg_email, st.session_state.reg_password)
    else:
        st.session_state["page"] = "Login"
        st.switch_page("pages/login_page.py")

if __name__ == "__main__":
    main()