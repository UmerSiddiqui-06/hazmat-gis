import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
import plotly.graph_objs as go
import random
import plotly.express as px
from rapidfuzz import process
from st_aggrid import AgGrid, GridOptionsBuilder
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from streamlit_plotly_events import plotly_events
import datetime
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import JsCode
import re
import utitlity
import time
import io
import base64
from openai import OpenAI
from streamlit_tags import st_tags
import string
import json
from streamlit_js_eval import streamlit_js_eval
from streamlit_modal import Modal
import os
from docx import Document
from io import BytesIO

st.set_page_config(page_title="HazMat GIS",page_icon="logo1.png")

from streamlit_cookies_manager import EncryptedCookieManager
import warnings
import yagmail


cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()


# Connection with database
conn = utitlity.sqlpy()

def load_data():
    dataframes = []
    
    # Iterate over all files in the folder
    for file_name in os.listdir("data"):
        # Build the full file path
        file_path = os.path.join("data", file_name)
        
        # Check if the file is an Excel file
        if file_name.endswith(('.xlsx', '.xls')):
            # Read the Excel file into a DataFrame and append to the list
            df = pd.read_excel(file_path)
            dataframes.append(df)
    
    # Concatenate all DataFrames into a single DataFrame
    data = pd.concat(dataframes, ignore_index=True)
    data["Date"] = pd.to_datetime(data["Date"])
    data['Country'] = standardize_country_column(data['Country'])
    return data

def load_country_list(file_path):
    """Load the country list from a file."""
    with open(file_path, 'r') as file:
        countries = [line.strip() for line in file.readlines()]
    return countries

def standardize_country_column(column):
    country_list = load_country_list("worldcountries.txt")
    country_variations = {
        "UAE": "United Arab Emirates",
        "United Arab Emirates": "United Arab Emirates",
        "USA": "United States",
        "United States": "United States",
        "United States of America": "United States",
        "UK": "United Kingdom",
        "United Kingdom": "United Kingdom",
        "Russia": "Russia",
        "Russian Federation": "Russia",
        "South Korea": "South Korea",
        "Republic of Korea": "South Korea"
    }
    def standardize_name(name):
        # Check for known variations
        if name in country_variations:
            return country_variations[name]
        # Fuzzy match if not in variations
        match = process.extractOne(name, country_list)
        return match[0] if match[1] > 80 else 'Unknown'


    # Apply the standardization function
    return column.apply(standardize_name)

@st.cache_data
def load_world():
    url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
    return gpd.read_file(url)


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

    result = data.apply(geocode_and_correct, axis=1)
    data["Coordinates"] = result["Coordinates"]
    data["City"] = result["City"]
    return data


def get_marker_icon(category):
    icons = {
        "Explosive": "bomb",
        "Biological": "bug",
        "Radiological": "radiation",
        "Chemical": "flask",
        "Nuclear": "atom",
    }
    return icons.get(category, "info-sign")


def get_marker_color(category):
    colors = {
        "Explosive": "black",
        "Biological": "green",
        "Radiological": "red",
        "Chemical": "orange",
        "Nuclear": "blue",
    }
    return colors.get(category, "gray")


