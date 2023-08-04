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
import pdb
import os
import platform
import multiprocessing

pdb.set_trace()

# configuration parameters - IMPORTANT
logorrheaversion = "1.7.0" # needed for compatibility check
timezone = "CET" # IMPORTANT
maxdormant = 3000 # max time user can be dormant
host = 'localhost' # IMPORTANT
port = 3141 # IMPORTANT
buffer_size = 1024 # IMPORTANT
shutdownpswd = "absturz" # any user with this passwd shuts down the chat server
osversion="OS X 10.10" # OS version for enquiries and stats
typehost="ThinkPad X230" # what kind of machine
hostloc = "Mein VW Golf" # where is this machine
sysopname = "Fred" # sysop user who can force users out
sysopemail = "fred@fred.net" # where to contact this sysop
compatibility = 2 # to distinguish between host systems - TODO
sysopuser = 'fred' # sysop user who can force users out
sysophost = socket.gethostbyname(socket.gethostname()) # sysop host automatically set
raterwatermark = 12 # max msgs per second set for this server



# Federation settings below
federation = 0 # 0 = federation off, receives/no sending, 1=on
federated = [("shell.xshellz.com", 3141)] # Logorrhea instances at these hosts will get all msgs!
federatednum = 1 # how many entries in the list

# global variables

logged_on_users = [] # dict of dicts of all logged on users
inputs = [] # list of all sockets
outputs = [] # list of uh, nothing
msgcount = 0 # total number of msgs sent
totaluser = 0 # online users at any given moment
highestusers = 0 # most users online at any given moment
otime = 0 # overtime to log off users after n minutes
starttime = None # time this server started
starttimeSEC = None # for msg rate calculation
logline = " " # initialize log line
receivedmsgs = 0 # number of messages received for stats and loop
premsg = [6, "", "", "", "", "", ""] # needed for loop detector to compare
msgrotator = 1 # this will rotate the 7 prev msgs

# CODE SECTION

if compatibility > 1: # this is macOS, not Linux
    print(f'All CPU avg: {cpu} %    Paging: {paging()}')
    
    print(f'Machine type: {configuration()}     RAM: {rstorage()}')
    print(f'Number of cores: {numcpus()}')

# Define SSL context
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile='server_cert.pem', keyfile='server_key.pem')

def main():
    global inputs
    global starttime
    global starttimeSEC
    global receivedmsgs
    starttime = mytime()
    starttimeSEC = exTime()
    log(f"Logorrhea chat {logorrheaversion} started. ")
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
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
                            log(f'from {userid}@{sock.getpeername()[0]} {msg}')
                            receivedmsgs = receivedmsgs + 1
                            # below line checks if high rate watermark is exceeded
                            # and if so... exits!
                            highrate(receivedmsgs, starttimeSEC, raterwatermark)
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
    umsg = msg.upper() # make upper case
    umsg = umsg.strip()
    commandumsg = umsg[1:6]
    updbuff = 1

    # HANDLE MESSAGE TYPES
    if umsg == "/WHO":
        sendwho(userid, sock)
    elif umsg == "/SYSTEM":
        systeminfo(userid, sock)
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
    elif commandumsg == 'FORCE':
        force(userid, sock, msg)
    else:
        sendchatmsg(userid, sock, msg)
    
    if updbuff == 1:
        refreshTime(CurrentTime, userid, sock) # for each msg!
    CheckTimeout(CurrentTime)

