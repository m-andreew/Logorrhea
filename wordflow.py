"""
wordflow v0.1 Jul 30 2023
an FSMP client connecting to a Logorrhea instance via TLS
Usage:
python wordflow.py host port
(c) 2023 The FSMP Committee
All rights reserved
"""

import socket
import ssl
import select
import os
import sys
import string
import tty
import termios 
import atexit

# Load SSH keys
with open('client_key.pem', 'rb') as f:
    client_key = f.read()
with open('client_cert.pem', 'rb') as f:
    client_cert = f.read()

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

def clear_line():
    sys.stdout.write('\033[2K\033[G')
    sys.stdout.flush()

def main():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock = context.wrap_socket(sock, server_hostname=HOST)
        sock.connect((HOST, PORT))
    except Exception as err:
        print("Error creating socket:", err)
        sys.exit()

    inputs = [sock, sys.stdin]
    outputs = []
    buffer = ''
    index = 0
    
    nick = input("Enter Nick: ")
    # Setup Terminal
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    atexit.register(lambda: termios.tcsetattr(fd, termios.TCSADRAIN, old_settings))
    tty.setcbreak(sys.stdin.fileno())
    
    while True:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        for r in readable:
            if r is sock:
                raw_message = sock.recv(1024)
                if not raw_message:
                    clear_line()
                    print("Server closed connection")
                    sys.exit()
                clear_line()
                # sys.stdout.write("< ")
                print(raw_message.decode())
                sys.stdout.write("> " + buffer)
                sys.stdout.flush()

            elif r is sys.stdin:
                c = sys.stdin.read(1)
                if c == '\x03':
                    sock.close()
                    sys.exit()
                elif c == '\n' or c == '\r':
                    sock.send((nick + ':' + buffer + '\n').encode('utf-8'))
                    # clear_line()
                    # sys.stdout.write('> ' + buffer +'\n')
                    # sys.stdout.flush()
                    buffer = ''
                    index = 0
                elif c == '\x1b':
                    next1, next2 = sys.stdin.read(1), sys.stdin.read(1)
                    if next1 == '[':
                        if next2 == 'D':
                            index = max(0, index - 1)
                        elif next2 == 'C':
                            index = min(len(buffer), index + 1)
                        
                        clear_line()
                        sys.stdout.write("> " + buffer)
                        sys.stdout.write("\u001b[1000D" + "\u001b[" + str(index+2) + "C")
                        sys.stdout.flush()
                        
                elif c == '\x7f':
                    if index > 0:
                        buffer = buffer[:index-1] + buffer[index:]
                        index -= 1
                    clear_line()
                    sys.stdout.write("> " + buffer)
                    sys.stdout.write("\u001b[1000D" + "\u001b[" + str(index+2) + "C")
                    sys.stdout.flush()
                else:
                    buffer = buffer[:index] + c + buffer[index:]
                    index += 1
                    clear_line()
                    sys.stdout.write("> " + buffer)
                    sys.stdout.write("\u001b[1000D" + "\u001b[" + str(index+2) + "C") 
                    sys.stdout.flush()
if __name__ == "__main__":
    main()
