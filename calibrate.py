#!/usr/bin/env python3
# coding=utf-8

import time

import board
from adafruit_dps310.advanced import DPS310_Advanced as DPS310
from adafruit_scd4x import SCD4X


p = DPS310(board.I2C())
p.initialize()
c = SCD4X(board.I2C())
c.self_calibration_enabled = False

print("Getting pressure...")
n = 10
pressure = 0
for i in range(n):
    p.wait_pressure_ready()
    _p = p.pressure
    print(_p)
    pressure += _p / n
    time.sleep(1)
pressure = round(pressure)
print(f"pressure = {pressure}\n")

c.set_ambient_pressure(pressure)
print("Warming up CO2 sensor (5 minutes)...")
c.start_periodic_measurement()
t = time.time()
while time.time() - t < 300:
    if c.data_ready:
        print(f"[{time.time() - t:.0f}] {c.CO2}")
    time.sleep(0.1)
print()

try:
    input("Calibrate current CO2 level as 400 ppm? (Enter for yes, ctrl-c for no)")
    c.force_calibration(400)
    c.persist_settings()
    print("Calibrated")
except KeyboardInterrupt:
    print("\nNot Calibrated")
