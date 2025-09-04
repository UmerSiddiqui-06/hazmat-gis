import streamlit as st
from db import sqlpy
import re
import yagmail
import json
import random
from components.custom_warnings import custom_error, custom_warning

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

def password_generator():
    return random.randint(100000, 999999)

def valid_password(password):
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
    )

def valid_email(email):
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_regex, email) is not None

def send_email_code(recipient):
    email = "HazMat.GIS@gmail.com"
    email_password = "edlxeiepcyjasoqg"
    code = password_generator()
    try:
        yag = yagmail.SMTP(email, email_password)
        email_code = load_email_template()
        subject = email_code["subject"]
        contents = email_code["contents"].replace("[code]", str(code))
        yag.send(to=recipient, subject=subject, contents=contents)
        return code
    except Exception as e:
        custom_error("Failed to send verification code")
        return None

def register_page():
    # Layout for title
    col1, col2, col3 = st.columns([1, 8, 1])
    with col2:
        st.subheader("Register")

    # Form for registration
    with st.form(key="register_form", border=True):
        email = st.text_input("Email", key="email_input").lower()
        password = st.text_input("Password", type="password", key="password_input")
        col1, col2, col3 = st.columns([2, 6, 2.7])
        with col1:
            submit = st.form_submit_button("Register")
        with col3:
            back_to_login = st.form_submit_button("Back to Login")
        
        if submit:
            if not email:
                custom_warning("Please enter email")
            elif not password:
                custom_warning("Please enter password")
            elif conn.is_user_exist(email):
                custom_warning("User Already Exists")
            elif not valid_email(email):
                custom_warning("Invalid Email, Try Again")
            elif not valid_password(password):
                custom_warning(
                    "Password must include 1 uppercase, 1 lowercase, 1 number, and be at least 8 characters."
                )
            else:
                status = conn.get_status(email)
                if status == "Rejected":
                    st.session_state.page = "Rejected"
                    st.switch_page("pages/rejected_page.py")
                elif status == "Pending":
                    st.session_state.page = "Pending"
                    st.switch_page("pages/pending_page.py")
                else:
                    code = send_email_code(email)
                    if code:
                        st.session_state.code = str(code)
                        st.session_state.reg_email = email
                        st.session_state.reg_password = password
                        st.session_state.page = "code_verification"
                        cookies["code"] = str(code)
                        cookies["reg_email"] = email
                        cookies["reg_password"] = password
                        cookies.save()
                        st.switch_page("pages/code_verification.py")

        if back_to_login:
            st.session_state.page = "Login"
            st.switch_page("pages/login_page.py")

if __name__ == "__main__":
    register_page()