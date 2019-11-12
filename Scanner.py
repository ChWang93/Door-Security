import DB
import RPi.GPIO as GPIO
import mail
import readline
import serial
import threading
import datetime
import time
from Functions import CheckDoorAccess,debouncedInput

class Door:

    __OFF   = 1
    __ON    = 0

    def __init__(self, Building, Door):
        self.building       = Building
        self.door           = Door
        self.run            = True
        self.switchPin      = False
        self.openingPort    = False
        self.lookingUpUser  = False
        self.DoorAttributes()
        
        print(self.__dict__)

        self.OpenPort()
        

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.relayPin,GPIO.OUT)
        GPIO.output(self.relayPin, self.__ON)

        if self.switchPin:
            GPIO.setup(self.switchPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        self.Start()

        

    def __del__(self):
        GPIO.output(self.relayPin,self.__OFF)
        mail.ReadError('Building ' + str(self.building) + ' ' + self.door + ' door script has gone offline door is now inactivated')
        class_name = self.__class__.__name__
        print("\r\n------ ",class_name,"destroyed ------")

    def DoorAttributes(self):
        server = DB.ReplicatedDB()
        s = server.cursor()
        s.execute("SELECT Door, Pi, Port, Relay, Contact, Type, Active, MotionSensor FROM Pi__Doors INNER JOIN Pi ON IP = Pi WHERE Building = %s AND Door = %s", (self.building,self.door));
        server.commit()
        info = s.fetchone()

        self.ip         = info['Pi']
        self.port       = info['Port']
        self.relayPin   = info['Relay']
        self.contact    = info['Contact']
        self.type       = info['Type']
        self.active     = info['Active']

        if info['MotionSensor']:
            self.switchPin = info['MotionSensor']

    def Connect(self):
        conn = DB.ReplicatedDB()
        if conn == False:
            mail.LocalFail()

        return conn


    def Time(self):
        return datetime.datetime.now().strftime("%H:%M:%S")

    def TestPort(self):
        return '/dev/ttyACM0'

    def GetPort(self):
        return '/dev/' + self.door.replace(' ','')

    def SendToServer(self,u):
        server = DB.Server()
        if server != False:
            s = server.cursor()
            s.execute("INSERT INTO Users__DoorLog (Username,RFID,Message,Building,Door) VALUES (%s,%s,%s,%s,%s)", (u['Username'],u['RFID'],u['Message'],self.building,self.door))
            server.commit()
        else:
            self.SendToLocal(u)

    def SendToLocal(self,u):
        conn = self.Connect()
        c = conn.cursor()
        c.execute("INSERT INTO Users__DoorLog (Username,RFID,Message,Building,Door) VALUES (%s,%s,%s,%s)", (u['Username'],u['RFID'],u['Message'],self.building,self.door))
        conn.commit()

    def turnOff(self):
        if self.Locked():
            GPIO.output(self.relayPin,self.__ON)
            print('Locked')


    def Success(self,User,Locked):
        GPIO.output(self.relayPin,self.__OFF)

        threading.Timer(5,self.turnOff).start()
        self.SendToServer(User)

    def Fail(self,ID,User):
        if User == 'None':
            User = {
                'Username': None,
                'RFID': ID,
                'Message': 'No User found'
            }
        else:
            mail.ReadError("User: %s\nRFID: %s\nBuilding: %s\nDoor: %s\n%s" % (User['Username'],User['RFID'],self.building,self.door,User['Message']) )

        
        self.SendToServer(User)

    def Locked(self):
        server = DB.ReplicatedDB()
        s = server.cursor()
        s.execute("""SELECT Days,UnlockStartTime,UnlockEndTime FROM Pi__Doors
                     INNER JOIN Pi ON IP = Pi
                     WHERE Building = %s AND Door = %s""", (self.building,self.door))

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

        return Locked

    def DoorAccess(self,User,conn,c):
        c.execute("""SELECT StartTime,EndTime,Level,InactiveLevel,Days,UnlockStartTime,UnlockEndTime,Active,COUNT(Ex.Username) AS ExceptionGranted
                    FROM Pi__Doors D
                    INNER JOIN Pi ON IP = Pi
                    LEFT JOIN Users__DoorExceptions Ex ON Ex.Door = D.Door AND Ex.Building = Pi.Building AND Ex.Username = %s
                    WHERE Pi = %s AND D.Door = %s""", (User['Username'],self.ip,self.door))
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
        self.lookingUpUser = True
        conn = self.Connect()
        c = conn.cursor()
        ID = int(rfid)

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
            mail.ReadError("No user found\nRFID: %d\r\nBuilding: %s\r\nDoor: %s" % (int(ID),self.building,self.door))

        self.lookingUpUser = False

    def OpenPort(self):
        try:
            self.ser            = serial.Serial(self.GetPort(),9600)
            self.read           = readline.ReadLine(self.ser)
        except:
            self.ser = False

        self.openingPort = False
            

    def Start(self):
        failed = 0
        while self.run:
            if self.switchPin and GPIO.input( self.switchPin ) and debouncedInput( self.switchPin ) and GPIO.input( self.relayPin ) == self.__ON:
                GPIO.output(self.relayPin,self.__OFF)
                threading.Timer(5,self.turnOff).start()
                while GPIO.input( self.switchPin ):
                    pass


                if self.ser:
                    try:
                        self.ser.flushInput()
                    except:
                        self.ser.close()
                        self.ser = False

            if self.ser and self.ser.isOpen() and self.lookingUpUser == False:
                failed = 0
                try:
                    while( self.ser.inWaiting() ):
                        rfid = self.read.readline()
                        self.ser.flushInput()
                        self.FindUser( rfid )
                except:
                    self.ser.close()
                    self.ser = False
                    continue
            elif self.ser == False and self.openingPort == False:
                failed += 1

                if failed == 1:
                    mail.ReadError('Building ' + str(self.building) + ' ' + self.door + ' door reader has gone offline')

                self.openingPort = True
                self.OpenPort()


        self.__del__
    
