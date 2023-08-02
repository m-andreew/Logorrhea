"""
LOGORRHEA CHAT PROGRAM
the FSMP (Fred Short Message Protocol) chat server

Copyright 2023 The FSMP Committee
All rights reserved
"""
import socket 
import ssl
import select
import sys
import time
import re
import datetime
import subprocess

# configuration parameters - IMPORTANT
logorrheaversion = "1.2.1" # needed for compatibility check
timezone = "CET" # IMPORTANT
maxdormant = 1000 # max time user can be dormant
HOST = 'localhost' # IMPORTANT
PORT = 3141 # IMPORTANT
BUFFER_SIZE = 1024 # IMPORTANT
shutdownpswd = "absturz" # any user who sends this password shuts down the chat server
osversion="OS X 10.10" # OS version for enquiries and stats
typehost="ThinkPad X230" # what kind of machine
hostloc = "Mein VW Golf" # where is this machine
osversion = "OS X 10.10" # OS version for enquiries and stats
osversion = "OS X 10.10" # OS version for enquiries and stats
sysopname = "Fred" # who is the sysop for this server
sysopemail = "fred" # where to contact this sysop

# determine uptime of this machine - WARNING OS DEPENDENCY!!!!!!
ProdName = subprocess.check_output("uname")
uptime = re.search(r'up (.+), .*', subprocess.check_output("uptime").decode()).group(1)
boottime = re.search(r'(\S+ \d\d \d\d:\d\d)', subprocess.check_output("who -b", shell=True).decode()).group(1)
"""print(ProdName
print(boottime))"""
# global vars

logged_on_users = [] # dict of dicts of all logged on users
inputs = [] # list of all sockets
outputs = [] # list of uh, nothing
msgcount = 0 # total number of msgs sent
totaluser = 0 # online users at any given moment
highestusers = 0 # most users online at any given moment
otime = 0 # overtime to log off users after n minutes
starttime = None # time this server started
logline = " " # initialize log line

# Define SSL context
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile='server_cert.pem', keyfile='server_key.pem')

def main():
    global inputs
    global starttime
    starttime = mytime()
    log(f"Logorrhea chat {logorrheaversion} started. ")
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
    except Exception as err:
        print("Error creating server socket:", err)
        sys.exit()
        
    inputs = [server_socket]
    outputs = []
    c = time.time()
    try:
        while inputs:
            readable, writable, exceptional = select.select(inputs, outputs, inputs)
            for sock in readable:
                if sock is server_socket:
                    conn, addr = sock.accept()
                    conn = context.wrap_socket(conn, server_side=True)
                    conn.send(" ".encode())
                    inputs.append(conn)
                else:
                    try:
                        line = sock.recv(BUFFER_SIZE) # wait for a message
                        if line:
                            text = line.decode() # we have a message
                            # parse it
                            # format is like this:
                            # *MSG  FRED    hello
                            typ, userid, msg = re.match(r"(\S+) (\S+) (.*)", text).groups()
                            handlemsg(userid, sock, msg) # pass incoming line to message parser
                        else:
                            if sock in inputs:
                                inputs.remove(sock)
                                for u in logged_on_users:
                                    if sock == u[1]:
                                        logged_on_users.remove(u)
                            try:
                                sock.close()
                            except:
                                pass
                    except Exception as e:
                        print(f"Exc {e}")
                        if sock in inputs:
                            inputs.remove(sock)
                        try:
                            sock.close()
                        except:
                            pass
            for sock in exceptional:
                if sock in inputs:
                    inputs.remove(sock)
                try:
                    sock.close()
                except:
                    pass
    except KeyboardInterrupt:
        xit()

def xit():
    # when it's time to quit, call this
    for sock in inputs:
        sock.close()

def handlemsg(userid, sock, msg):
    # handle all incoming messages and send to proper function
    userid = userid.strip()
    CurrentTime = exTime()
    umsg = msg.upper()
    updbuff = 1

    # HANDLE MESSAGE TYPES
    if umsg == "/WHO":
        sendwho(userid, sock)
    elif umsg == "/SYSTEM":
        systeminfo(userid, sock)
    elif umsg[:5] == "/ROOM":
        changeroom(userid, sock, msg) # logged on user wants to change room
    elif umsg == "/STATS":
        sendstats(userid, sock)
    elif umsg == "/LOGON":
        adduser(userid, sock, CurrentTime)
        updbuff = 0 # already up-to-date
    elif umsg == "/LOGOFF":
        deluser(userid, sock)
        updbuff = 0 # removed, nothing to update
    elif umsg == "/HELP":
        helpuser(userid, sock)
    elif umsg == shutdownpswd:
        log(f"Shutdown initiated by {userid}@{sock.getpeername()[0]}")
        xit()
    else:
        sendchatmsg(userid, sock, msg)
    
    if updbuff == 1:
        refreshTime(CurrentTime, userid, sock)
    CheckTimeout(CurrentTime)

