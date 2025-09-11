import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import folium_static
import plotly.express as px
from rapidfuzz import process
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
from st_aggrid.shared import JsCode
from db import sqlpy
from openai import OpenAI
import os
from docx import Document
from io import BytesIO
import ast
from components.custom_warnings import custom_error, custom_warning
from pages.db_path import db_path
import requests 


@st.cache_resource
def get_database_connection():
    return sqlpy.sqlpy()

conn = get_database_connection()

# Check if connection worked
if not conn or not conn.cursor:
    st.error("🚫 Database is temporarily unavailable.")
    if st.button("🔄 Retry"):
        st.cache_resource.clear()
        st.rerun()
    st.stop()
# Define the path for original files
PATH = db_path()
ORIGINAL_FILES_PATH = os.path.join(PATH, "original_files")

# Ensure the directory exists
os.makedirs(ORIGINAL_FILES_PATH, exist_ok=True)
st.set_page_config(
    page_title="HazMat GIS", page_icon="assets/logo.png", initial_sidebar_state="auto",layout="wide"
)
from streamlit_cookies_manager import EncryptedCookieManager
cookies = EncryptedCookieManager(prefix="leafapp_", password="leaf_left_000")
if not cookies.ready():
    st.stop()
if not conn:
    st.stop()
if cookies.get("logged_in") == "True":
    st.session_state.logged_in = True
PATH = db_path()

    # st.rerun()
def load_country_list(file_path):
    """Load the country list from a file."""
    with open(file_path, "r") as file:
        countries = [line.strip() for line in file.readlines()]
    return countries

@st.cache_data
def get_download_status():
    return conn.get_download_status()



@st.cache_data
def standardize_country_column(column):
    country_list = load_country_list("assets/worldcountries.txt")
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
        "Republic of Korea": "South Korea",
    }

    # cache results locally to avoid recomputation
    cache = {}

    def standardize_name(name):
        if name in cache:
            return cache[name]
        # check for known variations
        if name in country_variations:
            result = country_variations[name]
        else:
            match = process.extractOne(name, country_list)
            result = match[0] if match and match[1] > 80 else "Unknown"
        cache[name] = result
        return result

    # only compute unique names once
    unique_names = column.unique()
    standardized_map = {name: standardize_name(name) for name in unique_names}
    return column.map(standardized_map)

@st.cache_data
def load_world():
    local_path = os.path.join("assets", "world.geojson")
    if not os.path.exists(local_path):
        url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
        with open(local_path, "wb") as f:
            f.write(requests.get(url).content)
    return gpd.read_file(local_path)

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
#################################
import re
@st.cache_data
def merge_original_files(files_signature, folder):
    """
    Merge all original files into a single DataFrame with caching.
    Uses the provided files_signature to track changes.
    """
    print("merging")
    try:
        if not files_signature:
            return None

        dataframes = []
        for file_name, _, _ in files_signature:  # unpack (name, mtime, size)
            file_path = os.path.join(folder, file_name)
            df = pd.read_excel(file_path)
            dataframes.append(df)

        if not dataframes:
            return None

        merged_data = pd.concat(dataframes, ignore_index=True)
        return merged_data

    except Exception as e:
        custom_error(f"Error merging original files: {e}")
        return None


