# from socket import *
import time 
import os
import RDT

# 创建发送方类
sender = RDT.Sender('client', 8080, 8090)
filepath = 'article.txt'
file_content = open(filepath, 'rb')
send_size = 0
while 1:
    data = file_content.read(100)
    send_size += len(data)
    if not data:
        break
    print('send %d bytes' %send_size)
    sender.rdt_send(data.decode('utf-8'))

print('file sent over...')
sender.disconnect()