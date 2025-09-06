import streamlit as st
from db import sqlpy
import json
import yagmail
import string
import random
from components.custom_warnings import custom_error
import bcrypt

st.set_page_config(
    page_title="HazMat GIS", page_icon="assets/logo.png", initial_sidebar_state="auto"
)

# Cache database connection
@st.cache_resource
def get_database_connection():
    db = sqlpy.sqlpy()
    # 🔹 Ensure connection is alive when first created
    try:
        db.conn.ping(reconnect=True, attempts=3, delay=2)
    except Exception:
        db = sqlpy.sqlpy()
    return db


# Cache email template
@st.cache_data
def load_email_template():
    with open("Texts/password_reset.json", "r") as file:
        return json.load(file)


# Get database connection
conn = get_database_connection()
if not conn or not conn.cursor:
    st.error("🚫 Database is temporarily unavailable.")
    if st.button("🔄 Retry", key="retry_connection"):
        st.cache_resource.clear()
        st.experimental_rerun()
    st.stop()


# Generate temporary password
def generate_temp_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choices(characters, k=length))


# Forget password workflow
def forget_password():
    # Layout for logo and title
    col1, col2, col3 = st.columns([1, 8, 1])
    with col2:
        st.title("Forget Password")

    # Form for email input and buttons
    with st.form(key="forget_password_form", border=True):
        email = st.text_input("Enter your email", key="email_input").lower()
        col1, col2, col3 = st.columns([2, 6, 2.7])
        with col1:
            submit = st.form_submit_button("Submit")
        with col3:
            back_to_login = st.form_submit_button("Back to Login")

        

        if submit:
            if not email:
                custom_error("Email is required!")
                return

            user = conn.is_user_exist(email)
            if user:
                # Generate and set temporary password
                temp_password = generate_temp_password()
                hashed_password = bcrypt.hashpw(
                    temp_password.encode("utf-8"), bcrypt.gensalt()
                )

                try:
                    # 🔹 Ensure connection is alive before using it
                    try:
                        conn.conn.ping(reconnect=True, attempts=3, delay=2)
                    except Exception:
                        # 🔹 Refresh only the internal connection, not the wrapper
                        conn.conn = sqlpy.sqlpy().conn

                    # 🔹 Always create a NEW cursor, don’t reuse cached one
                    cur = conn.conn.cursor()
                    cur.execute(
                        "UPDATE users SET password = %s WHERE email = %s",
                        (hashed_password, email),
                    )
                    conn.conn.commit()
                    cur.close()  # close cursor after use
                except Exception as e:
                    custom_error(f"Failed to update password in database: {e}")
                    return

                # Send temporary password via email
                try:
                    admin_email = "HazMat.GIS@gmail.com"
                    email_password = "edlxeiepcyjasoqg"
                    yag = yagmail.SMTP(admin_email, email_password)

                    password_reset = load_email_template()
                    subject = password_reset["subject"]
                    contents = password_reset["content"].replace(
                        "[TEMPORARY_PASSWORD]", temp_password
                    )

                    yag.send(to=email, subject=subject, contents=contents)
                    st.success(f"A temporary password has been sent to {email}.")
                    st.session_state.page = "Login"
                    st.switch_page("pages/login_page.py")
                except Exception as e:
                    custom_error(f"Failed to send email: {e}")
            else:
                custom_error("Email not found!")

        if back_to_login:
            st.session_state.page = "Login"
            st.switch_page("pages/login_page.py")


if __name__ == "__main__":
    forget_password()