def apply_filters_with_regex(data, filters):
    """
    Apply filters to the data using regex for columns with multiple values.
    Handles comma-separated values in cells.
    """
    type_filter, category_filter, country_filter, impact_filter, severity_filter, search_term = filters

    # Ensure columns are of type string
    for col in ["Type", "Category", "Country", "Impact", "Severity"]:
        if col in data.columns:
            data[col] = data[col].astype(str)

    # Function to split cell values by commas and strip whitespace
    def split_and_strip(value):
        return [v.strip() for v in value.split(",")]

    if type_filter:
        data = data[data["Type"].apply(lambda x: any(re.search(rf'\b{re.escape(t)}\b', v) for v in split_and_strip(x) for t in type_filter))]
    if category_filter:
        data = data[data["Category"].apply(lambda x: any(re.search(rf'\b{re.escape(c)}\b', v) for v in split_and_strip(x) for c in category_filter))]
    if country_filter:
        data = data[data["Country"].apply(lambda x: any(re.search(rf'\b{re.escape(co)}\b', v) for v in split_and_strip(x) for co in country_filter))]
    if impact_filter:
        data = data[data["Impact"].apply(lambda x: any(re.search(rf'\b{re.escape(i)}\b', v) for v in split_and_strip(x) for i in impact_filter))]
    if severity_filter:
        data = data[data["Severity"].apply(lambda x: any(re.search(rf'\b{re.escape(s)}\b', v) for v in split_and_strip(x) for s in severity_filter))]
    if search_term:
        data = data[
            data["Title"].str.contains(search_term, case=False) |
            data["Country"].str.contains(search_term, case=False) |
            data["City"].str.contains(search_term, case=False)
        ]

    return data

def get_files_signature(folder):
    """Create a signature of (filename, last modified time, size) for all Excel files."""
    sig = []
    for file_name in os.listdir(folder):
        if file_name.endswith((".xlsx", ".xls")):
            path = os.path.join(folder, file_name)
            sig.append((file_name, os.path.getmtime(path), os.path.getsize(path)))
    return tuple(sorted(sig))  # hashable, used as cache key


@st.cache_data
def load_data(files_signature, folder):
    print("loading")
    try:
        dataframes = []
        for file_name, _, _ in files_signature:  # unpack 3 values
            file_path = os.path.join(folder, file_name)
            df = pd.read_excel(file_path)
            dataframes.append(df)

        if not dataframes:
            return None

        data = pd.concat(dataframes, ignore_index=True)
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce").dt.normalize()
        data["Country"] = standardize_country_column(data["Country"])
        data["Coordinates"] = data["Coordinates"].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) else None
        )
        data = data.drop_duplicates()
        return data

    except Exception as e:
        custom_error(f"Error Occured while loading Data: {e}")
        st.stop()

@st.cache_data
def group_data_by_title_location_and_date(filtered_data):
    # First, explode the Category column to handle multiple categories per row
    filtered_data = filtered_data.copy()
    filtered_data['Category'] = filtered_data['Category'].str.split(', ')
    filtered_data = filtered_data.explode('Category')
    
    # Then group by Title, Coordinates, City, Country, Date, and Category
    grouped_data = filtered_data.groupby(
        ['Title', 'Coordinates', 'City', 'Country', 'Date', 'Category']
    ).agg({
        'Impact': lambda x: ', '.join(sorted(set(x.astype(str).str.split(', ').explode().unique()))),
        'Severity': 'first',
        'Csuality': 'first',
        'Injuries': 'first',
        'Full Link': 'first',
    }).reset_index()
    
    return grouped_data

#country base+spiral fixed.