def sendchatmsg(userid, sock, msg):
    # what we got is a message to be distributed to all online users
    global msgcount
    inthere = 0
    for ci in range(len(logged_on_users)):
        entry = logged_on_users[ci]
        if entry[0] == userid and entry[1] == sock:
            inthere = 1
            break
    if inthere == 1:
        # USER IS ALREADY LOGGED ON
        for ci in range(len(logged_on_users)):
            entry = logged_on_users[ci]
            entry[1].send(f'<> {userid}@{sock.getpeername()[0]}:{msg}'.encode())
        
        msgcount = msgcount + 1
    else:
        # USER NOT LOGGED ON YET, LET'S SEND HELP TEXT
        sock.send(f'Welcome to Logorrhea, the FSMP chat server, v{logorrheaversion}'.encode())
        sock.send('You are currently NOT logged on.'.encode())
        sock.send('/HELP for help, or /LOGON to logon'.encode())
        msgcount = msgcount + 3

def sendwho(userid, sock):
    # who is online right now on this system?
    global msgcount
    userswho = 0
    sock.send('List of currently logged on users:'.encode())
    for ci in range(len(logged_on_users)):
        entry = logged_on_users[ci]
        sock.send(f'> {entry[0]}@{entry[1].getpeername()[0]}'.encode())
        msgcount = msgcount + 1
        userswho = userswho + 1
    sock.send(f'> Total online right now: {userswho}'.encode())
    msgcount = msgcount + 1

def sendstats(userid, sock):
    # send usage statistics to whoever asks, even if not logged on
    global msgcount
    sock.send(f'-> Total number of users: {totaluser}'.encode())
    sock.send(f'-> Highest nr.  of users: {highestusers}'.encode())
    sock.send(f'-> total number of msgs : {msgcount}'.encode())
    sock.send(f'-> Server up since      : {starttime} {timezone}'.encode())
    
    msgcount = msgcount + 4

def adduser(userid, sock, currentTime):
    # add user to list
    global totaluser
    global msgcount 
    global highestusers
    inthere = 0
    for cid in range(len(logged_on_users)):
        entry = logged_on_users[cid]
        if userid == entry[0] and sock == entry[1]:
            inthere = 1
            log(f"List already logged-on: {userid}@{sock.getpeername()[0]}")
            sock.send('-> You are already logged on.'.encode())
            sock.send(f'-> total number of users: {totaluser}'.encode())
    if inthere == 0:
        totaluser = totaluser + 1
        if totaluser < 0:
            totaluser = 0
        
        if highestusers < totaluser:
            highestusers = highestusers + 1
            
        logged_on_users.append([userid, sock, currentTime])
        log(f"List user added: {userid}@{sock.getpeername()[0]}")
        sock.send('-> LOGON succeeded. '.encode())

        sock.send(f'-> Total number of users: {totaluser}'.encode())
        announce(userid, sock) # announce new user to all users
    msgcount = msgcount + 2

def deluser(userid, sock):
    global totaluser
    global msgcount
    inthere = 0
    for cid in range(len(logged_on_users)):
        entry = logged_on_users[cid]
        if userid == entry[0] and sock == entry[1]:
            inthere = 1
            del logged_on_users[cid]
            totaluser = totaluser - 1
            sock.send('-> You are logged off now.'.encode())
            sock.send(f'-> New total number of users: {totaluser}'.encode())
            msgcount = msgcount + 2
            break
            
    if inthere == 0:
        log(f"User logoff rejected, not logged-on: {userid}@{sock.getpeername()[0]}")
    
    # Can keep an open conn if they want to
    #  table[user]['socket'].close()
    #  inputs.remove(table[user]['socket'])

def systeminfo(userid, sock):
    # send /SYSTEM info about this host
    global msgcount
    sock.send(f'-> Host                 : {HOST}:{PORT}'.encode())
    sock.send(f'-> Logorrhea version    : {logorrheaversion}'.encode())
    sock.send(f'-> OS for this host     : {osversion}'.encode())
    sock.send(f'-> Type of host         : {typehost}'.encode())
    sock.send(f'-> Location of this host: {hostloc}'.encode())
    sock.send(f'-> Time Zone of         : {timezone}'.encode())
    sock.send(f'-> SysOp for this server: {sysopname}'.encode())
    sock.send(f'-> SysOp email addr     : {sysopemail}'.encode())
    
    msgcount = msgcount + 7

