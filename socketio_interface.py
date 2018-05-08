import logging
from socketIO_client import SocketIO, LoggingNamespace
import numpy as np

# this should be stored persistently on disk
gestureDB = []

# debug environment setup
logging.getLogger('socketIO-client').setLevel(logging.DEBUG)
logging.basicConfig()

# create socket
socketIO =  SocketIO('http://brightsign.eu-gb.mybluemix.net', 80, LoggingNamespace)

# this is how we send a gesture to the server
socketIO.emit('gesture', repr(np.random.uniform((10,10,10))))
socketIO.wait(seconds=0.1)

# callback for update of gesture information
def onUpdateState(*args):
    gestureDB = args[0]

# listen for the update message
socketIO.on('updateState', onUpdateState)
# wait forever
socketIO.wait()