#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO: beautify code
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import *
import math
import matplotlib.pyplot as plt
import numpy as np
import threading
import time
import serial

master = Tk()
master.title('dT-FanControl')

s_min_var = IntVar()
s_max_var = IntVar()
s_slope_var = DoubleVar()
s_attack_var = DoubleVar()

s_min_var.set(1)
s_max_var.set(89)
s_slope_var.set(-0.43)
s_attack_var.set(5.71)

x = np.arange(0., 35., 0.2)

rad = 0.0
amb = 0.0
pwm = 0.0
dT = 0.0

sendingData = False
connected = False
serial_thread = None


def serial_listener():
    global amb
    global rad
    global pwm
    global dT
    global sendingData
    global connected
    global serial_thread

    try:
        serial_port = serial.Serial('COM3', 57600)
        print(f"The Port name is {serial_port.name}")
        statusbarleft.config(text='Connected')
        connected = True
        while connected:
            if sendingData:
                text = 'x{} {} {} {}\n'.format(s_min_var.get(), s_max_var.get(), int(s_slope_var.get()*100), int(s_attack_var.get()*100))
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
                dT = (rad-amb)

                statusbarright.config(text='air: {}°C  h2o: {}°C  dt: {}°C - pwm: {}%'.format(("%.1f" % amb), ("%.1f" % rad), ("%.1f" % dT), pwm))


        serial_port.close()
        statusbarright.config(text=' ')
        serial_thread = None
        dT = 0.0
        print("disconnected")

    except:
        connected = False
        serial_thread.raise_exception()
        serial_thread.join()
        statusbarleft.config(text='Not connected')
        statusbarright.config(text=' ')
        serial_thread = None
        print("Serial Error")
        print("check connection")


def sigmoid(val):
    smin = s_min_var.get()
    smax = s_max_var.get()
    slope = s_slope_var.get()
    attack = s_attack_var.get()

    a = []
    for item in val:
        a.append(smax * ((1 - (smin / smax)) / (1 + math.exp(slope * item + attack)) + (smin / smax)))
    return a


def sigm(val):
    smin = s_min_var.get()
    smax = s_max_var.get()
    slope = s_slope_var.get()
    attack = s_attack_var.get()
    return smax * ((1 - (smin / smax)) / (1 + math.exp(slope * val + attack)) + (smin / smax))


def update_slider_labels(val):
    s_min_label.config(text='min %: ' + str(s_min_var.get()))
    s_max_label.config(text='max %: ' + str(s_max_var.get()))
    s_slope_label.config(text='slope: ' + str(s_slope_var.get()))
    s_attack_label.config(text='attack: ' + str(s_attack_var.get()))


def draw_function():
    global fig

    fig.clear()

    sig = sigmoid(x)

    ax.set_ylim([-5, 105])
    ax.set_xlim([0, 30])
    ax.set_ylabel("% PWM")
    ax.set_xlabel("delta Temperature")
    ax.set_title('Resulting Sigmoid Function ')
    ax.grid()
    ax.plot(x, sig)

    draw_line()

    fig.subplots_adjust(bottom=0.15)

    canvas.draw()

    master.after(7,draw_function)


def draw_line():
    global fig
    x_ax = np.arange(0., dT, 0.2)  # x achse

    lineh = []
    for item in x_ax:
        lineh.append(sigm(dT))

    ax.plot(x_ax, lineh)
    fig.add_subplot(ax)


def reset_values():
    s_min_var.set(1)
    s_max_var.set(89)
    s_slope_var.set(-0.43)
    s_attack_var.set(5.71)
    update_slider_labels(None)


def send_values():
    global sendingData
    sendingData = True


def connect_disconnect():
    global connected
    global serial_thread
    if connected:
        connected = False
        statusbarleft.config(text='Not connected')
    else:
        serial_thread = threading.Thread(target=serial_listener)
        serial_thread.start()
        connectButton.config(text='Disconnect')


s_min_label = Label(master, bg='white', fg='black', width=20, text='min %: ' + str(s_min_var.get()))
s_max_label = Label(master, bg='white', fg='black', width=20, text='max %: ' + str(s_max_var.get()))
s_slope_label = Label(master, bg='white', fg='black', width=20, text='slope: ' + str(s_slope_var.get()))
s_attack_label = Label(master, bg='white', fg='black', width=20, text='attack: ' + str(s_attack_var.get()))

s_min_scale = Scale(master, from_=0, to=20, orient=HORIZONTAL, length=255, showvalue=0,
                    resolution=0.01, command=update_slider_labels, variable=s_min_var)
s_max_scale = Scale(master, from_=50, to=100, orient=HORIZONTAL, length=255, showvalue=0,
                    resolution=0.01, command=update_slider_labels, variable=s_max_var)
s_slope_scale = Scale(master, from_=-1, to=-0.2, orient=HORIZONTAL, length=255, showvalue=0,
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

fig = plt.Figure(figsize=(5, 3), dpi=100)
ax = plt.Subplot(fig, 111)
fig.add_subplot(ax)

canvas = FigureCanvasTkAgg(fig, master)  # A tk.DrawingArea.
canvas.get_tk_widget().grid(row=5, columnspan=2)

connectButton = Button(master, text="Connect", command=connect_disconnect, width=13)
connectButton.grid(row=6, column=0)

sendButton = Button(master, text="-> Arduino", command=send_values, width=13)
sendButton.grid(row=6, column=1)

statusbarleft = Label(master, text="Not connected ", bd=1)
statusbarleft.grid(row=7, column=0)
statusbarright= Label(master, text="", bd=1)
statusbarright.grid(row=7, column=1)
draw_function()

master.mainloop()
