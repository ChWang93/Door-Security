import RPi.GPIO as GPIO
import DB
import mail
import datetime
import time
import threading
import json
import sys
from datetime import timedelta

OFF = 1
ON = 0


class Scan:
    def __init__(self, Building, Door):
        self.Building = Building
        self.Door = Door
        self.DoorInfo = self.Map()
        self.IP = self.DoorInfo['Pi']
        self.RelayPin = self.DoorInfo['Relay']
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.RelayPin,GPIO.OUT)
        GPIO.output(self.RelayPin, ON)

        print(self.DoorInfo)

    def __del__(self):
        GPIO.output(self.RelayPin,OFF)
        mail.ReadError('Building ' + self.Building + ' ' + self.Door + ' door script has gone offline door is now inactivated')
        class_name = self.__class__.__name__
        print("\r\n------ ",class_name,"destroyed ------")

    def Connect(self):
        conn = DB.ReplicatedDB()
        if conn == False:
            mail.LocalFail()

        return conn

    def Map(self):
    	server = DB.ReplicatedDB()
    	s = server.cursor()
    	s.execute("SELECT Door, Pi, Port, Relay, Contact, Type, Active, MotionSensor FROM Pi__Doors INNER JOIN Pi ON IP = Pi WHERE Building = %s AND Door = %s", (self.Building,self.Door));
    	server.commit()
    	Map = s.fetchone()

    	return Map

    def Time(self):
        return datetime.datetime.now().strftime("%H:%M:%S")

    def TestPort(self):
        return '/dev/ttyACM0'

    def GetPort(self):
        return '/dev/' + self.DoorInfo['Door'].replace(' ','')

    def SendToServer(self,u):
        server = DB.Server()
        if server != False:
            s = server.cursor()
            s.execute("INSERT INTO Users__DoorLog (Username,RFID,Message,Building,Door) VALUES (%s,%s,%s,%s,%s)", (u['Username'],u['RFID'],u['Message'],self.Building,self.Door))
            server.commit()

            if u['Username'] == 'sebastien.lepoder':
                mail.RedAlert(self.Door,self.Building)

        else:
            self.SendToLocal(u)

    def SendToLocal(self,u):
        conn = self.Connect()
        c = conn.cursor()
        c.execute("INSERT INTO Users__DoorLog (Username,RFID,Message,Building,Door) VALUES (%s,%s,%s,%s)", (u['Username'],u['RFID'],u['Message'],self.Building,self.Door))
        conn.commit()

    def turnOff(self,locked):
        if locked:
            GPIO.output(self.RelayPin,ON)
            print('Locked')


    def Success(self,User,Locked):
        GPIO.output(self.RelayPin,OFF)

        threading.Timer(5,self.turnOff,[Locked]).start()
        self.SendToServer(User)

    def Fail(self,ID,User):
        if User == 'None':
            User = {
                'Username': None,
                'RFID': ID,
                'Message': 'No User found'
            }
        else:
            mail.ReadError("User: %s\nRFID: %s\n%s" % (User['Username'],User['RFID'],User['Message']) )

        
        self.SendToServer(User)


    def DoorAccess(self,User,conn,c):
        c.execute("""SELECT StartTime,EndTime,Level,InactiveLevel,Days,UnlockStartTime,UnlockEndTime,Active,COUNT(Ex.Username) AS ExceptionGranted
                    FROM Pi__Doors D
                    INNER JOIN Pi ON IP = Pi
                    LEFT JOIN Users__DoorExceptions Ex ON Ex.Door = D.Door AND Ex.Building = Pi.Building AND Ex.Username = %s
                    WHERE Pi = %s AND D.Door = %s""", (User['Username'],self.IP,self.Door))
        conn.commit()
        Row = c.fetchone()

        c.execute("""SELECT COUNT(ID) AS DayOff FROM HR__CompanyDaysOff
                        WHERE Date = DATE(NOW())""")
        conn.commit()
        DayOff = c.fetchone()['DayOff']
        
        Access = CheckDoorAccess(User['DoorLevel'],Row,DayOff)

        if Access['Status'] == 1:
            self.Success(User,Access['Locked'])
        else:
            User['Message'] = Access['ErrorMessage']
            self.Fail(User['RFID'],User)

    def FindUser(self,rfid):
        conn = self.Connect()
        c = conn.cursor()
        ID = int(rfid)
        print(rfid,datetime.datetime.now().strftime("%H:%M:%S"))
        c.execute("SELECT Username,DoorLevel,Active FROM Users WHERE RFID = %s", ID)
        conn.commit()
        Row = c.fetchone()

        print(Row)

        if c.rowcount > 0:
            User = {
                'Username': Row['Username'],
                'DoorLevel': Row['DoorLevel'],
                'Active': Row['Active'],
                'RFID': ID,
                'Message': None
            }

            if Row['Active'] == 0:
                User['Message'] = 'User is not active in the system'
                self.Fail(User['RFID'],User)
            else:
                Checks = self.DoorAccess(User,conn,c)

        
        else:
            self.Fail(ID,'None')
            mail.ReadError("No user found\nRFID: %d\r\nBuilding: %s\r\nDoor: %s" % (int(ID),self.Building,self.Door))


