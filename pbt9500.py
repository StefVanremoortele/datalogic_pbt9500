from serial.tools.list_ports import comports
from pathlib import Path 
import re
import serial
import logging
import time
import datetime
from PIL import Image
import io
import os

module_logger = logging.getLogger('pbt9500')
logging.basicConfig(level=logging.DEBUG,
                    format='[%(name)-12s] %(asctime)s %(levelname)-8s line:%(lineno)d | %(message)s',
                    datefmt='%m-%d %H:%M',
                    filemode='w')


class Scanner(object):

    def __init__(self):
        self.logger = logging.getLogger('pbt9500.Scanner')
        self.logger.info(logging.ERROR)
        
        self.port = None
        self.connection = None
        self.img_data = None
        self.img_path = Path().absolute()
        self.__logger_test__()
        self.__findCOMPort__()
        self.__reset__()

    def __logger_test__(self):
        self.logger.info("info")
        self.logger.warning("warn")
        self.logger.error("err")

    def __str__(self):
        return "TODO"


    def __findCOMPort__(self):
        try:
            available_ports = comports()
            for port_info in available_ports:
                if port_info.vid == 1529:
                    self.port = port_info.device
                    self.logger.info("scanner connected to port " + self.port) 
                    break

            if not self.port:
                self.logger.warning("no scanner detected on virtual COM")
                return None
            
            self.connection = serial.Serial(timeout=3)
            self.connection.port = self.port
        except Exception as ex:
            self.logger.error(ex)
    
    def __connect__(self):
        if not self.port:
            self.logger.error('connection failed: virtual COM port required')
            return

        try:
            # self.connection = serial(timeout=3)
            self.connection.port = self.port
            self.logger.debug('connection successful')
        except Exception as ex:
            self.logger.error(ex)
            
    def __reset__(self):
        # TODO: dir(connection) to find correct method for this
        try:
            self.connection.read_all()
            self.img_data = None
            # time.sleep(2)
            cmd = 'x040000000000'.encode('ascii')
            stop_bytes =  b'\r\n'
            cmd = cmd + stop_bytes
            self.connection.write(cmd)
            time.sleep(1)
        except Exception as ex:
            self.logger.error(ex)

    def __read_meta_data__(self):
        try:
            meta_data = self.connection.read(8)
            meta_data += self.connection.read(8)
            return meta_data
        except Exception as ex:
            self.logger.error(ex)

    def __save_image__(self):
        if not self.img_data:
            self.logger.warning("no image data in buffer")
            return

        try:
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%Hh%Mm%Ss')
            io_image = io.BytesIO(self.img_data)
            image = Image.open(io_image)
            image.save(self.img_path.joinpath(st + '.jpeg'))
            self.logger.info('Image saved: ' + st + '.jpeg')
        except Exception as ex:
            self.logger.error(ex)

    def set_image_path(self, path):
        try:
            self.img_path = path
            self.logger.debug("storage location folder set to '{}'".format(path))
        except Exception as ex:
            self.logger.error(ex)

    def open(self):
        try:
            self.__connect__()
            self.connection.open()
        except Exception as ex:
            self.logger.error(ex)

    def close(self):
        if not self.connection:
            self.logger.warning("no connection found")

        try:
            self.__reset__()
            self.connection.close()
            self.logger.debug("connection closed")
        except Exception as ex:
            self.logger.error(ex)

    def scan(self):
        # cmd = 'x021000000000' # ?? TODO
        # cmd = 'x008000000000' # Automatic Image
        # cmd = 'x018300000000' # With Trigger    
        cmd = 'x018000000000' .encode('ascii')
        stop_bytes = b'\r\n'
        cmd = cmd + stop_bytes
        # cmd = bytearray.fromhex(cmd) # TODO: monitor serial port
        self.connection.write(cmd)

    def capture_image(self):
        meta_data = self.__read_meta_data__()

        if not meta_data:
            self.logger.warning("no meta_data found")
            return # TODO: catch exception

        img_size = int(meta_data[4:12].decode('ascii'), 16)
        self.logger.debug(img_size)

        self.connection.read(1) #LF

        img_data = b''
        while img_size:
            byte = self.connection.read(1)
            img_data += byte
            img_size -= 1
            self.logger.debug(byte)

        self.img_data = img_data
        time.sleep(1)
        
        self.__save_image__()
        self.__reset__()