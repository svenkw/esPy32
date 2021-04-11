import time
import re
import socket

import jsonnify
import main_handlers

def status_json(client):
    values = [['clientNumber', len(main_handlers.stream_clients)], ['cameraActive', camera_active_check()]]

    json = jsonnify.list_to_json_2d(values)

    res_newline = '\r\n'
    res_ok_code = 'HTTP/1.1 200 OK\r\n'
    res_content_json = 'content-type: application/json\r\n'
    res_access_control = 'Access-Control-Allow-Origin: *\r\n'
    res_content_length = 'content-length: {}\r\n'.format(str(len(json)))

    response = res_ok_code + res_content_json + res_access_control + res_content_length + res_newline + json + res_newline
    response = bytes(response, encoding='ascii')

    client.send(response)

    client.close()

def camera_active_check():
    return 'true'