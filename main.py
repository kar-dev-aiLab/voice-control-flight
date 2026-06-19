# main.py

import time

from drone.connection import connect_vehicle
from drone.telemetry import is_armed

def main():
    vehicle = connect_vehicle()
    
    while True:
       
       print(f"Vehicle Armed: {is_armed(vehicle)}")
       time.sleep(1)

if __name__ == "__main__":
    main()