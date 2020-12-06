import time
import _thread
import serial
import threading
from struct import *
import binascii
import os
import logging
import inspect
import ctypes
from dwt_lib import load_img
from fountain_lib import Fountain, Glass
from fountain_lib import EW_Fountain, EW_Droplet
from spiht_dwt_lib import spiht_encode, func_DWT, code_to_file, spiht_decode, func_IDWT

def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)

LIB_PATH = os.path.dirname(__file__)
DOC_PATH = os.path.join(LIB_PATH, '../doc')
SIM_PATH = os.path.join(LIB_PATH, '../simulation')
PRO_PATH = os.path.join(SIM_PATH, 'processing')
TEST_PATH = os.path.join(DOC_PATH, 'test')

LEAN_IMG = os.path.join(DOC_PATH, 'lena.png')
ORCA_IMG = os.path.join(DOC_PATH, 'orca.jpg')
TIMG_IMG = os.path.join(DOC_PATH, 'timg.jpg')
WHALE_IMG= os.path.join(DOC_PATH, 'whale_512.bmp')
OUT_BIN = os.path.join(DOC_PATH, 'out_whale.bin')
OUT_BIN_R = os.path.join(DOC_PATH, 'out_whale_r.bin')
OUT_BIN_G = os.path.join(DOC_PATH, 'out_whale_g.bin')
OUT_BIN_B = os.path.join(DOC_PATH, 'out_whale_b.bin')
LEAN_IMG_NEW = os.path.join(DOC_PATH, 'lena512_reconstruct.bmp')
TIMG_IMG_NEW = os.path.join(DOC_PATH, 'timg_reconstruct.jpg')
WHALE_IMG_NEW = os.path.join(DOC_PATH, 'whale_reconstruct.bmp')
WHALE_IMG_128 = os.path.join(DOC_PATH, 'whale_128.bmp')

logging.basicConfig(level=logging.INFO,
        format="%(asctime)s %(filename)s:%(lineno)s %(levelname)s-%(message)s",)


def save(path, data):
    fh = open(path, 'w', encoding='utf-8')
    fh.write(data)
    fh.close()


class Sender_serial:
    def __init__(self, port, baudrate, timeout):
        self.port = serial.Serial(port, baudrate)
        if (self.port.is_open):
            print("串口{}打开成功".format(self.port.portstr))
        else:
            print("串口打开失败")

    def send_data(self):
        global send_thread_done
        while not send_thread_done:
            # send_data = input("input:")
            send_data = open('../doc/fountain.txt', 'r').read()
            send_data = send_data.encode('utf-8')
            self.port.write(send_data)
            send_thread_done = True


send_thread_done = False


class Receiver_serial:
    data_rec = ""

    def __init__(self, port, baudrate, timeout):
        self.port = serial.Serial(port, baudrate)
        if self.port.is_open:
            print("串口{}打开成功".format(self.port.portstr))
        else:
            print("串口打开失败")

    def read_data(self):
        while True:
            size = self.port.in_waiting
            if size:
                self.data_rec = self.port.read(size).decode('utf-8')
                # self.data_rec = self.port.read_all().decode('utf-8')        # 一次最多读8064
                # newsize = self.port.in_waiting                              # 读完一次self.port.in_waiting清零
                a = len(self.data_rec)
                return self.data_rec


if __name__ == '__main__':
    test_res_dir = os.path.join(TEST_PATH, time.asctime().replace(' ', '_').replace(':', '_'))
    txt_dir = os.path.join(test_res_dir, 'test.txt')
    os.mkdir(test_res_dir)

    print("starting")
    send_port = Sender_serial('COM6', baudrate=921600, timeout=1)
    recv_port = Receiver_serial('COM7', baudrate=921600, timeout=1)

    '''线程开启'''
    # _thread.start_new_thread(send_port.send_data, ())
    # send_thread_done = True
    # send_thread = threading.Thread(target=send_port.send_data)
    # send_thread.setDaemon(True)
    # send_thread.start()
    send_port.send_data()
    print(send_thread_done)


    recv_data = []
    while True:                            # flag
        data = recv_port.read_data()
        recv_data.append(data)

        data_string = ''.join(recv_data)
        print(data_string)
        save(txt_dir, data_string)





