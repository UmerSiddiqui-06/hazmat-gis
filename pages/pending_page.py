import streamlit as st
from custom_warnings import custom_warning
def pending_page():
    columns = st.columns((2, 6, 2))
    with columns[1]:
        with st.container(border=True):
            st.subheader("Please Wait ⏳")
            custom_warning("Your request has not been accepted yet.")
            if st.button("Back to Login Page"):
                st.switch_page("pages/login_page.py")
pending_page()
