from os import path, getcwd
from Camera import Camera
import threading
import socket
import time
import urllib.parse as ul
import json
import re

class Server:

    default_static_folder = "static"
    default_config_folder = "config"

    # Constructor for server class
    def __init__(self, config_folder = default_config_folder, static_folder = default_static_folder):
        # Set static and config folder. Unspecified leads to default location
        self.static_folder = path.join(getcwd(), static_folder)
        self.config_folder = path.join(getcwd(), config_folder)

        # Dict of defined cameras
        self.cameras = {}

        # Other important operation variables
        self.running = True

    # Method to start the esPy32 server
    def run(self):
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
                    self.cameras[camera].request_stream()
                    
                # Stop camera if necessary
                elif (len(self.cameras[camera].stream_clients) == 0) and (self.cameras[camera].active == True):
                    self.cameras[camera].disconnect()

                # Yeet all inactive/dead threads
                self.cameras[camera].stream_clients = [client for client in self.cameras[camera].stream_clients if client.is_alive()]

        time.sleep(0.05)


    # ========================================================================================
    # HANDLERS
    # ========================================================================================
    
    # Method to run when a new request comes in to dispatch the correct specialised handler
    def client_handler(self, client):
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

        # Send the status page
        if url_parsed[2] == "/status":
            status_thread = threading.Thread(target=self.status_handler, args=[client], daemon=True)
            status_thread.start()

        # Shut the server down
        elif url_parsed[2] == "/shutdown/imadmin":
            shutdown_thread = threading.Thread(target=self.shutdown_handler, args=[client], daemon=True)
            shutdown_thread.start()
            
        # Send the stream from a certain camera
        # Camera is defined in the querystring, using "cam=<camera>"
        elif url_parsed[2] == "/stream":
            # Check if a camera has been specified in the url
            if url_parsed[4]:
                print("camera requested")
                # Extract the name of the camera
                camera = url_parsed[4]
                var_name = re.search('cam=', camera)
                camera = camera[var_name.end():]

                # If the requested camera is initialised, start a stream thread
                if camera in self.cameras:
                    print("camera exists")
                    stream_thread = threading.Thread(target=self.stream_handler, args=[client], daemon=True)
                    stream_thread.start()
                    # Add stream thread to clients list of camera object
                    self.cameras[camera].stream_clients.append(stream_thread)
                # If the requested camera is not initialised or does not exist, send error response
                else:
                    print("camera does not exist")
                    request_thread = threading.Thread(target=self.bad_request_handler, args=[client], daemon=True)
                    request_thread.start()
            # If no camera has been specified, send error response
            else:
                print("no camera specified")
                request_thread = threading.Thread(target=self.bad_request_handler, args=[client], daemon=True)
                request_thread.start()
        
        # Send the last captured image of the camera specified in the querystring, using "cam=<camera>"
        elif url_parsed[2] == "/capture":
            # Extract the name of the camera
            camera = url_parsed[4]
            var_name = re.search('cam=', camera)
            camera = query[var_name.end():]

            capture_thread = threading.Thread(target=self.capture_handler, args=[client], daemon=True)
            capture_thread.start()
        # If none of the above registered URLs works, the requested function has not yet been implemented or does not exist
        # Send back a 404 page
        else:
            request_thread = threading.Thread(target=self.bad_request_handler, args=[client], daemon=True)
            request_thread.start()
    
    # Method that sends the stream from a specific camera to the client
    def stream_handler(self, client):

        pass

    # Method to send a single image to the client
    def capture_handler(self, client):

        pass

    # Method to remotely shut the server down
    def shutdown_handler(self, client):
        print("Server shutting down...")
        self.running = False
        client.close()

    # Method to send the status page to the client
    def status_handler(self, client):

        pass

    # Method to send a bad request response to the client. Used when no other handler is appropriate
    def bad_request_handler(self, client):
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