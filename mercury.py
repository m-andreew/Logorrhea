""" AUG 3, 2023
COPYRIGHT 2023 THE FSMP COMMITTEE
CHAT PROGRAM WITH PANELS AND SCROLLING"""

import curses
import socket
import ssl
import select
import os
import sys
import string
import tty
import termios 
import atexit


# address command
Welcome = 'Mercury v0'
stdscr = curses.initscr()
stdscr.nodelay(True)
curses.noecho()
curses.cbreak()
curses.start_color()
curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_BLACK)
curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)
curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
buffer = " "
index = 0
row = 9 # start scrolling at row 10

# Define SSL context
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.load_cert_chain(certfile='client_cert.pem', keyfile='client_key.pem')
context.load_verify_locations('server_cert.pem')
context.check_hostname = False
context.verify_mode = ssl.CERT_REQUIRED

# HOST = 'shell.xshellz.com'
HOST = 'localhost'
PORT = 3141
BUFFER_SIZE = 1024

def main():
    global Welcome
    global buffer
    global index
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock = context.wrap_socket(sock, server_hostname=HOST)
        sock.connect((HOST, PORT))
    except Exception as err:
        xit()

    inputs = [sock, sys.stdin]
    outputs = []
    index = 0
    Welcome = 'Enter Nick: '
    buffer = ''
    polling = True
    while polling:
        c = ask()
        if c == -1:
            continue
        if c == '\x03':
            xit()
        elif c == '\n' or c == '\r':
            if buffer == '':
                Welcome = '!No nick provided!'
            else:
                nick = buffer
                buffer = ''
                index = 0
                polling = False
        elif c == '\x1b':
            next1, next2 = sys.stdin.read(1), sys.stdin.read(1)
            if next1 == '[':
                if next2 == 'D':
                    index = max(0, index - 1)
                elif next2 == 'C':
                    index = min(len(buffer), index + 1)
        elif c == '\x7f':
            if index > 0:
                buffer = buffer[:index-1] + buffer[index:]
                index -= 1
        else:
            buffer = buffer[:index] + c + buffer[index:]
            index += 1
    Welcome = 'Mercury v0'
    while True:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        for r in readable:
            if r is sock:
                raw_message = sock.recv(1024)
                if not raw_message:
                    xit()
                showit(raw_message.decode())

            elif r is sys.stdin:
                c = ask()
                if c == -1:
                    continue
                elif c == '\x03':
                    xit()
                elif c == '\n' or c == '\r':
                    if buffer == '':
                        Welcome = '!No message provided!'
                    elif buffer == '//QUIT':
                        xit()
                    else:
                        sock.send((f'*MSG {nick} {buffer}').encode('utf-8'))
                        msgsent()
                    buffer = ''
                    index = 0
                elif c == '\x1b':
                    next1, next2 = sys.stdin.read(1), sys.stdin.read(1)
                    if next1 == '[':
                        if next2 == 'D':
                            index = max(0, index - 1)
                        elif next2 == 'C':
                            index = min(len(buffer), index + 1)
                elif c == '\x7f':
                    if index > 0:
                        buffer = buffer[:index-1] + buffer[index:]
                        index -= 1
                else:
                    buffer = buffer[:index] + c + buffer[index:]
                    index += 1
                stdscr.addstr(3, 4, buffer.ljust(30), curses.color_pair(2) | curses.A_UNDERLINE)
                stdscr.move(3, 4+index)
                stdscr.refresh()
                    
def xit(err = ""):    
    curses.nocbreak()
    curses.echo()
    curses.endwin()
    print(err)
    sys.exit()

def ask():
    stdscr.addstr(1, 34, Welcome.ljust(25), curses.color_pair(1))
    stdscr.addstr(3, 4, buffer.ljust(30), curses.color_pair(2) | curses.A_UNDERLINE)
    stdscr.move(3, 4+index)
    stdscr.refresh()
    try:
        return sys.stdin.read(1)
    except:
        return -1

def answer():
    global buffer
    stdscr.addstr(6, 1, 'You: '.ljust(5), curses.color_pair(3))
    stdscr.addstr(6, 9, buffer.ljust(30), curses.color_pair(4))
    stdscr.refresh()

def msgsent():
    stdscr.addstr(2, 9, 'Message sent! '.ljust(30), curses.color_pair(2))
    stdscr.refresh()

def showit(msg):
    global row
    if row > curses.LINES - 1:
        row = 9
        for i in range(row, curses.LINES):
            stdscr.addstr(i, 9, " "*30, curses.color_pair(1))
    stdscr.addstr(row, 9, msg.ljust(30), curses.color_pair(1))
    row = row + 1 + len(msg.ljust(30))//curses.COLS
    stdscr.move(3, 4+index)
    stdscr.refresh()

if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        xit(err)