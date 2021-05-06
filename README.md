# esPy32
An ESP32 CAM multiplexing server written in Python.

## Why?
The ESP32 CAM module is a nice, easy to use, and most of all cheap wifi-enabled camera. It does have an annoying limitation though: it can only handle one client at a time on its little web server. But what if you want to use the camera for a small streaming site? A site where multiple people can watch the ESP32 stream at the same time?

That is what this server, written in Python, tries to solve. It works roughly like a proxy, but not quite. Instead of opening a new connection to the ESP32 for every new client, it only opens one streaming connection to the camera and buffers the incoming images. Every new client that connects to the esPy server recieves the stream from this buffer. Now, only one connection to the camera is required. 

## How?
Using the `sockets` python module, a simple web server is created. With the standard `threading` Python module, a thread is created for each new client. As long as there is at least one active client thread, a connection to the camera is made. The server can handle multiple cameras, which can be configured in a separate .json file. The full documentation can be found [here](https://github.com/svenkw/esPy32/wiki).

## Development
The server is currently approaching the first complete version in its object-oriented form. I'm currently focusing on completing the documentation, and I will probably just add some quality-of-life improvements and some more debugging tools.

Finally, note that I am not a professional web developer, internet expert, or professional programmer at all. Everything in this project was developed by just Googling a lot. If you have a better understanding of all this, or just want to help: all help is welcome. 
