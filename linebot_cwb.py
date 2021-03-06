import os
from flask import Flask, request, abort
import requests
import json

#LINE bot 必要套件
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,ImageMessage,ImageSendMessage
)

app = Flask(__name__)

# Channel Access Token
line_bot_api = LineBotApi("Q2rAm21hU4XU10H4xAC9mH0FHIDrH9p0eEe9Fjdj10RyCOr9iQ/27kTAhjPSCr6COvM/dlLEvqTHhP+zHAD++Pj81IJ+So7v8G1sYln87NMbH/phN7p1SiALO9Us3U2A3ZNmnJo34js0R6gZLTDNUgdB04t89/1O/w1cDnyilFU=")

# Channel Secret
handler = WebhookHandler("5ed2975e9a7813871162fd58e5cba049")


def MakeAQI(station):
    end_point = "https://opendata.cwb.gov.tw/api/v1/rest/datastore/O-A0001-001?Authorization=rdec-key-123-45678-011121314" + \
        station + "'&sort=SiteName&offset=0&limit=1000"

    data = requests.get(end_point)
    AQImsg = ""

    if data.status_code == 500:
        return "無 AQI 資料"
    else:
        AQIdata = data.json()["result"]["records"][0]
        AQImsg += "AQI = " + AQIdata["AQI"] + "\n"
        AQImsg += "PM2.5 = " + AQIdata["PM2.5"] + " μg/m3\n"
        AQImsg += "PM10 = " + AQIdata["PM10"] + " μg/m3\n"
        AQImsg += "空品：" + AQIdata["Status"]
        return AQImsg


def GetWeather(station):
    end_point = "https://opendata.cwb.gov.tw/api/v1/rest/datastore/O-A0001-001?Authorization=rdec-key-123-45678-011121314"

    data = requests.get(end_point).json()
    data = data["records"]["location"]

    target_station = "not found"
    for item in data:
        if item["locationName"] == str(station):
            target_station = item
    return target_station


def MakeWeather(station):
    WeatherData = GetWeather(station)
    if WeatherData == "not found":
        return False

    WeatherData = WeatherData["weatherElement"]
    msg = "天氣報告 - " + station
    msg += "\n\n氣溫 = " + WeatherData[3]["elementValue"] + "℃\n"
    msg += "濕度 = " + \
        str(float(WeatherData[4]["elementValue"]) * 100) + "% RH\n"

    msg += MakeAQI(station)
    return msg


def MakeRailFall(station):
    result = requests.get(
        "https://opendata.cwb.gov.tw/api/v1/rest/datastore/O-A0002-001?Authorization=rdec-key-123-45678-011121314")
    msg = "天氣降雨 - " + station + "\n\n"

    if(result.status_code != 200):
        return "雨量資料讀取失敗"
    else:
        railFallData = result.json()
        for item in railFallData["records"]["location"]:
            if station in item["locationName"]:
                msg += "目前雨量：" + \
                    item["weatherElement"][7]["elementValue"] + "mm\n"
                if item["weatherElement"][3]["elementValue"] == "-998.00":
                    msg += "三小時雨量：0.00mm\n"
                else:
                    msg += "三小時雨量：" + \
                        item["weatherElement"][3]["elementValue"] + "mm\n"
                msg += "日雨量：" + \
                    item["weatherElement"][6]["elementValue"] + "mm\n"
                return msg
        return "沒有這個測站啦"

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    cmd = event.message.text.split(" ")

    if cmd[0] == "天氣":
        station = cmd[1]
        WeatherMsg = MakeWeather(station)

        if not WeatherMsg:
            WeatherMsg = "沒這個氣象站啦"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=WeatherMsg))
    if cmd[0] == "雨量":
        station = cmd[1]
        RailFallMsg = MakeRailFall(station)

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=RailFallMsg))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
