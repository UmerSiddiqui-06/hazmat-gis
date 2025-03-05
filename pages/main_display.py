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
import utitlity
from openai import OpenAI
import os
from docx import Document
from io import BytesIO
import ast
from custom_warnings import custom_error, custom_warning
from pages.db_path import db_path
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
if cookies.get("logged_in") == "True":
    st.session_state.logged_in = True
PATH = db_path()
def move_to_change_password():
    st.session_state.page = "change_password"
    # st.rerun()

    # st.rerun()
def load_country_list(file_path):
    """Load the country list from a file."""
    with open(file_path, "r") as file:
        countries = [line.strip() for line in file.readlines()]
    return countries


@st.cache_data
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
        "Republic of Korea": "South Korea",
    }

    def standardize_name(name):
        # Check for known variations
        if name in country_variations:
            return country_variations[name]
        # Fuzzy match if not in variations
        match = process.extractOne(name, country_list)
        return match[0] if match[1] > 80 else "Unknown"

    # Apply the standardization function
    return column.apply(standardize_name)

@st.cache_data
def load_world():
    url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
    return gpd.read_file(url)

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

def load_data():
    try:
        dataframes = []

        # Iterate over all files in the folder
        for file_name in os.listdir(f"{PATH}"):
            # Build the full file path
            file_path = os.path.join(f"{PATH}", file_name)

            # Check if the file is an Excel file
            if file_name.endswith((".xlsx", ".xls")):
                # Read the Excel file into a DataFrame and append to the list
                df = pd.read_excel(file_path)
                dataframes.append(df)
        if len(dataframes) == 0:
            return None
        # Concatenate all DataFrames into a single DataFrame
        data = pd.concat(dataframes, ignore_index=True)
        data["Date"] = pd.to_datetime(data["Date"], errors="coerce").dt.normalize()
        data["Country"] = standardize_country_column(data["Country"])
        data["Coordinates"] = data["Coordinates"].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) else None
        )
        data = data.drop_duplicates()
    except Exception as e:
        custom_error(f"Error Occured while loading Data: {e}")
        st.stop()
    return data
@st.cache_resource
def create_folium_map(filtered_data, _world, selected_categories=None):
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
        _world,
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
        st.session_state.page = "change_password"
    if st.session_state.page == "change_password":
        st.switch_page("pages/change_password.py")
    # Redirect to Change Password Page
    st.sidebar.button("Change Password", use_container_width=True,on_click=move_to_change_password)
        

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
    data = load_data()
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
            m = create_folium_map(filtered_data, world, selected_categories)

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
                    "Casuality",
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
                    "Casuality",
                    "Injuries",
                    "Impact",
                    "Severity",
                    "Full Link",
                ]
            df_display = filtered_data[display_columns].copy()
            df_display["Date"] = pd.to_datetime(
                df_display["Date"], errors="coerce"
            ).dt.strftime("%Y-%m-%d")

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
            with data_tab_cols[0]:
                st.download_button(
                    label="Download Data",
                    data=csv,
                    file_name="filtered_data.csv",
                    mime="text/csv",
                    on_click=add_download_history,
                    args=[filters],
                )
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
    print("admin ",st.session_state.user_type)
    if "page" not in st.session_state:
        st.session_state.page = "main_display"
        cookies["page"] = "main_display"
        cookies.save()
    if st.session_state.page == "maximize_data":
        st.switch_page("pages/maximize_data.py")
    
    main_display(st.session_state.user_type, st.session_state.user_email)
else:
    st.switch_page("pages/login_page.py")