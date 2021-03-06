from os import path, getcwd
from Camera import Camera
import threading
import socket
import time
import urllib.parse as ul
import json
import re

class Server:
    '''
    The main class of the esPy32 package. Objects of this class are servers that can manage images and streams from multiple ESP32 CAM modules to multiple clients.
    '''
    default_static_folder = "static"
    default_config_folder = "config"

    # Constructor for server class
    def __init__(self, config_folder = default_config_folder, static_folder = default_static_folder):
        '''
        The constructor of the Server class. It simply creates the object and initialises some variables

        params
        ------
        config_folder : string or path
            the path to the folder containing the config json files. Defaults to a folder called config in the same directory as the Server class file.

        returns
        -------
        None
        '''
        # Set static and config folder. Unspecified leads to default location
        self.static_folder = path.join(getcwd(), static_folder)
        self.config_folder = path.join(getcwd(), config_folder)

        # Dict of defined cameras
        self.cameras = {}

        # Other important operation variables
        self.running = True

    # Method to start the esPy32 server
    def run(self):
        '''
        Method to start the server. It will start an endless loop, so keep this in mind when embedding in larger projects.

        params
        ------
        None

        returns
        -------
        None
        '''
        # Load camera config file
        with open(path.join(self.config_folder, "cameras.json"), 'r') as config:
            self.camera_config = json.load(config)

        # Load server config file
        with open(path.join(self.config_folder, "server.json"), 'r') as config:
            self.server_config = json.load(config)

        # Create camera objects
        for camera in self.camera_config:
            ip = self.camera_config[camera]["ip"]
            port = self.camera_config[camera]["stream_port"]
            location = self.camera_config[camera]["location"]
            description = self.camera_config[camera]["description"]
            self.cameras[camera] = Camera(ip, port, location, description)

        # Get server info from config
        server_address = (self.server_config["ip"], self.server_config["port"])
        server_description = self.server_config["description"]

        # Initialise server socket
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(server_address)
        server.listen(5)
        server.settimeout(0.1)
        print(f"server running on ({server_address[0]}, {server_address[1]})")

        # Enter main server loop
        while self.running:
            # wait timeout time for new client, if not enter rest of main loop
            try:
                client_socket, client_address = server.accept()
            except:
                pass
            else:
                client_thread = threading.Thread(target=self.client_handler, args=[client_socket], daemon=True)
                client_thread.start()

            # Loop over all initialised cameras
            for camera in self.cameras:
                # Start camera if necessary
                if (len(self.cameras[camera].stream_clients) > 0) and (self.cameras[camera].active == False):
                    print(f"{camera} is now active")
                    camera_thread = threading.Thread(target=self.cameras[camera].request_stream, args=[], daemon=True)
                    
                # Stop camera if necessary
                elif (len(self.cameras[camera].stream_clients) == 0) and (self.cameras[camera].active == True):
                    print(f"{camera} is no longer active")
                    self.cameras[camera].disconnect()

                # Yeet all inactive/dead threads
                self.cameras[camera].stream_clients = [client for client in self.cameras[camera].stream_clients if client.is_alive()]

        time.sleep(0.05)


    # ========================================================================================
    # HANDLERS
    # ========================================================================================
    
    # Method to run when a new request comes in to dispatch the correct specialised handler
    def client_handler(self, client):
        '''
        The main handler of the server. It decides what subhandler should be started, depending on the request received.

        params
        ------
        client : socket
            the socket object of the client that sent the request

        returns
        -------
        None
        '''
        req = client.recv(1024)

        # Remove the GET part of the request
        req_get = re.search(b'GET ', req)
        req = req[req_get.end():]
        
        # Find the location of the end of the URL
        end_of_url = re.search(b' ', req)
        req = req[:end_of_url.start()]
        # Turn bytes into string for the url parser
        url = req.decode(encoding='ascii')

        # Parse the URL
        # Returns the following (ordered): scheme (0), netloc (1), path (2), params (3), query (4), fragment (5)
        url_parsed = ul.urlparse(url)

        # Shut the server down
        elif url_parsed[2] == "/shutdown/imadmin":
            shutdown_thread = threading.Thread(target=self.shutdown_handler, args=[client], daemon=True)
            shutdown_thread.start()
            
        # Send the stream from a certain camera
        # Camera is defined in the querystring, using "cam=<camera>"
        elif url_parsed[2] == "/stream":
            # Check if a camera has been specified in the url
            if url_parsed[4]:
                # Extract the name of the camera
                camera = url_parsed[4]
                var_name = re.search('cam=', camera)
                camera = camera[var_name.end():]

                # If the requested camera is initialised, start a stream thread
                if camera in self.cameras:
                    stream_thread = threading.Thread(target=self.stream_handler, args=[client, self.cameras[camera]], daemon=True)
                    stream_thread.start()
                    # Add stream thread to clients list of camera object
                    self.cameras[camera].stream_clients.append(stream_thread)
                # If the requested camera is not initialised or does not exist, send error response
                else:
                    print("Requested camera for stream does not exist")
                    request_thread = threading.Thread(target=self.bad_request_handler, args=[client], daemon=True)
                    request_thread.start()
            # If no camera has been specified, send error response
            else:
                print("no camera specified")
                request_thread = threading.Thread(target=self.bad_request_handler, args=[client], daemon=True)
                request_thread.start()
        
        # Send the last captured image of the camera specified in the querystring, using "cam=<camera>"
        elif url_parsed[2] == "/capture":
            if url_parsed[4]:
            # Extract the name of the camera
                camera = url_parsed[4]
                var_name = re.search('cam=', camera)
                camera = camera[var_name.end():]

                if camera in self.cameras:
                    capture_thread = threading.Thread(target=self.capture_handler, args=[client, self.cameras[camera]], daemon=True)
                    capture_thread.start()
                else:
                    print("Requested camera for capture does not exist")
                    request_thread = threading.Thread(target=self.bad_request_handler, args=[client], daemon=True)
                    request_thread.start()
            else:
                print("no camera specified")
                request_thread = threading.Thread(target=self.bad_request_handler, args=[client], daemon=True)
                request_thread.start()
        # If none of the above registered URLs works, the requested function has not yet been implemented or does not exist
        # Send back a 404 page
        else:
            request_thread = threading.Thread(target=self.bad_request_handler, args=[client], daemon=True)
            request_thread.start()
    
    # Method that sends the stream from a specific camera to the client
    def stream_handler(self, client, camera):
        '''
        The handler that sends the buffered images, received from the camera, the the client.

        params
        ------
        client : socket
            The socket object of the client that should receive the image stream
        camera : Camera
            The camera object (see Camera class) of the camera whose stream should be sent to the client.

        returns
        -------
        None
        '''
        res_newline = '\r\n'
        res_ok_code = 'HTTP/1.1 200 OK\r\n'
        res_content_jpeg = 'content-type: image/jpeg\r\n'
        res_content_stream = 'content-type: multipart/x-mixed-replace;boundary=NEWIMAGEFROMTHESERVER\r\n'
        res_boundary = 'NEWIMAGEFROMTHESERVER\r\n'
        
        response = res_ok_code + res_content_stream + res_newline
        response = bytes(response, encoding='ascii')
        client.send(response)
        client.setblocking(False)

        # Buffer only for this specific client
        internal_buffer = bytes()
        while True:
            if (internal_buffer != camera.image_buffer) and (camera.image_buffer != b'not an image'):
                internal_buffer = camera.image_buffer
                
                res_content_length = 'content-length: {}'.format(str(len(internal_buffer))) + '\r\n'
                response = '--' + res_boundary + res_content_jpeg + res_content_length + res_newline
                response = bytes(response, encoding='ascii')
                response += image_buffer
                
                # Break the loop if client has disconnected
                try:
                    client.send(response)
                except:
                    print("Client has disconnected")
                    break
                else:
                    time.sleep(0.1)
        client.close()

    # Method to send a single image to the client
    def capture_handler(self, client, camera):
        '''
        Handler to send the last received image to the client, instead of a video stream. 

        params
        ------
        client : socket
            The socket object of the client that should receive the image
        camera : Camera
            The camera object (see Camera class) of the camera whose image should be sent to the client

        returns
        -------
        None
        '''
        res_newline = '\r\n'
        res_ok_code = 'HTTP/1.1 200 OK\r\n'
        res_content_jpeg = 'content-type: image/jpeg\r\n'

        # If there is no image in the buffer, request a new image
        if (camera.image_buffer == b'not an image') and (camera.active == False):
            esp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            esp.settimeout(5)
            try:
                esp.connect((camera.address, camera.port))
            except:
                print("Camera could not be reached")
                self.bad_request_handler(client)
            else:
                esp.send(b'GET /capture HTTP/1.1\r\n\r\n')
                headers = esp.recv(1024)
                
                esp.setblocking(False)
                capture = bytes()
                while True:
                    try:
                        chunk = esp.recv(1024)
                        capture = capture + chunk
                        regex_end_code = re.search(b'\xff\xd9', capture)
                        if regex_end_code:
                            break
                    except:
                        time.sleep(0.01)

                regex_start_code = re.search(b'\xff\xd8\xff', capture)
                image = capture[regex_start_code.start():regex_end_code.end()]
                res_content_length = 'content-length: {}\r\n'.format(str(len(image)))

                esp.close()

                # Update the camera buffer to the new image
                camera.image_buffer = image

        # Else recycle the last image in the buffer
        elif (camera.image_buffer != b'not an image') and (len(camera.image_buffer) > 0):
            image = camera.image_buffer
            res_content_length = 'content-length: {}\r\n'.format(str(len(image)))

            response = bytes(res_ok_code + res_content_jpeg + res_content_length + res_newline, encoding='ascii') + image + b'\r\n'

            client.setblocking(False)
            client.send(response)

        client.close()

    # Method to remotely shut the server down
    def shutdown_handler(self, client):
        '''
        Method to shut the server down

        params
        ------
        client : socket
            The socket object of the client that wants to close the server

        returns
        -------
        None
        '''
        print("Server shutting down...")
        self.running = False
        client.close()
    
    # Method to send a bad request response to the client. Used when no other handler is appropriate
    def bad_request_handler(self, client):
        '''
        Method to send a 404 page to the user. The default when a request could not be handled by the server.

        params
        ------
        client : socket
            Socket object of the client that should receive the 404 page

        returns
        -------
        None
        '''
        res_newline = '\r\n'
        res_ok_code = 'HTTP/1.1 200 OK\r\n'
        res_content_html = 'content-type: text/html\r\n'

        with open(path.join(self.static_folder, "404.html")) as f:
            page_data = f.read()
        page_data = bytes(page_data, encoding='ascii')

        res_content_length = f'content-length: {str(len(page_data))}' + '\r\n'
        response = res_ok_code + res_content_html + res_content_length + res_newline
        response = bytes(response, encoding='ascii')
        response += page_data

        client.setblocking(False)
        time.sleep(0.01)
        try:
            client.send(response)
        except:
            pass
        client.close()