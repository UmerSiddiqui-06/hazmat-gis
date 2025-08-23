import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
import datetime
from streamlit_tags import st_tags
from streamlit_modal import Modal
import os
import utitlity
from io import BytesIO

from docx import Document
from geopy.geocoders import Nominatim
from rapidfuzz import process
import time
from pages.db_path import db_path
from custom_warnings import custom_error,custom_warning
st.set_page_config(
    page_title="HazMat GIS", page_icon="logo1.png", initial_sidebar_state="auto",layout="wide"
)
from streamlit_cookies_manager import EncryptedCookieManager
cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()
conn = utitlity.sqlpy()
if not conn:
    st.stop()
if cookies.get("user_type") == "admin":
    st.session_state.user_email = cookies.get("user_email")
    st.session_state.user_type = conn.is_admin(st.session_state.user_email)

PATH = db_path()
@st.cache_data
def load_world_cities():
    return pd.read_csv("worldcities.csv")
@st.cache_data
def fuzzy_match_city(city_name, limit=5, threshold=70):
    cities = load_world_cities()["city"].unique()  # Load unique city names
    matches = process.extract(city_name, cities, limit=limit)
    return [match for match, score, _ in matches if score >= threshold]


@st.cache_data
def geocode(city, country):
    geolocator = Nominatim(user_agent="my_app")
    try:
        location = geolocator.geocode(f"{city}, {country}")
        if location:
            return (location.latitude, location.longitude)
    except:
        pass
    return None
@st.cache_data
def preprocess_data(data):
    def geocode_and_correct(row):
        if row["City"] != "Unknown" and row["Country"] != "Unknown":
            coords = geocode(row["City"], row["Country"])

            if coords is None:
                matches = fuzzy_match_city(row["City"])
                if matches:
                    for match in matches:
                        coords = geocode(match, row["Country"])
                        if coords:
                            # row["City"] = match
                            break
        else:
            coords = row["Coordinates"]
        return pd.Series({"Coordinates": coords, "City": row["City"]})

    if "Coordinates" not in data.columns:
        data["Coordinates"] = None
    result = data.apply(geocode_and_correct, axis=1)
    data["Coordinates"] = result["Coordinates"]
    data["City"] = result["City"]
    return data
def toggle_twitter_access(user_id, toggle_key):
    # Compare with previous value and update if changed
    if st.session_state[toggle_key] != st.session_state.twitter_access_states[toggle_key]:
        # Update the toggle state in session and the database
        st.session_state.twitter_access_states[toggle_key] = st.session_state[toggle_key]
        conn.change_user_twitter_status(user_id)

def toggle_change_callback_gpt(user_id, toggle_key):
    # Compare with previous value and update if changed
    if st.session_state[toggle_key] != st.session_state.toggle_states_gpt[toggle_key]:
        # Update the toggle state in session and the database
        st.session_state.toggle_states_gpt[toggle_key] = st.session_state[toggle_key]
        conn.change_user_gpt_status(user_id)
        del st.session_state.gpt_limit_state
def increase_gpt_limit(user_id, number_key):
    if st.session_state[number_key] != st.session_state.gpt_limit_state[number_key]:
        st.session_state.gpt_limit_state[number_key] = st.session_state[number_key]
        conn.increase_gpt_limit(user_id, st.session_state[number_key])

def delete_user(email):
    conn.delete_user(email)
    st.session_state.show_modal = False
def show_delete_confirmation_modal(email):
    """
    Displays a confirmation message before deleting a user.

    Parameters:
        email (str): The email of the user to delete.
    """
    if st.session_state.get("show_modal", False):
        # Display the modal content
        custom_warning(f"Are you sure you want to delete the user with email: {email}?")
        col1, col2 = st.columns(2)
        with col1:
            st.button("Yes, Delete", on_click=delete_user, args=(email,))
        with col2:
            st.button("Cancel", on_click=cancel_delete)
    else:
        # Trigger the modal
        st.session_state.show_modal = True

def toggle_change_callback_status(user_id, toggle_key):
    # Compare with previous value and update if changed
    if (
        st.session_state[toggle_key]
        != st.session_state.toggle_states_status[toggle_key]
    ):
        # Update the toggle state in session and the database
        st.session_state.toggle_states_status[toggle_key] = st.session_state[toggle_key]
        conn.change_status(user_id)
def toggle_change_user_admin(user_id,toggle_key):
    if (
        st.session_state[toggle_key]
        != st.session_state.is_admin_user[toggle_key]
    ):
        # Update the toggle state in session and the database
        st.session_state.is_admin_user[toggle_key] = st.session_state[toggle_key]
        conn.change_admin(user_id)
