import socket
import struct
import cv2
import numpy as np
import queue
from enum import Enum
from threading import Thread
from PIL import Image
import pickle
import sys




class CamIndex(Enum):
    TOP = 0
    BOTTOM = 1



class ImageServer:
    def __init__(self, addr, img_w, img_h, camera):
        self.img_dim = (img_h, img_w)  # image dimensions
        self.img_bytes = img_w*img_h*2 # image size in bytes
        self.camera = camera           # camera
        self.running = True

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(addr)
        sock.listen()
        sock.settimeout(0.01)
        sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, (16+self.img_bytes)*4)
        self.sock = sock

        self.queue = queue.Queue(maxsize=3)
        self.thread = Thread(target=self.run, daemon=True)
        self.thread.start()



    def send(self, tick, image):
        self.queue.put((tick, image))



    def stop(self):
        self.running = False
        self.thread.join()



    def run(self):
        #print('start')
        conn = None
        while self.running:
            try:
                tick, img = self.queue.get(timeout=0.1)
                self.queue.task_done()
            except queue.Empty:
                continue

            if conn:
                header = struct.pack("8sHBBHH", b'wbimage\x00', tick, self.camera.value, 4, *self.img_dim)

                try:
                    conn.send(header)
                    BufSize = 65500
                    ImageMessage = img
                    while sys.getsizeof(ImageMessage) > BufSize:
                        conn.send(ImageMessage[:BufSize])
                        #print(sys.getsizeof(ImageMessage[:BufSize]))
                        ImageMessage = ImageMessage[BufSize:]
                    conn.send(ImageMessage)
                except ConnectionError:
                    conn.close()
                    conn = None
            else:
                try:
                    (conn, addr) = self.sock.accept()
                except:
                    conn = None
                    continue
