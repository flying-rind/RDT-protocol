import RDT
import time

receiver = RDT.Receiver('server', 8080, 8090)

new_file_name = 'receive_article.txt'
new_file = open(new_file_name, 'wb')
timeout = 5

# 写入内容
time_of_last_data = time.time()
while True:
    msg_S = receiver.rdt_receive()
    if msg_S == None:
        if time.time() - time_of_last_data > timeout:
            print("timeout")
            break
        else:
            continue

    time_of_last_data = time.time()
    new_file.write(msg_S.encode('utf-8'))

new_file.close()
print('Server ended')
receiver.disconnect()

    
