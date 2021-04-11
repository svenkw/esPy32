import re
import time
import socket
import threading
import urllib.parse as ul
import json

import api_handlers

# Open the config file
config_file = "C:/Users/svenk/Documents/Python/esp32 scripts/server/config.json"
with open(config_file, 'r') as f:
    data = json.load(f)
    
    # Create empty dict for the stream threads and camera status
    stream_clients = {}
    cameras_active = {}

    # Loop over all cameras in the config file
    for camera in data['cameras']:
        # Add a cameras active entry
        cameras_active[camera] = False

        # Create an empty list for every camera in the config file
        # Each list will hold the active stream threads for its camera
        stream_clients[camera] = []
        

# Global variables to control the server operations
running = True

# This buffer contains the last fully received image from the ESP
image_buffer = bytes('not an image', encoding='ascii')

# Main client handler to start the correct task-specific handler
def client_handler(client):
    req = client.recv(1024)

    #print(req)

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
        status_thread = threading.Thread(target=status_handler, args=[client], daemon=True)
        status_thread.start()
    # Shut the server down
    elif url_parsed[2] == "/shutdown/imadmin":
        shutdown_thread = threading.Thread(target=shutdown_handler, args=[client], daemon=True)
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
            if camera in stream_clients:
                print("camera exists")
                stream_thread = threading.Thread(target=stream_handler, args=[client], daemon=True)
                stream_thread.start()
                stream_clients[camera].append(stream_thread)
            # If the requested camera is not initialised or does not exist, send error response
            else:
                print("camera does not exist")
                request_thread = threading.Thread(target=bad_request_handler, args=[client], daemon=True)
                request_thread.start()
        # If no camera has been specified, send error response
        else:
            print("no camera specified")
            request_thread = threading.Thread(target=bad_request_handler, args=[client], daemon=True)
            request_thread.start()
    # Send the last captured image of the camera specified in the querystring, using "cam=<camera>"
    elif url_parsed[2] == "/capture":
        # Extract the name of the camera
        camera = url_parsed[4]
        var_name = re.search('cam=', camera)
        camera = query[var_name.end():]

        capture_thread = threading.Thread(target=capture_handler, args=[client], daemon=True)
        capture_thread.start()
    # Send the server status information as a json response to the client
    elif url_parsed[2] == "/api/status":
        api_thread = threading.Thread(target=api_handlers.status_json, args=[client], daemon=True)
        api_thread.start()
    # If none of the above registered URLs works, the requested function has not yet been implemented or does not exist
    # Send back a 404 page
    else:
        request_thread = threading.Thread(target=bad_request_handler, args=[client], daemon=True)
        request_thread.start()

# Client handler that sends an MJPEG-stream to the client
# Formatted using the appropriate HTTP headers
# The image boundary for the multipart content type is "NEWIMAGEFROMTHESERVER"
def stream_handler(client):
    res_newline = '\r\n'
    res_ok_code = 'HTTP/1.1 200 OK\r\n'
    res_content_jpeg = 'content-type: image/jpeg\r\n'
    res_content_stream = 'content-type: multipart/x-mixed-replace;boundary=NEWIMAGEFROMTHESERVER\r\n'
    res_boundary = 'NEWIMAGEFROMTHESERVER\r\n'
    
    response = res_ok_code + res_content_stream + res_newline
    response = bytes(response, encoding='ascii')
    client.send(response)
    client.setblocking(False)

    internal_buffer = bytes()
    while True:
        if (internal_buffer != image_buffer) and (image_buffer != b'not an image'):
            internal_buffer = image_buffer
            
            res_content_length = 'content-length: {}'.format(str(len(internal_buffer))) + '\r\n'
            response = '--' + res_boundary + res_content_jpeg + res_content_length + res_newline
            response = bytes(response, encoding='ascii')
            response += image_buffer
            
            try:
                client.send(response)
            except:
                print("Client has disconnected")
                break
            else:
                time.sleep(0.1)
    client.close()

# Handler to send only the current image in the image buffer to the client
# connection to client is closed immediately afterwards
def capture_handler(client):
    global image_buffer

    res_newline = '\r\n'
    res_ok_code = 'HTTP/1.1 200 OK\r\n'
    res_content_jpeg = 'content-type: image/jpeg\r\n'

    # If there is no image in the buffer, request a new image
    if image_buffer == b'not an image':
        esp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        esp.settimeout(5)
        esp.connect(('192.168.2.20', 80))
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

        image_buffer = image
    
    # Else recycle the last image in the buffer
    elif (image_buffer != b'not an image') and (len(image_buffer) > 0):
        image = image_buffer
        res_content_length = 'content-length: {}\r\n'.format(str(len(image)))

    response = bytes(res_ok_code + res_content_jpeg + res_content_length + res_newline, encoding='ascii') + image + b'\r\n'

    client.setblocking(False)
    client.send(response)

    client.close()

# Handler to send an empty HTTP response to the client when a server shutdown has been requested
# Shuts down the server afterwards
def shutdown_handler(client):
    global running
    client.settimeout(3)
    try:
        client.send(b'HTTP/1.1 204 NO CONTENT\r\n\r\n')
    except:
        pass
    
    print("Shutdown command recieved")
    running = False
    client.close()

# Handler to connect to the ESP camera and request an image stream
# Every new image is stored in a buffer variable to be sent to the client using stream_handler()
def esp_handler(address, camera):
    global running
    print("Starting connection with {} on {}".format(camera, address))
    
    # Connect to the streaming port
    esp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    esp.settimeout(10)
    try:
        esp.connect(address)
    except:
        print("Camera could not be reached")
        running = False

    global image_buffer
    req_stream = b'GET /stream HTTP/1.1\r\n\r\n'
    
    esp.send(req_stream)
    esp.setblocking(False)
    
    buffer = bytes()
    while cameras_active[camera]:
        try:
            chunk = esp.recv(64)
        except:
            time.sleep(0.05)
            continue
        buffer += chunk
        
        regex_start_code = re.search(b'\xff\xd8\xff', buffer)
        regex_end_code = re.search(b'\xff\xd9', buffer)

        if (regex_start_code and regex_end_code):            
            image_buffer = buffer[regex_start_code.start():regex_end_code.end()]

            regex_start_code = 0
            regex_end_code = 0
            buffer = bytes()
    esp.close()
    
    print("ESP connection terminated")

# Client handler to send an html-page to the client
# The page is saved as an html-file and loaded in through the handler
def status_handler(client):
    res_newline = '\r\n'
    res_ok_code = 'HTTP/1.1 200 OK\r\n'
    res_content_html = 'content-type: text/html\r\n'

    index = open('C:/Users/svenk/Documents/Python/esp32 scripts/server/status.html', 'r')
    page_data = index.read()
    page_data = bytes(page_data, encoding='ascii')

    res_content_length = 'content-length: {}'.format(str(len(page_data))) + '\r\n'
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

def bad_request_handler(client):
    res_newline = '\r\n'
    res_ok_code = 'HTTP/1.1 200 OK\r\n'
    res_content_html = 'content-type: text/html\r\n'

    page = open('C:/Users/svenk/Documents/Python/esp32 scripts/server/404.html', 'r')
    page_data = page.read()
    page_data = bytes(page_data, encoding='ascii')

    res_content_length = 'content-length: {}'.format(str(len(page_data))) + '\r\n'
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

    pass