def render_aggrid(df_display, user_type, filename="temp"):
    df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.strftime("%Y-%m-%d")
    full_data = df_display.copy()
    gb = GridOptionsBuilder.from_dataframe(df_display, editable=True)
    gb.configure_column("Category", minWidth=100)
    gb.configure_column("Title", minWidth=400)
    gb.configure_column("Country", minWidth=250)
    gb.configure_column("City", minWidth=200)
    gb.configure_column("Date", minWidth=100)
    gb.configure_column("Impact", minWidth=150)
    gb.configure_column("Casuality", minWidth=50)
    gb.configure_column("Injuries", minWidth=50)
    gb.configure_column("Full Link", minWidth=100)
    gb.configure_column("Severity", minWidth=100)
    if user_type == "admin":
        gb.configure_column("Coordinates", minWidth=200)

    gb.configure_selection("single", use_checkbox=True)
    if user_type == "admin":
        gb.configure_default_column(editable=True)
    gb.configure_column(
        "Full Link",
        headerName="Link",
        cellRenderer=JsCode(
            """
            class UrlCellRenderer {
            init(params) {
                this.eGui = document.createElement('a');
                this.eGui.innerText = 'Link';
                this.eGui.setAttribute('href', params.value);
                this.eGui.setAttribute('style', "text-decoration:none");
                this.eGui.setAttribute('target', "_blank");
            }
            getGui() {
                return this.eGui;
            }
            }
        """
        ),
    )
    gb.configure_default_column(
    flex=1,
    minWidth=100,
    maxWidth=500000,
    resizable=True,
)
    grid_options = gb.build()

    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        height=400,
        theme="streamlit",
        fit_columns_on_grid_load=False,
    )
    if user_type == "admin" and filename != "temp":
        if grid_response["data"] is not None:
            updated_df = pd.DataFrame(grid_response["data"])
            original_data = df_display.reset_index(drop=True)
            updated_data = updated_df.reset_index(drop=True)
            if not updated_data.equals(original_data):
                if st.button("Save Changes"):

                    # Update only the modified rows and cells
                    for index, row in updated_data.iterrows():
                        if not row.equals(
                            original_data.loc[index]
                        ):  # Check if the row has changed
                            for col in updated_data.columns:
                                if (
                                    row[col] != original_data.loc[index, col]
                                ):  # Check specific cell changes
                                    # Find the corresponding index in the full_data DataFrame
                                    full_index = full_data.index[
                                        original_data.index[index]
                                    ]
                                    full_data.loc[full_index, col] = row[col]

                    # Save back the updated Excel file
                    full_data.to_excel(f"data/{filename}", index=False)
                    st.success("Data saved to Excel successfully!")
                    df_display = updated_df
                    time.sleep(1)
                    st.rerun()

    return grid_response.get("selected_rows", [])

def create_word_file(content):
    doc = Document()
    doc.add_paragraph(content)  # Add the response text as a paragraph
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)  # Reset the buffer position to the start
    return buffer

def cancel_delete():
    st.session_state.show_modal = False


def display_col1():
    users = conn.get_users()

    if users:
        # Create DataFrame from users
        df = pd.DataFrame(
            users,
            columns=[
                "ID",
                "Email",
                "Password",
                "ChatGpt",
                "Status",
                "ChatGpt_used",
                "ChatGpt_limit",
                "Stopped Since",
                "gptlimittype",
                "is_admin",
                "allow_download",
                "twitterapi"
            ],
        )

        emails = list(df["Email"])
        selected_user = st_tags(
            label="Search User",
            text="Enter email to search...",
            value=[],
            suggestions=emails,
            key="user_search_col1",
        )

        if not selected_user:
            selected_user = emails[:]
        elif len(selected_user) > 0:
            df = df[df["Email"].isin(selected_user)]

        gpt_status = df["ChatGpt"]
        login_status = df["Status"]
        login_status = [
            0 if row in ["Pending", "Rejected"] else 1 for row in login_status
        ]
        gptlimit = df["ChatGpt_limit"]
        is_admin = df["is_admin"]
        allow_download = df["allow_download"]
        twitterapi = df["twitterapi"]

        df = df.drop(
            [
                "Password",
                "ChatGpt",
                "Status",
                "ChatGpt_used",
                "Stopped Since",
                "gptlimittype",
                "is_admin",
                "allow_download",
                "twitterapi"
            ],
            axis=1,
        )
        df.columns = ["ID", "Email", "ChatGpt_limit"]

        # Initialize session states if they don't exist
        if "toggle_states_gpt" not in st.session_state:
            st.session_state.toggle_states_gpt = {}
        if "toggle_states_status" not in st.session_state:
            st.session_state.toggle_states_status = {}
        if "gpt_limit_state" not in st.session_state:
            st.session_state.gpt_limit_state = {}
        if "is_admin_user" not in st.session_state:
            st.session_state.is_admin_user = {}
        if "allow_download_states" not in st.session_state:
            st.session_state.allow_download_states = {}

        # Display header
        header_col1, header_col2, header_col3, header_col4, header_col5, header_col6, header_col7, header_col8 = (
            st.columns((0.7, 2.8, 1.5, 1.5, 1.5, 1.5, 2, 1))
        )
        with header_col1:
            st.markdown("#### ID")
        with header_col2:
            st.markdown("#### Email")
        with header_col3:
            st.markdown("#### Access")
        with header_col4:
            st.markdown("#### GPT")
        with header_col5:
            st.markdown("#### Admin")
        with header_col6:
            st.markdown("#### Allow Download")
        with header_col7:
            st.markdown("#### GPT Limit")
        st.markdown(
            """
            <div style="border-top: 1px solid #ccc; margin: 5px 0;"></div>
            """,
            unsafe_allow_html=True,
        )
        
        ID = 1
        # Iterate over the DataFrame rows
        for i, row in df.iterrows():
            user_id = row["ID"]
            email = row["Email"]
            
            # Create unique keys using both user_id and email hash to ensure uniqueness
            user_hash = hash(email)  # Use email hash for additional uniqueness
            
            col31, col32, col33, col34, col35, col36, col37, col38 = st.columns((0.7, 2.8, 1.5, 1.5, 1.5, 1.5, 2, 1))
            
            with col31:
                st.markdown(f"#### {ID}", unsafe_allow_html=True)
                ID += 1
            
            with col32:
                st.write("")
                st.markdown(f"###### {email}", unsafe_allow_html=True)
            
            with col33:
                # Access toggle - use unique key with user_id and hash
                status_key = f"status_toggle_{user_id}_{user_hash}"
                if status_key not in st.session_state.toggle_states_status:
                    st.session_state.toggle_states_status[status_key] = bool(login_status[i])
                
                st.toggle(
                    "Revoke / Grant",
                    value=st.session_state.toggle_states_status[status_key],
                    key=status_key,
                    on_change=toggle_change_callback_status,
                    args=(user_id, status_key),
                )
            
            with col34:
                # GPT toggle
                gpt_key = f"gpt_toggle_{user_id}_{user_hash}"
                if gpt_key not in st.session_state.toggle_states_gpt:
                    st.session_state.toggle_states_gpt[gpt_key] = bool(gpt_status.iloc[i])
                
                st.toggle(
                    "Off / On",
                    value=st.session_state.toggle_states_gpt[gpt_key],
                    key=gpt_key,
                    on_change=toggle_change_callback_gpt,
                    args=(user_id, gpt_key),
                )
            
            with col35:
                # Admin toggle
                admin_key = f"admin_toggle_{user_id}_{user_hash}"
                if admin_key not in st.session_state.is_admin_user:
                    st.session_state.is_admin_user[admin_key] = bool(is_admin.iloc[i])
                
                st.toggle(
                    "Off / On",
                    value=st.session_state.is_admin_user[admin_key],
                    key=admin_key,
                    on_change=toggle_change_user_admin,
                    args=(user_id, admin_key),
                )
            
            with col36:
                # Download toggle
                download_key = f"download_toggle_{user_id}_{user_hash}"
                if download_key not in st.session_state.allow_download_states:
                    st.session_state.allow_download_states[download_key] = bool(allow_download.iloc[i])
                
                st.toggle(
                    "Off / On",
                    value=st.session_state.allow_download_states[download_key],
                    key=download_key,
                    on_change=lambda user_id=user_id, email=email, key=download_key: toggle_change_callback_download(user_id, email, key),
                )
            
            with col37:
                # GPT limit input
                limit_key = f"limit_input_{user_id}_{user_hash}"
                if limit_key not in st.session_state.gpt_limit_state:
                    st.session_state.gpt_limit_state[limit_key] = gptlimit.iloc[i]
                
                st.number_input(
                    " ",
                    key=limit_key,
                    label_visibility="collapsed",
                    value=st.session_state.gpt_limit_state[limit_key],
                    step=1,
                    format="%d",
                    on_change=increase_gpt_limit,
                    args=(user_id, limit_key),
                    min_value=0,
                )
            
            with col38:
                delete_key = f"delete_{user_id}_{user_hash}"
                if st.button("🗑", key=delete_key):
                    st.session_state.show_modal = True
                    st.session_state.delete_email = email
            
            st.markdown(
                """
                <div style="border-top: 1px solid #ccc; margin: 5px 0;"></div>
                """,
                unsafe_allow_html=True,
            )

            if (
                st.session_state.get("show_modal", False)
                and st.session_state.get("delete_email", False) == email
            ):
                show_delete_confirmation_modal(st.session_state.delete_email)
