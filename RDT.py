import Network
import argparse
from time import sleep
import hashlib


class Packet:
    ## the number of bytes used to store packet length
    seq_num_S_length = 10
    length_S_length = 10
    ## length of md5 checksum in hex
    checksum_length = 32 
        
    def __init__(self, seq_num, msg_S):
        self.seq_num = seq_num
        self.msg_S = msg_S
        
    @classmethod
    def from_byte_S(self, byte_S):
        if Packet.corrupt(byte_S):
            # raise RuntimeError('Cannot initialize Packet: byte_S is corrupt')
            # print("##########\nfind a corrupt packet\n##########")
            return None
        #extract the fields
        seq_num = int(byte_S[Packet.length_S_length : Packet.length_S_length+Packet.seq_num_S_length])
        msg_S = byte_S[Packet.length_S_length+Packet.seq_num_S_length+Packet.checksum_length :]
        return self(seq_num, msg_S)
        
        
    def get_byte_S(self):
        #convert sequence number of a byte field of seq_num_S_length bytes
        seq_num_S = str(self.seq_num).zfill(self.seq_num_S_length)
        #convert length to a byte field of length_S_length bytes
        length_S = str(self.length_S_length + len(seq_num_S) + self.checksum_length + len(self.msg_S)).zfill(self.length_S_length)
        #compute the checksum
        checksum = hashlib.md5((length_S+seq_num_S+self.msg_S).encode('utf-8'))
        checksum_S = checksum.hexdigest()
        #compile into a string
        byte_S = length_S + seq_num_S + checksum_S + self.msg_S
        # debug
        # print(byte_S)

        return length_S + seq_num_S + checksum_S + self.msg_S
   
    
    @staticmethod
    def corrupt(byte_S):
        #extract the fields
        length_S = byte_S[0:Packet.length_S_length]
        seq_num_S = byte_S[Packet.length_S_length : Packet.seq_num_S_length+Packet.seq_num_S_length]
        checksum_S = byte_S[Packet.seq_num_S_length+Packet.seq_num_S_length : Packet.seq_num_S_length+Packet.length_S_length+Packet.checksum_length]
        msg_S = byte_S[Packet.seq_num_S_length+Packet.seq_num_S_length+Packet.checksum_length :]
        
        #compute the checksum locally
        checksum = hashlib.md5(str(length_S+seq_num_S+msg_S).encode('utf-8'))
        computed_checksum_S = checksum.hexdigest()
        #and check if the same
        return checksum_S != computed_checksum_S
    
    # 这里不仅是ACK，而且没有错误
    def isACK(msg):
        return msg == "ACK"
    
    # 不仅是NAK，而且没有错误
    def isNAK(msg):
        return msg == "NAK"