def create_folium_map(grouped_data, _world, selected_categories=None):
    if grouped_data is None or _world is None:
        return folium.Map(location=[20, 0], zoom_start=2)

    try:
        if grouped_data is None:
            grouped_data = group_data_by_title_location_and_date(grouped_data)
            if grouped_data is None or grouped_data.empty:
                return folium.Map(location=[20, 0], zoom_start=2)
    except Exception:
        return folium.Map(location=[20, 0], zoom_start=2)

    m = folium.Map(
        location=[20, 0],
        zoom_start=2,
        tiles=None,
        max_bounds=True,
        control_scale=True,
        prefer_canvas=True
    )

    def add_tile_layer(map_obj, tiles, name, attr, overlay=False):
        try:
            folium.TileLayer(
                tiles=str(tiles),
                name=str(name),
                attr=str(attr),
                overlay=bool(overlay),
                control=True
            ).add_to(map_obj)
        except Exception:
            pass

    # Base tile layers
    add_tile_layer(m, "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", "Google Maps", "Google")
    add_tile_layer(m, "CartoDB dark_matter", "Dark Mode", "CartoDB")
    add_tile_layer(
        m,
        "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        "Terrain",
        "Map data: © OpenStreetMap contributors, SRTM | Tiles: © OpenTopoMap (CC-BY-SA)"
    )
    add_tile_layer(m, "OpenStreetMap", "OpenStreetMap", "OpenStreetMap")

    # Always-show Country Borders (not toggleable)
    try:
        folium.GeoJson(
            _world,
            style_function=lambda feature: {
                "fillColor": "transparent",
                "color": "#bcbcbc",
                "weight": 1,
                "fillOpacity": 0.5,
            },
            control=False
        ).add_to(m)
    except Exception:
        pass

    # Safe getter
    def safe_get(obj, key, default=""):
        try:
            val = obj.get(key, default)
            return str(val) if val is not None else default
        except Exception:
            return default

    valid_coords = []
    marker_data = []

    for idx, row in grouped_data.iterrows():
        try:
            coords = row.get("Coordinates")
            if not isinstance(coords, (list, tuple)) or len(coords) != 2:
                continue

            lat, lon = float(coords[0]), float(coords[1])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue

            category = safe_get(row, "Category", "Other").strip()
            if selected_categories and category not in selected_categories:
                continue

            valid_coords.append((lat, lon))
            marker_data.append({
                'coords': (lat, lon),
                'category': category,
                'country': safe_get(row, "Country", "Unknown").strip(),
                'title': safe_get(row, "Title", "No title").strip(),
                'row': row
            })
        except Exception:
            continue

    # Population Density Layer
    try:
        population_layer = folium.FeatureGroup(name="Population Density", show=False)
        pop_data_url = "https://raw.githubusercontent.com/datasets/geo-boundaries-world-110m/master/countries.geojson"

        pop_style = lambda feature: {
            "fillColor": "#ffeda0" if feature["properties"].get("pop_est", 0) < 10000000
                        else "#feb24c" if feature["properties"].get("pop_est", 0) < 50000000
                        else "#f03b20",
            "fillOpacity": 0.5,
            "color": "#333",
            "weight": 0.5,
        }

        folium.GeoJson(
            pop_data_url,
            name="Population Density",
            style_function=pop_style,
            tooltip=folium.GeoJsonTooltip(
                fields=["name", "pop_est"],
                aliases=["Country", "Estimated Population"],
                localize=True
            ),
        ).add_to(population_layer)

        population_layer.add_to(m)
    except Exception:
        pass

    # Marker Clusters
    country_clusters = {}
    marker_layer = folium.FeatureGroup(name='Incident Markers', show=True)

    for data in marker_data:
        try:
            country = data['country']
            if country not in country_clusters:
                country_clusters[country] = MarkerCluster(
                    name=f"{country} Cluster",
                    options={
                        "spiderfyOnMaxZoom": True,
                        "zoomToBoundsOnClick": True,
                    }
                )
                country_clusters[country].add_to(marker_layer)

            icon = folium.Icon(
                icon=get_marker_icon(data['category']),
                prefix="fa",
                color=get_marker_color(data['category']),
            )

            popup_content = create_popup_content(data['row'])
            folium.Marker(
                location=data['coords'],
                popup=folium.Popup(popup_content, max_width=350),
                tooltip=f"{data['title']} ({data['category']})",
                icon=icon,
            ).add_to(country_clusters[country])
        except Exception:
            continue

    marker_layer.add_to(m)

    try:
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
    except Exception:
        pass

    try:
        if valid_coords:
            min_lat = min(c[0] for c in valid_coords)
            max_lat = max(c[0] for c in valid_coords)
            min_lon = min(c[1] for c in valid_coords)
            max_lon = max(c[1] for c in valid_coords)
            m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
        else:
            m.fit_bounds([[-90, -180], [90, 180]])
    except Exception:
        m.fit_bounds([[-90, -180], [90, 180]])

    return m


