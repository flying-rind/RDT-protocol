# RDT可靠传输协议模拟实现

## Instruction
实现了RDT1.0，RDT2.0，RDT3.0和RDT-GBN，分别位于各自文件夹下

在每个实现中，
* client将一个txt文件（其中存放了马丁路德金的《I have a dream》）拆分为多份，每次发送100字节到server
  
* server接受client发送的数据包，将其整合起来并写入新的txt文件
  
* 通过比较两个txt文件是否一致来验证协议的正确性

## Code Structures
将项目整理为网络中的三个层次：应用层、传输层、网络层
```
APPLICATION LAYER (client.py, server.py)
TRANSPORT LAYER (rdt.py)
NETWORK LAYER (network.py)
```
* client和server程序在应用层调用传输层提供的rdt_send和rdt_receive接口来通信

* rdt_send和rdt_receive调用网络层的udt_send和udt_receive通信

* 通过以一定概率将udt_send发送的字节串改变来模拟网络层的不可靠链路通信。

## Program Invocation
想要运行代码，在两个独立终端中运行
```
python server.py
```
和
```
python client.py
```
需要确保server首先运行，运行server之后，尽快运行client防止超时