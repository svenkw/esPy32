class Camera:

    # Contructor for Camera class
    def __init__(self, address, port, location, description):
        # Basic information about the camera
        self.address = address
        self.port = port
        self.location = location
        self.description = description

        # The last completely received image from the server
        self.image_buffer = None

        # List of connected client threads
        self.stream_clients = []

        # Status variable to see if the camera is connected
        self.active = False

    # Method to connect to the ESP32 CAM and request stream
    def request_stream(self):
        
        self.active = True

    # Method to disconnect from ESP32 CAM
    def disconnect(self):
        self.active = False