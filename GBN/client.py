from socket import *
import time 
import os
import struct

client = socket(AF_INET,SOCK_DGRAM)
server_addr=('127.0.0.1',8080)
filepath = 'article.txt'
print("Start transferring files on client:")

if os.path.isfile(filepath):
    file_size=struct.calcsize('128sl')
    file_head=struct.pack('128sl',os.path.basename(filepath).encode('utf-8'),os.stat(filepath).st_size)
    client.sendto(file_head,server_addr)
    file_content = open(filepath,'rb')
    send_size=0
    while 1:
        data = file_content.read(1024)
        send_size+=len(data)
        if not data:
            print('file send over...')
            break
        print("send %d bytes"%send_size)
        client.sendto(data,server_addr)

else:
    print("No such file")
    exit()
