# _*_ coding=utf-8 _*_

from __future__ import print_function
from math import ceil, log
import sys, os
import random
import json
import bitarray
from time import sleep
import logging
import time, serial

from fountain_lib import Fountain, Glass
from fountain_lib import EW_Fountain, EW_Droplet

LIB_PATH = os.path.dirname(__file__)
# DOC_PATH = os.path.join(LIB_PATH, '../doc')
# SIM_PATH = os.path.join(LIB_PATH, '../simulation')
# SEND_PATH = os.path.join(DOC_PATH, 'sendbytes.txt')
# RECV_PATH = os.path.join(DOC_PATH, 'recvbytes.txt')

logging.basicConfig(level=logging.INFO, 
        format="%(asctime)s %(filename)s:%(lineno)s %(levelname)s-%(message)s",)

def bitarray2str(bit):
    return bit.tobytes().decode('utf-8')

# 接收校验
def recv_check(recv_data):
    data_array = bytearray(recv_data)
    sum = int(0)
    zero = bytes(0)
    odd_flag = False

    if not len(data_array) % 2 == 0:
        odd_flag = True
        data_array.insert(len(data_array), 0)

    for i in range(0, len(data_array), 2):
        val = int.from_bytes(data_array[i:i + 2], 'big')
        sum = sum + val
        sum = sum & 0xffffffff

    sum = (sum >> 16) + (sum & 0xffff)
    while sum > 65535:
        sum = (sum >> 16) + (sum & 0xffff)
    print('checksum:', sum)

    if sum == 65535:
        if odd_flag:
            data_array.pop()
            data_array.pop(0)
            data_array.pop(0)
        else:
            data_array.pop(0)
            data_array.pop(0)
        return bytes(data_array)
    else:
        print('Receive check wrong!')

class Receiver:
    def __init__(self, port,
                 baudrate,
                 timeout,
                 ):

        self.port = serial.Serial(port, baudrate)
        self.drop_id = 0
        self.glass = Glass(0)
        self.chunk_size = 0
        self.current_recv_bits_len = 0
        self.recv_done_flag = False
        self.data_rec = ''


    '''LT喷泉码接收解码部分'''
    def begin_to_catch(self):
        a_drop_bytes = self.catch_a_drop_use_serial()          # bytes

        if a_drop_bytes is not None:
            check_data = recv_check(a_drop_bytes)

            if not check_data == None:
                self.drop_id += 1
                print("recv drops id : ", self.drop_id)
                self.drop_byte_size = len(check_data)
                self.add_a_drop(check_data)                                           # bytes --- drop --- bits

    # data_rec =''

    def catch_a_drop_use_serial(self):
        time.sleep(1)
        size1 = self.port.in_waiting
        if size1:
            self.data_rec = self.port.read_all()
            frame_len = len(self.data_rec)
            if self.data_rec[0:2] == b'ok' and self.data_rec[frame_len - 4:frame_len] == b'fine':
                data_array = bytearray(self.data_rec)
                data_array.pop(0)
                data_array.pop(0)
                data_array.pop()
                data_array.pop()
                data_array.pop()
                data_array.pop()
                a = len(bytes(data_array))
                print('drop len(crc) :', a)
                self.data_rec = ''

                return bytes(data_array)
            else:
                print(self.data_rec[0:2], b'ok')
                print(self.data_rec[frame_len - 4:frame_len], b'fine')
                print('Wrong receive frame !')
                self.data_rec = ''
        else:
            self.port.flushInput()

    def add_a_drop(self, d_byte):
        drop = self.glass.droplet_from_Bytes(d_byte)           # drop
        print('drop data len: ', len(drop.data))

        if self.glass.num_chunks == 0:
            print('init num_chunks : ', drop.num_chunks)
            self.glass = Glass(drop.num_chunks)                 # 初始化接收glass
            self.chunk_size = len(drop.data)

        self.glass.addDroplet(drop)                             # glass add drops

        logging.info('current chunks')
        logging.info([ii if ii == None else '++++' for ii in self.glass.chunks])
        logging.info('=============================')

        if self.glass.isDone():
            self.recv_done_flag = True
            logging.info('============Recv done===========')
            logging.info(self.glass.getString())   
            self.send_recv_done_ack()         

    def send_recv_done_ack(self):
        if self.recv_done_flag:
            ack = b'done'
            self.port.write(ack)
            self.port.flushOutput()
            print('send recv_done_ack done')


   
def main_test_ew_fountain():
    m = open(os.path.join(DOC_PATH, 'fountain.txt'), 'r').read()
    fountain = EW_Fountain(m, chunk_size=10)
    glass = Glass(fountain.num_chunks)
    ew_drop = None
    i = 0
    drop_size = 0
    while not glass.isDone():
        i += 1
        a_drop = fountain.droplet()
        ew_drop = EW_Droplet(a_drop.data, a_drop.seed, a_drop.num_chunks)
        drop_size = len(ew_drop.data)
        glass.addDroplet(ew_drop)
        #  sleep(1)
        logging.info('+++++++++++++++++++++++++++++')
        logging.info(glass.getString())
    logging.info("data size : {}".format(len(m)))
    logging.info("send drop num : {} drop size : {}".format(i, drop_size))        
    logging.info("send data size : {}".format(i * drop_size))
    logging.info("scale : {}".format((i* drop_size) / float(len(m))))
    logging.info('done')


if __name__ == '__main__':
    receiver = Receiver('COM6', baudrate=9600, timeout=1)
    time.sleep(3)
    while True:
        receiver.begin_to_catch()
        if receiver.glass.isDone():
            print('receive done!')
            break

    








