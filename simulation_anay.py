# _*_ coding=utf-8 _*_ 
from __future__ import print_function
import sys, os
sys.path.append('./lib')
from spiht_dwt_lib import PSNR

BASE_DIR = os.path.dirname(__file__)
DOC_PATH = os.path.join(BASE_DIR, 'doc')
SIM_PATH = os.path.join(BASE_DIR, 'simulation')
WHALE_IMG= os.path.join(DOC_PATH, 'whale_512.bmp')
LENA_IMG = os.path.join(DOC_PATH, 'lena.png')


def anay_dir(dir_name, origin_image):
    print(dir_name)
    file_list = os.listdir(dir_name)
    for f in file_list:
        print("{:s}\t{:f}".format(f, PSNR(os.path.join(dir_name, f), origin_image)))

if __name__ == "__main__":
    dir_name = os.path.join(SIM_PATH, "Fri_Mar_15_20_22_29_2019")
    anay_dir(dir_name, WHALE_IMG)
    #  aa = os.path.join(dir_name, "501.bmp")
    #  PSNR(, WHALE_IMG)