def force(userid, sock, msg):
    global totaluser
    global msgcount
    # sysop forces a user out
    forceuser = msg[10:17] # extract user after /force command
    forceuser = strip(forceuser)
    # print(f"User to be forced - {forceuser}?")
    if userid == sysopuser and sock.getpeername()[0] == sysophost: #ok, user is autorized
        inthere = 0
        for ci in range(len(logged_on_users)):
            if logged_on_users[ci][0] == forceuser and logged_on_users[ci][1].getpeername()[0] == sock:
                inthere = 1
                del logged_on_users[ci]
                log(f'Forced: {forceuser}@{sock.getpeername()[0]}')
                totaluser = totaluser - 1
                sock.send(f'-> This user has been forced off: {forceuser}'.encode())
                sock.send(f'-> New total number of users: {totaluser}'.encode())
                msgcount = msgcount + 2
                break
        if inthere == 0:
            log(f"User logoff rejected, not logged-on: {forceuser}@{sock.getpeername()[0]}")
    else:
        log(f'This user:  {userid}@{sock.getpeername()[0]} tried to force off user: {forceuser}')
        sock.send(f'-> Not authorized to force off user: {forceuser}'.encode())
        msgcount = msgcount + 1

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
            entry[1].send(f'{userid}@{sock.getpeername()[0]}:{msg}'.encode())
        
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
    global totaluser
    userswho = 0
    sock.send('> List of currently logged on users:'.encode())
    msgcount = msgcount + 1
    for ci in range(len(logged_on_users)):
        entry = logged_on_users[ci]
        lasttime = ctime - entry[2]
        sock.send(f'> {entry[0]}@{entry[1].getpeername()[0]} - last seen in min: {lasttime}'.encode())
        msgcount = msgcount + 1
        userswho = userswho + 1
    sock.send(f'> Total online right now: {userswho}'.encode())
    totaluser = userswho
    msgcount = msgcount + 1

def sendstats(userid, sock):
    # send usage statistics to whoever asks, even if not logged on
    global msgcount
    global totaluser    
    onlinenow = countusers(userid, sock)
    cpu = subprocess.check_output("uptime | awk -F'[a-z]:' '{ print $2}'", shell=True).decode().strip()  
    actualtime = exTime()
    elapsedsec = actualtime - starttimeSEC
    elapsedhr = (elapsedsec / 60) / 60
    msgsrate = receivedmsgs / elapsedhr
    if totaluser < 0:
        totaluser = 0 # still goes negative sometimes
    sock.send(f'-> Total number of users: {onlinenow}'.encode())
    sock.send(f'-> Highest nr.  of users: {highestusers}'.encode())
    sock.send(f'-> total number of msgs : {msgcount}'.encode())
    sock.send(f'-> Server up since      : {starttime} {timezone}'.encode())
    sock.send(f'-> System CPU load      : {cpu}%'.encode())
    
    msgcount = msgcount + 6

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
        if totaluser < 0:
            totaluser = 0
        totaluser = totaluser + 1
        
        if highestusers < totaluser:
            highestusers = highestusers + 1
            
        logged_on_users.append([userid, sock, currentTime])
        log(f"List user added: {userid}@{sock.getpeername()[0]}")
        log(f'List size: {len(logged_on_users)}')
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
            log(f'List size: {len(logged_on_users)}')
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
    cpu = subprocess.check_output("uptime | awk -F'[a-z]:' '{ print $2}'", shell=True).decode().strip()  
    
    sock.send(f'-> Host                 : {host}:{port}'.encode())
    sock.send(f'-> Logorrhea version    : {logorrheaversion}'.encode())
    sock.send(f'-> OS for this host     : {osversion}'.encode())
    sock.send(f'-> Type of host         : {typehost}'.encode())
    sock.send(f'-> Location of this host: {hostloc}'.encode())
    sock.send(f'-> Time Zone of         : {timezone}'.encode())
    sock.send(f'-> SysOp for this server: {sysopname}'.encode())
    sock.send(f'-> SysOp email addr     : {sysopemail}'.encode())
    sock.send(f'-> System Load          : {cpu}'.encode())
    
    if compatibility > 1:
        page = paging()
        rstor = rstorage()
        cfg = configuration()
        lcpus = numcpus()
        sock.send(f'-> System Load          : {cpu}')
        sock.send(f'-> Machine Type         : {cfg}')
        sock.send(f'-> Memory               : {rstor}')
        sock.send(f'-> Number of CPUs       : {lcpus}')
    
    if compatibility > 1:
        msgcount = msgcount + 12
    else:
        msgcount = msgcount + 8