def create_popup_content(row):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 300px;">
        <h3 style="color: #3366cc;">{row['Title']}</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Category:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row['Category']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Date:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row['Date']}</td>
            </tr>
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Location:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row['City']}, {row['Country']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Casuality:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row['Casuality']}</td>
            </tr>
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Injuries:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row['Injuries']}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Impact:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row['Impact']}</td>
            </tr>
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Severity:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row['Severity']}</td>
            </tr>
        </table>
        <p style="margin-top: 10px;">
            <a href="{row['Full Link']}" target="_blank" style="color: #3366cc; text-decoration: none;">Read More</a>
        </p>
    </div>
    """
    return html


@st.cache_data
def filter_data(
    data,
    type_filter,
    category_filter,
    country_filter,
    impact_filter,
    severity_filter,
    start_date,
    end_date,
    search_term,
):
    filtered_data = data
    if type_filter:
        filtered_data = filtered_data[filtered_data["Type"].isin(type_filter)]
    if category_filter:
        filtered_data = filtered_data[filtered_data["Category"].isin(category_filter)]
    if country_filter:
        filtered_data = filtered_data[filtered_data["Country"].isin(country_filter)]
    if impact_filter:
        filtered_data = filtered_data[filtered_data["Impact"].isin(impact_filter)]
    if severity_filter:
        filtered_data = filtered_data[filtered_data["Severity"].isin(severity_filter)]

    filtered_data = filtered_data[
        (filtered_data["Date"] >= start_date) & (filtered_data["Date"] <= end_date)
    ]

    if search_term:
        filtered_data = filtered_data[
            filtered_data["Title"].str.contains(search_term, case=False)
            | filtered_data["Country"].str.contains(search_term, case=False)
            | filtered_data["City"].str.contains(search_term, case=False)
        ]

    return filtered_data


from folium.plugins import MarkerCluster


def create_folium_map(filtered_data, world, selected_categories=None):
    m = folium.Map(location=[0, 0], zoom_start=3, tiles=None, max_bounds=True)
    temp_df = filtered_data.copy()

    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Maps",
        overlay=False,
        control=True,
        show=True,
        no_wrap=True,
        min_zoom=1.5,
        max_zoom=18,
        detect_retina=True,
        opacity=1.0,
        subdomains=["mt0", "mt1", "mt2", "mt3"],
        # bounds=[[-90, -180], [90, 180]],
    ).add_to(m)

    folium.GeoJson(
        world,
        style_function=lambda feature: {
            "fillColor": "transparent",
            "color": "#bcbcbc",
            "weight": 1,
            "fillOpacity": 0,
        },
    ).add_to(m)

    marker_cluster = MarkerCluster(
        options={
            "spiderfyOnMaxZoom": True,
            "spiderLegPolylineOptions": {
                "weight": 1.5,
                "color": "#222",
                "opacity": 0.5,
            },
            "zoomToBoundsOnClick": True,
            "noWrap": True,
        }
    ).add_to(m)

    for idx, row in filtered_data.iterrows():
        if pd.notna(row["Coordinates"]):
            if selected_categories is None or row["Category"] in selected_categories:
                icon = folium.Icon(
                    icon=get_marker_icon(row["Category"]),
                    prefix="fa",
                    color=get_marker_color(row["Category"]),
                )

                folium.Marker(
                    location=row["Coordinates"],
                    popup=folium.Popup(create_popup_content(row), max_width=350),
                    tooltip=row["Title"],
                    icon=icon,
                ).add_to(marker_cluster)

    m.fit_bounds([[-90, -180], [90, 180]])

    return m


def create_heatmap(heat_data):
    heatmap = folium.Map(location=[0, 0], zoom_start=2, tiles=None, max_bounds=True)

    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Maps",
        overlay=False,
        control=True,
        show=True,
        no_wrap=True,
        min_zoom=3,
        max_zoom=18,
        max_native_zoom=25,
        detect_retina=True,
        opacity=1.0,
        subdomains=["mt0", "mt1", "mt2", "mt3"],
        bounds=[[-90, -180], [90, 180]],
    ).add_to(heatmap)

    HeatMap(heat_data).add_to(heatmap)

    return heatmap


def valid_email(email):
    email_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(email_regex, email) is not None


def valid_password(password):
    return (
        len(password) >= 8
        and re.search(r"[A-Z]", password)
        and re.search(r"[a-z]", password)
        and re.search(r"\d", password)
    )


def password_generator():
    return random.randint(100000, 999999)


def send_email_code(recipient):
    with open("Texts/email_code.json", "r") as file:
        email_code = json.load(file)
    email = "HazMat.GIS@gmail.com"
    email_password = "edlxeiepcyjasoqg"

    code = password_generator()

    subject = email_code["subject"]
    contents = email_code["contents"].replace("[code]", str(code))

    try:
        yag = yagmail.SMTP(email, email_password)
        yag.send(to=recipient, subject=subject, contents=contents)
    except Exception as e:
        st.error(f"Failed to send verification code")
    return code


def send_request_to_admin(user_email):
    email = "HazMat.GIS@gmail.com"
    email_password = "edlxeiepcyjasoqg"
    admin_email = "HazMat.GIS@gmail.com"
    with open("Texts/email_code.json", "r") as file:
        request_admin = json.load(file)
    subject = request_admin["subject"]
    body = request_admin["contents"].replace("[user_email]", user_email)
    try:
        yag = yagmail.SMTP(email, email_password)
        yag.send(to=admin_email, subject=subject, contents=body)
    except Exception as e:
        st.error(f"Failed to send verification code")


def code_verification(code, email, password):
    columns = st.columns((2.5, 5, 2.5))
    with columns[1]:
        with st.container(border=True):
            passcode = st.text_input("Enter 6-digit verification code: ")
            if st.button("Verify"):
                if not passcode:
                    st.warning("Please enter valid passcode")
                else:
                    if str(code) == passcode:
                        conn.register_user(email, password)
                        st.success("Your Registration Request has been submitted.")
                        send_request_to_admin(email)
                        st.session_state.page = "Login"
                        st.rerun()
                    else:
                        st.error("Wrong Code")


def rejected_page():
    columns = st.columns((2, 6, 2))
    with columns[1]:
        with st.container(border=True):
            st.subheader("Sorry to Say 😔")
            st.error("Your request was not accepted.")
            if st.button("Back to Login Page"):
                st.session_state.page = "Login"
                st.rerun()


def pending_page():
    columns = st.columns((2, 6, 2))
    with columns[1]:
        with st.container(border=True):
            st.subheader("Please Wait ⏳")
            st.warning("Your request has not been accepted yet.")
            if st.button("Back to Login Page"):
                st.session_state.page = "Login"
                st.rerun()


def register_page():
    columns = st.columns((2.5, 5, 2.5))
    with columns[1]:
        with st.container(border=True):
            st.subheader("Register")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Register"):
                if not email:
                    st.warning("Please enter email")
                elif not password:
                    st.warning("Please enter passowrd")
                else:
                    if conn.is_user_exist(email):
                        st.warning("User Already Exists")
                    else:
                        if valid_email(email):
                            if valid_password(password):
                                status = conn.get_status(email)
                                if status == "Rejected":
                                    st.session_state.page = "Rejected"
                                    st.rerun()
                                elif status == "Pending":
                                    st.session_state.page = "Pending"
                                    st.rerun()
                                else:
                                    code = send_email_code(email)
                                    st.session_state.code = code
                                    st.session_state.reg_email = email
                                    st.session_state.reg_password = password
                                    st.session_state.page = "code_verification"
                                    st.rerun()
                            else:
                                st.warning(
                                    "Password must include 1 uppercase, 1 lowercase, 1 number, and be at least 8 characters."
                                )
                        else:
                            st.warning("Invalid Email, Try Again")
            if st.button("Back to Login"):
                st.session_state.page = "Login"
                st.rerun()

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
        </style>
        """,
        unsafe_allow_html=True
    )
    
