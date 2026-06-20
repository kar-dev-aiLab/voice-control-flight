# main.py

import time

from drone.connection import connect_vehicle
from drone.telemetry import (is_armed, get_flight_mode)

def main():
    
    vehicle = connect_vehicle()
    
    while True:
       
        mode = get_flight_mode(vehicle)
        armed = is_armed(vehicle)

        print(
            f"Mode: {mode:<10} | Armed: {armed}"
        )

        time.sleep(1)

if __name__ == "__main__":
    main()