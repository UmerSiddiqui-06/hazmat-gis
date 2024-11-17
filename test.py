# Add CSS for central alignment
import streamlit as st
def centralize_content():
    st.markdown(
        """
        <style>
        .stApp {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
        }
        .main {
            width: 100%;
            max-width: 800px;
            margin: auto;
            text-align: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
def login_page(clients_df):
    centralize_content()
    c1,c2,c3 = st.columns(3)

    with c2:
        st.image("logo.png", width=200)  # Add logo
        st.title("REGMATIC SYSTEMS, SL - Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")

login_page(5)