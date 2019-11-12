import serial
import sys
import mail
from Functions import Scan
from time import sleep
import readline

Building = sys.argv[1]
Door = sys.argv[2]

s = Scan(Building,Door)
ser = serial.Serial(s.GetPort(),9600)
ReadLine = readline.ReadLine(ser)
# ser = serial.Serial(s.TestPort(),9600)
try:
    while True:
        try:
            s.FindUser( ReadLine.readline() )
            ser.reset_input_buffer()
            sleep(.1)
        except KeyboardInterrupt:
            break
except Exception as e:
    mail.ReadError(e)

ser.close()
del s
