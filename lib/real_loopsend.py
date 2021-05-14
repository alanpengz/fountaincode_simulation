# _*_ coding=utf-8 _*_

from __future__ import print_function
from math import ceil, log
import sys, os
import random
import json
import bitarray
from time import sleep
import logging
import time
import threading
import datetime
import pandas as pd
import numpy as np

LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
IMG_PATH = os.path.join(LIB_PATH, './imgSend/lena.bmp')
SIM_PATH = os.path.join(LIB_PATH, '../simulation')


logging.basicConfig(level=logging.INFO, 
        format="%(asctime)s %(filename)s:%(lineno)s %(levelname)s-%(message)s",)


class Droplet:
    def __init__(self,
                 id,
                 data,          
                 ):
        self.id = id
        self.data = data


class Sender:
    def __init__(self,
                 data = IMG_PATH,
                 chunk_size=215,          
                 ):
        self.data = data
        self.chunk_size = chunk_size
        self.dropid = 0
        self.chunk_nums = ceil(len(self.data)/self.chunk_size)
        self.process = range(0,self.chunk_nums)
        self.send_flag_list = [0]*self.chunk_nums
        self.feedback_flag = False

    def droplet(self, num):
        self.dropid += 1
        start = self.chunk_size * num
        end = min(self.chunk_size * (num+1), len(self.data))
        # print('send' + str(num))
        return Droplet(num, self.data[start:end])

    def update_send_flag_list(self):
        idx = 0
        while idx < self.chunk_nums:
            if idx not in self.process:
                self.send_flag_list[idx] = 1
            idx += 1
            

class Receiver:
    def __init__(self, num_chunks):
        self.num_chunks = num_chunks
        self.entries = [None]*num_chunks
        self.dropid = 0
        self.packid = 0
        self.process = []
        self.process_dropid = 0

    def add_a_drop(self, drop):
        self.dropid += 1 
        self.packid += 1
        self.entries[drop.id] = drop.data
        # print('recv' + str(drop.id))

    def getProcess(self):
        process = []
        idx = 0
        while idx < self.num_chunks:
            if self.entries[idx]==None:
                process.append(idx)
            idx += 1
        return process

    def isDone(self):
        return None not in self.entries

    def getString(self):
        return ''.join(x or ' _ ' for x in self.entries)


