from flask_socketio import SocketIO
from flask import Flask, render_template, request
from random import random
from time import sleep
from threading import Thread, Event
import logging

#import sys
#sys.path.append('../shongololo/shongololo/')
from shongololo import start_up
from shongololo import sys_admin

app = Flask(__name__)

# turn the flask app into a socketio app
socketio = SocketIO(app)

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

    def random_number_generator(self):
        """
        Generate a random number every 1 second and emit to a socketio instance (broadcast)
        Ideally to be run in a separate thread?
        """
        # infinite loop of magical random numbers
        print("Making random numbers")
        thread_stop_event.clear()
        while not thread_stop_event.isSet():
            number = round(random()*10, 3)
            print(number)
            socketio.emit('newnumber', {'number': number}, namespace='/test')
            sleep(self.delay)

    def run(self):
        self.random_number_generator()

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
        self.imets_sockets, self.k30_sockets  = start_up.start_up_for_web(flask_handler)

        start_up.test_sensors(self.imets_sockets,self.k30_sockets)

    def run(self):
        self.setup_shongololo()

@app.route('/')
def index():
    # only by sending this page first will the client be connected to the socketio instance
    my_list = ['./one.csv','./two.csv','./three.csv']
    return render_template('index.html', option_list=my_list)


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
    #TODO close down files
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

    #Close sensor sockets
    for i in mthread.imet_sockets:
        try:
            i.close()
        except:
            pass
    for k in mthread.k30_sockets:
        try:
            k.close()
        except:
            pass

    #Stop data capture thread if running
    if sthread.isAlive:
        stop_capture()

    #Close monitoring thread
    sys_admin.shutdown_monitor()
    mthread_stop_event.set()

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0')
