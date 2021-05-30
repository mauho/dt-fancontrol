#!/usr/bin/python3
# -*- coding: utf-8 -*-

import serial

connected = False


def serial_listener():
    global connected
    try:
        serial_port = serial.Serial("COM3", 57600)
        print("connected ")
        connected = True
        while connected:
            bla = '1'
            serial_port.write(bla.encode())
            print(serial_port.readline()[:-2])

    except serial.SerialException:
        print("Serial Error")


serial_listener()
