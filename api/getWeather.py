import io
import json
import os
import time
from base64 import b64encode

import configparser
import pytemperature
import requests
from datetime import datetime
#from dotenv import load_dotenv, find_dotenv
from flask import Flask, Response, render_template, request

current_file_path = os.path.realpath(__file__)
top_path = os.path.dirname(os.path.dirname(current_file_path))

#load_dotenv(find_dotenv())
app = Flask(__name__)

GITHUB_USERNAME = "atadi4"
GITHUB_REPO = "github-readme-weather-widget"
GIT_BRANCH = "main"
CONFIG_FILE_URL = "https://raw.githubusercontent.com/{}/{}/{}/api/config.ini".format(GITHUB_USERNAME,
                                                                                    GITHUB_REPO,
                                                                                    GIT_BRANCH)
CONFIGURATION = requests.get(CONFIG_FILE_URL).text
config_buffer = io.StringIO(CONFIGURATION)
config = configparser.ConfigParser()
config.read_file(config_buffer)

# 获取用户IP地址
def get_user_ip():
    response = requests.get('https://api.ipify.org?format=json')
    data = response.json()
    return data['ip']

def get_userip():
    ip = request.remote_addr
    print("Your ip is: ", ip)
    return ip

# 根据IP地址获取用户地理位置
def get_user_location(ip):
    response = requests.get(f'http://ip-api.com/json/{ip}')
    data = response.json()
    try:
        city, country = data['city'], data['country']
    except Exception:
        city, country = "Suzhou", "Jiangsu"
    return city, country

def get_configs():
    GITHUB_USERNAME = "Charmve"
    GITHUB_REPO = "github-readme-weather-widget"
    GIT_BRANCH = "master"

    CONFIG_FILE_URL = "https://raw.githubusercontent.com/{}/{}/{}/api/config.ini".format(GITHUB_USERNAME,
                                                                                        GITHUB_REPO,
                                                                                        GIT_BRANCH)

    CONFIGURATION = requests.get(CONFIG_FILE_URL).text

    config_buffer = io.StringIO(CONFIGURATION)

    config = configparser.ConfigParser()
    config.read_file(config_buffer)
    print("config:", config)

    return config

def get_openweathermap_api(city, forecast=False):
    OPENWEATHERMAP_KEY = os.getenv("OPENWEATHERMAP")

    global config
    
    if city is None:
        city = config["location"]["city"]
    
    if city and not forecast:
        OPENWEATHERMAP_API_URL = config["api2"]["openweathermap"].format(city,
                                                                        OPENWEATHERMAP_KEY)
    elif forecast:
        OPENWEATHERMAP_API_URL = config["forecast_api"]["openweathermap"].format(city,
                                                                        OPENWEATHERMAP_KEY)
    else:
        OPENWEATHERMAP_API_URL = config["api"]["openweathermap"].format(config["location"]["lat"],
                                                                    config["location"]["lon"],
                                                                    OPENWEATHERMAP_KEY)
    return OPENWEATHERMAP_API_URL

def get_utc_balace():
    global config
    UTC_PLUS = int(config["timezone"]["utc_plus"])
    UTC_MINUS = int(config["timezone"]["utc_minus"])
    UTC_BALANCE = UTC_PLUS + UTC_MINUS

    return UTC_BALANCE

def get_icon_url():
    global config
    ICON_URL = config["icon"]["openweathermap"]

    return ICON_URL

def load_image_b64(url):
    response = requests.get(url)
    return b64encode(response.content).decode("ascii")

def png2base(img_file):
    with open(img_file, "rb") as image_file:
        base64_image = b64encode(image_file.read()).decode('utf-8')

    return base64_image

