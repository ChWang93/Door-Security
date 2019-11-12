import os
import pymysql
import paramiko
import base64

key = paramiko.RSAKey(data=base64.b64decode(b'AAAAB3NzaC1yc2EAAAADAQABAAABAQDbXTsXLyRPCMqvEE2uhu0zsUI1payW5cBxiREU0HxbjeDPUP37pYwAfyodhisYgqEv1XWqedzDMe1IaNyB2RR4+slFA822f5Rl7dl9VbBy+XSTebnovzPhvWiPKnwzedFR6o9Cj7i6cUmADsjQyJA7S6kf1jVFA4M+kH/Wo6H42T7kwhftD9Z2YF1QlPkEm9pJrPLXUfQ4YwJ9vuz9I24SCeRBKCj33aTKmir0GkI9fr54x7s43p6xps3XqWjSgeUSXfcDoQdWWlWapRS4KeXFWRsFM7kHbEab+yPa2Q27sKqZ7rbUeRg2C4mZBQ9n0Nef686+Z0VijadolfwJIyPr root@DB-SERVER'))
client = paramiko.SSHClient()

# keys = client.get_host_keys().load("/home/pi/.ssh/known_hosts")

client.get_host_keys().add('192.168.15.146:22201', 'ssh-rsa', key)
client.connect('192.168.15.146', port=22201, username='root', password='Karamay54')
stdin, stdout, stderr = client.exec_command('ls')
for line in stdout:
    print('... ' + line.strip('\n'))
client.close()

# masterDB  = pymysql.connect(
#             db='inventory',
#             user='root',
#             passwd='95U3GYNb5uDN;yVb.q',
#             host='db-server.d3.diam-int.com',
#             cursorclass=pymysql.cursors.DictCursor,
#             connect_timeout= 5
#         )

# cursor = masterDB.cursor()

# cursor.execute("SELECT IP FROM Pi")
# masterDB.commit()
# slaves = cursor.fetchall()

# cursor.execute("RESET MASTER")
# masterDB.commit()

# cursor.execute("FLUSH TABLES WITH READ LOCK")
# masterDB.commit()

# os.system('mysqldump -u root --password="Karamay54" inventory HR__CompanyDaysOff Pi Pi__Doors Users Users__DoorExceptions  > ~/doorsDatabaseDump.sql')

# cursor.execute("UNLOCK TABLES")
# masterDB.commit()

# for slave in slaves:
#     slaveDB = pymysql.connect(
#                     db='inventory',
#                     user='root',
#                     passwd='Karamay54',
#                     host='127.0.0.1',
#                     cursorclass=pymysql.cursors.DictCursor,
#                     connect_timeout= 5
#                 )

#     slaveCursor = slaveDB.cursor()
#     slaveCursor.execute("STOP SLAVE;")
#     slaveDB.commit();

#     os.system('scp ~/doorDatabaseDump.sql pi@' + slave + ':dumps/doorDatabaseDump.sql')
#     os.system('ssh pi@' + slave + ' mysqldump -u root --password="Karamay54" < ~/dumps/doorDatabaseDump.sql')

#     slaveCursor = slaveDB.cursor()
#     slaveCursor.execute("RESET SLAVE; CHANGE MASTER_LOG_FILE='mysql-bin.000001', MASTER_LOG_POS=1; START SLAVE")
#     slaveDB.commit();
    
