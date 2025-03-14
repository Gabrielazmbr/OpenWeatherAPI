import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from PIL import Image
import io


st.set_page_config(layout='wide',
                   page_title = 'Real-Time OpenWeather API data')



def main_menu():
    st.write('# OpenWeather API')
    sidebar = st.sidebar

    city = sidebar.text_input('City')
    if city=='':
        st.write()
        sidebar.info('Enter a city to begin.')
    st.write(f'## {city.capitalize()}')
    api_key = sidebar.text_input('API KEY', type='password')
    return city, api_key

def weather_api(latitude, longitude, api_key):
    # GeoCoding API
    # Define the API URL with the query parameters
    with st.spinner('Getting weather data...'):
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {
            'lat': latitude,  # City name
            'lon': longitude,     # Limit to 5 results
            'appid': api_key  # Your API key
        }

        # Send the GET request
        response = requests.get(url, params=params)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the response as JSON
            data = response.json()
            print(data)  # Print the data to see the results
            return data
        else:
            print(f"Error: {response.status_code}")

def get_geolocation(city, api_key):
    # GeoCoding API
    # Define the API URL with the query parameters
    with st.spinner('getting geolocation'):
        url = "http://api.openweathermap.org/geo/1.0/direct"
        params = {
            'q': city,  # City name
            'limit': 10,     # Limit to 5 results
            'appid': api_key  # Your API key
        }

        # Send the GET request
        response = requests.get(url, params=params)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the response as JSON
            data = response.json()
            print(data)  # Print the data to see the results
            return data
        else:
            st.error(f"Error: {response.status_code}")


def get_coords(loc_data):
    coords = {}
    for n,i in enumerate(loc_data):
        if [i['lat'],i['lon']] not in coords.values():
            lbl = f'{n}_{i["name"]}_{i["country"]}'
            state = i.get('state',None)
            if state is not None:
                lbl += f'_{i["state"]}'
            coords[lbl] = [i['lat'],i['lon']] 

    return coords

def select_coords(coords):
    coords_vals = [f'({round(i[0], 4)}, {round(i[1],4)})' for i in coords.values()]
    temp = [i.split('_') for i in coords.keys()]
    coords_lbl = []
    for i in temp:
        num = str(int(i[0])+1)
        if len(i)==4:
            coords_lbl.append(f'{num}. {i[1]} ({i[2]}-{i[3]})')
        if len(i)==3:
            coords_lbl.append(f'{num}. {i[1]} ({i[2]})')
    
    coords_text = [f'{coords_lbl[num]}: {coords_vals[num]}' for num, _ in enumerate(coords.items())]
    selection = st.sidebar.radio('Available Coordinates:', coords_text)
    lat_long = coords_vals[coords_text.index(selection)]
    lat, long = eval(lat_long)
    return lat, long

def transform_data(data):
    dates = [i['dt'] for i in data['list']]
    feels_like_k = [i['main']['feels_like'] for i in data['list']]
    feels_like_c = [i-273.15 for i in feels_like_k]
    temp_max_k = [i['main']['temp_max'] for i in data['list']]
    temp_min_k = [i['main']['temp_min'] for i in data['list']]
    temp_max_c = [i-273.15 for i in temp_max_k]
    temp_min_c = [i-273.15 for i in temp_min_k]
    weather_conds = [i['weather'][0]['main'] for i in data['list']]
    weather_icons = [i['weather'][0]['icon'] for i in data['list']]
    humidity = [i['main']['humidity'] for i in data['list']]
    date_time = [datetime.utcfromtimestamp(date) for date in dates]
    formatted_date = [date.strftime('%Y-%m-%d %H:%M:%S') for date in date_time]

    df_data = pd.DataFrame([date_time, temp_min_c, temp_max_c, feels_like_k,feels_like_c, humidity, weather_conds, weather_icons], 
                           index=['date_time', 'temp_min_c', 'temp_max_c','feels_like_k', 'feels_like_c','humidity', 'weather_conds', 'weather_icons']).T
    sunrise = datetime.utcfromtimestamp(data['city']['sunrise'])
    sunset = datetime.utcfromtimestamp(data['city']['sunset'])
    timezone = data['city']['timezone']
    country = data['city']['country']
    hours = timezone // 3600
    timezone_offset = timedelta(seconds=timezone)
    local_sunrise = sunrise + timezone_offset
    local_sunset = sunset + timezone_offset
    extra = {'sunrise':local_sunrise.time(),
             'sunset':local_sunset.time(),
             'timezone':f'UTC{hours}' if hours<0 else f'UTC+{hours}',
             'country':country}
    icons = df_data['weather_icons'].unique()
    icon_dict = {}
    for icon in icons:
        icon_dict[icon] = get_icon_image(icon)
    df_data['icons'] = df_data['weather_icons'].map(icon_dict)
    df_data['formatted_date'] = formatted_date
    return df_data, extra

def show_templine_plot(df):
    df1 = df.rename(columns={'temp_min_c':'Min Temp','temp_max_c':'Max Temp','feels_like_c':'Feels-like Temp'})
    fig = px.line(df1, x='date_time', y=['Min Temp','Max Temp','Feels-like Temp'], title="Temperature")
    fig.update_layout(
        xaxis_title='Date Time',  # Change X axis label
        yaxis_title='°C',   # Change Y axis label
    )
    st.plotly_chart(fig)

def show_humidity_plot(df):
    fig = px.line(df, x='date_time', y=['humidity'], title="Humidity")
    fig.update_layout(
        xaxis_title='Date Time',  # Change X axis label
        yaxis_title='',   # Change Y axis label
    )
    st.plotly_chart(fig)

def show_extra(extra):
    cols = st.columns(len(extra.keys()))
    for n,i in enumerate(extra.keys()):
        with cols[n].container(border=True):
            cols[n].write(f'#### {i.capitalize()}')
            cols[n].write(f'{extra[i]}')

def show_icons(df):
    df['date_weather'] = df['date_time'].apply(lambda date: date.strftime('%a, %b-%d'))
    df['time_weather'] = df['date_time'].apply(lambda date: date.strftime('%H:%M'))
    with st.container(border=True):
        with st.spinner('Retrieving weather conditions...'):
            cols = st.columns(10)
            for n,col in enumerate(cols):
                col.write(df.loc[n,'date_weather'])
                col.write(df.loc[n,'time_weather'])
                col.write(df.loc[n,'weather_conds'])
                col.write(df.loc[n,'icons'])
    

def show_data(data):
    with st.spinner('Loading plots...'):
        st.write('#### 5-day forecast')
        df,extra = transform_data(data)
        show_extra(extra)
        show_templine_plot(df)
        show_icons(df)
        show_humidity_plot(df)


def get_icon_image(icon_code):
    icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png" 
    response = requests.get(icon_url)
    if response.status_code == 200:
        img = Image.open(io.BytesIO(response.content))
        return img
    else:
        print(f"Failed to fetch icon for {icon_code}")
        return None


if __name__ == "__main__":
    city, api_key = main_menu()
    if city != '' and api_key !='':
        loc_data = get_geolocation(city, api_key)
        if loc_data==[]:
            st.error('The input city was not found.')
        else:
            coords = get_coords(loc_data)
            latitude, longitude = select_coords(coords)
            data = weather_api(latitude, longitude, api_key)
            show_data(data)