def get_weather_widget(city, layout="horizontal"):
    global top_path
    api_url = get_openweathermap_api(city)
    weather_data = json.loads(requests.get(api_url).text)
    print(weather_data)
    UTC_BALANCE = get_utc_balace()
    current_time = datetime.fromtimestamp(weather_data["dt"] + UTC_BALANCE).strftime("%d %B, %Y - %I:%M:%S %p")
    temperature = pytemperature.k2c(weather_data["main"]["temp"])
    feels_like = pytemperature.k2c(weather_data["main"]["feels_like"])
    max_temperature = pytemperature.k2c(weather_data["main"]["temp_max"])
    min_temperature = pytemperature.k2c(weather_data["main"]["temp_min"])
    pressure = weather_data["main"]["pressure"]
    wind_speed = weather_data["wind"]["speed"]
    weather_type = weather_data["weather"][0]["main"]
    weather_description = weather_data["weather"][0]["description"]
    sunrise = datetime.fromtimestamp(weather_data["sys"]["sunrise"]).strftime("%I:%M:%S %p")
    sunset = datetime.fromtimestamp(weather_data["sys"]["sunset"]).strftime("%I:%M:%S %p")
    
    city = weather_data["name"]
    country = weather_data["sys"]["country"]
    icon = weather_data["weather"][0]["icon"]

    w_data = {
        "city": city,
        "country": country,
        "current_time": current_time,
        "weather_type": weather_type,
        "weather_description": weather_description,
        "temperature": int(temperature),
        "feels_like": int(feels_like),
        "max_temperature": int(max_temperature),
        "min_temperature": int(min_temperature),
        "sunrise": sunrise,
        "sunset": sunset,
        "pressure": pressure,
        "wind_speed": wind_speed,
        "image": load_image_b64(get_icon_url().format(icon)),
        "image_sunrise": png2base(top_path+"/api/asssets/weather_sunrise_sun_up_sea_icon_156089.png"),
        "image_sunset": png2base(top_path+"/api/asssets/weather_sunset_icon_156092.png")
    }
    
    if layout == "vertical":
        return render_template("widget_v.html", **w_data)
    else:
        return render_template("widget.html", **w_data)

# 获取三天的天气信息
def get_weather_forecast(city):
    # api_key = 'ab2a6465dac76c16a226e4f1a804433a'  # 请替换为您的OpenWeatherMap API密钥
    # url = f'http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric'
    
    api_url = get_openweathermap_api(city, True)
    response = requests.get(api_url)
    data = response.json()
    forecast_data = []
    for item in data['list'][:8]:  # 获取从今天开始往后的三天天气，每天8个数据点
        forecast_data.append({
            'date': datetime.utcfromtimestamp(item['dt']).strftime('%Y-%m-%d %H:%M:%S'),
            'weather': item['weather'][0]['main'],
            'temp': item['main']['temp'],
            'temp_min': item['main']['temp_min'],
            'temp_max': item['main']['temp_max']
        })
    return forecast_data

# 生成SVG图像
def generate_svg(city, country, weather_data):
    svg = f'<svg width="300" height="150" xmlns="http://www.w3.org/2000/svg">'
    svg += f'<text x="10" y="20" font-family="Arial" font-size="14">{city}, {country}</text>'
    y_offset = 40
    for day, data in enumerate(weather_data, 1):
        svg += f'<text x="10" y="{y_offset}" font-family="Arial" font-size="14">Day {day}: {data["date"]} - {data["weather"]}, {data["temp"]}°C</text>'
        y_offset += 20
    svg += '</svg>'
    return svg

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    # user_ip = get_userip()
    # city, country = get_user_location(user_ip)
    city = config["location"]["city"]  # 使用配置文件中的城市
    svg = get_weather_widget(city,)
    weather_forecast = get_weather_forecast(city)
    svg_image = generate_svg(city, country, weather_forecast)
    print(svg_image)

    # 保存SVG图像
    #with open('weather.svg', 'w') as f:
    #    f.write(svg_image)
    
    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "s-maxage=1"
    return resp


if __name__ == "__main__":
    app.run(debug=True)