def generateTimeRange(s,e):
    if s != None:
        Start = datetime.datetime.strptime(str(s),"%H:%M:%S").strftime("%H:%M:%S")
    else:
        Start = datetime.datetime.strptime('00:00:00',"%H:%M:%S").strftime("%H:%M:%S")

    if e != None:
        End = datetime.datetime.strptime(str(e),"%H:%M:%S").strftime("%H:%M:%S")
    else:
        End = datetime.datetime.strptime('23:59:59',"%H:%M:%S").strftime("%H:%M:%S")

    return {
        'Start': Start,
        'End': End
    }

def CheckDoorAccess(userDoorLevel,door,dayOff):
    DoorLevel = door['Level']
    DoorInactiveLevel = door['InactiveLevel']
    ExceptionGranted = door['ExceptionGranted']
    DaysOpen = door['Days'].split(',')
    ReaderRange = generateTimeRange(door['StartTime'],door['EndTime'])
    UnlockedTimeRange = generateTimeRange(door['UnlockStartTime'],door['UnlockEndTime'])

    Now = datetime.datetime.now().strftime("%H:%M:%S")
    NowFormat = datetime.datetime.now().strftime("%Y-%m-%d")
    DayOfWeek = int(datetime.datetime.now().strftime("%w")) + 1


    Level = userDoorLevel >= DoorLevel
    Active = door['Active']
    Locked = 1
    AfterHours = 0
    ErrorMessage = ''

    #Check if time of scan falls within time reader is active for door
    if Now < ReaderRange['Start'] or Now >= ReaderRange['End']:
        AfterHours = 1

    #Check if door should be locked after scan
    if dayOff == False and str(DayOfWeek) in DaysOpen and Now >= UnlockedTimeRange['Start'] and Now < UnlockedTimeRange['End'] and DayOfWeek != 7 and DayOfWeek != 1:
            Locked = 0

    if Active == False:
        ErrorMessage = 'Door is not active'
        Status = 0
    elif AfterHours == True and Level == False and ExceptionGranted == False:
        ErrorMessage = 'User does not have permission for this door after working hours'
        Status = 0
    elif AfterHours == True and (Level == True or ExceptionGranted == True):
        Status = 1
    elif Level == False and ExceptionGranted == False:
        ErrorMessage = 'User does not have permission for this door'
        Status = 0
    elif ExceptionGranted or Level == True:
        Status = 1
    else:
        ErrorMessage = 'Unkown error has occured'
        Status = 0

    return {
        'Status': Status,
        'ErrorMessage': ErrorMessage,
        'Locked': Locked,
        'DayOff': dayOff
    }

def debouncedInput(pin):
    tries = 12
    i, ones, zeroes = 0, 0, 0
    while i < tries:
        bit = GPIO.input(pin)
        if( bit == 1 ):
            ones = ones + 1
            zeroes = 0
        else:
            zeroes = zeroes + 1
            ones = 0
        i = i + 1
        if( ones >= 3 ):
            return 1
        if( zeroes >= 3 ):
            return 0
        time.sleep(0.03)

