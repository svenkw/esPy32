def list_to_json(data):
    if type(data) != list:
        raise TypeError("Expected <class 'list'> type, not {}".format(type(data)))
    
    json = "{\r\n"
    for i in range(len(data)):

        if type(data[i]) != str:
            json += "\"entry{}\": {},\r\n".format(i+1, data[i])
        else:
            json += "\"entry{}\": \"{}\",\r\n".format(i+1, data[i])

    json = json[:-3]
    json += "\r\n}"
    return json

def list_to_json_2d(data):
    if type(data) != list:
        raise TypeError("Expected <class 'list'> type, not {}".format(type(data)))
    
    json = "{\r\n"
    for datapair in data:
        if len(datapair) != 2:
            raise TypeError("List entry contains more or less than two values (key-value pair)")

        if (type(datapair[1]) != str):
            json += "\"{}\": {},\r\n".format(datapair[0], datapair[1])
        else:
            json += "\"{}\": \"{}\",\r\n".format(datapair[0], datapair[1])
    
    json = json[:-3]
    json += "\r\n}"
    return json

def dict_to_json(data):
    raise RuntimeError("This function is not yet written")

    if type(data) != dict:
        raise TypeError("Expected <class 'dict'> type, not {}".format(type(data)))
    
    pass
    #return json