'''
Network.py
提供一个网络层抽象
网络层提供不可靠链路,以固定概率丢包和比特错误
'''

import socket
import threading
import random
import RDT

'''
网络层类
为网络层链路提供一层抽象,发送方和接收方的send和recieve都
经过网络层,网络层链路以一定的概率丢包
'''
class NetworkLayer:
    # 丢包率和出错率
    prob_pkt_loss = 0
    prob_byte_corr = 0

    # 套接字
    sock = None
    server_address = None
    client_address = None

    # 接受缓冲区,其需要互斥访问
    buffer_S = ''
    lock = threading.Lock()
    # STOP信号
    stop = False
    collect_thread = None

    def __init__(self, role, server_port, client_port):
        self.role = role
        if role == 'client':
            print('Network: role is client')
            # 创建UDP套接字
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(('localhost', client_port))
            self.client_address = ('localhost', client_port)
        elif role == 'server':
            print('Network: role is server')
            # 创建UDP套接字
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 绑到本地IP和指定端口
            self.sock.bind(('localhost', server_port))
            self.server_address = ('localhost', server_port)

        # 启动线程不断地收集数据放入缓冲区
        self.collect_threads = threading.Thread(name = 'Collector', target=self.collect)

    '''
    回收线程
    '''
    def disconnect(self):
        if self.collect_thread:
            self.stop = True
            self.collect_thread.join()

    '''
    udt_send
    经不可靠链路传输,
    输入一个字节串,可能会丢失,也可能在字节串中随机插入一些错误
    '''
    def udt_send(self, msg_S):
        # 模拟丢包
        if random.random() < self.prob_pkt_loss:
            return
        
        # 模拟比特错误,在已经打包好的rdt报文中随机插入一定数量的XXX
        if random.random() < self.prob_byte_corr:
            # 保证长度字节不会发生错误
            start = random.randint(RDT.Packet.length_S_length, len(msg_S)-5)
            num = random.randint(1, 5)
            error_S = ''.join(random.sample('XXXXX', num))
            msg_S = msg_S[:start] + error_S + msg_S[start+num:]
        
        # 发送字节串
        totalsent = 0
        while totalsent < len(msg_S):
            # 分别发送给接收方和发送方
            if self.role == 'client':
                sent = self.sock.sendto(msg_S[totalsent:].encode('utf8'), self.server_address)
            elif self.role == 'server':
                sent = self.sock.sendto(msg_S[totalsent:].encode('utf8'), self.client_address)
                
            if sent == 0:
                raise RuntimeError('udp connection broken')
            totalsent += sent

    '''
    collect,线程函数
    发送方和接收方的网络层都创建一个线程来不断地接受字节并放入自己的缓存区
    '''
    def collect(self):
        while True:
            try:
                recv_bytes = self.sock.recvfrom(2048)[0]
                with self.lock:
                    self.buffer_S += recv_bytes.decode('utf-8')
            except:
                pass
            if self.stop:
                return

    '''
    udt_receive
    将缓存区中的所有内容取出提交
    '''
    def udt_receive(self):
        while self.lock:
            ret_S = self.buffer_S
            self.buffer_S = ''
        return ret_S