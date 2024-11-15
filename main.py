import asyncio
import os
import time
from dataclasses import asdict

import obsws_python as obs
from bambu_connect import BambuClient, PrinterStatus
from dotenv import load_dotenv
from kasa import Discover

load_dotenv()

hostname = os.getenv('HOSTNAME')
access_code = os.getenv('ACCESS_CODE')
serial = os.getenv('SERIAL')
obs_host = os.getenv('OBS_HOST')
obs_port = os.getenv('OBS_PORT')
obs_password = os.getenv('OBS_PASSWORD')
outlet_ip = os.getenv('OUTLET_IP')
username = os.getenv('USERNAME')
password = os.getenv('PASSWORD')
turn_outlet_off = os.getenv('TURN_OUTLET_OFF')

CHAMBER_LIGHT_OFF = '{"system": {"sequence_id": "0", "command": "ledctrl", "led_node": "chamber_light", "led_mode": "off", "led_on_time": 500, "led_off_time": 500, "loop_times": 0, "interval_time": 0}}'


def is_streaming():
    with obs.ReqClient(host=obs_host, port=obs_port, password=obs_password) as req_client:
        return req_client.get_stream_status().output_active


def stream(start):
    print(f"{'Starting' if start else 'Stopping'} stream...")
    with obs.ReqClient(host=obs_host, port=obs_port, password=obs_password) as req_client:
        req_client.start_stream() if start else req_client.stop_stream()


def turn_off_light():
    print("Turning off chamber light...")
    bambu_client.executeClient.send_command(CHAMBER_LIGHT_OFF)


async def turn_off_printer():
    device = await Discover.discover_single(outlet_ip, username=username, password=password)
    await device.update()
    await device.turn_off()


def custom_callback(msg: PrinterStatus):
    status = asdict(msg)
    if status['gcode_state'] == 'RUNNING' and not is_streaming():
        stream(True)
    elif status['gcode_state'] != 'RUNNING' and is_streaming():
        stream(False)
        time.sleep(5)
        turn_off_light()
        if turn_outlet_off == 'True':
            time.sleep(2 * 60)
            asyncio.run(turn_off_printer())


def on_watch_client_connect():
    print("WatchClient connected, Waiting for connection...")
    time.sleep(1)
    bambu_client.dump_info()


bambu_client = BambuClient(hostname, access_code, serial)
bambu_client.start_watch_client(custom_callback, on_watch_client_connect)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Streaming stopped by user.")
    bambu_client.stop_watch_client()
