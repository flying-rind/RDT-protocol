'''
RDT.py
这个文件中实现单向的可靠传输协议
还定义了RDT报文格式
'''
import hashlib
import Network
import time

'''
报文类
定义了RDT协议报文格式,和创建报文和将报文打包成字节串的方法
'''
class Packet:
    # RDT报文格式为 长度 + 序列号 + checksum + msg

    # 长度字段占字节数
    length_S_length = 10
    # 序号字段占字节数
    seq_length = 10
    # checksum字段占字节数
    checksum_length = 32

    '''
    创建一个报文时,给定其序号和消息内容
    '''
    def __init__(self, seq_num, msg_S:str):
        self.seq_num = seq_num
        self.msg_S = msg_S

    '''
    从一个字节串得到其对应的报文
    '''
    @classmethod
    def from_byte_S(cls, byte_S):
        if Packet.corrupt(byte_S):
            return None
        # 取出序号字段
        seq_num = int(byte_S[Packet.length_S_length: Packet.length_S_length + Packet.seq_length])
        msg_S = byte_S[Packet.length_S_length+Packet.seq_length+Packet.checksum_length :]
        return cls(seq_num, msg_S)

    '''
    给定报文各个字段的值,封装报文为字节串,以便发送
    '''
    def get_byte_S(self):
        #convert sequence number of a byte field of seq_num_S_length bytes
        seq_num_S = str(self.seq_num).zfill(self.seq_length)
        #convert length to a byte field of length_S_length bytes
        length_S = str(self.length_S_length + len(seq_num_S) + self.checksum_length + len(self.msg_S)).zfill(self.length_S_length)

        # debug
        # print(type(seq_num_S), type(length_S), type(self.msg_S))

        #compute the checksum
        checksum = hashlib.md5((length_S+seq_num_S+self.msg_S).encode('utf-8'))
        checksum_S = checksum.hexdigest()
        #compile into a string
        return length_S + seq_num_S + checksum_S + self.msg_S
    
    '''
    给定字节串,检查校验码以确定是否损坏
    '''
    @staticmethod
    def corrupt(byte_S):
        # 提取报文各个字段
        length_S = byte_S[0:Packet.length_S_length]
        seq_num_S = byte_S[Packet.length_S_length : Packet.seq_length+Packet.seq_length]
        checksum_S = byte_S[Packet.seq_length+Packet.seq_length : Packet.seq_length+Packet.length_S_length+Packet.checksum_length]
        msg_S = byte_S[Packet.seq_length+Packet.seq_length+Packet.checksum_length :]
        
        # 计算得到报文的校验和
        checksum = hashlib.md5(str(length_S+seq_num_S+msg_S).encode('utf-8'))
        computed_checksum_S = checksum.hexdigest()
        return checksum_S != computed_checksum_S
                       

'''
Sender类
提供发送方的方法
注意RDT是一个单向协议,这里只考虑了发送方发送消息报文,
所以发送发没有rdt_receive方法
'''
class Sender:
    # 期望的序号
    expectedseqnum = 0
    byte_buffer = ''

    def __init__(self, role, server_port, client_port):
        # 为发送发创建一个网络层
        self.network = Network.NetworkLayer(role, server_port, client_port)

    def disconnect(self):
        self.network.disconnect()

    '''
    rdt_send
    采用RDT2.2,发送方需要接受ACK报文
    停等协议,需要等待报文接受,即收到ACK后,函数才返回
    '''
    def rdt_send(self, msg_S:str):
        while True:
            # 首先发送一个报文,然后等待其
            sndpkt = Packet(self.expectedseqnum, msg_S)
            self.network.udt_send(sndpkt.get_byte_S())

            # 等待接受报文
            receive_bytes = ''
            while receive_bytes == '':
                receive_bytes = self.network.udt_receive()

            rcvpkt = Packet.from_byte_S(receive_bytes)

            # 报文没损坏,且序号等于期望值,则返回,否则重发报文
            if rcvpkt != None and rcvpkt.msg_S == 'ACK' and rcvpkt.seq_num == self.expectedseqnum:
                print('received expected ACK %d' %rcvpkt.seq_num)
                self.expectedseqnum = (self.expectedseqnum+1)%2
                break
            # 序号不对或者损坏,重发报文
            else:
                print('received unexpected ACK, resending the packet')

'''
接收方类
提供接收方的方法
'''
class Receiver:
    # 期望的序号
    expectedseqnum = 0
    # 从网络层读取的字节的缓冲区
    byte_buffer = ''

    def __init__(self, role, server_port, client_port):
        # 为发送发创建一个网络层
        self.network = Network.NetworkLayer(role, server_port, client_port)

    def disconnect(self):
        self.network.disconnect()

    '''
    rdt_receive
    RDT2.2中,无论是否损坏,接收方都发送ACK,但序号不同
    '''
    def rdt_receive(self):
        ret_S = None
        byte_S = self.network.udt_receive()
        self.byte_buffer += byte_S

        # 当处理完所有报文时才会返回
        while True:
            # 收到的字节数还不够RDT报文长度,不能提取长度,直接返回
            if (len(self.byte_buffer)) < Packet.length_S_length:
                return ret_S
            # 收到的字节可以提取长度,则提取出这个报文的长度
            length = int(self.byte_buffer[:Packet.length_S_length])
            # 这个报文还不完整
            if len(self.byte_buffer) < length :
                return ret_S
            
            # 提取一个完整报文
            pRec = Packet.from_byte_S(self.byte_buffer[0:length])
            # 注意将取完报文后更新自己的缓冲区
            self.byte_buffer = self.byte_buffer[length:]

            # 收到期望的报文值,发送ACK,更新自己的期望序号
            if pRec != None and pRec.seq_num == self.expectedseqnum :
                sndpkt = Packet(self.expectedseqnum, "ACK")
                self.network.udt_send(sndpkt.get_byte_S())
                self.expectedseqnum = (self.expectedseqnum+1)%2

                #debug
                print("Received expected packet, sent ACK %d" %sndpkt.seq_num)
                ret_S = pRec.msg_S if ret_S is None else ret_S + pRec.msg_S
            # 以前已经收到过的报文
            elif pRec != None:
                sndpkt = Packet((self.expectedseqnum + 1)%2, "ACK")
                self.network.udt_send(sndpkt.get_byte_S())

                # debug
                print("Received duplicate packet %d, drop the packet and sent a ACK %d" %(pRec.seq_num,sndpkt.seq_num))

                continue
            # 报文损坏了
            else:
                sndpkt = Packet((self.expectedseqnum+1)%2, "ACK")
                self.network.udt_send(sndpkt.get_byte_S())
                # debug
                print("Received corrupt packet, drop the packet and sent a ACK %d" %sndpkt.seq_num)