def helpuser(userid, sock):
    # send help menu
    global msgcount
    sock.send(f'Welcome to Logorrhea, the FSMP chat server, v{logorrheaversion}'.encode())
    sock.send('-----------------------------------------------------------------'.encode())
    sock.send(' '.encode())
    sock.send('/HELP    for this help'.encode())
    sock.send('/WHO     for connected users'.encode())
    sock.send('/LOGON   to logon to this chat room and start getting chat messages'.encode())
    sock.send('/LOGOFF  to logoff and stop getting chat messages'.encode())
    sock.send('/STATS   for chat statistics'.encode())
    sock.send('/SYSTEM  for info about this host'.encode())
    sock.send('/FORCE   to force a user off (SYSOP only)'.encode())
    sock.send(' '.encode())
#    sock.send('/ROOM 1-9 to join any room, default is room zero (0)'.encode())
    sock.send(' messages with <-> are incoming chat messages...'.encode())
    sock.send(' messages with   > are service messages from the chat server'.encode())
    
    
    
    msgcount = msgcount + 13

def countusers(userid, sock):
    onlineusers = 0
    for ci in range(len(logged_on_users)):
        entry = logged_on_users[ci]
        lasttime = ctime - entry[2]
        onlineusers = onlineusers + 1
    return onlineusers
    

def announce(userid, sock):
    # announce newly logged on user to all users
    cj = 0 # save logons to remove, else logon buffer doesn't match
    for ci in range(len(logged_on_users)):
        entry = logged_on_users[ci]
        logged_on_users[ci][1].send(f'-> New user joined:    {userid}@{sock.getpeername()[0]}'.encode())


def CheckTimeout(ctime):
    global totaluser
    # Check if user hasn't sent a message, automatic LOGOFF
    cj = [] # save logons to remove, else logon buffer doesn't match
    for ci in range(len(logged_on_users)):
        entry = logged_on_users[ci]
        # print(entry[0], entry[1].getpeername()[0], ctime, entry[2], int(ctime)-int(entry[2]))
        if int(ctime) - int(entry[2]) > maxdormant: # timeout per configuration
            totaluser = totaluser - 1
            print(f'removed user: {entry[1].getpeername()[0]}')
            cj.append(ci)
    for ci in range(len(cj)):
        log(f'{logged_on_users[cj[ci]][0]}@{logged_on_users[cj[ci]][1].getpeername()[0]} logged off due to timeout reached {maxdormant} minutes')
        deluser(logged_on_users[cj[ci]][0], logged_on_users[cj[ci]][1])
        totaluser = totaluser - 1
        
        
        
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

def cpubusy():
    cpu_load = subprocess.check_output("uptime | awk -F'[a-z]:' '{ print $2}'", shell=True).decode().strip()
    cpu = cpu_load.split()[0]
    return round(float(cpu) * 100, 3)

def paging():
    output = subprocess.check_output("vm_stat", shell=True).decode()
    
    lines = output.strip().split("\n")
    stats = {}
    for line in lines:
        parts = line.split(":")
        if len(parts) == 2:
            stats[parts[0].strip()] = int(parts[1].strip().replace(".", "").replace(",", ""))

    page_size = stats["Pages free"] / (256 * 1024)

    uptime = subprocess.check_output("uptime | awk -F'up' '{print $2}' | awk -F',' '{print $1}'", shell=True).decode().strip()
    uptime = int(uptime.split(":")[0]) * 60 + int(uptime.split(":")[1])
    paging_rate = (stats["Pages paged in"] + stats["Pages paged out"]) / uptime
    
    return paging_rate

def rstorage():
    output = subprocess.check_output("df -k / | tail -1", shell=True).decode().strip()
    
    _, total, used, available, percent, _ = output.split()
    
    return int(used)

def configuration():
    uname = platform.uname()
    uptime = subprocess.check_output("uptime | awk -F'up' '{print $2}' | awk -F',' '{print $1}'", shell=True).decode().strip()
    model_info = subprocess.check_output("sysctl hw.model", shell=True).decode().strip()
    cpu_info = subprocess.check_output("sysctl hw.ncpu", shell=True).decode().strip()
    
    system = uname.system
    node = uname.node
    release = uname.release
    version = uname.version
    machine = uname.machine
    model = model_info.split(":")[1].strip()
    ncpu = cpu_info.split(":")[1].strip()

    return system

def numcpus():
    lcpus = multiprocessing.cpu_count()
    return lcpus
    
if __name__ == '__main__':
    main()