class Doorbell:
    def __init__(self):
        self.Pin = {
            'Doorbell': 17,
            'Lobby': 27,
            'Front': 22
        }

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.Pin['Doorbell'], GPIO.OUT)
        GPIO.setup(self.Pin['Lobby'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.Pin['Front'], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.output(self.Pin['Doorbell'], OFF)

        self.loop()

    def turnOff(self):
        GPIO.output(self.Pin['Doorbell'],OFF)

    def dingDong(self,channel):
        GPIO.output(self.Pin['Doorbell'],ON)
        threading.Timer(1,self.turnOff).start()

    def loop(self):
        
        GPIO.add_event_detect(self.Pin['Front'],GPIO.RISING,callback=self.dingDong,bouncetime=1000)
        GPIO.add_event_detect(self.Pin['Lobby'],GPIO.RISING,callback=self.dingDong,bouncetime=1000)

        while True:
            try:
                pass
            except KeyboardInterrupt:
                break

        del self

    def __del__(self):
        class_name = self.__class__.__name__
        GPIO.output(self.Pin['Doorbell'],OFF)
        print(class_name,"destroyed")

class MotionSensor:
    def __init__(self,Building,Door):
        self.Building = Building
        self.Door = Door
        SQL = self.Fetch()
        self.TrackPin = SQL['MotionSensor']
        self.RelayPin = SQL['Relay']
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.RelayPin, GPIO.OUT)
        GPIO.setup(self.TrackPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        print(SQL)

    def Fetch(self):
        server = DB.ReplicatedDB()
        s = server.cursor()
        s.execute("""SELECT Relay, MotionSensor FROM Pi__Doors
                     INNER JOIN Pi ON IP = PI
                     WHERE Building = %s and Door = %s""", (self.Building,self.Door));
        server.commit()
        Map = s.fetchone()

        return Map

    def turnOff(self,locked):
        if locked:
            GPIO.output(self.RelayPin,ON)
            print('Locked')

    def Detect(self,pin):
        if GPIO.input(self.RelayPin) == ON and debouncedInput(self.TrackPin):
            GPIO.output(self.RelayPin,OFF)
            locked = self.Locked()
            threading.Timer(5,self.turnOff,[locked]).start()
            

    def Locked(self):
        server = DB.ReplicatedDB()
        s = server.cursor()
        s.execute("""SELECT Days,UnlockStartTime,UnlockEndTime FROM Pi__Doors
                     INNER JOIN Pi ON IP = Pi
                     WHERE Building = %s AND Door = %s""", (self.Building,self.Door))

        server.commit()
        Row = s.fetchone()
        DaysOpen = Row['Days'].split(',')

        if Row['UnlockStartTime'] != None:
            UnlockStart = datetime.datetime.strptime(str(Row['UnlockStartTime']),"%H:%M:%S").strftime("%H:%M:%S")
        else:
            UnlockStart = datetime.datetime.strptime('00:00:00',"%H:%M:%S").strftime("%H:%M:%S")

        if Row['UnlockEndTime'] != None:
            UnlockEnd = datetime.datetime.strptime(str(Row['UnlockEndTime']),"%H:%M:%S").strftime("%H:%M:%S")
        else:
            UnlockEnd = datetime.datetime.strptime('00:00:00',"%H:%M:%S").strftime("%H:%M:%S")

        Now = datetime.datetime.now().strftime("%H:%M:%S")
        DayOfWeek = int(datetime.datetime.now().strftime("%w")) + 1

        s.execute("SELECT COUNT(Reason) AS Reason FROM HR__CompanyDaysOff WHERE Date = DATE(NOW())")
        server.commit()
        DayOff = s.fetchone()['Reason']
        Locked = 1

        DaysOpen.remove('1')
        DaysOpen.remove('7')

        if str(DayOfWeek) in DaysOpen:
            if Now >= UnlockStart and Now < UnlockEnd and DayOff == 0:
                Locked = 0

        print(Locked)
        return Locked

    def Loop(self):
        GPIO.add_event_detect(self.TrackPin,GPIO.RISING,callback=self.Detect,bouncetime=5000)
        while True:
            try:
                time.sleep(0.01)
                pass
            except KeyboardInterrupt:
                break
        del self

    def __del__(self):
        class_name = self.__class__.__name__
        print(class_name,"destroyed")

class Timer:
    def __init__(self, IP):
        self.IP = IP
        self.server = DB.ReplicatedDB()

    def Fetch(self):
        server = self.server
        s = server.cursor()
        s.execute("""SELECT Relay, Days, UnlockStartTime, UnlockEndTime, Active FROM Pi__Doors
                     INNER JOIN Pi ON IP = Pi
                     WHERE Pi = %s AND Relay IS NOT NULL""", (self.IP));
        server.commit()
        Map = s.fetchall()

        return Map

    def CheckForDayOff(self):
        server = self.server
        s = server.cursor()
        s.execute("SELECT COUNT(Reason) AS Reason FROM HR__CompanyDaysOff WHERE Date = DATE(NOW())")

        server.commit()
        return s.fetchone()['Reason']

    def CheckLock(self):
        Doors = self.Fetch()

        for value in Doors:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(value['Relay'],GPIO.OUT)
            
            if value['Active'] == 0:
                if value['Relay'] != None:
                    GPIO.output(value['Relay'],OFF)
                
                continue


            if value['Active'] == 0:
                GPIO.output(value['Relay'],OFF)
                continue

            DaysOpen = value['Days'].split(',')

            if value['UnlockStartTime'] != None:
                UnlockStart = datetime.datetime.strptime(str(value['UnlockStartTime']),"%H:%M:%S").time()
                TempUnlockStart = (datetime.datetime.strptime(str(value['UnlockStartTime']),"%H:%M:%S") + timedelta(seconds=60)).time()
            else:
                UnlockStart = datetime.datetime.strptime('00:00:00',"%H:%M:%S").time()
                TempUnlockStart = datetime.datetime.strptime('00:00:00',"%H:%M:%S").time()

            if value['UnlockEndTime'] != None:
                UnlockEnd = datetime.datetime.strptime(str(value['UnlockEndTime']),"%H:%M:%S").time()
                TempUnlockEnd = (datetime.datetime.strptime(str(value['UnlockEndTime']),"%H:%M:%S") + timedelta(seconds=60)).time()

            else:
                UnlockEnd = datetime.datetime.strptime('00:00:00',"%H:%M:%S").time()
                TempUnlockEnd = datetime.datetime.strptime(str(value['UnlockEndTime']),"%H:%M:%S").time()

            Now = datetime.datetime.now().time()
            DayOfWeek = int(datetime.datetime.now().strftime("%w")) + 1
            DayOff = self.CheckForDayOff()

            DaysOpen.remove('1')
            DaysOpen.remove('7')
            if str(DayOfWeek) in DaysOpen:
                if UnlockStart.strftime("%H:%M") != UnlockEnd.strftime("%H:%M"):
                    if Now > UnlockStart and Now < TempUnlockStart and DayOff == 0:
                        GPIO.output(value['Relay'],GPIO.LOW)
                        GPIO.output(value['Relay'],OFF)
                    elif Now > UnlockEnd and Now < TempUnlockEnd :
                        GPIO.output(value['Relay'],ON)
                        GPIO.output(value['Relay'],GPIO.LOW)


class OpenDoor:
    def __init__(self, IP, Door, User, Device):
        self.IP = IP
        self.Door = Door
        self.User = User
        self.Device = Device
        self.Server = DB.ReplicatedDB()
        self.DoorInfo = self.Fetch()
        self.Level = self.UserInfo()['DoorLevel']
        self.Open()
        self.Log()

    def UserInfo(self):
        server = self.Server
        s = server.cursor()
        s.execute("SELECT DoorLevel FROM Users WHERE Username = %s", (self.User))
        server.commit()

        sql = s.fetchone()

        return sql

    def Fetch(self):
        server = self.Server
        s = server.cursor()
        s.execute("""SELECT Relay,Pi.Building,StartTime,EndTime,Level,InactiveLevel,Days,UnlockStartTime,UnlockEndTime,Active,COUNT(Ex.Username) AS ExceptionGranted
                    FROM Pi__Doors D
                    INNER JOIN Pi ON IP = Pi
                    LEFT JOIN Users__DoorExceptions Ex ON Ex.Door = D.Door AND Ex.Building = Pi.Building AND Ex.Username = %s
                    WHERE Pi = %s AND D.Door = %s""", (self.User,self.IP,self.Door))
        server.commit()
        Map = s.fetchone()

        s.execute("SELECT COUNT(Reason) AS Reason FROM HR__CompanyDaysOff WHERE Date = DATE(NOW())")
        server.commit()
        Map['DayOff'] = s.fetchone()['Reason']

        return Map

    def Log(self):
        server = DB.Server()
        s = server.cursor()
        s.execute("""INSERT INTO Users__DoorLog (Username,Door,Building,RFID)
                     VALUES (%s,%s,%s,%s)""", (self.User,self.Door,self.DoorInfo['Building'],self.Device))
        server.commit()

        if self.User == '':
            mail.RedAlert(self.Door,self.DoorInfo['Building'])

    def Open(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.DoorInfo['Relay'],GPIO.OUT)


        Access = CheckDoorAccess(self.Level,self.DoorInfo,self.DoorInfo['DayOff'])

        print(Access)

        if Access['Status'] == 1:
            GPIO.output(self.DoorInfo['Relay'],OFF)
            time.sleep(5)


        if Access['Locked'] == 1:
            GPIO.output(self.DoorInfo['Relay'],ON)
        else:
            print('Unlocked')

class ContactSwitch:
    def __init__(self,IP):
        self.IP = IP
        self.Server = DB.ReplicatedDB()
        self.Doors = self.Fetch()
        self.Building = self.GetBuilding()
        self.Setup()
        self.Loop()

    def GetBuilding(self):
        server = self.Server
        s = server.cursor()
        s.execute("""SELECT Building FROM Pi
                     WHERE IP = %s""", (self.IP));
        server.commit()
        return s.fetchone()['Building']

    def Fetch(self):
        server = self.Server
        s = server.cursor()
        s.execute("""SELECT Door, Relay, IF(Contact = 0 OR CONTACT IS NULL,NULL,Contact) AS Contact, Type FROM Pi__Doors
                     INNER JOIN Pi ON IP = Pi
                     WHERE Pi = %s and Active = 1""", (self.IP));
        server.commit()
        Map = s.fetchall()
        obj = {}

        for value in Map:
            obj[value['Door']] = value

        return obj

    def Setup(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for key,value in self.Doors.items():
            if value['Relay'] != None:
                GPIO.setup(value['Relay'],GPIO.OUT)
            if value['Contact'] != None:
                GPIO.setup(value['Contact'],GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

            value['OpenTime'] = 0
            value['Locked'] = True

            if value['Type'] == 'Emergency':
                value['FirstMessage'] = True;

    def Run(self):
        for key,value in self.Doors.items():
            if value['Relay'] != None:
                value['Locked'] = GPIO.input(value['Relay']) == ON
            if value['Contact'] != None:
                if GPIO.input(value['Contact']):
                    value['OpenTime'] = 0
                    if value['Type'] == 'Emergency':
                        value['FirstMessage'] = True
                else:
                    value['OpenTime'] += 1

                if value['Type'] == 'Emergency':
                    if value['FirstMessage'] == True and value['OpenTime'] > 1:
                        value['FirstMessage'] = False
                        mail.DoorAlert(value['Door'], self.Building)
                    elif value['OpenTime'] > 0 and value['OpenTime'] % 300 == 0:
                        mail.DoorWarning(value['Door'], self.Building, value['OpenTime'])
                elif value['OpenTime'] % 300 == 0 and value['OpenTime'] > 0:
                    mail.DoorWarning(value['Door'], self.Building, value['OpenTime'])


        with open('/var/www/html/DoorLog.json', 'w') as fp:
            json.dump(self.Doors,fp)

        time.sleep(1)
        print(json.dumps(self.Doors, sort_keys=True,indent=4, separators=(',',': ')))

    def Loop(self):
            while True:
                try:
                    self.Run()
                except KeyboardInterrupt:
                    break;
                time.sleep(0.01)
                
            del self

    def __del__(self):
        class_name = self.__class__.__name__
        print(class_name,"destroyed")
