import streamlit as st
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
