import time
import datetime
import smtplib
from gobiko.apns import APNsClient

sender = 'Security@diaminter.com'
to = ['6318382121@vtext.com']

smtp = smtplib.SMTP("192.168.2.2", 25)

def RedAlert(door,building):
    sender = "alert@diaminter.com"
    receivers = ['6318821181@tmomail.net']
    message = "ALERT! Seb has been spotted entering the %s door at %s" % (door,building)
    
    try:
        smtpObj = smtplib.SMTP("192.168.2.2", 25)
        smtpObj.sendmail(sender,receivers,message)
        print('Sent')
    except SMTPException:
        pass


def ErrorConn1():

    st = GetTime()

    try:
        apns( message )
        smtp.sendmail(sender,to,message)
    except:
        pass

def ErrorConn2():

    st = GetTime()

    try:
        message = """FATEL ERROR. Could not connect to Raspberry Pi Local DB.
        			 \rTime: %s""" % st

        apns( message )
        smtp.sendmail(sender,to,message)

    except:
        pass

def DoorWarning(door,building,time):

    st = GetTime()

    try:
        time = time / 60
        message = """Warning %s Door at building %s has been open for %i minutes.
                     \rTime: %s""" % (door,building,time,st)
        apns(message)

        smtp.sendmail(sender,to,message)
    except:
        pass

def DoorAlert(door,building):
    st = GetTime()

    try:
        message = """ALERT!
                     \r%s Door at building %s has been opened.
                     \rTime: %s""" % (door,building,st)
        apns(message)
        smtp.sendmail(sender,to,message)
    except:
        pass

def EmergencyDoorWarning(door,building):

    st = GetTime()

    try:
        message = """Warning %s Door at building %s has been opened.
                     \rTime: %s""" % (door,building,st)

        apns(message)
        smtp.sendmail(sender,to,message)
    except:
        pass

def ReadError(msg):

    st = GetTime()
    message = """%s \rTime: %s""" % (msg,st)
    apns( message )

    # try:
        
    # except:
    #     pass

def ScanError():

    st = GetTime()
    later = datetime.datetime.fromtimestamp(time.time() + 60).strftime('%I:%M:%S %p')
    message = """Error reading RFID key\rTime: %s\n%s""" % (st,later)
    apns(message)
    smtp.sendmail(sender,to,message)

    # try:
    # except:
    #     pass

def GetTime():
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%I:%M %p')
    return st

def phoneIDs(users=['sebastien.lepoder']):
    import pymysql
    local = pymysql.connect(
        db='inventory',
        user='root',
        passwd='Karamay54',
        host='127.0.0.1',
        cursorclass=pymysql.cursors.DictCursor
    )
    c = local.cursor()

    
    phones = []
    for user in users:
        c.execute("SELECT PhoneID FROM Users WHERE Username = %s AND PhoneID IS NOT NULL", (user))
        local.commit()
        pysql = c.fetchone()
        phones.append(pysql['PhoneID'])

    return phones

def apns(msg,identifier=None,priority=10,users=['sebastien.lepoder']):
    client = APNsClient(
        team_id='72D72PGS3Z',
        bundle_id='d3-connect',
        auth_key_id='GQUF76FL7C',
        auth_key_filepath='/home/pi/RFID/appKeys/AuthKey_GQUF76FL7C.p8',
        use_sandbox=False,
        force_proto='h2'
    )

    client.send_bulk_message(
        phoneIDs(users),
        alert={
            "body": msg,
            "title": 'Doors'
        },
        badge=0,
        sound='default',
        category='',
        content_available=False,
        extra={},
        priority=priority,
        expiration=int(time.time()) + 60
    )