def get_marker_icon(category):
    icons = {
        "Explosive": "bomb",
        "Biological": "bug",
        "Radiological": "radiation",
        "Chemical": "flask",
        "Nuclear": "atom",
        "Other": "question-circle"  # FontAwesome icon for "Other"
    }
    return icons.get(category, "question-circle")  # Default to "question-circle" if not found


def get_marker_color(category):
    colors = {
        "Explosive": "black",
        "Biological": "green",
        "Radiological": "red",
        "Chemical": "orange",
        "Nuclear": "blue",
        "Other": "gray"  # Color for "Other"
    }
    return colors.get(category, "gray")  # Default to "gray" if not found

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
@st.cache_data
def get_gpt_status_from_conn():
    return conn.get_gpt_status()


@st.cache_data
def get_user_gpt_status_from_conn(user_email):
    return conn.get_user_gpt_status(user_email)


@st.cache_data
def get_gpt_limit_check_from_conn(user_email):
    return conn.get_gpt_limit_check(user_email)

@st.fragment
def render_aggrid_data(df_display, user_type, user_email):
    full_data = df_display.copy()
    gb = GridOptionsBuilder.from_dataframe(df_display, editable=True)
    gb.configure_column("Category", minWidth=100)
    gb.configure_column("Title", minWidth=400)
    gb.configure_column("Country", minWidth=250)
    gb.configure_column("City", minWidth=200)
    gb.configure_column("Date", minWidth=100)
    gb.configure_column("Impact", minWidth=150)
    gb.configure_column("Csuality", minWidth=50)
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
        updateMode=GridUpdateMode.MODEL_CHANGED,
        allow_unsafe_jscode=True,
        height=400,
        theme="streamlit",
        fit_columns_on_grid_load=False,
    )

    selected_row = grid_response.get("selected_rows", [])
    chatgpt_status = get_gpt_status_from_conn()
    if user_type != "admin":
        user_gpt_status = get_user_gpt_status_from_conn(user_email)
        gpt_limit_check = get_gpt_limit_check_from_conn(user_email)

    if chatgpt_status and (
        user_type == "admin" or (user_gpt_status and gpt_limit_check)
    ):
        if "summarize" not in st.session_state:
            st.session_state.summarize = None
            cookies["summarize"] = "False"

        if cookies.get("summarize") == "True":
            if selected_row is not None:
                with st.container(border=True):
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
                                    conn.add_gpt_response(url, response)

                            if user_type != "admin":
                                conn.increase_gpt(user_email)
                                conn.add_gpt_history(user_email, url, title)

                    # Clear loader and display response
                    loader_placeholder.empty()
                    word_file = create_word_file(response)
                    st.download_button(
                        label="Download Response",
                        data=word_file,  # File content as a BytesIO object
                        file_name="response.docx",  # File name with .docx extension
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # MIME type for Word files
                    )
                    st.write(response)

                cookies["summarize"] = "False"
        else:
            if selected_row is not None:
                st.button("Summarize", on_click=summarize)

def create_word_file(content):
    doc = Document()
    doc.add_paragraph(content)  # Add the response text as a paragraph
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)  # Reset the buffer position to the start
    return buffer
def summarize():
    cookies["summarize"] = "True"
    # cookies.save()

def chatgpt_explain(prompt):
    gpt_api_key = os.getenv("gpt_api_key")
    if not gpt_api_key:
        raise ValueError("GPT API key is not set in the environment")
    client = OpenAI(api_key=gpt_api_key)
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
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>Csuality:</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{int(row['Csuality']) if pd.notna(row['Csuality']) else 0}</td>
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



