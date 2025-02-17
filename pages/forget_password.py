import streamlit as st
import utitlity
import json
import yagmail
import time
import string
import random
conn = utitlity.sqlpy()
if not conn:
    st.stop()
def generate_temp_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choices(characters, k=length))


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

def forget_password():
    columns = st.columns((1, 8, 1))
    with columns[1]:
        with st.container(border=True):
            st.title("Forget Password")

            email = st.text_input("Enter your email")

            columns = st.columns((2, 6, 2.7))
            with columns[0]:
                submit = st.button("Submit")
            with columns[2]:
                back_to_login = st.button("Back to Login")

            if submit:
                if not email:
                    custom_error("Email is required!")
                    return

                user = conn.is_user_exist(email)

                if user:
                    # Generate a temporary password
                    temp_password = generate_temp_password()

                    # Send the temporary password using yagmail
                    try:
                        admin_email = "HazMat.GIS@gmail.com"
                        email_password = "edlxeiepcyjasoqg"
                        yag = yagmail.SMTP(admin_email, email_password)

                        with open("Texts/password_reset.json", "r") as file:
                            password_reset = json.load(file)

                        subject = password_reset["subject"]
                        contents = password_reset["content"].replace(
                            "[TEMPORARY_PASSWORD]", temp_password
                        )

                        yag.send(to=email, subject=subject, contents=contents)
                        st.success(f"A temporary password has been sent to {email}.")
                        time.sleep(2)
                        st.session_state.page = "Login"
                        st.switch_page("pages/login_page.py")


                    except Exception as e:
                        custom_error(f"Failed to send email: {e}")
                else:
                    custom_error("Email not found!")
            elif back_to_login:
                st.session_state.page = "Login"
                st.switch_page("pages/login_page.py")

forget_password()