def login_page():
    centralize_content()
    
    # Logo and title
    c1, c2, c3 = st.columns(3)
    with c2:
        st.image("logo1.png", width=300)  # Add logo
    c1, c2, c3 = st.columns((3.8,7,2))
    with c2:
        st.header("HazMat GIS - Login")
    with st.container(border=True):
        # Login form
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        
        # Forget Password and Register buttons
        col1, col2, col3, col4, col5 = st.columns((2,2,2,2,2.3))
        with col1:
            login_button = st.button("Login")

        if login_button:
            print(st.session_state.logged_in)
            if not email:
                st.warning("Please enter email")
            elif not password:
                st.warning("Please enter password")
            else:
                is_admin = conn.check_login_admin(email, password)
                is_user = conn.check_login_user(email, password)
                if is_admin:
                    st.session_state.logged_in = True
                    cookies["logged_in"] = "True"
                    cookies["user_type"] = "admin"
                    cookies["page"] = "admin_panel"
                    cookies["user_email"] = email
                    st.session_state.page = "admin_panel"
                    st.session_state.user_email = email
                    st.session_state.user_type = "admin"
                    cookies.save()
                    if conn.is_temporary_password(email):
                        show_toast("This is a custom toast notification!")
                    time.sleep(2)
                    st.rerun()
                elif is_user == "Accepted":
                    conn.add_new_login(email)
                    st.session_state.user_email = email
                    st.session_state.logged_in = True
                    st.session_state.user_type = "user"
                    st.session_state.user_email = email
                    st.session_state.page = "main_display"

                    if conn.is_temporary_password(email):
                        show_toast(
                            "Your password is temporary. Please change it immediately!"
                        )
                    time.sleep(3)
                    # cookies['user_email'] = email
                    # cookies['logged_in'] =  'True'
                    # cookies['user_type'] = 'user'
                    # cookies['user_email'] = email
                    # cookies.save()
                    st.rerun()
                elif is_user == "Rejected":
                    st.session_state.page = "Rejected"
                    st.rerun()
                elif is_user == "Pending":
                    st.session_state.page = "Pending"
                    st.rerun()
                else:
                    st.error("Wrong Password, Try Again")
        
            
        with col5:
            if st.button("Forget Password"):
                st.session_state.page = "Forget_Password"
                st.rerun()
        col1, col2 = st.columns((2.5,7.5))
        col1.write("Don't have an account?")
        if col2.button("Register"):
            st.session_state.page = "Register"
            st.rerun()

def get_users():
    return conn.get_users()


