import streamlit as st
from custom_warnings import custom_error
def rejected_page():
    columns = st.columns((2, 6, 2))
    with columns[1]:
        with st.container(border=True):
            st.subheader("Sorry to Say 😔")
            custom_error("Your request was not accepted.")
            if st.button("Back to Login Page"):
                st.switch_page("pages/login_page.py")
rejected_page()