def helpuser(userid, sock):
    # send help menu
    global msgcount
    sock.send(f'Welcome to Logorrhea, the FSMP chat server, v{logorrheaversion}'.encode())
    sock.send('-----------------------------------------------------------------'.encode())
    sock.send(' '.encode())
    sock.send('/HELP for this help'.encode())
    sock.send('/WHO for connected users'.encode())
    sock.send('/LOGON to logon to this chat room and start getting chat messages'.encode())
    sock.send('/LOGOFF to logoff and stop getting chat messages'.encode())
    sock.send('/STATS for chat statistics'.encode())
    sock.send('/SYSTEM for info about this host'.encode())
    sock.send(' '.encode())
    sock.send('/ROOM 1-9 to join any room, default is room zero (0)'.encode())
    sock.send(' messages with <-> are incoming chat messages...'.encode())
    sock.send(' messages with   > are service messages from the chat server'.encode())
    
    
    
    msgcount = msgcount + 11

def announce(userid, sock):
    # announce newly logged on user to all users
    cj = 0 # save logons to remove, else logon buffer doesn't match
    for ci in range(len(logged_on_users)):
        entry = logged_on_users[ci]
        logged_on_users[ci][1].send(f'-> New user joined:    {userid}@{sock.getpeername()[0]}'.encode())

def changeroom(userid, sock, msg):
    # user who is already logged on wants to change to a different room
    stripmsg = msg.strip()
    wantsroom = stripmsg.split(None, 1)[1] # remove /ROOM from e.g. /ROOM 3 to leave only 3
    if (not re.match(r'^\d+$', wantsroom)) or (int(wantsroom) < 0) or (int(wantsroom) > 9):
        sock.send('-> You have chosen an invalid room number (0-9'.encode())
    else:
        inthere = 0
        for ci in range(len(logged_on_users)):
            entry = logged_on_users[ci]
            if entry[0] == userid and entry[1] == sock:
                inthere = 1
            break
        if inthere == 1:
            # USER IS ALREADY LOGGED ON
            for ci in range(len(logged_on_users)):
                entry = logged_on_users[ci]
                # TODO: change room to wantsroom
                entry[1].send(f'<> -> you are now in room {wantsroom}'.encode())
        
            msgcount = msgcount + 1
        else:
            # USER NOT LOGGED ON YET, LET'S SEND HELP TEXT
            sock.send(f'Welcome to Logorrhea, the FSMP chat server, v{logorrheaversion}'.encode())
            sock.send('You are currently NOT logged on.'.encode())
            sock.send('/HELP for help, or /LOGON to logon'.encode())
            msgcount = msgcount + 3


def CheckTimeout(ctime):
    # check if user hasn't sent a message, automatic LOGOFF
    cj = [] # save logons to remove, else logon buffer doesn't match
    for ci in range(len(logged_on_users)):
        entry = logged_on_users[ci]
        # print(entry[0], entry[1].getpeername()[0], ctime, entry[2], int(ctime)-int(entry[2]))
        if int(ctime) - int(entry[2]) > maxdormant: # timeout per configuration
            cj.append(ci)
    for ci in range(len(cj)):
        log(f'{logged_on_users[cj[ci]][0]}@{logged_on_users[cj[ci]][1].getpeername()[0]} logged off due to timeout reached {maxdormant} minutes')
        deluser(logged_on_users[cj[ci]][0], logged_on_users[cj[ci]][1])
        
def refreshTime(ctime, userid, sock):
    # Refresh last transaction time
    # pdb.set_trace()
    inthere = 0
    for ci in range(len(logged_on_users)):
        entry = logged_on_users[ci]
        if entry[0] == userid and entry[1] == sock:
            entry[2] = ctime

def exTime():
    # Calculate Seconds in this year
    now = datetime.datetime.now()
    day_of_year = now.timetuple().tm_yday
    seconds_in_days = (day_of_year - 1) * 86400
    current_time = time.strftime("%H:%M:%S")
    hh, mm, ss = current_time.split(":")
    seconds_in_time = int(hh) * 3600 + int(mm) * 60 + int(ss)
    total_seconds = seconds_in_days + seconds_in_time
    result = str(total_seconds).zfill(8)
    return result

def mytime():
    now = datetime.datetime.now()
    hr = now.hour
    mi = now.minute
    if hr > 12:
        ampm = 'pm'
        hr -= 12
    elif hr == 12:
        ampm = 'pm'
    else:
        ampm = 'am'
    timenow = f"{hr}.{mi} {ampm}"
    dow = now.strftime("%a")  
    day = now.day
    month = now.strftime("%b")
    year = str(now.year)
    
    return f"{timenow}, {dow} {day} {month} {year}" 

def log(logline):
    print(f"{mytime()} :: {logline}")
if __name__ == '__main__':
    main()