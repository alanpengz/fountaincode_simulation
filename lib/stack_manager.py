# _*_ coding=utf-8 _*_ 
from __future__ import print_function
import sys, os
import numpy as np
from math import ceil
import struct
import pywt
import bitarray
import matlab.engine
from PIL import Image
import time, socket, select, re
sys.path.append('.')
from dwt_lib import load_img
from send_recv import Sender, Receiver
from send_recv import EW_Sender, EW_Receiver

LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
SIM_PATH = os.path.join(LIB_PATH, '../simulation')
WHALE_IMG_128 = os.path.join(DOC_PATH, 'whale_128.bmp')


PORT_LIKE = 100
NORNAL = ord('0')
SIGNIFICANT = ord('1')

PARA_PACKET = 1
ACK_APP = 2
STOP_APP = 3
FILLING = '\0' * 5

SEND_ID = 1
RECV_ID = 5

HOST = '127.0.0.1'

'''
# 应用层数据包格式
--------------------------------------------------------------------------------------------------
| 端口 | 关键1/普通0 | 目的节点ID | 数据包类型 | 水滴数据包大小 |      数据部分      | 填充5字节 |
--------------------------------------------------------------------------------------------------
| 1字节|    1字节    |    1字节   |    1字节   |      1字节     | 至少chunk_size字节 |    5字节  |
--------------------------------------------------------------------------------------------------
例子：
参数数据包 : contant_para_packet 
-------------------------------------
| 100 | 1 | 3 | 1 | 78 | \0\0\0\0\0 |
-------------------------------------

ACK_APP : contant_ACK_app 
-------------------------------------
| 100 | 1 | 3 | 2 | \0 | \0\0\0\0\0 |
-------------------------------------

STOP_APP : stop_app 
-------------------------------------
| 100 | 1 | 1 | 3 | \0 | \0\0\0\0\0 |
-------------------------------------

水滴数据包 : drop_packet
-------------------------------------------------
| 100 | 0 | 3 | 4 | 水滴数据包数据 | \0\0\0\0\0 |
-------------------------------------------------

水滴数据包数据: fountain.droplet().toBytes()
----------------------------------------------------
| 随机数种子 | 喷泉码原始符号个数 | 喷泉码编码符号 |
----------------------------------------------------
|    4字节   |        2字节       | chunk_size字节 |
----------------------------------------------------
'''



def find_stop_app(read_byte):
    stop_app_pattern = ''.join([PORT_LIKE, SIGNIFICANT, '.', STOP_APP])
    if re.search(stop_app_pattern, read_byte):
        return True
    else:
        return False

class Stack_Sender(EW_Sender):
    def __init__(self,
            img_path = WHALE_IMG_128,
            chunk_size = 63,
            stack_port = 9080,
            seed = 233
            ):
        self.stack_port = stack_port
        Sender.__init__(self, img_path, fountain_chunk_size=chunk_size, fountain_type='ew', seed=seed)
        self.drop_interval = 19
        ACK_app = False # 是否收到ACK_app
        

    def socket_builder(self):
        stack_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stack_socket.connect((HOST, self.stack_port))
        print("connect to {} ...".format(self.stack_port))
        return stack_socket

    def sender_main(self):
        '''
        100 : 类似端口
        1：关键数据包,见demo.cc:64
        2 ：目标节点ID
        1 ：包类型是参数数据包para_packet,发送和接收自己约定
        78: chunk_size
        '''
        contant_para_packet = [
                PORT_LIKE,
                SIGNIFICANT,
                RECV_ID, 
                PARA_PACKET, 
                self.fountain.chunk_size]
        para_packet = ''.join([struct.pack("B", ii) for ii in contant_para_packet]) + FILLING
        self.write_fd.send(para_packet)
        print("para_packet len: {}, {}".format(len(para_packet), [ord(ii) for ii in para_packet]))
        while True:
            read_byte = self.write_fd.recv(self.fountain_chunk_size + 3)
            if not read_byte:
                pass
            elif ord(read_byte[0]) == PORT_LIKE \
                    and ord(read_byte[1]) == SIGNIFICANT \
                    and ord(read_byte[3]) == ACK_APP:
                print("recv ACK_app len : {}, {}".format(len(read_byte), [ord(ii) for ii in read_byte]))
                break
        self.send_drops_use_socket()    


    def catch_stop_app(self):
        self.write_fd.setblocking(0)
        ready = select.select([self.write_fd], [], [], self.drop_interval)
        if ready[0]:
            # 非阻塞读数据
            read_byte = self.write_fd.recv(999)
            print("recv len {} : {}".format(len(read_byte), [ord(ii) for ii in read_byte]))
            if not read_byte:
                return False
            byte_to_deal = len(read_byte)
            # 处理读取的数据
            while byte_to_deal > 0:
                # 处理非本程序的数据
                if ord(read_byte[0]) != 100:
                    byte_to_deal -= 46
                    read_byte = read_byte[46:]
                # 处理本程序的数据    
                else:
                    # 收到了stop_app
                    if ord(read_byte[0]) == PORT_LIKE and \
                        ord(read_byte[1]) == SIGNIFICANT and ord(read_byte[3]) == STOP_APP:
                            print('recv STOP_APP and stop')
                            return True
                    else:
                        byte_to_deal -= 4
                        read_byte = read_byte[4:]
            return False

    def send_drops_use_socket(self):
        recv_stop_app = False
        while not recv_stop_app:
            time.sleep(self.drop_interval)
            recv_stop_app = self.catch_stop_app()

            print('drop id : ', self.drop_id)
            a_drop = self.a_drop()
            header = [PORT_LIKE, NORNAL, RECV_ID]
            # print("Header Size : {}".format(len(''.join([struct.pack("B", ii) for ii in header]))))
            send_buff = ''.join([struct.pack("B", ii) for ii in header]) + a_drop + FILLING
            # print("Send Raw len {} : {}".format(len(send_buff), [ord(ii) for ii in send_buff]))
            self.write_fd.send(send_buff)