'''不同码长K与译码开销的关系'''
suffix_list = ['50.txt', '100.txt', '150.txt', '200.txt', '250.txt', '300.txt', '350.txt', '400.txt', '450.txt', '500.txt', '550.txt', '600.txt', '650.txt', '700.txt','750.txt','800.txt','850.txt','900.txt','950.txt','1000.txt']
def test_loopsend_K():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    avg_send_drops_list = [0]*len(suffix_list)
    avg_recv_drops_list = [0]*len(suffix_list)
    avg_idx = 0

    for f in file_list:
        m = open(f, 'r').read()
        # 测试1000次
        num_chunks_list = [0]*1000
        times_list = [0]*1000
        send_num_used_list = [0]*1000
        recv_num_used_list = [0]*1000

        times = 0
        K = 0
        while times < 1000:
            sender = Sender(m, 1)
            K = sender.chunk_nums
            receiver = Receiver(K)

            while not receiver.isDone():
                # 产生这轮的随机丢包列表
                PER = [ii for ii in random.sample(range(sender.chunk_nums), round(0.04*sender.chunk_nums))]
                chunk_id = 0
                while chunk_id < sender.chunk_nums:
                    a_drop = sender.droplet(chunk_id)    # send

                    if not a_drop.id in PER:             # 丢包
                        receiver.add_a_drop(a_drop)      # recv
                    chunk_id += 1

                    if receiver.isDone():
                        break

            # logging.info('+++++++++++++++++++++++++++++')
            # logging.info(receiver.getString())

            num_chunks_list[times] = K
            times_list[times] = times
            send_num_used_list[times] = sender.dropid
            recv_num_used_list[times] = receiver.dropid

            logging.info("K=" + str(K) +" times: " + str(times) + 'done, receive_drop_used: ' + str(receiver.dropid) + ' ,send: '+str(sender.dropid))
            times += 1

        res = pd.DataFrame({'num_chunks':num_chunks_list, 
            'times':times_list, 
            'send_drop_used':send_num_used_list,
            'recv_drop_used':recv_num_used_list})
        res.to_csv(os.path.join(SIM_PATH, '直传循环发/PER=0.04/loopsend_K' + '_'+ str(K) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        avg_send_drops_list[avg_idx] = float(sum(send_num_used_list) / len(send_num_used_list))
        avg_recv_drops_list[avg_idx] = float(sum(recv_num_used_list) / len(recv_num_used_list))
        avg_idx += 1
    
    avg_res = pd.DataFrame({'K': [ii.split('.')[0] for ii in suffix_list], 
            'avg_send_drops':avg_send_drops_list,
            'avg_recv_drops':avg_recv_drops_list})
    avg_res.to_csv(os.path.join(SIM_PATH, '直传循环发/PER=0.04/loopsend_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

# 接收端收到K个有效包之后进行反馈，之后更新K为反馈长度，反馈延迟1.8s；发送端收到反馈之后跳出当前循环进入发送新进度的循环，没收到则继续当前循环
def test_feedback_loopsend_K():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    avg_send_drops_list = [0]*len(suffix_list)
    avg_recv_drops_list = [0]*len(suffix_list)
    avg_idx = 0

    for f in file_list:
        m = open(f, 'r').read()
        # 测试1000次
        num_chunks_list = [0]*1000
        times_list = [0]*1000
        send_num_used_list = [0]*1000
        recv_num_used_list = [0]*1000

        times = 0
        K = 0
        while times < 1000:
            sender = Sender(m, 1)
            K = sender.chunk_nums
            receiver = Receiver(K)
            tmp_process_len = K
            rx_get_process_flag = False

            while not receiver.isDone():
                chunk_id = 0
                receiver.dropid = 0
                while True: # 发送端没收到新反馈就一直发上一个进度
                    if sender.send_flag_list[chunk_id]==0:
                        a_drop = sender.droplet(chunk_id)    # send

                        pack_loss = [True, False]
                        prob_loss = [0.04, 0.96]
                        pack_loss_flag = np.random.choice(pack_loss, 1, False, prob_loss)[0]
                        if pack_loss_flag==False:             # 丢包
                            receiver.add_a_drop(a_drop)      # recv
                    chunk_id += 1
                    if chunk_id >= K:
                        chunk_id = 0

                    if receiver.isDone():
                        break

                    if receiver.dropid >= tmp_process_len:
                        if rx_get_process_flag==False:
                            receiver.process = receiver.getProcess()
                            receiver.process_dropid = tmp_process_len
                            rx_get_process_flag = True
                            # print(receiver.process)
                        if receiver.dropid - receiver.process_dropid == 18:
                            sender.process = receiver.process
                            sender.update_send_flag_list()
                            tmp_process_len = len(receiver.process)
                            rx_get_process_flag = False
                            # print(tmp_process_len)
                            break

            # logging.info('+++++++++++++++++++++++++++++')
            # logging.info(receiver.getString())

            num_chunks_list[times] = K
            times_list[times] = times
            send_num_used_list[times] = sender.dropid
            recv_num_used_list[times] = receiver.packid

            logging.info("K=" + str(K) +" times: " + str(times) + 'done, receive_drop_used: ' + str(receiver.packid) + ' ,send: '+str(sender.dropid))
            times += 1

        res = pd.DataFrame({'num_chunks':num_chunks_list, 
            'times':times_list, 
            'send_drop_used':send_num_used_list,
            'recv_drop_used':recv_num_used_list})
        res.to_csv(os.path.join(SIM_PATH, '直传循环发/有反馈/PER=0.04/loopsend_K' + '_'+ str(K) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        avg_send_drops_list[avg_idx] = float(sum(send_num_used_list) / len(send_num_used_list))
        avg_recv_drops_list[avg_idx] = float(sum(recv_num_used_list) / len(recv_num_used_list))
        avg_idx += 1
    
    avg_res = pd.DataFrame({'K': [ii.split('.')[0] for ii in suffix_list], 
            'avg_send_drops':avg_send_drops_list,
            'avg_recv_drops':avg_recv_drops_list})
    avg_res.to_csv(os.path.join(SIM_PATH, '直传循环发/有反馈/PER=0.04/loopsend_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')




'''不同per与译码开销的关系'''
# suffix_list = ['115.txt']
per_list = [0,0.01,0.02,0.03,0.04,0.05,0.06,0.07,0.08,0.09,0.1,0.125,0.15,0.175,0.2,0.225,0.25,0.275,0.3,0.325,0.35,0.375,0.4,0.425,0.45,0.475,0.5]
def test_loopsend_per():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    avg_send_drops_list = [0]*len(per_list)
    avg_recv_drops_list = [0]*len(per_list)
    avg_idx = 0

    for per in per_list:
        m = open(file_list[0], 'r').read()
        # 测试1000次
        tmp_per_list = [0]*1000
        times_list = [0]*1000
        send_num_used_list = [0]*1000
        recv_num_used_list = [0]*1000

        times = 0
        K = 0
        while times < 1000:
            sender = Sender(m, 1)
            K = sender.chunk_nums
            receiver = Receiver(K)

            while not receiver.isDone():
                # 产生这轮的随机丢包列表
                # PER = [ii for ii in random.sample(range(sender.chunk_nums), round(per*sender.chunk_nums))]
                chunk_id = 0
                while chunk_id < sender.chunk_nums:
                    a_drop = sender.droplet(chunk_id)    # send

                    pack_loss = [True, False]
                    prob_loss = [per, 1-per]
                    pack_loss_flag = np.random.choice(pack_loss, 1, False, prob_loss)[0]
                    if pack_loss_flag==False:             # 丢包
                        receiver.add_a_drop(a_drop)      # recv
                    # if not a_drop.id in PER:             # 丢包
                    #     receiver.add_a_drop(a_drop)      # recv
                    chunk_id += 1

                    if chunk_id >= sender.chunk_nums:
                        chunk_id = 0

                    if receiver.isDone():
                        break

            # logging.info('+++++++++++++++++++++++++++++')
            # logging.info(receiver.getString())

            tmp_per_list[times] = per
            times_list[times] = times
            send_num_used_list[times] = sender.dropid
            recv_num_used_list[times] = receiver.dropid

            logging.info("per=" + str(per) + " times: " + str(times) + 'done, receive_drop_used: ' + str(receiver.dropid) + ' ,send: '+str(sender.dropid))
            times += 1

        res = pd.DataFrame({'num_chunks':tmp_per_list, 
            'times':times_list, 
            'send_drop_used':send_num_used_list,
            'recv_drop_used':recv_num_used_list})
        res.to_csv(os.path.join(SIM_PATH, '直传循环发/K=115(不同PER)/loopsend_K=115' + '_'+ 'PER=' + str(per) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        avg_send_drops_list[avg_idx] = float(sum(send_num_used_list) / len(send_num_used_list))
        avg_recv_drops_list[avg_idx] = float(sum(recv_num_used_list) / len(recv_num_used_list))
        avg_idx += 1
    
    avg_res = pd.DataFrame({'per': per_list, 
            'avg_send_drops':avg_send_drops_list,
            'avg_recv_drops':avg_recv_drops_list})
    avg_res.to_csv(os.path.join(SIM_PATH, '直传循环发/K=115(不同PER)/loopsend_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

def test_feedback_loopsend_per():
    file_list = [DOC_PATH + '/text' + ii for ii in suffix_list]
    avg_send_drops_list = [0]*len(per_list)
    avg_recv_drops_list = [0]*len(per_list)
    avg_idx = 0

    for per in per_list:
        m = open(file_list[0], 'r').read()
        # 测试1000次
        tmp_per_list = [0]*1000
        times_list = [0]*1000
        send_num_used_list = [0]*1000
        recv_num_used_list = [0]*1000

        times = 0
        K = 0
        while times < 1000:
            sender = Sender(m, 1)
            K = sender.chunk_nums
            receiver = Receiver(K)
            tmp_process_len = K
            rx_get_process_flag = False

            while not receiver.isDone():
                # 产生这轮的随机丢包列表
                # PER = [ii for ii in random.sample(sender.process, round(0.04*len(sender.process)))]
                chunk_id = 0
                receiver.dropid = 0
                while True: # 发送端没收到新反馈就一直发上一个进度
                    if sender.send_flag_list[chunk_id]==0:
                        a_drop = sender.droplet(chunk_id)    # send

                        pack_loss = [True, False]
                        prob_loss = [per, 1-per]
                        pack_loss_flag = np.random.choice(pack_loss, 1, False, prob_loss)[0]
                        if pack_loss_flag==False:             # 丢包
                            receiver.add_a_drop(a_drop)      # recv
                    chunk_id += 1
                    if chunk_id >= K:
                        chunk_id = 0

                    if receiver.isDone():
                        break

                    if receiver.dropid >= tmp_process_len:
                        if rx_get_process_flag==False:
                            receiver.process = receiver.getProcess()
                            receiver.process_dropid = tmp_process_len
                            rx_get_process_flag = True
                            # print(receiver.process)
                        if receiver.dropid - receiver.process_dropid == 18:
                            sender.process = receiver.process
                            sender.update_send_flag_list()
                            tmp_process_len = len(receiver.process)
                            rx_get_process_flag = False
                            # print(tmp_process_len)
                            break

            # logging.info('+++++++++++++++++++++++++++++')
            # logging.info(receiver.getString())

            tmp_per_list[times] = per
            times_list[times] = times
            send_num_used_list[times] = sender.dropid
            recv_num_used_list[times] = receiver.packid

            logging.info("per=" + str(per) + " times: " + str(times) + 'done, receive_drop_used: ' + str(receiver.packid) + ' ,send: '+str(sender.dropid))
            times += 1

        res = pd.DataFrame({'num_chunks':tmp_per_list, 
            'times':times_list, 
            'send_drop_used':send_num_used_list,
            'recv_drop_used':recv_num_used_list})
        res.to_csv(os.path.join(SIM_PATH, '直传循环发/有反馈/K=115(不同PER)/loopsend_K=115' + '_'+ 'PER=' + str(per) + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')

        avg_send_drops_list[avg_idx] = float(sum(send_num_used_list) / len(send_num_used_list))
        avg_recv_drops_list[avg_idx] = float(sum(recv_num_used_list) / len(recv_num_used_list))
        avg_idx += 1
    
    avg_res = pd.DataFrame({'per': per_list, 
            'avg_send_drops':avg_send_drops_list,
            'avg_recv_drops':avg_recv_drops_list})
    avg_res.to_csv(os.path.join(SIM_PATH, '直传循环发/有反馈/K=115(不同PER)/loopsend_avgs' + '_' + time.asctime().replace(' ', '_').replace(':', '_') + '.csv'),  mode='a')


if __name__ == '__main__':
    # test_loopsend_K()
    # test_loopsend_per()
    test_feedback_loopsend_K()
    # test_feedback_loopsend_per()
    pass
