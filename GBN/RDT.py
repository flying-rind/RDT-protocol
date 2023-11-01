'''
RDT.py
这个文件中实现单向的可靠传输协议
还定义了RDT报文格式
'''
import hashlib
import Network
import threading
import time

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
    nextseqnum = 1
    # 最早的未确认分组
    base = 1
    # 从网络层读取的字节的缓冲区
    byte_buffer = ''
    # 窗口大小固定为5
    N = 5
    # 用于计时
    start_time = 0
    end_time = 0
    # 是否正在计时
    timing_switch = False
    # 由于发送和接受报文时需要互斥的修改变量，这里加锁
    lock = threading.Lock()
    # 最大超时时间
    timeout = 0.1
    # 发送发缓存所有已经发送而未确认的报文,以字典形式存储,序号作为索引
    packet_buffer = {}

    # 创建一个线程用来不断接受报文
    receiver_thread = None
    # 接受线程是否继续工作
    receiving = False

    def __init__(self, role, server_port, client_port):
        # 为发送发创建一个网络层
        self.network = Network.NetworkLayer(role, server_port, client_port)
        self.receiving = True
        self.receiver_thread = threading.Thread(name = 'receiver', target=self.rdt_receive)
        self.receiver_thread.start()
                                                

    def disconnect(self):
        # 标记发送方的接受线程可以终止了
        self.receiving = False
        self.receiver_thread.join()
        self.network.disconnect()

    '''
    采用GBN协议,允许发送连续发送多个报文

    '''
    def rdt_send(self, msg_S:str):
        with self.lock:
            # 窗口未满
            if self.nextseqnum < self.base + self.N:
                p = Packet(self.nextseqnum, msg_S)
                self.network.udt_send(p.get_byte_S())

                # debug
                print("sent a new packet %d" %p.seq_num)
                
                # 开始计时
                if self.base == self.nextseqnum:
                    self.timing_switch = True
                    self.start_time = time.time()
                # 发送后将其加入发送方的报文缓存列表中
                self.nextseqnum += 1
                self.packet_buffer[p.seq_num] = p
                return True
            # 窗口满时,不允许再发送
            else:
                return False

    '''
    创建一个线程不断地接受报文
    从网络层接受的报文传送到传输层
    收到完整的报文时,做出相应的回应
    '''
    def rdt_receive(self):
        while True:
            # 注意回收线程,不能发送完立刻回收,这样最后一些报文可能错误或丢失,只有当报文缓存区里为空,
            # 也就是所有报文都已经确认了,才回收线程,否则线程继续等待,超时可能重发
            if self.receiving == False and len(self.packet_buffer) == 0:
                break
            with self.lock:
                # 更新计时器
                if self.timing_switch == True:
                    self.end_time = time.time()

                    # 若超时,重发所有未确认报文,且重新开始计时
                    if self.end_time - self.start_time > self.timeout:
                        self.timing_switch = True
                        self.start_time = time.time()
                        for packet in self.packet_buffer.values():
                            self.network.udt_send(packet.get_byte_S())
                            # debug
                            print("Timeout, resent packet %d" %(packet.seq_num))


                # 接受报文
                byte_S = self.network.udt_receive()
                self.byte_buffer += byte_S

                # 长度不够
                if (len(self.byte_buffer)) < Packet.length_S_length:
                    continue
                # 收到的字节可以提取长度,则提取出这个报文的长度
                length = int(self.byte_buffer[:Packet.length_S_length])
                # 这个报文还不完整
                if len(self.byte_buffer) < length:
                    continue

                # 提取出一个完整报文
                pRec = Packet.from_byte_S(self.byte_buffer[0:length])
                # 注意从缓冲区取出报文后将其从缓冲区去掉
                self.byte_buffer = self.byte_buffer[length:]

                # 接受的报文出错,不做任何处理
                if pRec == None:
                    continue
                
                # 接收到完整的ACK报文
                elif pRec.msg_S == 'ACK':

                    #debug
                    print("Received ACK %d" % pRec.seq_num)


                    self.base = pRec.seq_num + 1
                    # 只用缓存那些比base大的报文
                    self.packet_buffer = {key: value for key, value in self.packet_buffer.items() if key >= self.base}
                    if self.base == self.nextseqnum:
                        # 停止计时
                        self.end_time = time.time()
                        self.timing_switch = False
                            
                    else:
                        # 重新开始计时
                        self.timing_switch = True
                        self.start_time = time.time()

'''
接收方类
提供接收方的方法
'''
class Receiver:
    # 期望的序号
    expectedseqnum = 1
    # 从网络层读取的字节的缓冲区
    byte_buffer = ''
    # 上一次收到的sndpkt
    sndpkt = Packet(0, 'ACK')

    def __init__(self, role, server_port, client_port):
        # 为发送发创建一个网络层
        self.network = Network.NetworkLayer(role, server_port, client_port)

    def disconnect(self):
        self.network.disconnect()

    '''
    从网络层接受的字节放入自己的缓存区
    逐个报文处理,直到处理完所有报文
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

            # 收到了没有错误的报文且其序列号为期望值
            if pRec != None and pRec.seq_num == self.expectedseqnum :
                self.sndpkt = Packet(self.expectedseqnum, "ACK")
                self.network.udt_send(self.sndpkt.get_byte_S())

                #debug
                print("Received expected packet, sent ACK %d" %self.sndpkt.seq_num)

                self.expectedseqnum += 1
                ret_S = pRec.msg_S if ret_S is None else ret_S + pRec.msg_S
            # 以前已经收到过的报文
            elif pRec != None:
                self.network.udt_send(self.sndpkt.get_byte_S())
                # debug
                print("Received duplicate packet %d, drop the packet and sent a ACK %d" %(pRec.seq_num,self.sndpkt.seq_num))

                continue
            else:
                self.network.udt_send(self.sndpkt.get_byte_S())
                # debug
                print("Received corrupt packet, drop the packet and sent a ACK %d" %self.sndpkt.seq_num)