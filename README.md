# Logorrhea
This chat server acts as a reference implementation for the Fred Short Message Protocol.
Also included is a simple client (WordFlow).

# Usage
Run `./certs`, then `python3 logorrhea.py` for the server or `wordflow.py` for the client.
The commands available to clients are:
* `/LOGON` to add yourself to the distribution list for messages
* `/LOGOFF` to remove yourself from the distribution of messages
* `/WHO` who is logged on currently?
* `/STATS` some chat server stats
* `message` whatever you want to tell your friends on the channel

# Typical Logorrhea Session
```
> /LOGON fred
-> LOGON succeeded. 
-> Total number of users: 1
-> New user joined:    FRED@127.0.0.1
> /HELP
Welcome to Logorrhea, the FSMP chat server, v1.2
-------------------------------------   ----------------------------
 
/HELP for this help
/WHO for connected users
/LOGON to logon to this chat room and start getting chat messages
/LOGOFF to logoff and stop getting chat messages
/STATS for chat statistics
 
/ROOM 1-9 to join any room, default is room zero (0)
 messages with <-> are incoming chat messages...
 messages with   > are service messages from the chat server
```