def get_download_history():
    return conn.get_download_history()


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
            ],
        )

        emails = list(df["Email"])
        selected_user = st_tags(
            label="Search User",
            text="Enter email to search...",
            value=[],
            suggestions=emails,
            key="3",
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

        df = df.drop(
            [
                "Password",
                "ChatGpt",
                "Status",
                "ChatGpt_used",
                "Stopped Since",
                "gptlimittype",
            ],
            axis=1,
        )
        df.columns = ["ID", "Email", "ChatGpt_limit"]

        # Check for changes in the number of users and reinitialize session states
        if "prev_user_count" not in st.session_state or st.session_state.prev_user_count != len(users):
            st.session_state.prev_user_count = len(users)  # Update user count
            st.session_state.toggle_states_gpt = {
                f"t{i}": gpt_status.iloc[i] for i in range(len(users))
            }
            st.session_state.toggle_states_status = {
                f"t1{i}": login_status[i] for i in range(len(users))
            }
            st.session_state.gpt_limit_state = {
                f"number{i}": gptlimit.iloc[i] for i in range(len(users))
            }

        # Display header
        header_col1, header_col2, header_col3, header_col4, header_col5,header_col6 = st.columns(
            (1, 3, 2, 2, 2,1)
        )
        with header_col1:
            st.markdown("#### ID")
        with header_col2:
            st.markdown("#### Email")
        with header_col3:
            st.markdown("#### Access")
        with header_col4:
            st.markdown("#### GPT Access")
        with header_col5:
            st.markdown("#### GPT Limit")

        # Iterate over the DataFrame rows
        for i, row in df.iterrows():
            col31, col32, col33, col34, col35, col36 = st.columns((1, 3, 2, 2, 2, 1))
            id = row["ID"]
            with col31:
                st.write("")
                st.write(str(row["ID"]))
            with col32:
                st.write("")
                st.write(row["Email"])
            with col34:
                st.write("")
                toggle_key_1 = f"t{i}"
                st.toggle(
                    "Off / On",
                    value=st.session_state.toggle_states_gpt[toggle_key_1],
                    key=toggle_key_1,
                    on_change=toggle_change_callback_gpt,
                    args=(id, toggle_key_1),
                )
            with col33:
                st.write("")
                toggle_key = f"t1{i}"
                st.toggle(
                    "Revoke / Grant",
                    value=st.session_state.toggle_states_status[toggle_key],
                    key=toggle_key,
                    on_change=toggle_change_callback_status,
                    args=(id, toggle_key),
                )
            with col35:
                st.write("")
                number_key = f"number{i}"
                st.number_input(
                    " ",
                    key=number_key,
                    label_visibility="collapsed",
                    value=st.session_state.gpt_limit_state[number_key],
                    step=1,
                    format="%d",
                    on_change=increase_gpt_limit,
                    args=(id, number_key),
                    min_value=0,
                )
            with col36:
                st.write("")
                if st.button("🗑️", key=f"delete_{i}"):
                    st.session_state.show_modal = True
                    st.session_state.delete_email = row["Email"]
                    
            if st.session_state.get("show_modal", False) and st.session_state.get("delete_email", False)==row["Email"]:            
                show_delete_confirmation_modal(st.session_state.delete_email)


def show_delete_confirmation_modal(email):
    """
    Displays a confirmation message before deleting a user.

    Parameters:
        email (str): The email of the user to delete.
    """
    if st.session_state.get("show_modal", False):
        # Display the modal content
        st.warning(f"Are you sure you want to delete the user with email: {email}?")
        col1, col2 = st.columns(2)
        with col1:
            st.button("Yes, Delete",on_click=delete_user,args=(email,))
        with col2:
            st.button("Cancel",on_click=cancel_delete)      
    else:
        # Trigger the modal
        st.session_state.show_modal = True
def delete_user(email):
    conn.delete_user(email)
    st.session_state.show_modal = False
    # st.rerun()

def cancel_delete():
    st.session_state.show_modal = False
    # st.rerun()

def admin_panel():
    
    with st.sidebar:
        # Go Back Button
        if st.button("Go Back"):
            st.session_state.page = "main_display"
            cookies["page"] = "main_display"
            cookies["selected_tab"] = "login_history"
            cookies.save()
            st.rerun()

        # Header for ChatGPT Settings
        st.sidebar.header("ChatGPT Settings")

        # Toggle ChatGPT Status
        # columns = st.sidebar.columns([5, 5])
        # with columns[0]:
        chatgpt = conn.get_gpt_status()
        chatgpt_toggle = st.toggle(
            "Enable ChatGPT",
            value=chatgpt,
            help="Activate or deactivate ChatGPT across the application.",
        )
        if chatgpt_toggle != chatgpt:
            conn.change_gpt_status()

        # # Set GPT Limit
        # with columns[1]:

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
    col1, col2, col3, col4, col5 = st.tabs(
        ["Manage Access", "Login History", "Download History", "GPT Stats","Upload Data"]
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
            gb.configure_column("ID", tooltipField="ID")
            gb.configure_column("Email", tooltipField="Email")
            # gb.configure_column("Password", tooltipField="Password")
            # gb.configure_column("ChatGPT", tooltipField="ChatGPT")
            gb.configure_column("Status", tooltipField="Status")
            # gb.configure_column("ChatGPT Usage", tooltipField="ChatGPT Usage")
            # gb.configure_column("ChatGPT Usage Limit", tooltipField="ChatGPT Usage Limit")
            # gb.configure_column("Stopped Since", tooltipField="Stopped Since")
            gridOptions = gb.build()

            grid_response = AgGrid(
                filtered_df,
                gridOptions=gridOptions,
                enable_enterprise_modules=True,
                update_mode="MODEL_CHANGED",
                height=400,
                fit_columns_on_grid_load=True,
                theme="alpine",
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
                                st.warning("Please select a valid start and end date.")

                        gb = GridOptionsBuilder.from_dataframe(temp_data)
                        # gb.configure_grid_options(rowStyle={"backgroundColor": "white"})
                        gb.configure_grid_options(domLayout="normal")
                        gb.configure_column("Email", tooltipField="Email")
                        gb.configure_column("Time", tooltipField="Time")
                        grid_options = gb.build()

                        # Display with AgGrid
                        AgGrid(
                            temp_data,
                            gridOptions=grid_options,
                            # Themes: 'streamlit', 'light', 'dark', 'balham', 'material'
                            fit_columns_on_grid_load=True,
                            height=200,
                            theme="alpine",
                        )

                    else:
                        st.warning("Not Enough Data")
        else:
            st.warning("Not Enough Data")
    with col3:
        users = conn.get_users()
        # if users:

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
            enable_enterprise_modules=True,
            update_mode="MODEL_CHANGED",
            height=400,  # Set a fixed height for vertical scrolling
            fit_columns_on_grid_load=True,  # Disable auto-fit on initial load
            theme="alpine",
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

        # except Exception as e:
        #     # If there is any error (e.g., in conversion), set values to 0
        #     total_downloads = 0
        #     downloads_this_week = 0
        #     downloads_today = 0
        #     downloads_this_month = 0

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
                        st.warning("Please select a valid start and end date.")

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
                    theme="alpine",  # Themes: 'streamlit', 'light', 'dark', 'balham', 'material'
                    fit_columns_on_grid_load=True,
                    height=200,
                )
            else:
                st.warning("Not Enough Data")
    with col1:
        display_col1()
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
            enable_enterprise_modules=True,
            update_mode="MODEL_CHANGED",
            height=400,
            fit_columns_on_grid_load=True,
            theme="alpine",
            allow_unsafe_jscode=True,
        )
        modal = Modal(key="example_modal", title="Link Details")
        selected_row = grid_response.get("selected_rows", [])
        if selected_row is not None:
            row_data = selected_row.iloc[0]  # Access the first selected row
            if st.button("Show Details"):
                
                with modal.container():  # Use st.container() for a scoped layout
                    link = row_data["Link"]
                    st.markdown(f'''
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
                    ''', unsafe_allow_html=True)
                    response = conn.get_gpt_response(row_data["Link"])
                    def create_word_file(content):
                        doc = Document()
                        doc.add_paragraph(content)  # Add the response text as a paragraph
                        buffer = BytesIO()
                        doc.save(buffer)
                        buffer.seek(0)  # Reset the buffer position to the start
                        return buffer
                    word_file = create_word_file(response)
                    st.download_button(
                        label="Download Response",
                        data=word_file,  # File content as a BytesIO object
                        file_name="response.docx",  # File name with .docx extension
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"  # MIME type for Word files
                    )
                    st.write("Summary Response:", response)  

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
            editable=False, groupable=True
        )  # Default column settings
        gb.configure_selection(selection_mode="multiple")
        grid_options = gb.build()

        grid_response = AgGrid(
            filtered_df,
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            update_mode="MODEL_CHANGED",
            height=400,
            fit_columns_on_grid_load=True,
            theme="alpine",
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
        st.header("Upload Data")
        new_data_file = st.file_uploader(
            "Upload an Excel File", type="xlsx", label_visibility="collapsed"
        )

        if new_data_file:
            # Concatenate Data Button
            filename = st.text_input("Filename:",placeholder="Enter file name without extension")
            if st.button("Add File"):
                if filename:
                    try:
                        new_data = pd.read_excel(new_data_file)
                        columns_to_strip = ["Type", "Category", "Impact", "Severity"]
                        new_data[columns_to_strip] = new_data[columns_to_strip].apply(lambda col: col.str.strip())
                        new_data['Category'] = new_data['Category'].str.title()
                        new_data['Impact'] = new_data['Impact'].str.title()
                        columns_to_clean = ["Type", "Category", "Impact", "Severity"]
                        for column in columns_to_clean:
                            if column in new_data.columns:
                                new_data[column] = new_data[column].str.strip()
                        
                        valid_type = {"Incident", "Activity"}
                        valid_category = {"Explosive", "Biological", "Radiological", "Chemical", "Nuclear"}
                        valid_impact = {"Infrastructure", "Human", "Environmental", "Economic", "Nuclear", "Animal"}
                        valid_severity = {"Low", "Medium"}

                        # Function to check if any value in a comma-separated list is valid
                        def check_validity(value, valid_set):
                            # Split the value by commas, strip whitespace, and check if any part is in the valid set
                            values = {item.strip() for item in value.split(',')}
                            return values.issubset(valid_set)

                        # Apply the validity checks
                        new_data["Type_Valid"] = new_data["Type"].apply(lambda x: check_validity(x, valid_type))
                        new_data["Category_Valid"] = new_data["Category"].apply(lambda x: check_validity(x, valid_category))
                        new_data["Impact_Valid"] = new_data["Impact"].apply(lambda x: check_validity(x, valid_impact))
                        new_data["Severity_Valid"] = new_data["Severity"].apply(lambda x: check_validity(x, valid_severity))

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
                            columns=["Type_Valid", "Category_Valid", "Impact_Valid", "Severity_Valid"]
                        )
                        
                        filename = filename + ".xlsx"
                        new_data.to_excel(f"data/{filename}", index=False)
                        st.success("Data concatenated successfully")

                        # Provide download button for rejected rows
                        dcol,icol = st.columns(2)
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
                        st.error(f"Error occurred: {str(e)}")
                else:
                    st.warning("Please enter filename")

        excel_files = {}
        for file_name in os.listdir("data"):
            if file_name.endswith(('.xlsx', '.xls')):
                file_path = os.path.join("data", file_name)
                excel_files[file_name] = pd.read_excel(file_path)
        
        if not excel_files:
            st.warning("No Excel files found in the specified folder.")
            return
        
        # Streamlit dropdown to select a file
        selected_file = st.selectbox("Select an Excel file to view:", list(excel_files.keys()))
        if "confirm_delete" not in st.session_state:
            st.session_state.confirm_delete = False
            st.session_state.file_to_delete = None
        
        # Display the selected file's DataFrame
        if selected_file:
            # Create a header for the file
            st.subheader(f"Contents of {selected_file}")

            # Use a container to tightly group the buttons
            with st.container():
                col1, col2 = st.columns([1, 1])  # Equal-sized columns for buttons
                with col1:
                    excel_buffer = BytesIO()
                    excel_files[selected_file].to_excel(excel_buffer, index=False, engine='openpyxl')
                    excel_data = excel_buffer.getvalue()
                    st.download_button(
                    label="⬇️ Download",
                    data=excel_data,
                    file_name=selected_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                with col2:
                    if st.button("🗑️ Delete"):
                        st.session_state.confirm_delete = True
                        st.session_state.file_to_delete = "data/" + selected_file
            
            # Confirmation Modal
            if st.session_state.confirm_delete:
                st.warning(f"Are you sure you want to delete {selected_file}?")
                confirm_col1, confirm_col2 = st.columns([1, 1])

                with confirm_col1:
                    if st.button("Yes, Delete"):
                        if os.path.exists(st.session_state.file_to_delete):
                            os.remove(st.session_state.file_to_delete)
                            st.success(f"File {selected_file} has been deleted.")
                            st.session_state.confirm_delete = False
                            st.session_state.file_to_delete = None
                            st.rerun()

                with confirm_col2:
                    if st.button("Cancel"):
                        st.session_state.confirm_delete = False
                        st.session_state.file_to_delete = None


            render_aggrid(excel_files[selected_file],user_type="admin",filename=selected_file)

def increase_gpt_limit(user_id, number_key):
    if st.session_state[number_key] != st.session_state.gpt_limit_state[number_key]:
        st.session_state.gpt_limit_state[number_key] = st.session_state[number_key]
        conn.increase_gpt_limit(user_id, st.session_state[number_key])


def toggle_change_callback_gpt(user_id, toggle_key):
    # Compare with previous value and update if changed
    if st.session_state[toggle_key] != st.session_state.toggle_states_gpt[toggle_key]:
        # Update the toggle state in session and the database
        st.session_state.toggle_states_gpt[toggle_key] = st.session_state[toggle_key]
        conn.change_user_gpt_status(user_id)
        del st.session_state.gpt_limit_state


def toggle_change_callback_status(user_id, toggle_key):
    # Compare with previous value and update if changed
    if (
        st.session_state[toggle_key]
        != st.session_state.toggle_states_status[toggle_key]
    ):
        # Update the toggle state in session and the database
        st.session_state.toggle_states_status[toggle_key] = st.session_state[toggle_key]
        conn.change_status(user_id)


def add_download_history(filters):
    if filters[0] is not None:
        filters_1 = [
            (
                ", ".join(record)
                if isinstance(record, list) and len(record) > 0
                else (None if isinstance(record, list) else record)
            )
            for record in filters
        ]
        conn.add_download_history(
            filters_1[0],
            filters_1[1],
            filters_1[2],
            filters_1[3],
            filters_1[4],
            filters_1[5],
            filters_1[6],
        )


def chatgpt_explain(prompt):
    gpt_api_key = os.getenv("gpt_api_key")
    if not gpt_api_key:
        raise ValueError("GPT API key is not set in the environment")
    client = OpenAI(
        api_key=gpt_api_key
    )
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"An Error Occured while summarizing: {e}"


def summarize():
    cookies["summarize"] = "True"
    # cookies.save()


def render_aggrid(df_display, user_type,filename="temp"):
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
    if user_type=="admin":
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
    grid_options = gb.build()

    grid_response = AgGrid(
        df_display,
        gridOptions=grid_options,
        updateMode=GridUpdateMode.MODEL_CHANGED,
        allow_unsafe_jscode=True,
        height=400,
        theme="streamlit",
        fit_columns_on_grid_load=True,
    )
    if user_type == "admin" and filename!="temp":
        if grid_response['data'] is not None:
            updated_df = pd.DataFrame(grid_response['data'])
            original_data = df_display.reset_index(drop=True)
            updated_data = updated_df.reset_index(drop=True)
            if not updated_data.equals(original_data): 
                if st.button("Save Changes"):
                    
                    # Update only the modified rows and cells
                    for index, row in updated_data.iterrows():
                        if not row.equals(original_data.loc[index]):  # Check if the row has changed
                            for col in updated_data.columns:
                                if row[col] != original_data.loc[index, col]:  # Check specific cell changes
                                    # Find the corresponding index in the full_data DataFrame
                                    full_index = full_data.index[original_data.index[index]]
                                    full_data.loc[full_index, col] = row[col]
                    
                    # Save back the updated Excel file
                    full_data.to_excel(f"data/{filename}", index=False)
                    st.success("Data saved to Excel successfully!")
                    df_display = updated_df
                    time.sleep(1)
                    st.rerun()

    return grid_response.get("selected_rows", [])


def change_password(email):
    st.write(email)
    columns = st.columns((2.5, 5, 2.5))
    with columns[1]:
        st.subheader("Change Password")
        with st.container(border=True):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            is_user = conn.check_login_user(email, current_password)

            is_admin = conn.check_login_admin(email, current_password)
            columns = st.columns((2.5, 4, 3.5))
            with columns[2]:
                update_password = st.button("Update Password")
            with columns[0]:
                go_back = st.button("Go Back", key="back_chng_pass")

            if go_back:
                st.session_state.logged_in = True
                st.session_state.page = "main_display"
                st.rerun()

            elif update_password:
                if is_user:
                    if new_password != confirm_password:
                        st.warning("Passwords do not match!")
                    else:
                        if valid_password(new_password):
                            conn.update_password_users(email, new_password)
                            st.success("Password updated successfully!")
                        else:
                            st.warning(
                                "Password must include 1 uppercase, 1 lowercase, 1 number, and be at least 8 characters."
                            )
                elif is_admin:
                    if new_password != confirm_password:
                        st.warning("Passwords do not match!")
                    else:
                        if valid_password(new_password):
                            conn.update_password_admin(email, new_password)
                            st.success("Password updated successfully!")
                        else:
                            st.warning(
                                "Password must include 1 uppercase, 1 lowercase, 1 number, and be at least 8 characters."
                            )
                else:
                    st.warning("Wrong Password. Try Again")


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


def main_display(user_type, user_email):
    # st.sidebar.image('logo.png',width=120)
    if user_type == "admin":
        if st.sidebar.button("Admin Panel", use_container_width=True):
            st.session_state.page = "admin_panel"
            cookies["page"] = "admin_panel"
            st.rerun()

    if st.sidebar.button("Change Password", use_container_width=True):
        st.session_state.page = "change_password"
        st.rerun()

    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.page = "Login"
        st.session_state.logged_in = False
        st.session_state.user_email = False
        if user_type != "admin":
            st.rerun()
        cookies["user_email"] = "False"
        cookies["logged_in"] = "False"
        cookies["page"] = "Login"
        cookies.save()
        st.rerun()
    data = load_data()
    world = load_world()
    split_rows = data.dropna(subset=["Country", "City"])
    processed_split = (
        split_rows.assign(
            country_city=split_rows.apply(
                lambda row: list(zip(row["Country"].split(", "), row["City"].split(", "))),
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
    missing_rows = data[data[["Country", "City"]].isnull().any(axis=1)]
    final_df = pd.concat([processed_split, missing_rows], ignore_index=True)
    final_df["City"] = final_df["City"].fillna("Unknown")  # Replace NaN with a default value
    final_df["City"] = final_df["City"].astype(str)        # Ensure all values are strings
    final_df["Country"] = final_df["Country"].fillna("Unknown")  # Replace NaN with a default value
    final_df["Country"] = final_df["Country"].astype(str)        # Ensure all values are strings
    # final_df.to_excel("data/First File.xlsx", index=False)
    final_df['Category'] = final_df['Category'].str.split(',')
    df_exploded = final_df.explode('Category', ignore_index=True)
    df_exploded['Category'] = df_exploded['Category'].str.strip()
    data = preprocess_data(df_exploded)

    search_term = st.text_input("Search incidents", "")

    st.sidebar.header("Filters")
    type_filter = st.sidebar.multiselect("Type", data["Type"].unique())
    category_filter = st.sidebar.multiselect("Category", data["Category"].unique())
    country_filter = st.sidebar.multiselect("Country", data["Country"].unique())
    impact_filter = st.sidebar.multiselect("Impact", data["Impact"].unique())
    severity_filter = st.sidebar.multiselect("Severity", data["Severity"].unique())

    st.sidebar.header("Date Range")
    date_filter = st.sidebar.radio(
        "Select time range:",
        ("All Time", "Past Day", "Past Week", "Past Month", "Past Year", "Custom"),
    )

    if date_filter == "Custom":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input(
                "From date",
                value=data["Date"].min().date(),
                min_value=data["Date"].min().date(),
                max_value=data["Date"].max().date(),
            )
        with col2:
            end_date = st.date_input(
                "To date",
                value=data["Date"].max().date(),
                min_value=data["Date"].min().date(),
                max_value=data["Date"].max().date(),
            )
    else:
        end_date = pd.Timestamp.now().date()
        if date_filter == "All Time":
            start_date = data["Date"].min().date()
        elif date_filter == "Past Day":
            start_date = end_date - pd.Timedelta(days=1)
        elif date_filter == "Past Week":
            start_date = end_date - pd.Timedelta(weeks=1)
        elif date_filter == "Past Month":
            start_date = end_date - pd.Timedelta(days=30)
        elif date_filter == "Past Year":
            start_date = end_date - pd.Timedelta(days=365)

    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    filtered_data = filter_data(
        data,
        type_filter,
        category_filter,
        country_filter,
        impact_filter,
        severity_filter,
        start_date,
        end_date,
        search_term,
    )

    tab1, tab2, tab3 = st.tabs(["Incident Map", "Heatmap", "Data"])

    with tab1:
        st.subheader("Incident Map")
        
        selected_categories = st.session_state.get("selected_categories", None)
        m = create_folium_map(filtered_data, world, selected_categories)
        
        folium_static(m, width=900, height=500)
        df = filtered_data.copy()
        df['Category'] = df['Category'].str.split(',')
        df_exploded = df.explode('Category', ignore_index=True)
        df_exploded['Category'] = df_exploded['Category'].str.strip()
        category_counts = df_exploded["Category"].value_counts()
        color_map = {
            "Explosive": "black",
            "Biological": "green",
            "Radiological": "red",
            "Chemical": "orange",
            "Nuclear": "blue",
        }

        fig1 = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title="Distribution by Category",
            color=category_counts.index,
            color_discrete_map=color_map,  # Use the dictionary directly
        )

        fig1.update_layout(
            template="plotly_dark",
            height=400,
            margin=dict(l=150),
            legend_title="Categories",
            legend=dict(
                orientation="v", yanchor="middle", y=0.5, xanchor="left", x=-0.2
            ),
        )

        fig1.update_traces(
            textposition="inside",
            textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>",
        )
        selected_points = plotly_events(fig1, click_event=True, hover_event=False)
        if selected_points:
            selected_category = category_counts.index[selected_points[0]["pointNumber"]]
            st.session_state["selected_categories"] = [selected_category]
        elif "selected_categories" in st.session_state:
            del st.session_state["selected_categories"]

        country_counts = filtered_data["Country"].value_counts().reset_index()
        country_counts.columns = ["Country", "Count"]

        color_sequence = px.colors.qualitative.Set3
        fig2 = px.bar(
            country_counts,
            x="Country",
            y="Count",
            title="Distribution by Country",
            color="Country",
            color_discrete_sequence=color_sequence,
        )

        fig2.update_layout(
            template="plotly_dark",
            height=400,
            xaxis_title="Countries",
            yaxis_title="Count",
            showlegend=False,
            xaxis_tickangle=45,
            hovermode="closest",
            xaxis=dict(showticklabels=False),
        )

        fig2.update_traces(hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>")

        st.plotly_chart(fig2, use_container_width=True)
        
        st.subheader("Trend of Articles Over Time")
        articles_by_date = (
            filtered_data.groupby("Date").size().reset_index(name="count")
        )

        color_scales = [
            px.colors.qualitative.Plotly,
            px.colors.qualitative.D3,
            px.colors.qualitative.G10,
            px.colors.qualitative.T10,
            px.colors.qualitative.Alphabet,
        ]

        all_colors = []
        for scale in color_scales:
            all_colors.extend(scale)

        def is_not_black(color):
            # Convert hex to RGB
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

            return (r + g + b) > 60

        filtered_colors = [color for color in all_colors if is_not_black(color)]
        fig3 = px.bar(
            articles_by_date,
            x="Date",
            y="count",
            labels={"count": "Number of Articles", "Date": "Date"},
            title="Articles Published Over Time",
        )
        fig3.update_layout(
            template="plotly_white",
            height=300,
            # width=300,
            xaxis_title="Date",
            yaxis_title="Number of Articles",
            showlegend=False,
        )
        fig3.update_traces(
            marker_color=filtered_colors,  # Use the filtered color palette
            hovertemplate="<b>Date</b>: %{x}<br><b>Articles</b>: %{y}",
        )
        st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        st.subheader("Incident Heatmap")

        link_counts = (
            filtered_data.groupby(["Country", "City"])["Full Link"].count().reset_index()
        )
        link_counts = link_counts.rename(columns={"Full Link": "LinkCount"})
        heatmap_data = pd.merge(filtered_data, link_counts, on=["Country", "City"])

        heat_data = heatmap_data[heatmap_data["Coordinates"].notna()][
            ["Coordinates", "LinkCount"]
        ]
        heat_data["lat"] = heat_data["Coordinates"].apply(lambda x: x[0])
        heat_data["lon"] = heat_data["Coordinates"].apply(lambda x: x[1])
        heat_data = heat_data[["lat", "lon", "LinkCount"]].values.tolist()

        heatmap = create_heatmap(heat_data)
        folium_static(heatmap, width=1400)

    with tab3:
        st.subheader("Filtered Data")
        if user_type == "admin":
            display_columns = [
                "Category",
                "Title",
                "Country",
                "City",
                "Date",
                "Casuality",
                "Injuries",
                "Impact",
                "Severity",
                "Full Link",
                "Coordinates"
            ]
        else:
            display_columns = [
                "Category",
                "Title",
                "Country",
                "City",
                "Date",
                "Casuality",
                "Injuries",
                "Impact",
                "Severity",
                "Full Link"
            ]
        df_display = filtered_data[display_columns].copy()
        df_display["Date"] = df_display["Date"].dt.strftime("%d-%m-%Y")

        csv = df_display.to_csv(index=False)
        filters = [
            user_email,
            type_filter,
            category_filter,
            country_filter,
            impact_filter,
            severity_filter,
            date_filter,
        ]
        st.download_button(
            label="Download Data",
            data=csv,
            file_name="filtered_data.csv",
            mime="text/csv",
            on_click=add_download_history,
            args=[filters],
        )

        with st.container():
            selected_row = render_aggrid(df_display, user_type)
        chatgpt = conn.get_gpt_status()
        if chatgpt and (
            user_type == "admin"
            or (
                conn.get_user_gpt_status(user_email)
                and conn.get_gpt_limit_check(user_email)
            )
        ):
            if "summarize" not in st.session_state:
                st.session_state.summarize = None
            if cookies.get("summarize") == "True":
                if selected_row is not None:
                    with st.container():
                        st.subheader("Summary")
                        url = selected_row["Full Link"][0]
                        title = selected_row["Title"][0]

                        # Placeholder for loader
                        loader_placeholder = st.empty()

                        with loader_placeholder:
                            # Display loading spinner
                            with st.spinner("Generating response, please wait..."):
                                response = conn.get_gpt_response(url)
                                if not response:
                                    if cookies.get(title) is not None:
                                        response = cookies.get(title)
                                    else:
                                        prompt = f"URL: {url} Title: {title} "
                                        with open("prompt.txt", "r") as file:
                                            content = file.read()
                                        prompt = prompt + content
                                        response = chatgpt_explain(prompt)
                                        cookies[title] = response

                                if user_type != "admin":
                                    conn.increase_gpt(user_email)
                                    conn.add_gpt_history(user_email, url, title)
                                    conn.add_gpt_response(url, response)

                        # Clear loader and display response
                        loader_placeholder.empty()
                        st.download_button(
                            label="Download Response",
                            data=response,  # File content as a string
                            file_name="response.txt",  # File name with .txt extension
                            mime="text/plain"  # MIME type for plain text files
                        )
                        st.write(response)

                    cookies["summarize"] = "False"
            else:
                if selected_row is not None:
                    st.button("Summarize", on_click=summarize)

    st.markdown("---")
    with st.expander("HazMat GIS Disclaimer", expanded=False):
        st.markdown(
            """
        The information presented on the HazMat GIS Dashboard is aggregated from publicly available news articles and other reputable sources. While we strive to ensure the accuracy and timeliness of the data, we cannot guarantee that all information is complete, up-to-date, or free from errors. The incidents, maps, charts, and other visualizations are intended for general informational purposes only.

        Users should not rely solely on the information provided herein for critical decision-making related to hazardous materials or CBRNE (Chemical, Biological, Radiological, Nuclear, Explosive) incidents. We recommend verifying the data with official sources and consulting qualified professionals when necessary.

        By accessing and using this dashboard, you acknowledge and agree that the creators and maintainers of the HazMat GIS Dashboard are not liable for any inaccuracies, omissions, or any outcomes resulting from the use of this information. Use of the dashboard is at your own risk, and you accept full responsibility for any decisions or actions taken based on the data provided.
        """
        )


def generate_temp_password(length=8):
    characters = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choices(characters, k=length))


# Function to check email and send temporary password
def forget_password():
    columns = st.columns((2.5, 5, 2.5))
    with columns[1]:
        with st.container(border=True):
            st.title("Forget Password")

            email = st.text_input("Enter your email")

            columns = st.columns((2.5, 5, 2.5))
            with columns[2]:
                submit = st.button("Submit")
            with columns[0]:
                back_to_login = st.button("Back to Login")

            if submit:
                if not email:
                    st.error("Email is required!")
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
                        st.rerun()

                    except Exception as e:
                        st.error(f"Failed to send email: {e}")
                else:
                    st.error("Email not found!")
            elif back_to_login:
                st.session_state.page = "Login"
                st.rerun()


def main():
    # st.title("HazMat GIS")
    # st.sidebar.image('logo.png',width=120)
    if "page" not in st.session_state:
        st.session_state.page = "Login"

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "user_type" not in st.session_state:
        st.session_state.user_type = None
    if "code" not in st.session_state:
        st.session_state.code = None
    if "reg_email" not in st.session_state:
        st.session_state.reg_email = None
    if "reg_password" not in st.session_state:
        st.session_state.reg_password = None
    if "selected_tab" not in st.session_state:
        st.session_state.selected_tab = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None

    if st.session_state.page == "Forget_Password":
        forget_password()

    elif st.session_state.page == "change_password":
        change_password(st.session_state.user_email)

    elif st.session_state.page == "code_verification":
        code_verification(
            st.session_state.code,
            st.session_state.reg_email,
            st.session_state.reg_password,
        )

    elif st.session_state.page == "Rejected":
        rejected_page()

    elif st.session_state.page == "Pending":
        pending_page()

    elif (
        st.session_state.logged_in == True
        and st.session_state.user_email
        and st.session_state.page not in ["change_password", "admin_panel"]
    ):
        main_display(st.session_state.user_type, st.session_state.user_email)
    else:

        if cookies.get("logged_in") == "True":
            st.session_state.logged_in = True
            st.session_state.page = cookies.get("page")
        else:
            st.session_state.logged_in = False

        if not st.session_state.logged_in:
            if st.session_state.page == "Login":
                login_page()
            if st.session_state.page == "Register":
                register_page()
        else:
            if st.session_state.page == "admin_panel":
                admin_panel()
            else:
                if cookies.get("user_type") == "admin":
                    st.session_state.user_type = "admin"
                elif cookies.get("user_type") == "user":
                    st.session_state.user_type = "user"
                cookies["page"] = "main_display"
                cookies.save()
                st.session_state.user_email = cookies.get("user_email", None)
                if st.session_state.user_email == "False":
                    st.session_state.user_email = None
                main_display(st.session_state.user_type, st.session_state.user_email)


if __name__ == "__main__":
    main()

