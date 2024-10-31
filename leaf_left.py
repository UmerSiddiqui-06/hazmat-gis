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
from fuzzywuzzy import process
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

st.set_page_config(layout="wide")

from streamlit_cookies_manager import EncryptedCookieManager
import warnings
import yagmail



cookies = EncryptedCookieManager(prefix='leafapp_',password='leaf_left_000')
if not cookies.ready():
    st.stop()


# Connection with database
conn = utitlity.sqlpy()

# Ignore deprecation warnings from Streamlit
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

@st.cache_data
def load_data():
    data = pd.read_excel('News GIS.xlsx', engine='openpyxl')
    data['Date'] = pd.to_datetime(data['Date'])
    return data

@st.cache_data
def load_world():
    url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
    return gpd.read_file(url)

@st.cache_data
def load_world_cities():
    return pd.read_csv('worldcities.csv')

@st.cache_data
def fuzzy_match_city(city_name, limit=5, threshold=70):
    cities = load_world_cities()['city'].unique()
    matches = process.extract(city_name, cities, limit=limit)
    return [match for match, score in matches if score >= threshold]

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
        coords = geocode(row['City'], row['Country'])
        if coords is None:
            matches = fuzzy_match_city(row['City'])
            if matches:
                for match in matches:
                    coords = geocode(match, row['Country'])
                    if coords:
                        row['City'] = match
                        break
        return pd.Series({'Coordinates': coords, 'City': row['City']})

    result = data.apply(geocode_and_correct, axis=1)
    data['Coordinates'] = result['Coordinates']
    data['City'] = result['City']
    return data

def get_marker_icon(category):
    icons = {
        'Explosive': 'bomb',
        'Biological': 'bug',
        'Radiological': 'radiation',
        'Chemical': 'flask',
        'Nuclear': 'atom'
    }
    return icons.get(category, 'info-sign')

