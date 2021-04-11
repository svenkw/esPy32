# esPy32
An ESP32 CAM multiplexing server written in Python

# Why?
The ESP32 CAM module is a nice, easy to use, and most of all cheap wifi-enabled camera. It does have an annoying limitation though: it can only handle one client at a time on its little web server. But what if you want to use the camera for a small streaming site? A site where multiple people can watch the ESP stream at the same time?

That is what this server, written in Python tries to solve. It is like a proxy, but not quite. Instead of opening a new connection to the ESP for every new client, it only opens one streaming connetion to the camera and buffers the incoming images. Every new client that connects to the esPy server recieves the stream from this buffer. Now, only one connection to the camera is required. 

# How?
Using the `sockets` python module, a simple web server is created. With the standard `threading` Python module, a thread is created for each new client. As long as there is at least one active client thread, a connection to the camera is made. The server can handle multiple cameras, which can be configured in a separate .json file. 

# Development
Currently, the server is just one long python script. I would like to change this into a class, so that the server can be started by simply creating a server object and calling its `run` method. 
