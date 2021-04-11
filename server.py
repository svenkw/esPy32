import socket
import time
import threading
import re
import json
from os import path

# Add path to the extra modules just in case python can't find
#path.join(0, '/var/www/html/camera_server')

# Local libraries
import main_handlers
import api_handlers

# Load the setup info from the config.json file
config_file = "C:/Users/svenk/Documents/Python/esp32 scripts/server/config.json"
with open(config_file, 'r') as config:
    setup = json.load(config)

esp_address = {}
for camera in setup['cameras']:
    esp_address[camera] = (setup['cameras'][camera]['ip'], setup["cameras"]["camera1"]["stream_port"])

# Start up the server socket and bind it to the correct address
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#server.bind((setup["server"]["ip"], setup["server"]["port"]))
server.bind(('0.0.0.0', setup["server"]["port"]))
server.listen(5)
server.settimeout(0.1)

start_time = time.time()

# The main server loop
# Keep server alive while the running control variable is set to True
while main_handlers.running:
    # Wait for a client for the set timeout
    # If no client connects, just pass to the rest of the server loop
    try:
        client_socket, client_address = server.accept()
    except:
        pass
    else:
        # If client connected, dispatch a thread to handle the client
        client_thread = threading.Thread(target=main_handlers.client_handler, args=[client_socket], daemon=True)
        client_thread.start()

    # Loop over all cameras in the config file
    for camera in setup['cameras']:
        # Check for camera if there are people requesting a stream. If so and no ESP-connection is active, start ESP thread
        if (len(main_handlers.stream_clients[camera]) > 0) and (main_handlers.cameras_active[camera] == False):
            main_handlers.cameras_active[camera] = True

            esp_thread = threading.Thread(target=main_handlers.esp_handler, args=[esp_address[camera], camera])
            esp_thread.daemon=True
            esp_thread.start()

        # If there are no active clients requesting a stream, but there is still a connection to the ESP32, break the connection
        elif (len(main_handlers.stream_clients[camera]) == 0) and (main_handlers.cameras_active[camera] == True):
            main_handlers.cameras_active[camera] = False
    
        # Update the list of active stream clients
        main_handlers.stream_clients[camera] = [client for client in main_handlers.stream_clients[camera] if client.is_alive()]

    time.sleep(0.05)

# Always close the server, or face the problems
main_handlers.cameras_active = False
print("Server closed")
server.close()