def main_display(user_type, user_email):
    def move_to_admin():
        st.session_state.page = "admin_panel"
        cookies["page"] = "admin_panel"
        cookies.save()
    if st.session_state.page == "admin_panel":
        st.switch_page("pages/admin_panel.py")
    
    if user_type == "admin":
        st.sidebar.button("Admin Panel", use_container_width=True,on_click=move_to_admin)
            
    def move_to_change_password():
        # Set a one-time flag
        st.session_state["__goto_change_password__"] = True

    # Show button
    st.sidebar.button("Change Password", use_container_width=True, on_click=move_to_change_password)

    # Redirect only once, then clear the flag
    if st.session_state.pop("__goto_change_password__", False):
        st.switch_page("pages/change_password.py")


    def logout(user_type):
        st.session_state.page = "Login"
        st.session_state.logged_in = False
        st.session_state.user_email = None
        st.session_state.user_type = None
        cookies["user_email"] = "False"
        cookies["logged_in"] = "False"
        cookies["page"] = "Login"
        cookies["user_type"] = "False"
        cookies.save()

    # Logout Handling
    st.sidebar.button("Logout", use_container_width=True,on_click=logout,args=(user_type,))
    # Perform conditional rendering based on the updated state
    files_signature = get_files_signature(PATH)
    data = load_data(files_signature, PATH)
    if data is not None:
        world = load_world()

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
            filtered_data["Date"] = pd.to_datetime(
                filtered_data["Date"], errors="coerce"
            ).dt.date
            grouped_data = group_data_by_title_location_and_date(filtered_data)

            m = create_folium_map(grouped_data, world, selected_categories)

            folium_static(m, width=900, height=500)
            df = filtered_data.copy()

            df["Category"] = df["Category"].str.split(",")
            df_exploded = df.explode("Category", ignore_index=True)
            df_exploded["Category"] = df_exploded["Category"].str.strip()
            category_counts = df_exploded["Category"].value_counts()

            color_map = {
                "Explosive": "black",
                "Biological": "green",
                "Radiological": "red",
                "Chemical": "orange",
                "Nuclear": "blue",
            }
            temp_df = category_counts.reset_index()
            temp_df.columns = ["Category", "Counts"]
            temp_fig = px.pie(
                temp_df,
                names="Category",
                values="Counts",
                title="Distribution by Category",
                color=category_counts.index.tolist(),
                color_discrete_map=color_map,
            )
            temp_fig.update_layout(
                template="plotly_dark",
                height=400,
                margin=dict(l=150),
                legend_title="Categories",
                legend=dict(
                    orientation="v", yanchor="middle", y=0.5, xanchor="left", x=-0.2
                ),
            )

            temp_fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>",
            )
            st.plotly_chart(temp_fig)

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

            fig2.update_traces(
                hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>"
            )

            st.plotly_chart(fig2, use_container_width=True)

            st.subheader("Trend of Articles Over Time")
# Prepare data for stacked bar chart
            df = filtered_data.copy()
            df["Category"] = df["Category"].str.split(", ")
            df_exploded = df.explode("Category")
            articles_by_date_category = df_exploded.groupby(["Date", "Category"]).size().reset_index(name="count")

