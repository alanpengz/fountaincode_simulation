# -*- coding: utf-8 -*
import serial
import time
# 打开串口
ser = serial.Serial("COM6", 9600)

def main():
    if ser.is_open:
        print("serial port {} open succcess".format(ser.portstr))
    else:
        print("serial port open failed")
    
    id = 0
    while True:
        time.sleep(1)
        id = id + 1
        size = ser.in_waiting
        if size:
            data = ser.read_all()
            print(id, data)
            if(id == 10):
                print('send ack')
                ser.write('ack'.encode())
                
       
        ser.flushInput()
 
    
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        if ser != None:
            ser.close()


