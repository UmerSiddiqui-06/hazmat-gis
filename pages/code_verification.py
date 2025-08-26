import streamlit as st
from db import sqlpy
import yagmail
import json
import time
from components.custom_warnings import custom_error

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
from streamlit_cookies_manager import EncryptedCookieManager
cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()
conn = sqlpy.sqlpy()
if not conn:
    st.stop()

def send_request_to_admin(user_email):
    email = "HazMat.GIS@gmail.com"
    email_password = "edlxeiepcyjasoqg"
    admin_email = "HazMat.GIS@gmail.com"
    with open("Texts/email_code.json", "r") as file:
        request_admin = json.load(file)
    subject = request_admin["subject"]
    body = request_admin["contents"].replace("[user_email]", user_email)
    try:
        yag = yagmail.SMTP(email, email_password)
        yag.send(to=admin_email, subject=subject, contents=body)
    except Exception as e:
        custom_error(f"Failed to send verification code")


def custom_warning(message):
    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: center;
            background-color: #fff3cd;
            color: #856404;
            padding: 10px 16px;
            border-radius: 4px;
            border: 1px solid #ffeeba;
            font-weight: 700;
            font-size: 16px;
        ">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" style="margin-right: 10px; flex-shrink: 0;" viewBox="0 0 16 16">
                <path d="M7.002 1.316a1.5 1.5 0 0 1 1.996 0l6.857 6.195a1.5 1.5 0 0 1 0 2.26l-6.857 6.195a1.5 1.5 0 0 1-1.996 0L.145 9.771a1.5 1.5 0 0 1 0-2.26L7.002 1.316zM8 5.5a.75.75 0 0 0-.75.75v3.5a.75.75 0 0 0 1.5 0v-3.5A.75.75 0 0 0 8 5.5zm0 6.25a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5z"/>
            </svg>
            {message}
        </div>
        """,
        unsafe_allow_html=True,
    )

def code_verification(code, email, password):
    columns = st.columns((1, 8, 1))
    with columns[1]:
        with st.container(border=True):
            passcode = st.text_input("Enter 6-digit verification code: ")
            columns = st.columns((2, 6, 3.2))
            wrong_code=False
            success=False
            with columns[0]:
                if st.button("Verify"):
                    if not passcode:
                        custom_warning("Please enter valid passcode")
                    else:
                        if str(code) == passcode:
                            wrong_code=False
                            conn.register_user(email, password)                 
                            send_request_to_admin(email)
                            success=True

                        else:
                            wrong_code=True
                            
            with columns[2]:
                if st.button("Back to Register"):
                    st.session_state.page = "Register"
                    st.switch_page("pages/register_page.py")
            if wrong_code:
                custom_error("Wrong Code")
            if success:
                st.success("Your Registration Request has been submitted.")
                time.sleep(1)
                st.session_state.page = "Login"
                st.switch_page("pages/login_page.py")
try:
    st.session_state["code"] = cookies.get("code")
    st.session_state["reg_email"] = cookies.get("reg_email")
    st.session_state["reg_password"] = cookies.get("reg_password")
    code_verification(st.session_state.code,st.session_state.reg_email,st.session_state.reg_password)
except:
    st.session_state["page"] = "Login"
    st.switch_page("pages/login_page.py")