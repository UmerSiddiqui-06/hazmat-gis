import streamlit as st
import utitlity
import re
import yagmail
import json
import random
from streamlit_cookies_manager import EncryptedCookieManager
cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()
conn = utitlity.sqlpy()
if not conn:
    st.stop()
def custom_error(message):
    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: center;
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px 16px;
            border-radius: 4px;
            border: 1px solid #f5c6cb;
            font-weight: 700;
            font-size: 16px;
        ">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" style="margin-right: 10px; flex-shrink: 0;" viewBox="0 0 16 16">
                <path d="M8.982 1.566a1.5 1.5 0 0 0-1.964 0L.165 7.47a1.5 1.5 0 0 0 0 2.26l6.853 5.905a1.5 1.5 0 0 0 1.964 0l6.853-5.905a1.5 1.5 0 0 0 0-2.26L8.982 1.566zM8 5.5a.75.75 0 0 1 .75.75v3.5a.75.75 0 0 1-1.5 0v-3.5A.75.75 0 0 1 8 5.5zm0 6.25a.75.75 0 1 1 0 1.5.75.75 0 0 1 0-1.5z"/>
            </svg>
            {message}
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    with open("Texts/email_code.json", "r") as file:
        email_code = json.load(file)
    email = "HazMat.GIS@gmail.com"
    email_password = "edlxeiepcyjasoqg"

    code = password_generator()

    subject = email_code["subject"]
    contents = email_code["contents"].replace("[code]", str(code))

    try:
        yag = yagmail.SMTP(email, email_password)
        yag.send(to=recipient, subject=subject, contents=contents)
    except Exception as e:
        custom_error(f"Failed to send verification code")
    return code

def register_page():
    columns = st.columns((1, 8, 1))
    with columns[1]:
        with st.container(border=True):
            st.subheader("Register")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            columns = st.columns((2, 6, 2.7))
            is_weak_password = False
            is_invalid_password = False
            user_exists=False
            none_email=False
            none_password=False
            with columns[0]:
                if st.button("Register"):
                    if not email:
                        none_email=True
                        
                    elif not password:
                        none_password=True
                        
                    else:
                        if conn.is_user_exist(email):
                            user_exists=True
                        else:

                            if valid_email(email):
                                is_invalid_password = False
                                if valid_password(password):
                                    is_weak_password = False
                                    status = conn.get_status(email)
                                    if status == "Rejected":
                                        st.session_state.page = "Rejected"
                                        st.switch_page("pages/rejected_page.py")

                                    elif status == "Pending":
                                        st.session_state.page = "Pending"
                                        st.switch_page("pages/pending_page.py")

                                    else:
                                        code = send_email_code(email)
                                        st.session_state.code = str(code)
                                        st.session_state.reg_email = email
                                        st.session_state.reg_password = password
                                        st.session_state.page = "code_verification"
                                        cookies["code"] = str(code)
                                        cookies["reg_email"] = email
                                        cookies["reg_password"] = password
                                        cookies.save()
                                        st.switch_page("pages/code_verification.py")

                                else:
                                    is_weak_password = True
                            else:
                                is_invalid_password = True

            with columns[2]:
                if st.button("Back to Login"):
                    st.switch_page("pages/login_page.py")
            if user_exists:
                custom_warning("User Already Exists")
            if none_email:
                custom_warning("Please enter email")
            if none_password:
                custom_warning("Please enter passowrd")
            if is_weak_password:
                custom_warning(
                    "Password must include 1 uppercase, 1 lowercase, 1 number, and be at least 8 characters."
                )
            if is_invalid_password:
                custom_warning("Invalid Email, Try Again")
register_page()