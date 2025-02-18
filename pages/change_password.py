import streamlit as st
import utitlity
import re
from custom_warnings import custom_warning
conn = utitlity.sqlpy()
if not conn:
    st.stop()
st.set_page_config(
    page_title="HazMat GIS", page_icon="logo1.png", initial_sidebar_state="auto")
from streamlit_cookies_manager import EncryptedCookieManager
cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()
if cookies.get("logged_in") == "True":
    st.session_state.logged_in = True
def valid_password(password):
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
    )
def change_password(email):
    columns = st.columns((1, 8, 1))
    with columns[1]:
        st.subheader("Change Password")
        with st.container(border=True):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            is_user = conn.check_login_user(email, current_password)

            is_admin = conn.check_login_admin(email, current_password)
            columns = st.columns((2.7, 4, 1.5))
            with columns[0]:
                update_password = st.button("Update Password")
            with columns[2]:
                go_back = st.button("Go Back", key="back_chng_pass")

            if go_back:
                st.session_state.logged_in = True
                st.session_state.page = "main_display"
                st.switch_page("pages/main_display.py")
                st.rerun()

            elif update_password:
                if is_user:
                    if new_password != confirm_password:
                        custom_warning("Passwords do not match!")
                    else:
                        if valid_password(new_password):
                            conn.update_password_users(email, new_password)
                            st.success("Password updated successfully!")
                        else:
                            custom_warning(
                                "Password must include 1 uppercase, 1 lowercase, 1 number, and be at least 8 characters."
                            )
                elif is_admin:
                    if new_password != confirm_password:
                        custom_warning("Passwords do not match!")
                    else:
                        if valid_password(new_password):
                            conn.update_password_admin(email, new_password)
                            st.success("Password updated successfully!")
                        else:
                            custom_warning(
                                "Password must include 1 uppercase, 1 lowercase, 1 number, and be at least 8 characters."
                            )
                else:
                    custom_warning("Wrong Password. Try Again")
if "logged_in" in st.session_state and st.session_state.logged_in:
    st.session_state.user_email = cookies.get("user_email")
    change_password(st.session_state.user_email)
else:
    st.switch_page("pages/login.py")
