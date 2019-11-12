from Functions import OpenDoor
import sys

IP = sys.argv[1]
user = sys.argv[2]
door = sys.argv[3]
device = sys.argv[4]



o = OpenDoor(IP,door,user,device)
