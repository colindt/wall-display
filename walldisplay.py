#!/usr/bin/env python3
# coding=utf-8

import sys
import os
import time
from datetime import datetime
import json

import board
import adafruit_character_lcd.character_lcd as LCD
from adafruit_mcp230xx.mcp23017 import MCP23017
from adafruit_dps310.advanced import DPS310_Advanced as DPS310
from adafruit_dps310.advanced import Mode as DPS310_Mode
from adafruit_scd4x import SCD4X
from adafruit_dht import DHT22


metric = False

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

dht22_pin = board.D12


def main():
    extender = MCP23017(board.I2C())
    
    lcd_io = {k: extender.get_pin(v) for k,v in lcd_pins.items()}
    lcd = LCD.Character_LCD_RGB(columns=20, lines=4, **lcd_io)
    lcd.clear()
    lcd.color = (100,100,100)
    
    pressure_sensor_dps310 = DPS310(board.I2C())
    pressure_sensor_dps310.initialize()

    co2_sensor_scd40 = SCD4X(board.I2C())
    if co2_sensor_scd40.self_calibration_enabled:
        print("WARNING: CO2 sensor may behave unexpectedly in self calibration mode. Run `calibrate.py` to calibrate it manually.")
        time.sleep(5)
    co2_sensor_scd40.start_periodic_measurement()
    while not co2_sensor_scd40.data_ready:
        time.sleep(0.1)

    try:
        thermometer_dht22 = DHT22(dht22_pin)
    except RuntimeError as e:
        if e.args[0] == "Timed out waiting for PulseIn message. Make sure libgpiod is installed.":
            print("libgpiod required. Run `sudo apt install libgpiod2`")
            sys.exit()
        else:
            raise e

    try:
        while True:
            dps310_pressure = pressure_sensor_dps310.pressure
            dps310_temp = pressure_sensor_dps310.temperature

            co2_sensor_scd40.set_ambient_pressure(round(dps310_pressure))
            
            scd40_co2 = co2_sensor_scd40.CO2
            scd40_temp = co2_sensor_scd40.temperature
            scd40_humid = co2_sensor_scd40.relative_humidity

            dht22_temp = None
            dht22_humid = None
            try:
                thermometer_dht22.measure()
                dht22_temp = thermometer_dht22.temperature
                dht22_humid = thermometer_dht22.humidity
            except RuntimeError as e:
                print(f"DHT22 error: {e}")
            except OverflowError as e:
                print(f"DHT22 error: OverflowError: {e}")
            
            now = datetime.now()

            data = {
                "time"    : now.isoformat(' ', "seconds"),
                "sensors" : [
                    {
                        "name"     : "dps310",
                        "readings" : {
                            "pressure" : {
                                "value" : dps310_pressure,
                                "units" : "hPa"
                            },
                            "temperature" : {
                                "value" : dps310_temp,
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
                                "value" : scd40_temp,
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
                                "value" : dht22_temp,
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

            log(data, now)

            print(f"[{time.asctime()}] {c2f(dps310_temp):.1f}°F {c2f(scd40_temp):.1f}°F {c2f(dht22_temp or 0):.1f}°F  {scd40_humid:.1f}%rH {dht22_humid or 0}%rH  {hpa2inhg(dps310_pressure):.2f}inHg  {scd40_co2}ppm")
            
            time.sleep(5)
    except KeyboardInterrupt:
        print("Exiting")
        pressure_sensor_dps310.mode = DPS310_Mode.IDLE
        co2_sensor_scd40.stop_periodic_measurement()
        thermometer_dht22.exit()
        lcd.clear()
        lcd.color = (0,0,0)
        lcd.display = False


def log(data, dt):
    os.makedirs("logs", exist_ok=True)
    fname = f"logs/{dt.date().isoformat()}.jsonl"
    data_str = json.dumps(data, separators=(',',':'))
    with open(fname, "a") as f:
        f.write(data_str + "\n")


c2f      = lambda c: (c * 9/5) + 32
f2c      = lambda f: (f - 32) * 5/9
hpa2inhg = lambda p: p * 29.92 / 1013.25
inhg2hpa = lambda p: p * 1013.25 / 29.92
m2ft     = lambda m: m / 0.3048
ft2m     = lambda m: m * 0.3048


if __name__ == "__main__":
    main()