def get_marker_color(category):
    colors = {
        'Explosive': 'black',
        'Biological': 'green',
        'Radiological': 'red',
        'Chemical': 'orange',
        'Nuclear': 'blue'
    }
    return colors.get(category, 'gray')

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
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Casualty:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row['Casualty']}</td>
            </tr>
            <tr style="background-color: #f2f2f2;">
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Injury:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{row['Injury']}</td>
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
            <a href="{row['Link']}" target="_blank" style="color: #3366cc; text-decoration: none;">Read More</a>
        </p>
    </div>
    """
    return html

@st.cache_data
def filter_data(data, type_filter, category_filter, country_filter, impact_filter, severity_filter, start_date, end_date, search_term):
    filtered_data = data
    if type_filter:
        filtered_data = filtered_data[filtered_data['Type'].isin(type_filter)]
    if category_filter:
        filtered_data = filtered_data[filtered_data['Category'].isin(category_filter)]
    if country_filter:
        filtered_data = filtered_data[filtered_data['Country'].isin(country_filter)]
    if impact_filter:
        filtered_data = filtered_data[filtered_data['Impact'].isin(impact_filter)]
    if severity_filter:
        filtered_data = filtered_data[filtered_data['Severity'].isin(severity_filter)]
    
    filtered_data = filtered_data[(filtered_data['Date'] >= start_date) & (filtered_data['Date'] <= end_date)]

    if search_term:
        filtered_data = filtered_data[filtered_data['Title'].str.contains(search_term, case=False) |
                                      filtered_data['Country'].str.contains(search_term, case=False) |
                                      filtered_data['City'].str.contains(search_term, case=False)]
    
    return filtered_data

from folium.plugins import MarkerCluster

def create_folium_map(filtered_data, world, selected_categories=None):
    m = folium.Map(location=[0, 0], zoom_start=3, tiles=None, max_bounds=True)

    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps',
        overlay=False,
        control=True,
        show=True,
        no_wrap=True,
        min_zoom=3,
        max_zoom=18,
        detect_retina=True,
        opacity=1.0,
        subdomains=['mt0', 'mt1', 'mt2', 'mt3'],
        bounds=[[-90, -180], [90, 180]]
    ).add_to(m)

    folium.GeoJson(
        world,
        style_function=lambda feature: {
            'fillColor': 'transparent',
            'color': '#bcbcbc',
            'weight': 1,
            'fillOpacity': 0,
        }
    ).add_to(m)

    marker_cluster = MarkerCluster(
        options={
            'spiderfyOnMaxZoom': True,
            'spiderLegPolylineOptions': {'weight': 1.5, 'color': '#222', 'opacity': 0.5},
            'zoomToBoundsOnClick': True,
            'noWrap': True  
        }
    ).add_to(m)

    for idx, row in filtered_data.iterrows():
        if row['Coordinates'] and None not in row['Coordinates']:
            if selected_categories is None or row['Category'] in selected_categories:
                icon = folium.Icon(icon=get_marker_icon(row['Category']), 
                                   prefix='fa', 
                                   color=get_marker_color(row['Category']))
                
                folium.Marker(
                    location=row['Coordinates'],
                    popup=folium.Popup(create_popup_content(row), max_width=350),
                    tooltip=row['Title'],
                    icon=icon
                ).add_to(marker_cluster)


    m.fit_bounds([[-90, -180], [90, 180]])

    return m
def create_heatmap(heat_data):
    heatmap = folium.Map(location=[0, 0], zoom_start=2, tiles=None, max_bounds=True)
    
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
        attr='Google',
        name='Google Maps',
        overlay=False,
        control=True,
        show=True,
        no_wrap=True,
        min_zoom=3,
        max_zoom=18,
        max_native_zoom=25,
        detect_retina=True,
        opacity=1.0,
        subdomains=['mt0', 'mt1', 'mt2', 'mt3'],
        bounds=[[-90, -180], [90, 180]]
    ).add_to(heatmap)

    HeatMap(heat_data).add_to(heatmap)
    
    return heatmap

def valid_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

def valid_password(password):
    return (len(password) >= 8 and 
            re.search(r'[A-Z]', password) and 
            re.search(r'[a-z]', password) and 
            re.search(r'\d', password))

def password_generator():
    return random.randint(100000,999999)

def send_email_code(recipient):
    email = "HazMat.GIS@gmail.com"
    email_password = "edlxeiepcyjasoqg"
    subject = "Your Verification Code for CBRNE"
    code = password_generator()
    body = f"""
    Dear User,

    Thank you for registering with CBRNE. Please use the following code to verify your account:

    **{code}**

    If you did not request this code, please disregard this email.

    Best regards,
    The CBRNE Team
    """
    try:
        yag = yagmail.SMTP(email, email_password)
        yag.send(to=recipient, subject=subject, contents=body)
    except Exception as e:
        st.error(f"Failed to send verification code")
    return code
def send_request_to_admin(user_email):
    email = "HazMat.GIS@gmail.com"
    email_password = "edlxeiepcyjasoqg"
    admin_email = "HazMat.GIS@gmail.com"
    subject = "New User Registration Request"
    body = f"""
    Admin,

    A new user has requested to register for CBRNE. Below are the user's details:

    Email: {user_email}

    
    Please review the registration request here.
    xyz.com

    Best regards,
    The CBRNE System
    """
    try:
        yag = yagmail.SMTP(email, email_password)
        yag.send(to=admin_email, subject=subject, contents=body)
    except Exception as e:
        st.error(f"Failed to send verification code")
def code_verification(code,email,password):
    columns = st.columns((2.5,5,2.5))
    with columns[1]:
        with st.container(border=True):
            passcode = st.number_input('Enter 6-digit verification code: ',0,999999)
            if st.button('Verify'):
                if not passcode:
                    st.warning('Please enter valid passcode')
                else:
                    if code == passcode:
                        conn.register_user(email,password)
                        st.success('Your Registration Request has been submitted.')
                        send_request_to_admin(email)
                        st.session_state.page = 'Login'
                        st.rerun()
                    else:
                        st.error('Wrong Code')

def rejected_page():
    columns = st.columns((2,6,2))
    with columns[1]:
        with st.container(border=True):
            st.subheader('Sorry to Say 😔')
            st.error('Your request was not accepted.')
            if st.button('Back to Login Page'):
                st.session_state.page = 'Login'
                st.rerun()

def pending_page():
    columns = st.columns((2,6,2))
    with columns[1]:
        with st.container(border=True):
            st.subheader('Please Wait ⏳')
            st.warning('Your request has not been accepted yet.')
            if st.button('Back to Login Page'):
                st.session_state.page = 'Login'
                st.rerun()

def register_page():
    columns = st.columns((2.5,5,2.5))
    with columns[1]:
        with st.container(border=True):
            st.subheader('Register')
            email = st.text_input('Email')
            password = st.text_input('Password',type='password')
            if st.button('Register'):
                if not email:
                    st.warning('Please enter email')
                elif not password:
                    st.warning('Please enter passowrd')
                else:
                    if conn.is_user_exist(email):
                        st.warning('User Already Exists')
                    else:
                        if valid_email(email):
                            if valid_password(password):
                                status = conn.get_status(email)
                                if status == 'Rejected':
                                    st.session_state.page = 'Rejected'
                                    st.rerun()
                                elif status == 'Pending':
                                    st.session_state.page = 'Pending'
                                    st.rerun()
                                else:
                                    code = send_email_code(email)
                                    st.session_state.code = code
                                    st.session_state.reg_email = email
                                    st.session_state.reg_password = password
                                    st.session_state.page = 'code_verification'
                                    st.rerun()
                            else:
                                st.warning('Password must include 1 uppercase, 1 lowercase, 1 number, and be at least 8 characters.')
                        else:
                            st.warning('Invalid Email, Try Again')
            if st.button('Back to Login'):
                st.session_state.page = 'Login'
                st.rerun()
def login_page():
    columns = st.columns((2.5,5,2.5))
    with columns[1]:
        with st.container(border=True):
            st.subheader('Login')
            email = st.text_input('Email')
            password = st.text_input('Password',type='password')
            if st.button('Login'):
                print(st.session_state.logged_in)
                if not email:
                    st.warning('Please enter email')
                elif not password:
                    st.warning('Please enter password')
                else:
                    is_admin = conn.check_login_admin(email,password)
                    is_user = conn.check_login_user(email,password)
                    if is_admin:
                        st.session_state.logged_in = True
                        cookies['logged_in'] =  'True'
                        cookies['user_type'] = 'admin'
                        cookies['page'] = 'main_display'
                        cookies.save()  
                        st.rerun()
                    elif is_user == 'Accepted':
                        conn.add_new_login(email)
                        st.session_state.user_email = email
                        st.session_state.logged_in = True
                        cookies['user_email'] = email
                        cookies['logged_in'] =  'True'
                        cookies['user_type'] = 'user'
                        cookies['user_email'] = email
                        cookies.save() 
                        st.rerun()
                    elif is_user == 'Rejected':
                        st.session_state.page = 'Rejected'
                        st.rerun()
                    elif is_user == 'Pending':
                        st.session_state.page = 'Pending'
                        st.rerun()
                    else:
                        st.error('Wrong Password, Try Again')
            col1, col2 = st.columns((3.2,6.8))
            col1.write("Don't have an account? ")
            if col2.button('Register'):
                st.session_state.page = 'Register'
                st.rerun()
def admin_panel_styling():
    # st.sidebar.image('logo.png',width=120)
    # Custom CSS to change the background color
    page_bg_color = '''
        <style>
        [data-testid="stAppViewContainer"] {
            background-color: #161d25;
        }
        [data-testid="stSidebar"] {
            background-color: #577175;
        }
        </style>
    '''

    # Apply the custom background color
    st.markdown(page_bg_color, unsafe_allow_html=True)
    # Custom CSS to change the text color on the main page
    custom_css = '''
        <style>
        /* Targeting the main content area */
        [data-testid="stAppViewContainer"] .main {
            color: #ffffff;  /* Change text color to white */
        }

        /* Target specific headers and text inside the main area */
        [data-testid="stAppViewContainer"] h1, h2, h3, p {
            color: #ffffff;  /* Change the text color of headers and paragraphs to white */
        }
        </style>
    '''

    # Apply the custom text color
    st.markdown(custom_css, unsafe_allow_html=True)

    # Custom CSS for changing the button color
    custom_button_css = '''
        <style>
        /* Target all buttons */
        div.stButton > button {
            background-color: #161d25;  /* Button background color */
            color: white;               /* Button text color */
            border-radius: 10px;        /* Rounded corners */
            border: 2px solid #577175;  /* Border color */
            font-size: 16px;            /* Font size */
            padding: 10px 24px;         /* Padding */
        }
        
        /* Change button color on hover */
        div.stButton > button:hover {
            background-color: #a0b7a9;  /* New background on hover */
            color: black;               /* New text color on hover */
        }
        </style>
    '''

    # Inject the custom CSS for the button
    st.markdown(custom_button_css, unsafe_allow_html=True)

def admin_panel():
    
    admin_panel_styling()

    if st.sidebar.button('Go Back'):
        st.session_state.page = 'main_display'
        cookies['page'] = 'main_display'
        cookies['selected_tab'] = 'login_history'
        cookies.save()
        st.rerun()

    chatgpt = conn.get_gpt_status()

    col1, col2, col3, col4, col5 = st.tabs(['Login History','Download History','Manage Access','Upload Data','ChatGpt'])

    with col1:
        users = conn.get_users()
        st.subheader('Select Users to See Login details: ')
        if users:
            df = pd.DataFrame(users,columns=['ID','Email','Password','ChatGpt','Status'])
            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_pagination(paginationAutoPageSize=True) 
            gb.configure_side_bar()  
            gb.configure_selection('multiple', use_checkbox=True)
            gridOptions = gb.build()

            grid_response = AgGrid(
                df, 
                gridOptions=gridOptions,
                enable_enterprise_modules=True,
                update_mode='MODEL_CHANGED', 
                fit_columns_on_grid_load=True
            )

            selected_users = grid_response.get('selected_rows', [])

            if selected_users is not None:
                st.subheader('Login Information for Selected Users: ')
                users_emails = [user for user in selected_users.iloc[:,1]]   
                users_data = conn.get_login_info(users_emails)
                users_data = pd.DataFrame(users_data,columns=['Email','Time'])
                users_data['Time'] = pd.to_datetime(users_data['Time'])


                selected_filter = st.selectbox('Select Time Filter', ['All Time', 'This Month', 'Today', 'Custom Range'])
                
                temp_data = users_data.copy()
                if not temp_data.empty:
                    if selected_filter == 'This Month':
                        current_month = datetime.datetime.now().month
                        temp_data = temp_data[temp_data['Time'].dt.month == current_month]
                    elif selected_filter == 'Today':
                        current_date = datetime.datetime.now().date()
                        temp_data = temp_data[temp_data['Time'].dt.date == current_date]
                    elif selected_filter == 'Custom Range':
                        start_date = st.date_input('Start Date',temp_data['Time'].min())
                        end_date = st.date_input('End Date',temp_data['Time'].max())
                        temp_data = temp_data[(temp_data['Time'].dt.date >= start_date) & (temp_data['Time'].dt.date <= end_date)]
                    
                    st.write(temp_data)
                else:
                    st.warning('Not Enough Data')
        else:
            st.warning('Not Enough Data')
    with col2:
        data = conn.get_download_history()
        df = pd.DataFrame(data,columns=['Email','Time','Type','Category','Country','Impact','Severity','Date'])
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(True)
        for col in df.columns:
            gb.configure_column(col, tooltipField=col)
        gridOptions = gb.build()

        grid_response = AgGrid(df,gridOptions=gridOptions,fit_columns_on_grid_load=True)
    with col3:
        users = conn.get_users()
        st.subheader('Select User to Change Status:')
        if users:
            df = pd.DataFrame(users,columns=['ID','Email','Password','ChatGpt','Status'])

            gb = GridOptionsBuilder.from_dataframe(df)
            gb.configure_pagination(paginationAutoPageSize=True) 
            gb.configure_side_bar()  
            gb.configure_selection('single', use_checkbox=True)
            gridOptions = gb.build()

            grid_response = AgGrid(
                df, 
                gridOptions=gridOptions,
                enable_enterprise_modules=True,
                update_mode='MODEL_CHANGED', 
                fit_columns_on_grid_load=True
            )

            selected_rows = grid_response.get('selected_rows', [])

            if selected_rows is not None:

                st.write("Selected User(s):")
                st.write(selected_rows)
                already_status = selected_rows.iloc[0,3]

                status_change = st.radio("Change the status of the selected user(s):",('Accepted', 'Rejected'))
                
                if st.button("Submit"):
                    if already_status == status_change:
                        st.warning(f'Status is already {already_status}')
                    else:
                        id = selected_rows.iloc[0,0]
                        if status_change == 'Accepted':
                            conn.accept_user(id)
                        else:
                            conn.reject_user(id)
                        st.success('Status Changed Successfully')
                        time.sleep(1.5)
                        st.rerun()
    with col4:
        new_data = st.file_uploader('Select File', type='xlsx')
        if new_data:
            if st.button('Concatenate'):
                try:
                    old_data = pd.read_excel('News GIS.xlsx')
                    new_data = pd.read_excel(new_data)
                    if len(new_data.columns) == len(old_data.columns) and (new_data.dtypes.values == old_data.dtypes.values).all():
                        result = pd.concat([old_data, new_data], axis=0)
                        result.to_excel('News GIS.xlsx', index=False)
                        st.success('Data concatenated successfully')
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.warning('Invalid Data, Try again with a different file.')
                except Exception as e:
                    st.error(f"Error occurred: {str(e)}")
    with col5:
        st.subheader('ChatGpt Status')
        chatgpt = conn.get_gpt_status()
        button_name = 'Turn Off' if chatgpt else 'Turn On'
        button_gpt,status_gpt = st.columns((2,8))
        with button_gpt:
            if st.button(button_name):
                conn.change_gpt_status()
                st.rerun()
        with status_gpt:
            if chatgpt:
                st.success('ChatGpt Enabled')
            else:
                st.error('ChatGpt Disabled')
        users = conn.get_users()
        if users:
            users = pd.DataFrame(users)
            status = users[3]
            users = users.drop([2, 3, 4], axis=1)
            users.columns = ['ID', 'Email']

            header_col1, header_col2, header_col3 = st.columns((2, 5, 3))
            with header_col1:
                st.markdown("### ID")
            with header_col2:
                st.markdown("### Email")
            with header_col3:
                st.markdown("### Status")

            

            if 'toggle_states' not in st.session_state:
                st.session_state.toggle_states = {f't{i}': status.iloc[i] for i in range(len(users))}

            for i, row in users.iterrows():
                # Create columns for each row dynamically
                col1, col2, col3 = st.columns((2, 5, 3))
                id = row['ID']
                with col1:
                    st.write(row['ID'])
                with col2:
                    st.write(row['Email'])
                with col3:
                    toggle_key = f't{i}'
                    new_value = st.toggle(
                        'Change Status', 
                        value=st.session_state.toggle_states[toggle_key], 
                        key=toggle_key,
                        on_change=toggle_change_callback, 
                        args=(id, toggle_key)
                    )

def toggle_change_callback(user_id, toggle_key):
    # Compare with previous value and update if changed
    if st.session_state[toggle_key] != st.session_state.toggle_states[toggle_key]:
        # Update the toggle state in session and the database
        st.session_state.toggle_states[toggle_key] = st.session_state[toggle_key]
        conn.change_user_gpt_status(user_id)

def add_download_history(filters):
    if filters[0] is not None:
        filters_1 = [
            ', '.join(record) if isinstance(record, list) and len(record) > 0 
            else (None if isinstance(record, list) else record)
            for record in filters
        ]
        conn.add_download_history(filters_1[0],filters_1[1],filters_1[2],filters_1[3],filters_1[4],filters_1[5],filters_1[6])

def chatgpt_explain(prompt):
    client = OpenAI(api_key="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")
    try:
        completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
        return completion.choices[0].message.content
    except Exception as e:
        return f"An Error Occured while summarizing: {e}"
def summarize():
    cookies['summarize'] = 'True'
    # cookies.save()
def main_display(user_type,user_email):
    #st.sidebar.image('logo.png',width=120)
    if user_type == 'admin':
        if st.sidebar.button('Admin Panel',use_container_width=True):
            st.session_state.page = 'admin_panel'
            cookies['page'] = 'admin_panel'
            st.rerun()

    if st.sidebar.button('Logout',use_container_width=True):
        st.session_state.page = 'Login'
        st.session_state.logged_in = False
        cookies['user_email'] = 'False'
        cookies['logged_in'] = 'False'
        cookies['page'] = 'Login'    
        st.rerun()
    data = load_data()
    world = load_world()
        
    data = preprocess_data(data)

    search_term = st.text_input("Search incidents", "")
        
    st.sidebar.header("Filters")
    type_filter = st.sidebar.multiselect("Type", data['Type'].unique())
    category_filter = st.sidebar.multiselect("Category", data['Category'].unique())
    country_filter = st.sidebar.multiselect("Country", data['Country'].unique())
    impact_filter = st.sidebar.multiselect("Impact", data['Impact'].unique())
    severity_filter = st.sidebar.multiselect("Severity", data['Severity'].unique())
        
    st.sidebar.header("Date Range")
    date_filter = st.sidebar.radio(
        "Select time range:",
        ("All Time", "Past Week", "Past Month", "Past Year", "Past Day", "Custom")
    )

    if date_filter == "Custom":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input(
                "From date",
                value=data['Date'].min().date(),
                min_value=data['Date'].min().date(),
                max_value=data['Date'].max().date()
            )
        with col2:
            end_date = st.date_input(
                "To date",
                value=data['Date'].max().date(),
                min_value=data['Date'].min().date(),
                max_value=data['Date'].max().date()
            )
    else:
        end_date = pd.Timestamp.now().date()
        if date_filter == "All Time":
            start_date = data['Date'].min().date()
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

    filtered_data = filter_data(data, type_filter, category_filter, country_filter, impact_filter, severity_filter, start_date, end_date, search_term)

    tab1, tab2, tab3 = st.tabs(["Incident Map", "Heatmap", "Data"])

    with tab1:
        st.subheader("Incident Map")
        

        selected_categories = st.session_state.get('selected_categories', None)
        m = create_folium_map(filtered_data, world, selected_categories)
        

        folium_static(m, width=1400, height=500)
        

        category_counts = filtered_data['Category'].value_counts()
        color_map = {
            'Explosive': 'black',
            'Biological': 'green',
            'Radiological': 'red',
            'Chemical': 'orange',
            'Nuclear': 'blue'
        }

        fig1 = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title="Distribution by Category",
            color=category_counts.index,
            color_discrete_map=color_map  # Use the dictionary directly
        )

        fig1.update_layout(
            template="plotly_dark",
            height=400,
            margin=dict(l=150),
            legend_title="Categories",
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=-0.2
            )
        )

        fig1.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>"
        )
        selected_points = plotly_events(fig1, click_event=True, hover_event=False)
        if selected_points:
            selected_category = category_counts.index[selected_points[0]['pointNumber']]
            st.session_state['selected_categories'] = [selected_category]
        elif 'selected_categories' in st.session_state:
            del st.session_state['selected_categories']


        country_counts = filtered_data['Country'].value_counts().reset_index()
        country_counts.columns = ['Country', 'Count']

    
        color_sequence = px.colors.qualitative.Set3  
        fig2 = px.bar(country_counts, x='Country', y='Count', 
                    title="Distribution by Country",
                    color='Country',  
                    color_discrete_sequence=color_sequence) 

        fig2.update_layout(
            template="plotly_dark", 
            height=400, 
            xaxis_title="Countries", 
            yaxis_title="Count",
            showlegend=False,
            xaxis_tickangle=45,
            hovermode="closest",
            xaxis=dict(showticklabels=False)  
        )

        fig2.update_traces(
            hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>"
        )

        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Trend of Articles Over Time")
        articles_by_date = filtered_data.groupby('Date').size().reset_index(name='count')


        color_scales = [
            px.colors.qualitative.Plotly,
            px.colors.qualitative.D3,
            px.colors.qualitative.G10,
            px.colors.qualitative.T10,
            px.colors.qualitative.Alphabet
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
            x='Date', 
            y='count',
            labels={'count': 'Number of Articles', 'Date': 'Date'},
            title="Articles Published Over Time"
        )
        fig3.update_layout(
            template="plotly_white",
            height=300, 
            xaxis_title="Date", 
            yaxis_title="Number of Articles",
            showlegend=False
        )
        fig3.update_traces(
            marker_color=filtered_colors,  # Use the filtered color palette
            hovertemplate="<b>Date</b>: %{x}<br><b>Articles</b>: %{y}"
        )
        st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        st.subheader("Incident Heatmap")

        link_counts = filtered_data.groupby(['Country', 'City'])['Link'].count().reset_index()
        link_counts = link_counts.rename(columns={'Link': 'LinkCount'})
        heatmap_data = pd.merge(filtered_data, link_counts, on=['Country', 'City'])

        heat_data = heatmap_data[heatmap_data['Coordinates'].notna()][['Coordinates', 'LinkCount']]
        heat_data['lat'] = heat_data['Coordinates'].apply(lambda x: x[0])
        heat_data['lon'] = heat_data['Coordinates'].apply(lambda x: x[1])
        heat_data = heat_data[['lat', 'lon', 'LinkCount']].values.tolist()

        heatmap = create_heatmap(heat_data)
        folium_static(heatmap, width=1400)


    with tab3:
        st.subheader("Filtered Data")
        display_columns = ['Category','Title', 'Country', 'City', 'Date', 'Casualty', 'Injury', 'Impact', 'Severity', 'Link']
        df_display = filtered_data[display_columns].copy()
        df_display['Date'] = df_display['Date'].dt.strftime('%d-%m-%Y')


        csv = df_display.to_csv(index=False)
        filters = [user_email,type_filter,category_filter,country_filter,impact_filter,severity_filter,date_filter]
        st.download_button(label="Download Data",data=csv,file_name="filtered_data.csv",mime="text/csv",on_click=add_download_history,args=[filters])
 
        gb = GridOptionsBuilder.from_dataframe(df_display, editable=True)
        gb.configure_column("Category", minWidth=100)
        gb.configure_column("Title", minWidth=400)
        gb.configure_column("Country", minWidth=250)
        gb.configure_column("City", minWidth=200)
        gb.configure_column("Date", minWidth=100)
        gb.configure_column("Impact", minWidth=150)
        gb.configure_column("Casualty", minWidth=50)
        gb.configure_column("Injury", minWidth=50)
        gb.configure_column('Link', minWidth=100)
        gb.configure_column("Severity", minWidth=100)
        gb.configure_selection('single', use_checkbox=True)
        
        gb.configure_column(
            "Link",
            headerName="Link",
            cellRenderer=JsCode("""
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
            """)
            )

        grid_options = gb.build()

        grid_response = AgGrid(
            df_display,
            gridOptions=grid_options,
            pdateMode=GridUpdateMode.VALUE_CHANGED,
            allow_unsafe_jscode=True,
            height=400,
            theme="streamlit",
            fit_columns_on_grid_load=True,
        )

        selected_row = grid_response.get('selected_rows', [])
        chatgpt = conn.get_gpt_status()
        if chatgpt and (user_type=='admin' or conn.get_user_gpt_status(user_email)):
            if 'summarize' not in st.session_state:
                st.session_state.summarize = None
            if cookies.get('summarize') == 'True':
                if selected_row is not None:
                    # st.write(selected_row['Link'][0])
                    with st.container(border=True):
                        st.subheader('Summary')
                        url = selected_row['Link'][0]
                        title = selected_row['Title'][0]
                        if cookies.get(title) is not None:
                            response = cookies.get(title)
                        else:
                            prompt = f"URL: {url} Title: {title} "
                            with open('prompt.txt', 'r') as file:
                                content = file.read()
                            prompt = prompt + content
                            response = chatgpt_explain(prompt)
                            cookies[title] = response
                        st.write(response)

                    cookies['summarize'] = 'False'
            else:
                if selected_row is not None:
                    st.button('Summarize',on_click=summarize)
                    
    st.markdown("---")  
    with st.expander("HazMat GIS Disclaimer", expanded=False):
        st.markdown("""
        The information presented on the HazMat GIS Dashboard is aggregated from publicly available news articles and other reputable sources. While we strive to ensure the accuracy and timeliness of the data, we cannot guarantee that all information is complete, up-to-date, or free from errors. The incidents, maps, charts, and other visualizations are intended for general informational purposes only.

        Users should not rely solely on the information provided herein for critical decision-making related to hazardous materials or CBRNE (Chemical, Biological, Radiological, Nuclear, Explosive) incidents. We recommend verifying the data with official sources and consulting qualified professionals when necessary.

        By accessing and using this dashboard, you acknowledge and agree that the creators and maintainers of the HazMat GIS Dashboard are not liable for any inaccuracies, omissions, or any outcomes resulting from the use of this information. Use of the dashboard is at your own risk, and you accept full responsibility for any decisions or actions taken based on the data provided.
        """)

def main():
    st.title("HazMat GIS")
    #st.sidebar.image('logo.png',width=120)
    if 'page' not in st.session_state:
        st.session_state.page = 'Login'

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_type' not in st.session_state:
        st.session_state.user_type = None
    if 'code' not in st.session_state:
        st.session_state.code = None
    if 'reg_email' not in st.session_state:
        st.session_state.reg_email = None
    if 'reg_password' not in st.session_state:
        st.session_state.reg_password = None
    if 'selected_tab' not in st.session_state:
        st.session_state.selected_tab = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None

    


    if st.session_state.page == 'code_verification':
        code_verification(st.session_state.code,st.session_state.reg_email,st.session_state.reg_password)

    if st.session_state.page == 'Rejected':
        rejected_page()

    if st.session_state.page == 'Pending':
        pending_page()


    if cookies.get('logged_in') == 'True':
        st.session_state.logged_in = True
        st.session_state.page = cookies.get('page')
    else:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:    
        if st.session_state.page == 'Login':
            login_page()
        if st.session_state.page == 'Register':
            register_page()
    else:
        if st.session_state.page == 'admin_panel':
            admin_panel()
        else:
            if cookies.get('user_type') == 'admin':
                st.session_state.user_type = 'admin'
            elif cookies.get('user_type') == 'user':
                st.session_state.user_type = 'user'
            cookies['page'] = 'main_display'
            cookies.save()
            st.session_state.user_email = cookies.get('user_email',None)
            if st.session_state.user_email == 'False':
                st.session_state.user_email = None
            main_display(st.session_state.user_type,st.session_state.user_email)

if __name__ == "__main__":
    main()
