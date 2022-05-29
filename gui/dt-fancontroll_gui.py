#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import threading
import time
import math
import numpy as np

from tkinter import *

import serial
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from get_serial_ports import get_serial_ports

master = Tk()
master.title('dT-FanControl')
master.resizable(False, False)

s_min_var = IntVar()
s_max_var = IntVar()
s_slope_var = DoubleVar()
s_attack_var = DoubleVar()

s_min_var.set(18)
s_max_var.set(100)
s_slope_var.set(-0.40)
s_attack_var.set(6.0)

try:
    with open('last_values.json') as json_file:
        last_values = json.load(json_file)
        s_min_var.set(last_values['s_min'])
        s_max_var.set(last_values['s_max'])
        s_slope_var.set(last_values['s_slope'])
        s_attack_var.set(last_values['s_attack'])
except FileNotFoundError:
    print("There were no values saved - using default values")

x = np.arange(0., 40., 0.2)

rad = 0.0
amb = 0.0
pwm = 0.0
dT = 0.0

sendingData = False
connected = False
serial_thread = None
selected_port = None


def serial_listener():
    global amb
    global rad
    global pwm
    global dT
    global sendingData
    global connected
    global serial_thread
    global selected_port

    try:
        serial_port = serial.Serial(selected_port, 57600)
        print("connected to port", format(selected_port))
        status_left.config(text='Connected')
        connected = True
        while connected:
            if sendingData:
                text = 'x{} {} {} {}\n'.format(s_min_var.get(), s_max_var.get(), int(s_slope_var.get() * 100),
                                               int(s_attack_var.get() * 100))
                print('sending Data: {}'.format(text))
                serial_port.write(text.encode())
                time.sleep(0.8)
                sendingData = False

            else:
                lines = serial_port.readline()[:-2]
                decoded = lines.decode('utf-8')
                val = decoded.split(";")
                rad = float(val[0])
                amb = float(val[1])
                pwm = float(val[3])
                dT = (rad - amb)

                status_right.config(text='air: {}°C  h2o: {}°C  dt: {}°C - pwm: {}%'
                                    .format(("%.1f" % amb), ("%.1f" % rad), ("%.1f" % dT), pwm))

        serial_port.close()
        status_right.config(text=' ')
        # serial_thread = None
        dT = 0.0
        print("disconnected")

    except serial.SerialException:
        connected = False
        status_left.config(text='Not connected')
        status_right.config(text=' ')
        serial_thread = None
        print("Serial Error")
        print("check connection")


def sigmoid_array(val):
    slope_min = s_min_var.get()
    slope_max = s_max_var.get()
    slope = s_slope_var.get()
    attack = s_attack_var.get()

    a = []
    for item in val:
        a.append(slope_max * ((1 - (slope_min / slope_max)) / (1 + math.exp(slope * item + attack))
                              + (slope_min / slope_max)))
    return a


def sigmoid_single(val):
    slope_min = s_min_var.get()
    slope_max = s_max_var.get()
    slope = s_slope_var.get()
    attack = s_attack_var.get()
    return slope_max * ((1 - (slope_min / slope_max)) / (1 + math.exp(slope * val + attack))
                        + (slope_min / slope_max))


def update_slider_labels(_):
    s_min_label.config(text='min %: ' + str(s_min_var.get()))
    s_max_label.config(text='max %: ' + str(s_max_var.get()))
    s_slope_label.config(text='slope: ' + str(s_slope_var.get()))
    s_attack_label.config(text='attack: ' + str(s_attack_var.get()))


def draw_function():
    global fig

    fig.clear()

    sig = sigmoid_array(x)

    ax.set_ylim([-5, 105])
    ax.set_xlim([0, 40])
    ax.set_ylabel("% PWM")
    ax.set_xlabel("delta Temperature")
    ax.set_title('Resulting Sigmoid Function ')
    ax.grid()
    ax.plot(x, sig)

    draw_line()

    fig.subplots_adjust(bottom=0.15)

    canvas.draw()

    master.after(7, draw_function)


def draw_line():
    global fig
    x_ax = np.arange(0., dT, 0.2)

    line_height = []
    for _ in x_ax:  # _ represents an invisible variable -> pep8 compatible
        line_height.append(sigmoid_single(dT))

    ax.plot(x_ax, line_height)
    fig.add_subplot(ax)


