import requests
import streamlit as st 
import pandas as pd
from datetime import datetime, timedelta
#pip install --upgrade streamlit "pyarrow<15" 
import plotly.express as px

st.set_page_config(page_title = "Weather Dashboard", layout = "wide")


#Changing colour of background/text

st.markdown(
    """
    <style>
    /* Main background */
    .stApp {
        background-color: #f0f8ff;         /*Blue*/
    }

    /* Sidebar background */
    section[data-testid="stSidebar"] {
        background-color: #e6f2ff;         /*Light blue*/
    }

    /* Input widgets: force white background */
    div[data-baseweb="input"] > div {
        background-color: white !important;
        color: black !important;
        border-radius: 6px;
    }

    /* Slider background */
    div[data-baseweb="slider"] {
        background: transparent;
    }

    /* Make titles a bit bolder */
    h1, h2, h3, h4, h5, h6 {
        color: #003366;                    /*Deep Navy*/
    }

    /* General text color */
    .stApp p {
        color: #000000;                    /*Black text*/
    }
    </style>
    """,
    unsafe_allow_html = True
)

#Building an app where user inputs city and the output is a visual weather summary

#Step 1. Convert city and country input to geographical coordinates.

@st.cache_data(ttl=3600)                             #Keeps data cached for 1 hr
def city_to_coordinates(city, country):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{city}, {country}",
        "format": "json",
        "limit": 1
    }
    headers = {
        "User-Agent": "city-coordinates-script/1.0 (mkgithub@icloud.com)"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")
        return None, None

    if response.status_code == 200:
        location_data = response.json()
        if location_data:
            return float(location_data[0]["lat"]), float(location_data[0]["lon"])
        else:
            st.warning("Location not found. Please try again.")
            return None, None
    else:
        st.error(f"API request failed with status code {response.status_code}: {response.text}")
        return None, None

#Step 2. Retrieve weather data for inputted coordinates for the next x days.

@st.cache_data(ttl=600)                     #Keeps data cached for 10 minutes
def weather_data(latitude, longitude, days):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&hourly=temperature_2m,relativehumidity_2m,windspeed_10m&daily=precipitation_sum,temperature_2m_min,temperature_2m_max&timezone=auto&forecast_days={days}"
    response = requests.get(url)
    

    if response.status_code == 200:
        return response.json()
    else:
        st.error("Failed to retrieve weather data for these coordinates. Please try again.")
        return None

#Step 3. Set up user inputs via Streamlit.

st.title("Weather Dashboard")
st.write("Live weather forecasts.")

city_name = st.text_input("Enter city name.", value = "London")
country_name = st.text_input("Enter country name.", value = "UK")

forecast_days = st.slider("Select the number of days.", min_value = 1, max_value = 7, value = 2, step = 1)
    
weather_parameters = st.multiselect("Select which parameters to display (hourly).", options = ["Temperature (°C)", "Humidity (%)", "Wind Speed (km/h)"], 
default = ["Temperature (°C)"])

#Step 4. Display the weather data.

latitude, longitude = city_to_coordinates(city_name, country_name)

if latitude and longitude:
    data = weather_data(latitude, longitude, forecast_days)
    if data and "hourly" in data:

        df = pd.DataFrame({"Time": data["hourly"]["time"][:24*forecast_days]})

        #Converting time to more user-friendly format
        df["Time"] = pd.to_datetime(df["Time"])
        df["Time"] = df["Time"].dt.strftime("%Y-%m-%d %H:%M")

        st.subheader(f"Daily Forecast Summary")
        st.write(f"Min Temperature (°C): ", data["daily"]["temperature_2m_min"][0]) 
        st.write(f"Max Temperature (°C): ", data["daily"]["temperature_2m_max"][0])
        st.write(f"Total rainfall (mm): ", data["daily"]["precipitation_sum"][0]) 
	
        if "Temperature (°C)" in weather_parameters:
            df["Temperature (°C)"] = data["hourly"]["temperature_2m"][:24*forecast_days]

        if "Humidity (%)" in weather_parameters:
            df["Humidity (%)"] = data["hourly"]["relativehumidity_2m"][:24*forecast_days]

        if "Wind Speed (km/h)" in weather_parameters:
            df["Wind Speed (km/h)"] = data["hourly"]["windspeed_10m"][:24*forecast_days]

        view_mode = st.radio(
            "Display mode:",
            options = ["Graph", "Table", "Both"],
            horizontal = True
        )

        if view_mode in ["Table", "Both"]:
            st.subheader(f"Hourly weather forecast for {city_name}")
            st.write(df)

        if view_mode in ["Graph", "Both"]:

            plot_df = df[["Time"] + weather_parameters] #Only keep selected metrics

            #Convert to Plotly format
            plot_df = plot_df.melt(id_vars = "Time", var_name = "Metric", value_name = "Value")

            #Create line chart
            fig = px.line(
                plot_df,
                x = "Time",
                y = "Value",
                color = "Metric",
                title = f"Hourly Weather Forecast for {city_name}",
                markers = True
            )

            fig.update_layout(autosize = True, margin = dict(l = 40, r = 40, t = 40, b = 40))

            #Display in Streamlit
            st.plotly_chart(fig, use_container_width = True)
    
