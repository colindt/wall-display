#!/usr/bin/env python3
# coding=utf-8

import sys
import os
from time import sleep
from datetime import datetime
import json
from typing import Optional, Sequence

import board                                                    # type: ignore
import adafruit_character_lcd.character_lcd as LCD              # type: ignore
from adafruit_mcp230xx.mcp23017 import MCP23017                 # type: ignore
from adafruit_dps310.advanced import DPS310_Advanced as DPS310  # type: ignore
from adafruit_dps310.advanced import Mode as DPS310_Mode
from adafruit_scd4x import SCD4X                                # type: ignore
from adafruit_dht import DHT22                                  # type: ignore


lcd_pins = {
    "rs"    : 0,
    "en"    : 1,
    "db4"   : 2,
    "db5"   : 3,
    "db6"   : 4,
    "db7"   : 5,
    "red"   : 6,
    "green" : 7,
    "blue"  : 8
}
COLUMNS = 20
ROWS = 4

dht22_pin = board.D12

REFRESH_INTERVAL = 5  # seconds to sleep between each loop


def main():
    print("Initializing...")

    extender = MCP23017(board.I2C())
    
    lcd_io = {k: extender.get_pin(v) for k,v in lcd_pins.items()}
    lcd = LCD.Character_LCD_RGB(columns=COLUMNS, lines=ROWS, **lcd_io)
    lcd.clear()
    lcd.color = (100,100,100)

    try:
        thermometer_dht22 = DHT22(dht22_pin)
    except RuntimeError as e:
        if e.args[0] == "Timed out waiting for PulseIn message. Make sure libgpiod is installed.":
            print("libgpiod required. Run `sudo apt install libgpiod2`")
            sys.exit()
        else:
            raise e
    
    pressure_sensor_dps310 = DPS310(board.I2C())
    pressure_sensor_dps310.initialize()

    co2_sensor_scd40 = SCD4X(board.I2C())
    if co2_sensor_scd40.self_calibration_enabled:
        print("WARNING: CO2 sensor may behave unexpectedly in self calibration mode. Run `calibrate.py` to calibrate it manually.")
        sleep(5)
    co2_sensor_scd40.start_periodic_measurement()
    print("Waiting for CO2 sensor to start...")
    while not co2_sensor_scd40.data_ready:
        sleep(0.1)

    last_log_time = 0

    try:
        while True:
            dps310_pressure_hPa = pressure_sensor_dps310.pressure
            dps310_temp_c = pressure_sensor_dps310.temperature

            co2_sensor_scd40.set_ambient_pressure(round(dps310_pressure_hPa))
            
            scd40_co2 = co2_sensor_scd40.CO2
            scd40_temp_c = co2_sensor_scd40.temperature
            scd40_humid = co2_sensor_scd40.relative_humidity

            dht22_temp_c = None
            dht22_humid = None
            try:
                thermometer_dht22.measure()
                dht22_temp_c = thermometer_dht22.temperature
                dht22_humid = thermometer_dht22.humidity
            except RuntimeError as e:
                print(f"DHT22 error: {e}")
            except OverflowError as e:
                print(f"DHT22 error: OverflowError: {e}")
            
            now = datetime.now()
            now_str = now.isoformat(' ', "seconds")

            data = {
                "time"    : now_str,
                "sensors" : [
                    {
                        "name"     : "dps310",
                        "readings" : {
                            "pressure" : {
                                "value" : dps310_pressure_hPa,
                                "units" : "hPa"
                            },
                            "temperature" : {
                                "value" : dps310_temp_c,
                                "units" : "C"
                            }
                        }
                    },
                    {
                        "name"     : "scd40",
                        "readings" : {
                            "CO2" : {
                                "value" : scd40_co2,
                                "units" : "ppm"
                            },
                            "temperature" : {
                                "value" : scd40_temp_c,
                                "units" : "C"
                            },
                            "humidity" : {
                                "value" : scd40_humid,
                                "units" : r"%rH"
                            }
                        }
                    },
                    {
                        "name"     : "dht22",
                        "readings" : {
                            "temperature" : {
                                "value" : dht22_temp_c,
                                "units" : "C"
                            },
                            "humidity" : {
                                "value" : dht22_humid,
                                "units" : r"%rH"
                            }
                        }
                    }
                ]
            }

            if now.timestamp() - last_log_time >= 60 - REFRESH_INTERVAL:  # log only once per minute or so
                log(data, now)
                last_log_time = now.timestamp()

            avg_temp_c = average((dps310_temp_c, scd40_temp_c, dht22_temp_c))
            avg_humid = average((scd40_humid, dht22_humid))

            dps310_pressure_inHg = hpa2inhg(dps310_pressure_hPa)
            dps310_temp_f = c2f(dps310_temp_c)
            scd40_temp_f  = c2f(scd40_temp_c)
            dht22_temp_f  = c2f(dht22_temp_c)
            avg_temp_f    = c2f(avg_temp_c)

            dht22_temp_f_str = f"{dht22_temp_f:.1f}" if dht22_temp_f is not None else None
            dht22_humid_str  = f"{dht22_humid:.1f}" if dht22_humid is not None else None

            print(f"[{now_str}] {avg_temp_f:.1f}°F ({dps310_temp_f:.1f}/{scd40_temp_f:.1f}/{dht22_temp_f_str})   {avg_humid:.1f}%rH ({scd40_humid:.1f}/{dht22_humid_str})   {dps310_pressure_inHg:.2f}inHg   {scd40_co2}ppm")
            
            date_msg     = f"{now.strftime(r'%a %d %b %Y')}"
            time_msg     = f"{now.strftime(r'%I:%M %p')}"
            error_msg    = "*" if dht22_temp_c is None else ""
            temp_f_msg   = f"{avg_temp_f:.1f}\xdfF"
            temp_c_msg   = f"{avg_temp_c:.1f}\xdfC"
            humid_msg    = f"{avg_humid:.1f}%rH"
            pressure_msg = f"{dps310_pressure_inHg:.2f} inHg"
            co2_msg      = f"{scd40_co2} ppm"

            msg  = f"{msg_line(date_msg, error_msg)}\n"
            msg += f"{msg_line(time_msg, humid_msg)}\n"
            msg += f"{msg_line(temp_f_msg, pressure_msg)}\n"
            msg += f"{msg_line(temp_c_msg, co2_msg)}"
            lcd.message = msg

            sleep(REFRESH_INTERVAL)
    except KeyboardInterrupt:
        print("Exiting")
        pressure_sensor_dps310.mode = DPS310_Mode.IDLE
        co2_sensor_scd40.stop_periodic_measurement()
        thermometer_dht22.exit()
        lcd.clear()
        lcd.color = (0,0,0)
        lcd.display = False


def average(values:Sequence[Optional[float]]) -> float:
    numbers = [i for i in values if i is not None]
    return sum(numbers) / len(numbers)


def spacer(max_length:int, s1:str, s2:str) -> str:
    return ' ' * (max_length - len(s1 + s2))


def msg_line(left:str, right:str, length:int=COLUMNS) -> str:
    return f"{left}{spacer(length, left, right)}{right}"


def log(data, dt:datetime) -> None:
    os.makedirs("logs", exist_ok=True)
    fname = f"logs/{dt.date().isoformat()}.jsonl"
    data_str = json.dumps(data, separators=(',',':'))
    with open(fname, "a") as f:
        f.write(data_str + "\n")


c2f      = lambda c: ((c * 9/5) + 32) if c is not None else None
f2c      = lambda f: (f - 32) * 5/9
hpa2inhg = lambda p: p * 29.92 / 1013.25
inhg2hpa = lambda p: p * 1013.25 / 29.92
m2ft     = lambda m: m / 0.3048
ft2m     = lambda m: m * 0.3048


if __name__ == "__main__":
    main()