class RDT:
    ## latest sequence number used in a packet
    seq_num = 0
    last_seq = 1
    ## buffer of bytes read from network
    byte_buffer = '' 

    def __init__(self, role_S, server_S, port):
        self.network = Network.NetworkLayer(role_S, server_S, port)
    
    def disconnect(self):
        self.network.disconnect()
        
    def rdt_1_0_send(self, msg_S):
        p = Packet(self.seq_num, msg_S)
        self.seq_num += 1
        self.network.udt_send(p.get_byte_S())
        
    def rdt_1_0_receive(self):
        ret_S = None
        byte_S = self.network.udt_receive()
        self.byte_buffer += byte_S
        #keep extracting packets - if reordered, could get more than one
        while True:
            #check if we have received enough bytes
            if(len(self.byte_buffer) < Packet.length_S_length):
                return ret_S #not enough bytes to read packet length
            #extract length of packet
            length = int(self.byte_buffer[:Packet.length_S_length])
            if len(self.byte_buffer) < length:
                return ret_S #not enough bytes to read the whole packet
            #create packet from buffer content and add to return string
            p = Packet.from_byte_S(self.byte_buffer[0:length])
            ret_S = p.msg_S if (ret_S is None) else ret_S + p.msg_S
            #remove the packet bytes from the buffer
            self.byte_buffer = self.byte_buffer[length:]
            #if this was the last packet, will return on the next iteration
            
    def rdt_2_2_send(self, msg_S):
        # 先创建一个报文并发送
        send_pkt = Packet(self.seq_num, msg_S)

        # 循环直到期望的序号改变
        while True:
            # 无条件发送报文，直到进入下一个状态跳出循环
            self.network.udt_send(send_pkt.get_byte_S())
            print("##########\nSent a packet %d, waiting for response\n" %self.seq_num)

            self.byte_buffer = ''
            receive_pkt = ''

            # 然后等待接受接收方发过来的ACK或NAK报文（可能有比特差错）
            while receive_pkt == '':
                receive_pkt = self.network.udt_receive()
            # 接受报文的长度
            pkt_length = int(receive_pkt[:Packet.length_S_length])
            self.byte_buffer = receive_pkt

            pRec = Packet.from_byte_S(self.byte_buffer[:pkt_length])

            # 检查是否出错
            if pRec == None:
                self.byte_buffer = ''
                print("##########\nReceived corrupt packet\n")
                continue
            # 没有出错
            else:
                if pRec.seq_num < self.seq_num:
                    ack_packet = Packet(pRec.seq_num, "1")
                    print("**********\nSending ACK packet for duplicate packet\n**********\n")
                    self.network.udt_send(ack_packet.get_byte_S())
                
                # notcorruot && isACK,则可以进入下一个状态
                if pRec.msg_S == '1':
                    print("##########\nreceived right ACK, move to next state\n")
                    self.seq_num += 1
                    break
                elif pRec.msg_S == '0':
                    print("##########\nreceived wrong ACK, resending the packet\n")
                    continue

    def rdt_2_2_receive(self):
        ret_S = None
        # 首先接受一个报文,将其存入buffer
        byte_S = self.network.udt_receive()
        self.byte_buffer += byte_S

        while True:
            # 如果没有接受足够长的字节，则返回None
            if(len(self.byte_buffer) < Packet.length_S_length):
                return ret_S
            
            length = int(self.byte_buffer[:Packet.length_S_length])
            if len(self.byte_buffer) < length:
                return ret_S
            
            # 获取接受报文，如果接受报文有错，则p为None
            p = Packet.from_byte_S(self.byte_buffer[0:length])

            # 接受报文损坏了，发送NAK
            if (p == None):
                print("##########\nReceived a Corrupt packet,about to respond\n")
                print("################\nSending wrong ACK\n")
                pak = Packet(self.seq_num, "0")
                self.network.udt_send(pak.get_byte_S())

            else:
                # 这是send为了处理冗余报文发送的ACK，接收方不管
                if p.msg_S == '0' or p.msg_S == '1':
                    # print('##########\nReceived a dupilicate ACK packet,ignore\n')
                    self.byte_buffer = self.byte_buffer[length:]
                    continue
                
                # 已经接受过的报文，重发ACK
                if p.seq_num < self.seq_num:
                    print("##########\nReceived a duplicate packet, sending ACK\n")
                    ack = Packet(p.seq_num, '1')
                    self.network.udt_send(ack.get_byte_S())
                # 新的报文
                elif p.seq_num == self.seq_num:
                    ack = Packet(self.seq_num, "1")
                    print("##########\nReceived the exepcted packet\n")
                    print("##########\nsending right ACK\n")
                    self.network.udt_send(ack.get_byte_S())
                    self.seq_num += 1

                ret_S = p.msg_S if (ret_S is None) else ret_S + p.msg_S

            self.byte_buffer = self.byte_buffer[length:]

    def rdt_3_0_send(self, msg_S):
        pass
        
    def rdt_3_0_receive(self):
        pass
        

if __name__ == '__main__':
    parser =  argparse.ArgumentParser(description='RDT implementation.')
    parser.add_argument('role', help='Role is either client or server.', choices=['client', 'server'])
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()
    
    rdt = RDT(args.role, args.server, args.port)
    if args.role == 'client':
        rdt.rdt_1_0_send('MSG_FROM_CLIENT')
        sleep(2)
        print(rdt.rdt_1_0_receive())
        rdt.disconnect()
        
        
    else:
        sleep(1)
        print(rdt.rdt_1_0_receive())
        rdt.rdt_1_0_send('MSG_FROM_SERVER')
        rdt.disconnect()