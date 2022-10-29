#!/usr/bin/env python3

import sys
import struct
import json
from datetime import datetime

NULL = 0x7FFF
FORMAT = ">LffhHHhh"

fname = sys.argv[1]
with open(fname) as f, open(fname + ".dat", "rb") as g:
    for i,(line,d) in enumerate(zip(f, struct.iter_unpack(FORMAT, g.read()))):
        print(i)
        print(line.strip())
        print(d)
        print()

        data = json.loads(line)
        t_j = int(datetime.fromisoformat(data["time"]).timestamp())
        dps310_pressure_hPa_j = data["sensors"][0]["readings"]["pressure"]["value"]
        dps310_temp_c_j       = data["sensors"][0]["readings"]["temperature"]["value"]
        scd40_co2_j           = int(data["sensors"][1]["readings"]["CO2"]["value"])
        scd40_temp_c_j        = data["sensors"][1]["readings"]["temperature"]["value"]
        scd40_humid_j         = data["sensors"][1]["readings"]["humidity"]["value"]
        dht22_temp_c_j        = data["sensors"][2]["readings"]["temperature"]["value"]
        dht22_humid_j         = data["sensors"][2]["readings"]["humidity"]["value"]

        t_d, dps310_pressure_hPa_d, dps310_temp_c_d, scd40_co2_d, scd40_temp_bin_d, scd40_humid_bin_d, dht22_temp_c_d, dht22_humid_d = d

        scd40_temp_c_d = -45 + 175 * (scd40_temp_bin_d / 2**16)
        scd40_humid_d = 100 * (scd40_humid_bin_d / 2**16)

        if dht22_temp_c_d == NULL:
            dht22_temp_c_d = None
        else:
            dht22_temp_c_d = dht22_temp_c_d / 10
        
        if dht22_humid_d == NULL:
            dht22_humid_d = None
        else:
            dht22_humid_d = dht22_humid_d / 10
        
        assert t_j == t_d
        assert abs(dps310_pressure_hPa_j - dps310_pressure_hPa_d) < 1e-4
        assert abs(dps310_temp_c_j - dps310_temp_c_d) < 1e-4
        assert scd40_co2_j == scd40_co2_d
        assert scd40_temp_c_j == scd40_temp_c_d
        assert scd40_humid_j == scd40_humid_d
        assert dht22_temp_c_j == dht22_temp_c_d
        assert dht22_humid_j == dht22_humid_d
