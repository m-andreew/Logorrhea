"""
chat v.0.9.7 Jul 30 2023
an FSMP (Fred Short Message Protocol) chat server, starts and listens at
HOST:PORT
invoke with:
python logorrhea.py
(c) 2023 The FSMP Committee
All rights reserved
"""

import socket
import ssl
import select
import os
import signal
import sys
import string
import time
import datetime
from dataclasses import dataclass

import traceback


# Load SSH keys
with open('server_key.pem', 'rb') as f:
    server_key = f.read()
with open('server_cert.pem', 'rb') as f:
    server_cert = f.read()

# Define SSL context
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile='server_cert.pem', keyfile='server_key.pem')

# HOST = 'shell.xshellz.com'
HOST = 'localhost'
PORT = 3141
BUFFER_SIZE = 1024

table = {} # dict of dicts of all logged on users

inputs = []
outputs = []
msgcount = 0 # total messages sent, used by /STATS command
totaluser = 0 # total users logged in, used by /STATS command

# function to prune old inactive users
def ticker():
    users_to_remove = []
    thirtyMinutesAgo = time.time()-120*60
    for username, userDict in table.items():
        if userDict["lastactivity"] < thirtyMinutesAgo:
            print("Deleting inactive user '%s'" % (username))
            users_to_remove.append(username)
    
    for user in users_to_remove:
        del table[user]

def main():
    global inputs
    print("FSMP chat server started....")
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print("Server socket successfully created, now listening")
    except Exception as err:
        print("Error creating server socket:", err)
        sys.exit()
        
    inputs = [server_socket]
    outputs = []
    c = time.time()
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
                    line = sock.recv(BUFFER_SIZE)
                    if line:
                        readcommand(sock, line.decode().removesuffix("\n")) # pass incoming line to message parser
                    else:
                        if sock in inputs:
                            inputs.remove(sock)
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
            if time.time()-c >= 60:
                c = time.time()
                ticker()
            time.sleep(0.4)

        for sock in exceptional:
            if sock in inputs:
                inputs.remove(sock)
            try:
                sock.close()
            except:
                pass

def send(user, *args):
    global msgcount
    try:
        table[user]['socket'].send(''.join(args).encode())
        msgcount += 1
    except Exception as err:
        print("send failed with %s" % (err))

def readcommand(sock, sockline):
    global msgcount
    s = sockline.split("}") # split this message into sender and msg content

    sockuser = s[0]
    sockmsg = s[1] # This is the payload part of the incoming msg
    uppersockmsg = sockmsg.upper() # make upper case for command processing
    uppersockuser = sockuser.upper() # make user upper case
    print("'%s' '%s'" % (uppersockuser, sockmsg))

    # at this point we have the sock, the username in uppersockuser and the
    # payload in sockmsg/uppersockmg. Now we start with some very simple
    # processing
    # -------------------------------------------------------------------------
    # /HELP sends a help menu to the user
    # /WHO sends a list of (recently) logged on users
    # /LOGON logs the user on and adds them to the list
    # /LOGOFF logs the user off and removes them from the list
    # /STATS sends usage statistics
    # -------------------------------------------------------------------------

    if uppersockmsg == "/HELP":
        # print("This is the help case")
        return
    elif uppersockmsg == "/WHO":
        # print("This is the WHO case")
        senduserlist(uppersockuser)
    elif uppersockmsg == "/STATS":
        # print("This is the STATS case")
        sendstats(uppersockuser)
    elif uppersockmsg == "/LOGON":
        # print("This is the LOGON case")
        adduser(uppersockuser, sock)
    elif uppersockmsg == "/LOGOFF":
        # print("This is the LOGOFF case")
        deluser(uppersockuser)
    else:
        # must be regular message
        if uppersockuser in table:
            table[uppersockuser]['lastactivity'] = time.time()
            broadcastmsg(sockuser, sockmsg)
        else:
            try:
                sock.send("You are not currently logged on to Logorrhea".encode())
                msgcount += 1
            except Exception as err:
                print("failed with %s" % (err))
                sock.close()

def senduserlist(uppersockuser):
    for user in table:
        send(uppersockuser, "Online last 120 min: ", user)

def sendstats(user):
    s = str(msgcount)
    t = str(totaluser)
    send(user, "  Total messages: ", s, "   Total users:", t)

def adduser(user, sock):
    global totaluser
    table[user] = {'lastactivity': time.time(), 'socket': sock}
    try:
        send(user, "  Welcome to Logorrhea v0.9.6")
        totaluser += 1
    except Exception as err:
        print("failed with %s" % (err))

def deluser(user):
    global inputs
    send(user, "  Goodbye from Logorrhea v0.9.6")
    table[user]['socket'].close()
    inputs.remove(table[user]['socket'])
    del table[user]

def broadcastmsg(sockuser, sockmsg):
    # remove users inactive for 120 minutes
    users_to_remove = []
    thirtyMinutesAgo = time.time()-120*60
    for username, userDict in table.items():
        if userDict["lastactivity"] < thirtyMinutesAgo:
            print("Deleting inactive user '%s'" % (username))
            users_to_remove.append(username)
    
    for user in users_to_remove:
        del table[user]
    
    for user in table:
        send(user, "> ", sockuser, sockmsg)

if __name__ == '__main__':
    main()
