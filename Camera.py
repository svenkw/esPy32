import socket
import re

class Camera:

    # Contructor for Camera class
    def __init__(self, address, port, location, description):
        # Basic information about the camera
        self.address = address
        self.port = port
        self.location = location
        self.description = description

        # The last completely received image from the server
        self.image_buffer = b'not an image'

        # List of connected client threads
        self.stream_clients = []

        # Status variable to see if the camera is connected
        self.active = False

    # Method to connect to the ESP32 CAM and request stream
    def request_stream(self):
        self.active = True
        
        # Connect to the streaming port
        esp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        esp.settimeout(10)
        try:
            esp.connect((self.address, self.port))
        except:
            print("Camera could not be reached")
            self.stream_clients = []
        else:
            req_stream = b'GET /stream HTTP/1.1\r\n\r\n'
            
            esp.send(req_stream)
            esp.setblocking(False)
            
            buffer = bytes()
            while self.active:
                try:
                    chunk = esp.recv(64)
                except:
                    time.sleep(0.05)
                    continue
                buffer += chunk
                
                # Check if JPEG start and end code have been found yet
                regex_start_code = re.search(b'\xff\xd8\xff', buffer)
                regex_end_code = re.search(b'\xff\xd9', buffer)

                # If start code and end code have been found, put the complete image in the buffer
                if (regex_start_code and regex_end_code):            
                    self.image_buffer = buffer[regex_start_code.start():regex_end_code.end()]

                    regex_start_code = 0
                    regex_end_code = 0
                    buffer = bytes()
        
        # Close the socket to stop the camera from streaming
        esp.close()

    # Method to disconnect from ESP32 CAM
    def disconnect(self):
        self.active = False