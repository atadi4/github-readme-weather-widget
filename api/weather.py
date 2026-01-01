from datetime import datetime
import io
import json
import os
import time
from base64 import b64encode

import configparser
import pytemperature
import requests
from dotenv import load_dotenv, find_dotenv
from flask import Flask, Response, render_template

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

load_dotenv(find_dotenv())

app = Flask(__name__)

# OPENWEATHERMAP_KEY = os.getenv("OPENWEATHERMAP")
OPENWEATHERMAP_KEY = "ab2a6465dac76c16a226e4f1a804433a"
city = config["location"]["city"]
forecast = False
if city and not forecast:
    OPENWEATHERMAP_API_URL = config["api2"]["openweathermap"].format(config["location"]["city"],
                                                                    OPENWEATHERMAP_KEY)
elif forecast:
    OPENWEATHERMAP_API_URL = config["forecast_api"]["openweathermap"].format(config["location"]["city"],
                                                                    OPENWEATHERMAP_KEY)
else:
    OPENWEATHERMAP_API_URL = config["api"]["openweathermap"].format(config["location"]["lat"],
                                                                    config["location"]["lon"],
                                                                    OPENWEATHERMAP_KEY)
ICON_URL = config["icon"]["openweathermap"]
UTC_PLUS = int(config["timezone"]["utc_plus"])
UTC_MINUS = int(config["timezone"]["utc_minus"])
UTC_BALANCE = UTC_PLUS + UTC_MINUS

"""
This program will give wrong output in local.
This is configured for Vercel deployment.
Since it runs on UTC..
"""


def get_user_ip_info():
    return requests.get('https://ipinfo.io').json()

def set_sys_time():
    os.environ["TZ"] = config["timezone"]["sys"]
    time.tzset()


def load_image_b64(url):
    response = requests.get(url)
    return b64encode(response.content).decode("ascii")


def get_weather_widget():
    global config
    weather_data = json.loads(requests.get(OPENWEATHERMAP_API_URL).text)
    print(weather_data)
    current_time = datetime.fromtimestamp(weather_data["dt"] + (UTC_BALANCE * 3600)).strftime("%d %B, %Y - %I:%M:%S %p")
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
    
    # city = config["location"]["city"]
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
        "image": load_image_b64(ICON_URL.format(icon))
    }
    return render_template("widget.html", **w_data)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    svg = get_weather_widget()
    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "s-maxage=1"
    return resp


if __name__ == "__main__":
    app.run(debug=True)