# Define color map for categories
            color_map = {
            "Explosive": "black",
            "Biological": "green",
            "Radiological": "red",
            "Chemical": "orange",
           "Nuclear": "blue",
           "Other": "gray"
}

            fig3 = px.bar(
            articles_by_date_category,
            x="Date",
            y="count",
            color="Category",
            labels={"count": "Number of Articles", "Date": "Date"},
            title="Articles Published Over Time",
            color_discrete_map=color_map
)
            fig3.update_layout(
            template="plotly_white",
            height=300,
            xaxis_title="Date",
            yaxis_title="Number of Articles",
            showlegend=True,
            barmode="stack"
)
# Update hover template to ensure correct category-color mapping
            fig3.update_traces(
            hovertemplate="<b>Date</b>: %{x}<br><b>Category</b>: %{fullData.name}<br><b>Articles</b>: %{y}",
            hoverlabel=dict(bgcolor=[color_map[cat] for cat in articles_by_date_category["Category"]])
            )
            st.plotly_chart(fig3, use_container_width=True)
        with tab2:
            st.subheader("Incident Heatmap")

            link_counts = (
                filtered_data.groupby(["Country", "City"])["Full Link"]
                .count()
                .reset_index()
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
                    "Csuality",
                    "Injuries",
                    "Impact",
                    "Severity",
                    "Full Link",
                    "Coordinates",
                ]
            else:
                display_columns = [
                    "Category",
                    "Title",
                    "Country",
                    "City",
                    "Date",
                    "Csuality",
                    "Injuries",
                    "Impact",
                    "Severity",
                    "Full Link",
                ]
            df_display = filtered_data[display_columns].copy()
            df_display["Date"] = pd.to_datetime(
                df_display["Date"], errors="coerce"
            ).dt.strftime("%Y-%m-%d")
            #########################3


            #########################3
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
            data_tab_cols = st.columns((8.6, 1.4))
            download_status = conn.get_user_download_status(user_email)  # Fetch from the database
            with data_tab_cols[0]:
                if download_status == 1:  # Show only if enabled in database
                    files_signatures=get_files_signature(ORIGINAL_FILES_PATH)
                    merged_data = merge_original_files(files_signatures,ORIGINAL_FILES_PATH)
                    if merged_data is not None:
                       filters = [type_filter, category_filter, country_filter, impact_filter, severity_filter, search_term]
                       filtered_original_data = apply_filters_with_regex(merged_data, filters)
                       if "Date" in filtered_original_data.columns:
                            # convert to datetime and normalize (drop time part)
                            filtered_original_data["Date"] = pd.to_datetime(filtered_original_data["Date"], errors="coerce").dt.normalize()

                            # start_date and end_date are already pd.Timestamp in your code
                            # keep rows between start_date and end_date (inclusive)
                            filtered_original_data = filtered_original_data[
                                (filtered_original_data["Date"] >= start_date) & (filtered_original_data["Date"] <= end_date)
                            ]

                            # Generate CSV from the filtered data
                       csv = filtered_original_data.to_csv(index=False)
                       st.download_button(
                       label="Download",
                       data=csv,
                       file_name="filtered_original_data.csv",
                       mime="text/csv",
                        )
                    else:
                        st.warning("No original files found to download.")

            with data_tab_cols[1]:

                def go_to_page():
                    st.session_state.page = "maximize_data"

                # Button with on_click event
                st.button("Maximize", on_click=go_to_page)
            with st.container():
                selected_row = render_aggrid_data(df_display, user_type, user_email)

        st.markdown("---")
        with st.expander("HazMat GIS Disclaimer", expanded=False):
            st.markdown(
                """
            The information presented on the HazMat GIS Dashboard is aggregated from publicly available news articles and other reputable sources. While we strive to ensure the accuracy and timeliness of the data, we cannot guarantee that all information is complete, up-to-date, or free from errors. The incidents, maps, charts, and other visualizations are intended for general informational purposes only.

            Users should not rely solely on the information provided herein for critical decision-making related to hazardous materials or CBRNE (Chemical, Biological, Radiological, Nuclear, Explosive) incidents. We recommend verifying the data with official sources and consulting qualified professionals when necessary.

            By accessing and using this dashboard, you acknowledge and agree that the creators and maintainers of the HazMat GIS Dashboard are not liable for any inaccuracies, omissions, or any outcomes resulting from the use of this information. Use of the dashboard is at your own risk, and you accept full responsibility for any decisions or actions taken based on the data provided.
            """
            )
    else:
        custom_warning("Data Unavailable")
    

if "logged_in" in st.session_state and st.session_state.logged_in:
    st.session_state.user_email = cookies.get("user_email")
    st.session_state.user_type = conn.is_admin(st.session_state.user_email)
    print("usertype: ",st.session_state.user_type)
    if "page" not in st.session_state:
        st.session_state.page = "main_display"
        cookies["page"] = "main_display"
        cookies.save()
    if st.session_state.page == "maximize_data":
        st.switch_page("pages/maximize_data.py")
    
    main_display(st.session_state.user_type, st.session_state.user_email)
else:
    st.switch_page("pages/login_page.py")