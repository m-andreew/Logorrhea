"""
chat v.0.5 Jul 30 2023
an FSMP (Fred Short Message Protocol) chat server, starts and listens at
HOST:PORT
invoke with:
python chat.py host port defaultlogofftime
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

import logging
logging.basicConfig(level=logging.DEBUG)


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

# Users
table = {}

inputs = []
outputs = []
    
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
    while inputs:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)

        for sock in readable:
            if sock is server_socket:
                conn, addr = sock.accept()
                conn = context.wrap_socket(conn, server_side=True)
                conn.send("Welcome to Logorrhea!".encode())
                inputs.append(conn)
            else:
                try:
                    line = sock.recv(BUFFER_SIZE)
                    if line:
                        # print("message received:"+line.decode())
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

        for sock in exceptional:
            if sock in inputs:
                inputs.remove(sock)
            try:
                sock.close()
            except:
                pass

def readcommand(sock, sockline):

    # sockmsgtime = time.time()

    s = sockline.split(":")

    sockuser = s[0]
    sockmsg = s[1] # This is the payload part of the incoming msg
    uppersockmsg = sockmsg.upper() # make upper case for command processing
    uppersockuser = sockuser.upper() # make user upper case
    print("'%s' '%s'" % (uppersockuser, uppersockmsg))

    # at this point we have the sock, the username in uppersockuser and the
    # payload in sockmsg/uppersockmg. Now we start with some very simple
    # processing
    # -------------------------------------------------------------------------
    # /HELP sends a help menu to the user
    # /WHO sends a list of (recently) logged on users
    # /LOGON logs the user on and adds them to the list
    # /LOGOFF logs the user off and removes them from the list
    # /TIMER30 sets the timer to 30 min for inactive users
    # /TIME60 sets the timer to 60 min for inactive users
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
        # user sending to broadcast LOGGED ON?? if so, broadcast
        if uppersockuser in table:
            broadcastmsg(uppersockuser, sockmsg)
        else:
            try:
                sock.send("You are not currently logged on to Logorrhea".encode())
            except Exception as err:
                print("failed with %s" % (err))
                sock.close()

def senduserlist(uppersockuser):
    # loop through user list and do
    # sock.send(user1...99)

    for user in table:
        try:
            table[uppersockuser]['socket'].send(f"Online last 30min: {user}".encode())
        except Exception as err:
            print("failed with %s" % (err))
            break

def sendstats(user):
    # sock.send(<string of collected usage stats>)
    pass

def adduser(user, sock):
    # add user to userlist dict and inform him he's been added
    # sock.send(<string of collected usage stats>)
    table[user] = {'lastactivity': time.time(), 'socket': sock}
    try:
        sock.send("Welcome to Logorrhea v0.1.".encode())
    except Exception as err:
        print("failed with %s" % (err))

def deluser(user):
    global inputs
    # del user to userlist dict and inform him he's been added
    # sock.send(<string of collected usage stats>)
    try:
        table[user]['socket'].send("Goodbye from Logorrhea v0.1..".encode())
        table[user]['socket'].close()
        inputs.remove(table[user]['socket'])
    except Exception as err:
        print("failed with %s" % (err))
    finally:
        del table[user]

def broadcastmsg(uppersockuser, sockmsg):
    # loop through all users WHO HAVE NOT BEEN IDLE FOR TOO LONG and
    # THE SEND COMMAND NEEDS TO BE LIKE THIS: sock.send(sockmsg)
    # for username, userDict in table.items():
    # if userDict['lastActivity'] `is before 30 minutes`:
    # -->> QUESTION? del table[username] HOW DO I DO TIME.TIME-30M?
    users_to_remove = []
    for user in table:
        try:
            table[user]['socket'].send(sockmsg.encode())
        except Exception as err:
            print("failed with %s" % (err))
            users_to_remove.append(user)
    
    for user in users_to_remove:
        deluser(user) 

if __name__ == '__main__':
    main()
