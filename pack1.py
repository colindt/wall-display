#!/usr/bin/env python3

import sys
import struct
import json
from datetime import datetime

NULL = 0x7FFF

fname = sys.argv[1]
with open(fname) as f, open(fname + ".dat", "wb") as g:
    for line in f:
        data = json.loads(line)
        t = int(datetime.fromisoformat(data["time"]).timestamp())
        dps310_pressure_hPa = data["sensors"][0]["readings"]["pressure"]["value"]
        dps310_temp_c       = data["sensors"][0]["readings"]["temperature"]["value"]
        scd40_co2           = int(data["sensors"][1]["readings"]["CO2"]["value"])
        scd40_temp_c        = data["sensors"][1]["readings"]["temperature"]["value"]
        scd40_humid         = data["sensors"][1]["readings"]["humidity"]["value"]
        dht22_temp_c        = data["sensors"][2]["readings"]["temperature"]["value"]
        dht22_humid         = data["sensors"][2]["readings"]["humidity"]["value"]

        scd40_temp_bin = int(2**16 * ((scd40_temp_c + 45) / 175))
        scd40_humid_bin = int(2**16 * (scd40_humid / 100))

        if dht22_temp_c is None:
            dht22_temp_c = NULL
        else:
            dht22_temp_c = int(10 * dht22_temp_c)
        
        if dht22_humid is None:
            dht22_humid = NULL
        else:
            dht22_humid = int(10 * dht22_humid)
        
        d = struct.pack(">LffhHHhh", t, dps310_pressure_hPa, dps310_temp_c, scd40_co2, scd40_temp_bin, scd40_humid_bin, dht22_temp_c, dht22_humid)
        print(d.hex())
        print(struct.pack(">L", t).hex(), end=" ")
        print(struct.pack(">f", dps310_pressure_hPa).hex(), end=" ")
        print(struct.pack(">f", dps310_temp_c).hex(), end=" ")
        print(struct.pack(">h", scd40_co2).hex(), end=" ")
        print(struct.pack(">H", scd40_temp_bin).hex(), end=" ")
        print(struct.pack(">H", scd40_humid_bin).hex(), end=" ")
        print(struct.pack(">h", dht22_temp_c).hex(), end=" ")
        print(struct.pack(">h", dht22_humid).hex(), end=" ")
        print()

        g.write(d)