def display_col6():
    users = conn.get_users()

    if users:
        # Create DataFrame from users
        df = pd.DataFrame(
            users,
            columns=[
                "ID",
                "Email",
                "Password",
                "ChatGpt",
                "Status",
                "ChatGpt_used",
                "ChatGpt_limit",
                "Stopped Since",
                "gptlimittype",
                "is_admin",
                "allow_download",
                "twitterapi"
            ],
        )

        emails = list(df["Email"])
        selected_user = st_tags(
            label="Search User",
            text="Enter email to search...",
            value=[],
            suggestions=emails,
            key="twitter_search",
        )

        if not selected_user:
            selected_user = emails[:]
        elif len(selected_user) > 0:
            df = df[df["Email"].isin(selected_user)]

        twitter_access = df["twitterapi"]

        df = df.drop(
            [
                "Password",
                "ChatGpt",
                "Status",
                "ChatGpt_used",
                "Stopped Since",
                "gptlimittype",
                "is_admin",
                "allow_download",  # Drop the column after fetching the status
                "twitterapi"
            ],
            axis=1,
        )
        df.columns = ["ID", "Email", "ChatGpt_limit"]

        # Check for changes in the number of users and reinitialize session states
        if (
            "prev_user_count" not in st.session_state
            or st.session_state.prev_user_count != len(users)
            or "twitter_access_states" not in st.session_state
        ):
            st.session_state.prev_user_count = len(users)  # Update user count
            st.session_state.twitter_access_states = {
                f"twitter{i}": twitter_access.iloc[i] for i in range(len(users))
            }

        # Display header
        header_col1, header_col2, header_col3= (
            st.columns((0.7, 2.8, 1.5))
        )
        with header_col1:
            st.markdown("#### ID")
        with header_col2:
            st.markdown("#### Email")
        with header_col3:
            st.markdown("#### Twitter Access")
        st.markdown(
            """
            <div style="border-top: 1px solid #ccc; margin: 5px 0;"></div>
            """,
            unsafe_allow_html=True,
        )
        ID = 1
        # Iterate over the DataFrame rows
        for i, row in df.iterrows():
            col31, col32, col33 = st.columns((0.7, 2.8, 1.5))
            id = row["ID"]
            email = row["Email"]  # Get the email for the current user
            with col31:
                st.markdown(f"#### {ID}", unsafe_allow_html=True)
                ID += 1
            with col32:
                st.write("")
                st.markdown(f"###### {email}", unsafe_allow_html=True)
            with col33:
                toggle_key_1 = f"twitter{i}"
                st.toggle(
                    "Off / On",
                    value=st.session_state.twitter_access_states[toggle_key_1],
                    key=toggle_key_1,
                    on_change=toggle_twitter_access,
                    args=(id, toggle_key_1),
                )
            st.markdown(
                """
                <div style="border-top: 1px solid #ccc; margin: 5px 0;"></div>
                """,
                unsafe_allow_html=True,
            )


def toggle_change_callback_download(user_id, email, toggle_key):
    """
    Callback function for the "Allow Download" toggle.
    Updates the database and session state.
    """
    # Toggle the session state
    st.session_state.allow_download_states[toggle_key] = not st.session_state.allow_download_states[toggle_key]

    # Update the database
    conn.change_user_download_status(email)