class Stack_Receiver(EW_Receiver):
    def __init__(self, stack_port = 9079 + RECV_ID):
        print('stack_port : {}'.format(stack_port))
        self.stack_port = stack_port
        EW_Receiver.__init__(self)
        self.chunk_size = 0

    def socket_builder(self):
        socket_recv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_recv.connect((HOST, self.stack_port))
        print("connect to port {}".format(self.stack_port))
        return socket_recv

    def begin_to_catch(self):
        '''
        100 : 类似端口
        1：关键数据包,见demo.cc:64
        1 ：目标节点ID
        2 ：包类型是参数数据包ACK_APP,发送和接收自己约定
        '''
         # 等待参数数据包
        while True:
            read_byte = self.socket_recv.recv(100)
            if not read_byte:
                pass
            elif ord(read_byte[0]) == PORT_LIKE \
                    and ord(read_byte[1]) == SIGNIFICANT \
                    and ord(read_byte[3]) == PARA_PACKET:
                # 收到参数数据包
                print("recv PARA_PACKET len : {}, {}".format(len(read_byte), [ord(ii) for ii in read_byte]))
                self.chunk_size = ord(read_byte[4])
                
                # 发送 ACK_APP[100, ord('1'), 1, 2]
                contant_ACK_app = [PORT_LIKE, SIGNIFICANT, SEND_ID, ACK_APP]
                ACK_app = ''.join([struct.pack("B", ii) for ii in contant_ACK_app]) + FILLING
                self.socket_recv.send(ACK_app)
                break;
        # 接收水滴数据包    
        while True:
            a_drop = self.catch_a_drop_use_socket()
            data_offset = 6 # fountain_lib.py:238
            if not a_drop == None:
                self.drop_id += 1
                print("drops id : ", self.drop_id)
                self.drop_byte_size = len(a_drop)
                if len(a_drop) >= self.chunk_size + data_offset:
                    a_drop = a_drop[:self.chunk_size+data_offset]
                    self.add_a_drop(a_drop)
                    if self.glass.isDone():
                        print('recv done drop num {}'.format(self.drop_id))
                        break
                else:
                    print('recv broken drop, discard it ----------------')
        stop_app = [PORT_LIKE, SIGNIFICANT, SEND_ID, STOP_APP]
        buff_stop_app = ''.join([struct.pack("B", ii) for ii in stop_app]) + FILLING
        print('send STOP APP len {} : {}'.format(len(buff_stop_app), [ord(ii) for ii in buff_stop_app]))
        self.socket_recv.send(buff_stop_app)
        self.socket_recv.close()


    def catch_a_drop_use_socket(self):
        read_byte = self.socket_recv.recv(self.drop_byte_size + 3)
        if not read_byte:
            return None;
        elif not ord(read_byte[0]) == 100:
            print("not a drop !!! size: {}".format(len(read_byte)))
            return None;
        # print("Read Raw Byte {}".format([ord(ii) for ii in read_byte]))
        print("Read len: {}".format(len(read_byte)))
        drop_byte = read_byte[3:]
        print("Drop Byte len {} : {}".format(len(drop_byte), [ord(ii) for ii in drop_byte]))
        return drop_byte



if __name__ == '__main__':
    if sys.argv[1] == 'send':
        stack_manager = Stack_Sender()
        stack_manager.sender_main()
    elif sys.argv[1] ==  'recv':
        stack_manager = Stack_Receiver()




