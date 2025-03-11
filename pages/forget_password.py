import streamlit as st
import utitlity
import json
import yagmail
import time
import string
import random
from custom_warnings import custom_error
st.set_page_config(
    page_title="HazMat GIS", page_icon="logo1.png", initial_sidebar_state="auto")
conn = utitlity.sqlpy()
if not conn:
    st.stop()
def generate_temp_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choices(characters, k=length))



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
                    #set forgeted password
                    import bcrypt
                    hashed_password = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt())
                    try:
                       conn.cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_password, email))
                       conn.conn.commit()
                    except Exception as e:
                       custom_error(f"Failed to update password in database: {e}")
                       return  # Stop execution if password update fails
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