def admin_panel():
    with st.sidebar:
        if st.button("Go Back"):
            st.session_state.page = "main_display"
            cookies["page"] = "main_display"
            cookies.save()
            st.switch_page("pages/main_display.py")

        # Header for ChatGPT Settings
        st.sidebar.header("ChatGPT Settings")

        # Toggle ChatGPT Status
        chatgpt = conn.get_gpt_status()
        chatgpt_toggle = st.toggle(
            "Enable ChatGPT",
            value=chatgpt,
            help="Activate or deactivate ChatGPT across the application.",
        )
        if chatgpt_toggle != chatgpt:
            conn.change_gpt_status()
        

        chatgpt_limit = conn.get_gpt_limit()
        gpt_limit = st.number_input(
            "Set ChatGPT Limit",
            value=chatgpt_limit,
            step=1,
            format="%d",
            min_value=0,
            help="Adjust the limit for ChatGPT usage",
        )
        if gpt_limit != chatgpt_limit:
            conn.set_gpt_limit(gpt_limit)
            del st.session_state.gpt_limit_state
            st.rerun()
        # Add separator between sections for better readability
        st.sidebar.markdown("---")
    col1, col2, col3, col4, col5, col6 = st.tabs(
        [
            "Manage Access",
            "Login History",
            "Download History",
            "GPT Stats",
            "Upload Data",
            "Twitter Access"
        ]
    )

    with col2:
        users = conn.get_users()
        if users:
            df = pd.DataFrame(
                users,
                columns=[
                    "ID",
                    "Email",
                    "Password",
                    "ChatGPT",
                    "Status",
                    "ChatGPT Usage",
                    "ChatGPT Usage Limit",
                    "Stopped Since",
                    "gptlimittype",
                    "is_admin",
                    "allow_download",
                    "twitterapi"
                ],
            )
            df = df[["ID", "Email", "Status"]]
            emails = list(df["Email"])
            if "selected_emails" not in st.session_state:
                st.session_state.selected_emails = []

            manual_emails = st.multiselect(
                label="Search User",
                placeholder="Enter email to search...",
                options=emails,
                default=st.session_state.selected_emails,
                help="Select or type to search for users.",
            )

            if set(manual_emails) != set(st.session_state.selected_emails):
                st.session_state.selected_emails = manual_emails
                st.rerun()

            filtered_df = (
                df[df["Email"].isin(st.session_state.selected_emails)]
                if st.session_state.selected_emails
                else df
            )

            gb = GridOptionsBuilder.from_dataframe(filtered_df)
            gb.configure_grid_options(domLayout="normal")
            gb.configure_selection(selection_mode="multiple")
            gb.configure_column("ID", tooltipField="ID", flex=1)
            gb.configure_column("Email", tooltipField="Email", flex=1)
            gb.configure_column("Status", tooltipField="Status", flex=1)
            gridOptions = gb.build()
            grid_response = AgGrid(
                filtered_df,
                gridOptions=gridOptions,
                update_mode="MODEL_CHANGED",
                height=400,
                fit_columns_on_grid_load=True,
                theme="streamlit",
            )

            selected_rows = grid_response.get("selected_rows", [])

            try:
                grid_selected_emails = [email for email in selected_rows["Email"]]
            except:
                grid_selected_emails = []

            final_selected_emails = list(
                set(st.session_state.selected_emails).union(set(grid_selected_emails))
            )

            if set(final_selected_emails) != set(st.session_state.selected_emails):
                st.session_state.selected_emails = final_selected_emails
                st.rerun()

            selected_user = manual_emails
            if len(selected_user) == 0:
                selected_user = emails
            if selected_user is not None:
                st.subheader("Login History of Selected Users: ")
                users_data = conn.get_login_info(selected_user)
                users_data = pd.DataFrame(users_data, columns=["Email", "Time"])
                users_data["Time"] = pd.to_datetime(users_data["Time"])

                selected_filter = st.selectbox(
                    "Select Time Filter",
                    [
                        "All time",
                        "Past Day",
                        "Past Week",
                        "Past Month",
                        "Past Year",
                        "Custom Range",
                    ],
                )

                temp_data = users_data.copy()

                if selected_filter == "Custom Range":
                    try:
                        start_date = st.date_input(
                            "Start Date", temp_data["Time"].min()
                        )
                        end_date = st.date_input("End Date", temp_data["Time"].max())
                    except:
                        start_date = st.date_input(
                            "Start Date", datetime.datetime.today().date()
                        )
                        end_date = st.date_input(
                            "End Date", datetime.datetime.today().date()
                        )
                else:
                    start_date, end_date = None, None

                if st.button("View History"):
                    if not temp_data.empty:
                        current_time = datetime.datetime.now()

                        if selected_filter == "All time":
                            pass

                        elif selected_filter == "Past Day":
                            yesterday = current_time - datetime.timedelta(days=1)
                            temp_data = temp_data[
                                temp_data["Time"] >= pd.Timestamp(yesterday)
                            ]

                        elif selected_filter == "Past Week":
                            past_week = current_time - datetime.timedelta(weeks=1)
                            temp_data = temp_data[
                                temp_data["Time"] >= pd.Timestamp(past_week)
                            ]

                        elif selected_filter == "Past Month":
                            past_month = current_time - datetime.timedelta(days=30)
                            temp_data = temp_data[
                                temp_data["Time"] >= pd.Timestamp(past_month)
                            ]

                        elif selected_filter == "Past Year":
                            past_year = current_time - datetime.timedelta(days=365)
                            temp_data = temp_data[
                                temp_data["Time"] >= pd.Timestamp(past_year)
                            ]

                        elif selected_filter == "Custom Range":
                            if start_date and end_date:
                                temp_data = temp_data[
                                    (temp_data["Time"] >= pd.Timestamp(start_date))
                                    & (temp_data["Time"] <= pd.Timestamp(end_date))
                                ]
                            else:
                                custom_warning(
                                    "Please select a valid start and end date."
                                )

                        gb = GridOptionsBuilder.from_dataframe(temp_data)
                        # gb.configure_grid_options(rowStyle={"backgroundColor": "white"})
                        gb.configure_grid_options(domLayout="normal")
                        gb.configure_column("Email", tooltipField="Email")
                        gb.configure_column("Time", tooltipField="Time")
                        gb.configure_default_column(
                            editable=True, resizable=True, flex=1
                        )
                        grid_options = gb.build()

                        # Display with AgGrid
                        AgGrid(
                            temp_data,
                            gridOptions=grid_options,
                            # Themes: 'streamlit', 'light', 'dark', 'balham', 'material'
                            fit_columns_on_grid_load=True,
                            height=200,
                            theme="streamlit",
                        )

                    else:
                        custom_warning("Not Enough Data")
        else:
            custom_warning("Not Enough Data")
    with col3:
        users = conn.get_users()
        # if users:
        
        def get_download_history():
            return conn.get_download_history()
        data = get_download_history()
        df = pd.DataFrame(
            data,
            columns=[
                "Email",
                "Download Date",
                "Type",
                "Category",
                "Country",
                "Impact",
                "Severity",
                "Date",
            ],
        )
        emails = pd.DataFrame(
            users,
            columns=[
                "ID",
                "Email",
                "Password",
                "ChatGpt",
                "Status",
                "ChatGpt_used",
                "ChatGpt_limit",
                "Stopped Since",
                "gptlimittype",
                "is_admin",
                "allow_download",
                "twitterapi"
            ],
        )
        emails = list(emails["Email"])
        selected_user = st_tags(
            label="Search User",
            text="Enter email to search...",
            value=[],
            suggestions=emails,
            key="2",
        )
        # selected_user = st.multiselect('Search User ',emails,key='download_select',placeholder="Enter email to search...")
        if not selected_user:
            pass
        elif len(selected_user) > 0:
            df = df[df["Email"].isin(selected_user)]
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_grid_options(domLayout="normal")
        gb.configure_column("Download Date", tooltipField="Download Date")
        gb.configure_column("Email", tooltipField="Email")
        gb.configure_column("Type", tooltipField="Type")
        gb.configure_column("Category", tooltipField="Category")
        gb.configure_column("Country", tooltipField="Country")
        gb.configure_column("Impact", tooltipField="Impact")
        gb.configure_column("Severity", tooltipField="Severity")
        gb.configure_column("Date", tooltipField="Date")
        gridOptions = gb.build()

        grid_response = AgGrid(
            df,
            gridOptions=gridOptions,
            update_mode="MODEL_CHANGED",
            height=400,  # Set a fixed height for vertical scrolling
            fit_columns_on_grid_load=True,  # Disable auto-fit on initial load
            theme="streamlit",
        )

        # try:
        # Convert the 'Time' column from string to datetime
        df["Download Date"] = pd.to_datetime(df["Download Date"])

        # Get current date and time
        today = datetime.datetime.today()

        # Calculate total downloads
        total_downloads = len(df)

        # Calculate downloads this week
        downloads_this_week = len(
            df[df["Download Date"] >= today - datetime.timedelta(days=7)]
        )

        # Calculate downloads today
        downloads_today = len(df[df["Download Date"].dt.date == today.date()])

        # Calculate downloads this month
        downloads_this_month = len(
            df[df["Download Date"] >= today - datetime.timedelta(days=30)]
        )


        st.markdown(
            f"""
    <div style="display: flex; justify-content: space-between; width: 100%; padding: 10px;">
        <div style="width: 23%; padding: 10px; border-radius: 5px; background-color: #a0b7a9; 
                    box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2); text-align: center;">
            <p style="font-size: 16px; color: #161d25; margin: 0; font-weight: bold;">Downloads Today</p>
            <p style="font-size: 24px; color: #161d25; margin: 0;">{downloads_today}</p>
        </div>
        <div style="width: 23%; padding: 10px; border-radius: 5px; background-color: #a0b7a9; 
                    box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2); text-align: center;">
            <p style="font-size: 16px; color: #161d25; margin: 0; font-weight: bold;">Downloads This Week</p>
            <p style="font-size: 24px; color: #161d25; margin: 0;">{downloads_this_week}</p>
        </div>
        <div style="width: 23%; padding: 10px; border-radius: 5px; background-color: #a0b7a9; 
                    box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2); text-align: center;">
            <p style="font-size: 16px; color: #161d25; margin: 0; font-weight: bold;">Downloads This Month</p>
            <p style="font-size: 24px; color: #161d25; margin: 0;">{downloads_this_month}</p>
        </div>
        <div style="width: 23%; padding: 10px; border-radius: 5px; background-color: #a0b7a9; 
                    box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2); text-align: center;">
            <p style="font-size: 16px; color: #161d25; margin: 0; font-weight: bold;">Total Downloads</p>
            <p style="font-size: 24px; color: #161d25; margin: 0;">{total_downloads}</p>
        </div>
    </div>
    """,
            unsafe_allow_html=True,
        )
        if len(selected_user) == 0:
            selected_user = emails
        st.subheader("Download History of Selected Users: ")
        users_data = conn.get_user_download_history(selected_user)
        users_data = pd.DataFrame(
            users_data,
            columns=[
                "Email",
                "Download Date",
                "Type",
                "Category",
                "Country",
                "Impact",
                "Severity",
                "Date",
            ],
        )
        users_data["Download Date"] = pd.to_datetime(users_data["Download Date"])
        selected_filter = st.selectbox(
            "Select Time Filter",
            [
                "All time",
                "Past Day",
                "Past Week",
                "Past Month",
                "Past Year",
                "Custom Range",
            ],
            key="down-user",
        )

        temp_data = users_data.copy()
        if selected_filter == "Custom Range":
            try:
                start_date = st.date_input(
                    "Start Date", temp_data["Download Date"].min(), key="k1"
                )
                end_date = st.date_input(
                    "End Date", temp_data["Download Date"].max(), key="k2"
                )
            except:
                start_date = st.date_input(
                    "Start Date", datetime.datetime.today().date(), key="k3"
                )
                end_date = st.date_input(
                    "End Date", datetime.datetime.today().date(), key="k4"
                )
        else:
            start_date, end_date = None, None

        if st.button("View History", key="down-find"):
            if not temp_data.empty:
                current_time = datetime.datetime.now()

                if selected_filter == "All time":
                    pass

                elif selected_filter == "Past Day":
                    yesterday = current_time - datetime.timedelta(days=1)
                    temp_data = temp_data[
                        temp_data["Download Date"] >= pd.Timestamp(yesterday)
                    ]

                elif selected_filter == "Past Week":
                    past_week = current_time - datetime.timedelta(weeks=1)
                    temp_data = temp_data[
                        temp_data["Download Date"] >= pd.Timestamp(past_week)
                    ]

                elif selected_filter == "Past Month":
                    past_month = current_time - datetime.timedelta(days=30)
                    temp_data = temp_data[
                        temp_data["Download Date"] >= pd.Timestamp(past_month)
                    ]

                elif selected_filter == "Past Year":
                    past_year = current_time - datetime.timedelta(days=365)
                    temp_data = temp_data[
                        temp_data["Download Date"] >= pd.Timestamp(past_year)
                    ]

                elif selected_filter == "Custom Range":
                    if start_date and end_date:
                        temp_data = temp_data[
                            (temp_data["Download Date"] >= pd.Timestamp(start_date))
                            & (temp_data["Download Date"] <= pd.Timestamp(end_date))
                        ]
                    else:
                        custom_warning("Please select a valid start and end date.")

                gb = GridOptionsBuilder.from_dataframe(temp_data)
                gb.configure_grid_options(domLayout="normal")
                gb.configure_column("Download Date", tooltipField="Download Date")
                gb.configure_column("Email", tooltipField="Email")
                gb.configure_column("Type", tooltipField="Type")
                gb.configure_column("Category", tooltipField="Category")
                gb.configure_column("Country", tooltipField="Country")
                gb.configure_column("Impact", tooltipField="Impact")
                gb.configure_column("Severity", tooltipField="Severity")
                gb.configure_column("Date", tooltipField="Date")
                grid_options = gb.build()

                # Display with AgGrid
                AgGrid(
                    temp_data,
                    gridOptions=grid_options,
                    theme="streamlit",  # Themes: 'streamlit', 'light', 'dark', 'balham', 'material'
                    fit_columns_on_grid_load=True,
                    height=200,
                )
            else:
                custom_warning("Not Enough Data")
    with col1:
        display_col1()
    with col6:
        display_col6()
    with col4:
        history = (
            conn.get_gpt_history()
        )  # Replace with your actual method to get history
        df = pd.DataFrame(history, columns=["Email", "Link", "Title", "Time"])

        # Display the DataFrame using AgGrid
        st.subheader("GPT History")

        emails = list(df["Email"].unique())
        if "selected_emails_gpt" not in st.session_state:
            st.session_state.selected_emails_gpt = []

        manual_emails = st.multiselect(
            label="Search User",
            placeholder="Enter email to search...",
            options=emails,
            default=[],
            help="Select or type to search for users.",
        )

        if set(manual_emails) != set(st.session_state.selected_emails_gpt):
            st.session_state.selected_emails_gpt = manual_emails
            st.rerun()

        filtered_df = (
            df[df["Email"].isin(st.session_state.selected_emails_gpt)]
            if st.session_state.selected_emails_gpt
            else df
        )

        gb = GridOptionsBuilder.from_dataframe(filtered_df)

        gb.configure_selection(selection_mode="single")
        grid_options = gb.build()

        grid_response = AgGrid(
            filtered_df,
            gridOptions=grid_options,
            update_mode="MODEL_CHANGED",
            height=400,
            fit_columns_on_grid_load=True,
            theme="streamlit",
            allow_unsafe_jscode=True,
        )
        modal = Modal(key="example_modal", title="Link Details")

        @st.dialog("Response", width="large")
        def show_full_screen_modal(row_data):
            link = row_data["Link"]
            st.markdown(
                f"""
                    <a href="{link}" target="_blank" style="
                        text-decoration: none;
                        padding: 8px 15px;
                        background-color: #0e1117;  /* Blue background color */
                        color: white;
                        border-radius: 7px;
                        text-align: center;
                        display: inline-block;
                        border: 7px solid black;  /* Black border */
                    ">
                        Open Link
                    </a>
                """,
                unsafe_allow_html=True,
            )
            response = conn.get_gpt_response(row_data["Link"])

            word_file = create_word_file(response)
            st.download_button(
                label="Download Response",
                data=word_file,  # File content as a BytesIO object
                file_name="response.docx",  # File name with .docx extension
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # MIME type for Word files
            )
            st.write("Summary Response:", response)

        selected_row = grid_response.get("selected_rows", [])
        if selected_row is not None:
            row_data = selected_row.iloc[0]  # Access the first selected row
            if st.button("Show Details"):
                show_full_screen_modal(row_data)

        try:
            grid_selected_emails = [email for email in selected_rows["Email"]]
        except:
            grid_selected_emails = []

        final_selected_emails = list(
            set(st.session_state.selected_emails_gpt).union(set(grid_selected_emails))
        )

        if set(final_selected_emails) != set(st.session_state.selected_emails_gpt):
            st.session_state.selected_emails_gpt = final_selected_emails
            st.rerun()

        usage = conn.get_gpt_usage()
        df = pd.DataFrame(usage, columns=["Email", "Usage", "Limit"])

        # Display the DataFrame using AgGrid
        st.subheader("GPT Usage")

        emails = list(df["Email"].unique())
        if "selected_emails_usage" not in st.session_state:
            st.session_state.selected_emails_usage = []

        manual_emails = st.multiselect(
            label="Search User",
            placeholder="Enter email to search...",
            options=emails,
            default=st.session_state.selected_emails_usage,
            help="Select or type to search for users.",
            key="gpt_usage",
        )

        if set(manual_emails) != set(st.session_state.selected_emails_usage):
            st.session_state.selected_emails_usage = manual_emails
            st.rerun()

        filtered_df = (
            df[df["Email"].isin(st.session_state.selected_emails_usage)]
            if st.session_state.selected_emails_usage
            else df
        )

        gb = GridOptionsBuilder.from_dataframe(filtered_df)
        gb.configure_default_column(
            editable=False, groupable=True, flex=1
        )  # Default column settings
        gb.configure_selection(selection_mode="multiple")
        grid_options = gb.build()

        grid_response = AgGrid(
            filtered_df,
            gridOptions=grid_options,
            update_mode="MODEL_CHANGED",
            height=400,
            fit_columns_on_grid_load=True,
            theme="streamlit",
        )

        selected_rows = grid_response.get("selected_rows", [])

        try:
            grid_selected_emails = [email for email in selected_rows["Email"]]
        except:
            grid_selected_emails = []

        final_selected_emails = list(
            set(st.session_state.selected_emails_usage).union(set(grid_selected_emails))
        )

        if set(final_selected_emails) != set(st.session_state.selected_emails_usage):
            st.session_state.selected_emails_usage = final_selected_emails
            st.rerun()
    with col5:
        if "selected_file" not in st.session_state:
            st.session_state.selected_file = None
        if "filename" not in st.session_state:
            st.session_state.filename = None
        st.header("Upload Data")
        new_data_file = st.file_uploader(
            "Upload an Excel File", type="xlsx", label_visibility="collapsed"
        )
