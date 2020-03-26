from machine import Pin, I2C, Timer, UART
from micropython import mem_info
import response
import urequests
import _thread
import network
import socket
import ssd1306
import json
import time
import dht
import re

mem_info()

ip = "0.0.0.0"
mask = "0.0.0.0"
gw = "0.0.0.0"
dns = "0.0.0.0"
timeout = False
ap = network.WLAN(network.AP_IF)
station = network.WLAN(network.STA_IF)

humidity = 0
temperature = 0
dht11 = dht.DHT11(Pin(25))

i2c = I2C(scl=Pin(15), sda=Pin(4), freq=100000)
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

jsondoc = {
    'Sid_Pwd': [{'ssid': 'example', 'password': 'yourpassword'}]
}

Air = {"PM1_0CF1": "31", "PM2_5CF1": "46", "PM10CF1": "58", "PM1_0AE": "34", "PM2_5AE": "43", "PM10AE": "48",
       "Gt0_3um": "1620", "Gt0_5um": "288", "Gt1_0um": "32", "Gt2_5um"
       : "9", "Gt5_0um": "2", "Gt10um": "1"}


def checkwifi(tim0):
    if not station.isconnected():
        station.disconnect()


def refresh_oled(tim1):
    oled.fill(0)
    dht11.measure()
    global humidity
    global temperature
    humidity = dht11.humidity()
    temperature = dht11.temperature()
    oled.text("I" + ip, 0, 0, col=1)
    oled.text("G" + gw, 0, 9, col=1)
    oled.text("Humidity:" + str(humidity) + "%", 0, 18, col=1)
    oled.text("Temperature:" + str(temperature) + "'C", 0, 27, col=1)  # Celsius ℃
    oled.show()


def configwifi(sid, pwd):
    global station, ap, ip, mask, gw, dns
    station.disconnect()
    station.connect(sid, pwd)
    try:
        for s in range(0, 50):  # i 0-49
            if not station.isconnected():
                time.sleep(0.1)
            else:
                print("Connection successful")
                # print(station.ifconfig())
                return True
    finally:
        ip = station.ifconfig()[0]
        mask = station.ifconfig()[1]
        gw = station.ifconfig()[2]
        dns = station.ifconfig()[3]
    station.disconnect()
    print("out of 5s connect fail......")
    return False


def webserver():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 80))
    s.listen(1)
    print("listen on 80.")
    while True:
        try:
            client, address = s.accept()
            request = client.recv(1024).decode().split('\r\n')
            route = request[0].split(' ')
            print(address, client)
            print(route[1])  # request_url
            # client.sendall('<script>alert("Welcome!");</script>')

            if route[1] == '/':
                client.sendall(response.header200())
                with open('index.html', 'r') as html:
                    client.sendall(html.read())
                sids = station.scan()
                for i in sids:
                    client.sendall(i[0].decode())
                    client.sendall('<br>')

            elif re.match(r'/\?ssid=(.*?)&pwd=(.*)', route[1]):
                obj1 = re.match(r'/\?ssid=(.*?)&pwd=(.*)', route[1])   # sid=obj.group(1);pwd=obj.group(2)

                client.sendall(response.header200())
                client.sendall("<p>Waiting......</p>")

                if not re.match('192.168.4', address[0]):
                    client.sendall("<p>当前访问IP是 {0} ,WIFI连接过程中将中断Web通信,连接结果看OLED屏</p>".format(address[0]))
                    client.close()
                    configwifi(obj1.group(1), obj1.group(2))
                    continue

                if configwifi(obj1.group(1), obj1.group(2)):
                    client.sendall("<p>Connected to {0} </p>".format(obj1.group(1)))
                    savekey(obj1.group(1), obj1.group(2))
                else:
                    client.sendall("<p>Fail......</p>")

            elif route[1] == '/api':
                client.sendall(response.header200('json'))
                client.sendall(json.dumps(Air))

            else:
                client.sendall(response.header404())

            client.close()

        except OSError as e:
            print(e)


def rwjson(c):
    global jsondoc
    try:
        if c:
            with open('wificonfig.json', "r") as f:
                jsondoc = json.loads(f.read())
            f.close()
        else:
            with open('wificonfig.json', "w") as f:
                f.write(json.dumps(jsondoc))
            f.close()
    except:
        pass


def firstload():
    global jsondoc
    rwjson(True)  # 读取json文件里的数据
    station.active(True)
    ssids = station.scan()
    for i in jsondoc['Sid_Pwd']:
        for j in ssids:
            if j[0].decode() == i['ssid']:
                if configwifi(i['ssid'], i['password']):
                    return


def savekey(sid, pwd):
    global jsondoc
    for i in jsondoc['Sid_Pwd']:
        if sid == i['ssid']:
            i['password'] = pwd
            rwjson(False)  # 写入json
            return
    jsondoc['Sid_Pwd'].append({'ssid': sid, 'password': pwd})
    rwjson(False)


def analysis():
    while True:
        if (uart2.any()):
            rec = uart2.read().decode()
            # print(rec)
        time.sleep(0.05)  # 不加延迟且串口没有收到数据的时候会卡死


if __name__ == '__main__':
    tim0 = Timer(0)
    tim1 = Timer(1)
    tim0.init(period=50000, mode=Timer.PERIODIC, callback=checkwifi)  # 检测WiFi是否断线,防止无限重连
    tim1.init(period=1000, mode=Timer.PERIODIC, callback=refresh_oled)  # 一秒刷新一次oled
    # uart1 = UART(1, baudrate=115200, bits=8, rx=9, tx=10, stop=1, timeout=10)   # 串口1串口2，还有一个串口被micropython使用
    uart2 = UART(2, baudrate=115200, bits=8, rx=16, tx=17, stop=1, timeout=10)

    firstload()  # sta加载json文件并自动连接WiFi

    ap.active(True)
    ap.config(essid="ESP32-Webconfig", authmode=4, password="12345678")  # authmode=network.AUTH_WPA_WPA2_PSK=4

    lock = _thread.allocate_lock()

    _thread.start_new_thread(webserver, ())  # 多线程运行webserver
    _thread.start_new_thread(analysis, ()) # 接受串口数据

    # while True:
    #     if (uart2.any()):
    #         rec = uart2.read().decode()
    #         # print(rec)
    #     time.sleep(0.05)  # 不加延迟且串口没有收到数据的时候会卡死
