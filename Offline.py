#!/bin/sh
import RPi.GPIO as GPIO
import Layout
import time
import serial
import DB
import mail
import sys

def SetInactive(d,m):
    new = DB.Server()
    n = new.cursor()
    n.execute("UPDATE Pi__Doors SET Active = 0 WHERE Door = %s AND Pi = %s", (d,m))
    new.commit()

Building = sys.argv[1]
Door = sys.argv[2]

Map = Layout.Map()
Pin = Map[Building][Door]['Relay']


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(Pin,GPIO.OUT)
GPIO.output(Pin, 1)

SetInactive(Door,Map[Building][Door]['Pi'])

mail.ReadError('Building ' + Building + ' ' + Door + ' door has been deactivated');
