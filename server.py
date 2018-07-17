from flask_socketio import SocketIO
from flask import Flask, render_template, request
from time import sleep
from threading import Thread, Event
from flask_autoindex import AutoIndex
import logging
import os

from shongololo import start_up
from shongololo import sys_admin
from shongololo import K30_serial
from shongololo import Imet_serial

app = Flask(__name__)

# turn the flask app into a socketio app
socketio = SocketIO(app)
#TODO change hardcoded download files dir  to config based
filesindex = AutoIndex(app, os.path.join(app.root_path, '/home/uvm/DATA/'), add_url_rules=False)

sthread = Thread()
sthread_stop_event = Event()
mthread = Thread()
mthread_stop_event = Event()
sensors=[]

class FlaskHandler(logging.Handler):
    def __init__(self, a_socket, level=logging.NOTSET):
        super().__init__(level=level)
        self.socketio = a_socket

    def emit(self, record):
        socketio.emit('newmsg', {'lmsg': self.format(record)}, namespace='/test')


class shongololo_thread(Thread):
    def __init__(self):
        self.delay = 1
        super(shongololo_thread, self).__init__()
        self.imet_sockets = []
        self.k30_sockets = []
        self.datafile = None    #File handle

    def capture_data(self):
        """
        Start capturing data from sensore and writing it to file
        """
        thread_stop_event.clear()
        # Open sensor sockets
        imet_dict = Imet_serial.find_imets()
        self.imet_sockets = Imet_serial.open_imets(imet_dict)

        k30_dict = K30_serial.find_k30s()
        self.k30_sockets = K30_serial.open_k30s(k30_dict)

        # Create data log file
        status, ND = sys_admin.mk_ND(start_up.DATADIR)
        if status !=0:
            error = "Failed to create directory for data logging, data will not be saved to file, try restarting the application"
            socketio.emit('newnumber', {'number': error}, namespace='/test')
            sys.exit()
        else:
            self.datafile = SA.ini_datafile(str(ND + SA.DATAFILE))
            socketio.emit('newnumber', {'number': "Starting log in {}".format(sys_admin.DATAFILE)}, namespace='/test')
            socketio.emit('newnumber', {'number': sys_admin.DATA_HEADER}, namespace='/test')
            self.datafile.write(sys_admin.DATA_HEADER)

            #Sample data until told to stop
            while not thread_stop_event.isSet():
                numbers = sys_admin.read_data(self.imet_sockets, self.k30_sockets)
                socketio.emit('newnumber', {'number': numbers}, namespace='/test')
                sleep(self.delay)


    def stop_capture(self):
        sys_admin.close_sensors(self.imet_sockets+self.k30_sockets)
        self.datafile.close()

    def run(self):
        self.capture_data()

class monitoring_thread(Thread):
    """Prints application log to webpage and carries out initial setup work"""
    def __init__(self):
        self.delay = 1
        self.imet_sockets = []
        self.k30_sockets = []
        self.datafile = ""
        super(monitoring_thread, self).__init__()

    def setup_shongololo(self):
        """
        Capture the apps log stream and output it to webpage along with performing initial setup work
        """
        mthread_stop_event.clear()
        flask_handler = FlaskHandler(socketio)

        #Do startup sequence
        self.imets_sockets, self.k30_sockets  = start_up.start_up(flask_handler)

        #Test sensors
        start_up.test_sensors(self.imets_sockets,self.k30_sockets)

        #Close sensor sockets
        sys_admin.close_sensors(mthread.imet_sockets+mthread.k30_sockets)

    def run(self):
        self.setup_shongololo()

@app.route('/')
def index():
    # only by sending this page first will the client be connected to the socketio instance
    my_list = ['./one.csv','./two.csv','./three.csv']
    return render_template('index.html', option_list=my_list)


@app.route('/files')
@app.route('/files/<path:path>')
def autoindex(path='.'):
    return filesindex.render_autoindex(path)


@socketio.on('connect', namespace='/test')
def test_connect():
    print('Client connected')

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')


# Functions for controlling sensors and data capture
@socketio.on('start capture', namespace='/test') #'my start' is referenced in java script
def start_capture():
    """Start a data capture session"""
    global sthread
    # Start the random number generator thread only if the thread has not been started before.
    if not sthread.isAlive():
        print("Starting Thread")
        sthread = shongololo_thread()
        sthread.start()

@socketio.on('stop capture', namespace='/test')
def stop_capture():
    """Stop a data capture session"""
    sthread.stop_capture()
    sthread_stop_event.set()

# Functions controlling whole system
@socketio.on('do setup', namespace='/test')
def do_setuplogging():
    """Do pre data capture setup and initialise application logging"""
    global mthread
    if not mthread.isAlive():
        mthread = monitoring_thread()
        mthread.start()

@socketio.on('shutdown app', namespace='/test')
def shutdown_app():
    """Shutdown whole application gracefully"""

    #Stop data capture thread if running
    if sthread.isAlive:
        stop_capture()

    #Close monitoring thread
    sys_admin.shutdown_monitor()
    mthread_stop_event.set()

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0')
