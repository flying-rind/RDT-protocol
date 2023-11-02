# from socket import *
import time 
import os
import RDT

# 创建发送方类
sender = RDT.Sender('client', 8080, 8090)
filepath = 'article.txt'
file_content = open(filepath, 'rb')
send_size = 0

# 已发送的字节数
sent = 0
# 文件的大小
file_len = os.path.getsize(filepath)
print("file_len = %d" % file_len)
data = file_content.read(100)

while 1:
    sender.rdt_send(data.decode('utf-8'))
    sent += len(data)
    print('sent %d bytes' % sent)
    data = file_content.read(100)
    if sent >= file_len:
        break

print('file sent over...')
sender.disconnect()