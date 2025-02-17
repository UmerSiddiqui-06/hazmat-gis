import streamlit as st
import utitlity
import time
st.set_page_config(
    page_title="HazMat GIS", page_icon="logo1.png", initial_sidebar_state="auto")
from streamlit_cookies_manager import EncryptedCookieManager
cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()
conn = utitlity.sqlpy()
if not conn:
    st.stop()
def show_toast(message, duration=2):
    toast_html = f"""
    <style>
        .toast {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 15px 25px;
            background-color: #f8d7da; /* Soft red for warning */
            color: #842029; /* Dark red for text */
            border: 1px solid #f5c2c7; /* Subtle border to complement background */
            border-radius: 8px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; /* Modern font */
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1); /* Subtle shadow for depth */
            z-index: 1000;
            opacity: 0;
            animation: fadein {duration}s forwards;
        }}

        @keyframes fadein {{
            0% {{
                opacity: 0;
                transform: translate(-50%, 20px); /* Slide up effect */
            }}
            100% {{
                opacity: 1;
                transform: translate(-50%, 0);
            }}
        }}
    </style>
    <div class="toast">
        ⚠️ {message}
    </div>
    """
    st.markdown(toast_html, unsafe_allow_html=True)

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

def login_page():
    # Logo and title
    c1, c2, c3 = st.columns(3)
    with c2:
        st.image("logo1.png", width=300)  # Add logo
    c1, c2, c3 = st.columns((3.8, 7, 2))
    with c2:
        st.header("HazMat GIS - Login")
    with st.container(border=True):
        # Login form
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        # Forget Password and Register buttons
        col1, col2, col3, col4, col5 = st.columns((2, 2, 2, 2, 2.3))
        with col1:
            login_button = st.button("Login")

        if login_button:
            if not email:
                custom_warning("Please enter email")
            elif not password:
                custom_warning("Please enter password")
                custom_warning("Please enter password")
            else:
                is_admin = conn.check_login_admin(email, password)
                is_user = conn.check_login_user(email, password)
                if is_admin:
                    st.session_state.logged_in = True
                    cookies["logged_in"] = "True"
                    cookies["user_type"] = "admin"
                    cookies["page"] = "main_display"
                    cookies["user_email"] = email
                    st.session_state.page = "main_display"
                    st.session_state.user_email = email
                    st.session_state.user_type = "admin"
                    st.session_state.sidebar_hidden = False
                    cookies.save()
                    if conn.is_temporary_password(email):
                        show_toast("This is a custom toast notification!")
                    time.sleep(2)
                    st.switch_page("pages/main_display.py")
                elif is_user == "Accepted":
                    conn.add_new_login(email)
                    st.session_state.user_email = email
                    st.session_state.logged_in = True
                    st.session_state.user_type = "user"
                    st.session_state.user_email = email
                    st.session_state.page = "main_display"
                    st.session_state.sidebar_hidden = False

                    if conn.is_temporary_password(email):
                        show_toast(
                            "Your password is temporary. Please change it immediately!"
                        )
                    time.sleep(3)
                    st.switch_page("pages/main_display.py")
                elif is_user == "Rejected":
                    st.session_state.page = "Rejected"
                    st.switch_page("pages/rejected_page.py")

                elif is_user == "Pending":
                    st.session_state.page = "Pending"
                    st.switch_page("pages/pending_page.py")

                else:
                    custom_error("Wrong Password, Try Again")

        with col5:
            if st.button("Forget Password"):
                st.session_state.page = "Forget_Password"
                st.switch_page("pages/forget_password.py")

        col1, col2 = st.columns((2.5, 7.5))
        col1.write("Don't have an account?")
        if col2.button("Register"):
            st.session_state.page = "Register"
            st.switch_page("pages/register_page.py")

login_page()