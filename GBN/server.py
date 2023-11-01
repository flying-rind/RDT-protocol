from socket import *
import struct

server = socket(AF_INET,SOCK_DGRAM)
server_addr=('127.0.0.1',8080)
server.bind(server_addr)

#解析文件信息
fileinfo_size = struct.calcsize('128sl')
fileinfo_pack=server.recvfrom(fileinfo_size)
#print(fileinfo_pack)
filename,filesize=struct.unpack('128sl',fileinfo_pack[0])
#除去多余字符
filename=filename.strip(b'\00')
filename=filename.decode()
# print(filename)
# server.close()
count=0
#已接收文件大小：
receive_size = 0
#创建本地文件：
fp = open('./'+'receive_'+str(filename),'wb')
#写入内容：
while receive_size!=filesize:
    if filesize-receive_size>1024:
        count+=1
        pack=server.recvfrom(1024)[0]
        receive_size+=len(pack)
        #print("received number %d packes"%count)
    else:
        count+=1
        pack=server.recvfrom(filesize-receive_size)[0]
        receive_size=filesize
        #print("received number %d packes"%count)
    print("received number %d bytes"%receive_size)
    fp.write(pack)
fp.close()
print('end receive:')
server.close()