def reset_values():
    s_min_var.set(1)
    s_max_var.set(89)
    s_slope_var.set(-0.43)
    s_attack_var.set(5.71)
    update_slider_labels(None)


def save_json():
    data = {'s_min': s_min_var.get(),
            's_max': s_max_var.get(),
            's_slope': s_slope_var.get(),
            's_attack': s_attack_var.get()}
    with open('last_values.json', 'w') as outfile:
        json.dump(data, outfile)


def send_values():
    global sendingData
    sendingData = True
    save_json()


def connect_disconnect():
    global connected
    global serial_thread
    if connected:
        opt.config(state=NORMAL)
        connected = False
        status_left.config(text='Not connected')
        connectButton.config(text='Connect')
    else:
        opt.config(state=DISABLED)
        serial_thread = threading.Thread(target=serial_listener)
        serial_thread.start()
        connectButton.config(text='Disconnect')


def set_port(_):
    global selected_port
    global var
    global connectButton
    selected_port = var.get()

    if selected_port.startswith('C'):
        connectButton.config(state=NORMAL)
    else:
        connectButton.config(state=DISABLED)


s_min_label = Label(master, bg='white', fg='black', width=20, text='min %: ' + str(s_min_var.get()))
s_max_label = Label(master, bg='white', fg='black', width=20, text='max %: ' + str(s_max_var.get()))
s_slope_label = Label(master, bg='white', fg='black', width=20, text='slope: ' + str(s_slope_var.get()))
s_attack_label = Label(master, bg='white', fg='black', width=20, text='attack: ' + str(s_attack_var.get()))

s_min_scale = Scale(master, from_=0, to=50, orient=HORIZONTAL, length=255, showvalue=0,
                    resolution=0.01, command=update_slider_labels, variable=s_min_var)
s_max_scale = Scale(master, from_=50, to=100, orient=HORIZONTAL, length=255, showvalue=0,
                    resolution=0.01, command=update_slider_labels, variable=s_max_var)
s_slope_scale = Scale(master, from_=-1, to=-0.3, orient=HORIZONTAL, length=255, showvalue=0,
                      resolution=0.01, command=update_slider_labels, variable=s_slope_var)
s_attack_scale = Scale(master, from_=3, to=7, orient=HORIZONTAL, length=255, showvalue=0,
                       resolution=0.01, command=update_slider_labels, variable=s_attack_var)

s_min_label.grid(row=0, column=0)
s_min_scale.grid(row=0, column=1)
s_min_scale.set(s_min_var.get())

s_max_label.grid(row=1, column=0)
s_max_scale.grid(row=1, column=1)
s_max_scale.set(s_max_var.get())

s_slope_label.grid(row=2, column=0)
s_slope_scale.grid(row=2, column=1)
s_slope_scale.set(s_slope_var.get())

s_attack_label.grid(row=3, column=0)
s_attack_scale.grid(row=3, column=1)
s_attack_scale.set(s_attack_var.get())

resetButton = Button(master, text="Reset to default", command=reset_values, width=13)
resetButton.grid(row=4, column=0)

sendButton = Button(master, text="-> Arduino", command=send_values, width=13)
sendButton.grid(row=4, column=1)

fig = plt.Figure(figsize=(5, 3), dpi=100)
ax = plt.Subplot(fig, 111)
fig.add_subplot(ax)

canvas = FigureCanvasTkAgg(fig, master)  # A tk.DrawingArea.
canvas.get_tk_widget().grid(row=5, columnspan=2)

var = StringVar()
var.set('Select COM Port')

opt = OptionMenu(master, var, 'Select COM Port', *get_serial_ports(), command=set_port)
opt.grid(row=6, column=0)

connectButton = Button(master, text="Connect", command=connect_disconnect, width=13)
connectButton.config(state=DISABLED)
connectButton.grid(row=6, column=1)

status_left = Label(master, text="Not connected ", bd=1)
status_left.grid(row=7, column=0)
status_right = Label(master, text="", bd=1)
status_right.grid(row=7, column=1)
draw_function()

master.mainloop()
