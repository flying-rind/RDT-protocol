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

# debug
# for i in range(20):
while 1:
    # 若rdt_send发送,则返回True,否则返回False
    result = sender.rdt_send(data.decode('utf-8'))
    # print("sender base: %d, nextseqnum: %d" %(sender.base, sender.nextseqnum))
    if result == True:
        sent += len(data)
        print('sent %d bytes' % sent)
        data = file_content.read(100)
    if sent >= file_len:
        break

print('file sent over...')
sender.disconnect()