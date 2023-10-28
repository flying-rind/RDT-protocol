import argparse
import RDT
import time

if __name__ == '__main__':
    parser =  argparse.ArgumentParser(description='Quotation client talking to a Pig Latin server.')
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()
    
    
    msg_L = [
        'message1: computer Networking',
        'message2: superScalar RISC Processor Design',
        'message3: Coputer graphics',
        'message4: artificial itelligence'
    ]
     
    timeout = 2 #send the next message if no response
    time_of_last_data = time.time()
     
    rdt = RDT.RDT('client', args.server, args.port)
    for msg_S in msg_L:
        rdt.rdt_3_0_send(msg_S)
        print('Client Sent msg: '+msg_S+'\n')
       
        # try to receive message before timeout 
        msg_S = None
        while msg_S == None:
            msg_S = rdt.rdt_3_0_receive()
            if msg_S is None:
                if time_of_last_data + timeout < time.time():
                    break
                else:
                    continue
        time_of_last_data = time.time()
        
        #print the result
        if msg_S:
            print('Client Received msg: '+msg_S+'\n')
        
    rdt.disconnect()