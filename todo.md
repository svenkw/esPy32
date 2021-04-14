# TODO

#### Get rid of `jsonnify`
No need to reinvent the wheel. The `json` library works fine, but right now the API-handlers still use `jsonnify`. 

#### Implement new folder structure
All files were in the same folder. Now, html-pages and other static files are stored in the `static` folder, and all config files are stored in the `config` folder. This makes the structure a lot more clear. Also implement a way to change the default folder path on server creation.

#### Objectify the server
Turn the entire server script into a class. The server is then started by creating a server object and calling the `run` method. 

#### Objectify the cameras
Each camera specified in the `config.json` file in the config folder should be turned into a camera object at the start/creation of the server. Each object contains the important information about the camera, like the IP, port and location.

#### Split `config.json` into separate files for server and camera configuration
Now, all configuration is in one single file. This is not ideal, especially if the esPy32 server has to work together with another webserver. All should be neatly organised in a clear folder structure anyways now.