########################################
        # Define the path for original files
        ORIGINAL_FILES_PATH = os.path.join(PATH, "original_files")

        # Ensure the directory exists
        os.makedirs(ORIGINAL_FILES_PATH, exist_ok=True)
        
        if new_data_file:
            # Concatenate Data Button
            filename = st.text_input(
                "Filename:", placeholder="Enter file name without extension"
            )
            if st.button("Add File"):
                if filename:
                    try:
                        new_data = pd.read_excel(new_data_file)
                        ########### Save the original file in the original_files directory
                        original_file_path = os.path.join(ORIGINAL_FILES_PATH, f"{filename}.xlsx")
                        new_data.to_excel(original_file_path, index=False)


                        valid_type = {"Incident", "Activity", "Study", "Report", "MoU", "Exercise", "Training", "Cooperation", "Workshop", "Guidance", "Conference"}
                        valid_category = {
                            "Explosive",
                            "Biological",
                            "Radiological",
                            "Chemical",
                            "Nuclear",
                            "Other",
                        }
                        valid_impact = {
                            "Infrastructure",
                            "Human",
                            "Environment",
                            "Economic",
                            "Animal",
                            "Technology",
                            "Weapon",
                        }
                        valid_severity = {"Low", "Medium", "High"}

                        # Function to check if any value in a comma-separated list is valid
                        def check_validity(value, valid_set):
                           # Convert valid_set values to lowercase
                           valid_set = {item.lower() for item in valid_set}
    
                           # Split the value by commas, strip whitespace, and convert to lowercase
                           values = {item.strip().lower() for item in value.split(",")}
    
                           # Check if all extracted values are in the valid set
                           return values.issubset(valid_set)

                        # Apply the validity checks
                        new_data["Type_Valid"] = new_data["Type"].apply(
                            lambda x: check_validity(x, valid_type)
                        )
                        new_data["Category_Valid"] = new_data["Category"].apply(
                            lambda x: check_validity(x, valid_category)
                        )
                        new_data["Impact_Valid"] = new_data["Impact"].apply(
                            lambda x: check_validity(x, valid_impact)
                        )
                        new_data["Severity_Valid"] = new_data["Severity"].apply(
                            lambda x: check_validity(x, valid_severity)
                        )

                        conditions = (
                            new_data["Type_Valid"]
                            & new_data["Category_Valid"]
                            & new_data["Impact_Valid"]
                            & new_data["Severity_Valid"]
                        )

                        rejected_rows = new_data[~conditions].copy()
                        rejected_rows["Failure_Reason"] = rejected_rows.apply(
                            lambda row: ", ".join(
                                [
                                    reason
                                    for reason, valid in [
                                        ("Invalid Type", not row["Type_Valid"]),
                                        ("Invalid Category", not row["Category_Valid"]),
                                        ("Invalid Impact", not row["Impact_Valid"]),
                                        ("Invalid Severity", not row["Severity_Valid"]),
                                    ]
                                    if valid
                                ]
                            ),
                            axis=1,
                        )

                        new_data = new_data[conditions].drop(
                            columns=[
                                "Type_Valid",
                                "Category_Valid",
                                "Impact_Valid",
                                "Severity_Valid",
                            ]
                        )
                        new_data["Type"] = new_data["Type"].str.title()
                        new_data["Severity"] = new_data["Severity"].str.title()
                        new_data["Category"] = new_data["Category"].str.title()
                        new_data["Impact"] = new_data["Impact"].str.title()
                        new_data.loc[new_data["Impact"] == "Environment", "Impact"] = (
                            "Environmental"
                        )
                        columns_to_clean = ["Type", "Category", "Impact", "Severity"]
                        for column in columns_to_clean:
                            if column in new_data.columns:
                                new_data[column] = new_data[column].str.strip()
                        filename = filename + ".xlsx"
                        split_rows = new_data.dropna(subset=["Country", "City"])
                        processed_split = (
                            split_rows.assign(
                                country_city=split_rows.apply(
                                    lambda row: list(
                                        zip(
                                            row["Country"].split(", "),
                                            row["City"].split(", "),
                                        )
                                    ),
                                    axis=1,
                                )
                            )
                            .explode("country_city")
                            .assign(
                                Country=lambda df: df["country_city"].str[0],
                                City=lambda df: df["country_city"].str[1],
                            )
                            .drop(columns=["country_city"])  # Drop intermediate column
                            .reset_index(drop=True)  # Reset index for clarity
                        )

                        # Append rows with missing values back to the processed DataFrame
                        missing_rows = new_data[
                            new_data[["Country", "City"]].isnull().any(axis=1)
                        ]
                        final_df = pd.concat(
                            [processed_split, missing_rows], ignore_index=True
                        )
                        final_df["City"] = final_df["City"].fillna(
                            "Unknown"
                        )  # Replace NaN with a default value
                        final_df["City"] = final_df["City"].astype(
                            str
                        )  # Ensure all values are strings
                        final_df["Country"] = final_df["Country"].fillna(
                            "Unknown"
                        )  # Replace NaN with a default value
                        final_df["Country"] = final_df["Country"].astype(
                            str
                        )  # Ensure all values are strings
                        # final_df.to_excel("data/First File.xlsx", index=False)
                        final_df["Category"] = final_df["Category"].str.split(",")
                        final_df = final_df.explode("Category", ignore_index=True)
                        final_df["Category"] = final_df["Category"].str.strip()
                        final_df["Impact"] = final_df["Impact"].str.split(",")
                        final_df = final_df.explode("Impact", ignore_index=True)
                        final_df["Impact"] = final_df["Impact"].str.strip()
                        final_df = final_df.drop_duplicates()
                        new_data = preprocess_data(final_df)
                        new_data.to_excel(f"{PATH}/{filename}", index=False)
                        st.success("Data concatenated successfully")
                        # Provide download button for rejected rows
                        dcol, icol = st.columns(2)
                        with dcol:
                            if not rejected_rows.empty:
                                st.download_button(
                                    label="Download Rejected Rows",
                                    data=rejected_rows.to_csv(index=False),
                                    file_name="Rejected_Rows.csv",
                                    mime="text/csv",
                                )
                        with icol:
                            if not rejected_rows.empty and st.button("Ignore"):
                                st.rerun()

                    except Exception as e:
                        custom_error(f"Error occurred: {str(e)}")
                else:
                    custom_warning("Please enter filename")

        excel_files = {}
        try:
            for file_name in os.listdir(f"{PATH}"):
                if file_name.endswith((".xlsx", ".xls")):
                    file_path = os.path.join(f"{PATH}", file_name)
                    excel_files[file_name] = pd.read_excel(file_path)

            if not excel_files:
                st.markdown(
                    "⚠ *No Excel files found in the specified folder.*",
                    unsafe_allow_html=True,
                )

                # custom_warning("No Excel files found in the specified folder.")
            else:
                # Streamlit dropdown to select a file
                selected_file = st.selectbox(
                    "Select an Excel file to view:", list(excel_files.keys())
                )
                if "confirm_delete" not in st.session_state:
                    st.session_state.confirm_delete = False
                    st.session_state.file_to_delete = None

                # Display the selected file's DataFrame
                if selected_file:
                    st.session_state.filename = selected_file
                    st.session_state.selected_file = excel_files[selected_file]
                    

                    # Create a header for the file
                    st.subheader(f"Contents of {selected_file}")

                    # Use a container to tightly group the buttons
                    with st.container():
                        col1, col2, col3 = st.columns(
                            3
                        )  # Equal-sized columns for buttons
                        with col1:
                            excel_buffer = BytesIO()
                            excel_files[selected_file].to_excel(
                                excel_buffer, index=False, engine="openpyxl"
                            )
                            excel_data = excel_buffer.getvalue()
                            st.download_button(
                                label="⬇ Download",
                                data=excel_data,
                                file_name=selected_file,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )
                        with col2:
                            if st.button("🗑 Delete"):
                                st.session_state.confirm_delete = True
                                st.session_state.file_to_delete = (
                                    f"{PATH}/" + selected_file
                                )
                        with col3:

                            def goto_admin_data():
                                st.session_state.page = "maximize_admin_data"
                            st.button("Maximize", on_click=goto_admin_data)

                    def confirm_delete():
                        if os.path.exists(st.session_state.file_to_delete):
                            os.remove(st.session_state.file_to_delete)
                             # Construct the path to the original file
                            original_file_name = os.path.basename(st.session_state.file_to_delete)
                            original_file_path = os.path.join(ORIGINAL_FILES_PATH, original_file_name)
        
        # Check if the original file exists and delete it
                            if os.path.exists(original_file_path):
                                os.remove(original_file_path)
                            st.success(f"File {selected_file} has been deleted.")
                            st.session_state.confirm_delete = False
                            st.session_state.file_to_delete = None

                    def cancel_delete():
                        st.session_state.confirm_delete = False
                        st.session_state.file_to_delete = None

                    # Confirmation Modal
                    if st.session_state.confirm_delete:
                        custom_warning(
                            f"Are you sure you want to delete {selected_file}?"
                        )
                        confirm_col1, confirm_col2 = st.columns([1, 1])

                        with confirm_col1:
                            st.button("Yes, Delete", on_click=confirm_delete)

                        with confirm_col2:
                            st.button("Cancel", on_click=cancel_delete)

                    render_aggrid(
                        excel_files[selected_file],
                        user_type="admin",
                        filename=selected_file,
                    )

        except Exception as e:
            custom_warning(f"No Excel files found in the specified folder.{e}")
if "user_type" in st.session_state and st.session_state.user_type=="admin":
    if "page" in st.session_state and st.session_state.page == "maximize_admin_data":
        cookies["filename"] = st.session_state.filename
        cookies.save()
        st.switch_page("pages/maximize_admin_data.py")

    admin_panel()
else:
    st.switch_page("pages/login_page.py")