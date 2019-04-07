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
import _thread

module_logger = logging.getLogger('pbt9500')
logging.basicConfig(level=logging.DEBUG,
                    format='[%(name)s] %(asctime)s %(levelname)s line:%(lineno)d | %(message)s',
                    datefmt='%m-%d %H:%M')

class Scanner(object):

    def __init__(self):
        self.logger = logging.getLogger('pbt9500.Scanner')
        
        self.port = None
        self.connection = None
        self.img_path = Path().absolute()
        self.__findCOMPort__()
        self.__reset__()

    def __str__(self):
        return "PBT9500 on port {}".format(self.port)

    def __findCOMPort__(self):
        try:
            available_ports = comports()
            for port_info in available_ports:
                if port_info.vid == 1529:
                    self.port = port_info.device
                    self.logger.info("virtual COM found on port " + self.port) 
                    break
            if not self.port:
                self.logger.warning("no scanner detected on virtual COM")
                return
            self.connection = serial.Serial(timeout=3)
            self.connection.port = self.port
        except Exception as ex:
            self.logger.error(ex)
    
    def __connect__(self):
        if not self.port:
            self.logger.error('Connection failed: virtual COM port required')
            return
        try:
            self.connection.port = self.port
            self.connection.open()
            self.logger.debug('Connection established')
        except Exception as ex:
            self.logger.error(ex)
            
    def __reset__(self):
        try:
            if self.connection.isOpen():
                cmd = 'x040000000000'.encode('ascii')
                stop_bytes =  b'\r\n'
                cmd = cmd + stop_bytes
                self.connection.write(cmd)
                self.connection.read_all()
                self.connection.close()
                self.connection.open()
            else:
                self.__connect__()
        except Exception as ex:
            self.logger.error(ex)

    def __read_meta_data__(self):
        meta = b''
        while True:
            byte = self.connection.read(1)
            if byte == b'\r':
                break
            if byte != b'':
                meta += byte
        return meta

    def __read_img_data__(self, img_size):
        self.logger.info("Collecting image data")
        self.logger.debug("Waiting for the blue light to stop blinking...")
        img = b''
        while img_size:
            byte = self.connection.read(1)
            if byte == b'':
                break
            img += byte
            img_size -= 1
        return img

    def __sendImgCaptureCmd__(self):
        # cmd = 'x021000000000' # ?? TODO
        # cmd = 'x008000000000' # Automatic Image
        # cmd = 'x018000000000' # With Trigger    
        # cmd = 'x018000000000'.encode('ascii')
        cmd = 'x008000000000'.encode('ascii')
        stop_bytes = b'\r\n'
        cmd = cmd + stop_bytes
        self.connection.write(cmd)

    def __get_img_size__(self, meta_data):
        return int(meta_data[4:12].decode('ascii'), 16)

    def __save__(self, data, barcode):
        if not data:
            self.logger.warning("no data to save")
            return
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%HH_%MM_%SS')
        self.logger.info("Saving image: %s", barcode + st + ".jpeg")
        try:
            io_image = io.BytesIO(data)    
            image = Image.open(io_image)
            image.save(self.img_path.joinpath(barcode + '_' + st + '.jpeg'))
            self.logger.info('Image saved: ' + barcode + st + '.jpeg')
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
            if not self.isOpen():
                self.__connect__()
            else:
                self.logger.info("Already connected on port %s", self.connection.port)

        except Exception as ex:
            self.logger.error(ex)

    def close(self):
        if not self.connection:
            self.logger.warning("No connection found")
            return

        try:
            self.connection.close()
            self.logger.debug("Connection closed")
        except Exception as ex:
            self.logger.error(ex)

    def scan(self):
        barcode = b''
        while True:
            byte = self.connection.read(1)
            if byte == b'':
                self.logger.info("Waiting for scan")
            if byte == b'\r':
                break
            barcode += byte
        self.logger.debug("Barcode: %s", barcode.decode('ascii'))

        time.sleep(0.1)
        self.__sendImgCaptureCmd__()

        meta_data = self.__read_meta_data__()
        if not meta_data:
            self.logger.error("No meta data found")
            return

        self.logger.debug("Meta: %s", meta_data.decode('ascii'))

        img_size_int = self.__get_img_size__(meta_data)
        if not img_size_int:
            self.logger.error("Failed to find image size")
            return

        image = self.__read_img_data__(img_size_int)
        _thread.start_new_thread ( self.__save__, (image, barcode.decode('ascii')) )
    
    def isOpen(self):
        return self.connection.is_open
