from flask_socketio import SocketIO
from flask import Flask, render_template, request
from random import random
from time import sleep
from threading import Thread, Event
import logging

import sys
sys.path.append('../code/shongololos/shongololos/')
import shongololos

app = Flask(__name__)

# turn the flask app into a socketio app
socketio = SocketIO(app)

# random number Generator Thread
thread = Thread()
thread_stop_event = Event()
lthread = Thread()
lthread_stop_event = Event()


class FlaskHandler(logging.Handler):
    def __init__(self, a_socket, level=logging.NOTSET):
        super().__init__(level=level)
        self.socketio = a_socket

    def emit(self, record):
        socketio.emit('newmsg', {'lmsg': self.format(record)}, namespace='/test')


class RandomThread(Thread):
    def __init__(self):
        self.delay = 1
        super(RandomThread, self).__init__()

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

class LoggingThread(Thread):
    """Prints application log to webpage and carries out initial setup work"""
    def __init__(self):
        self.delay = 1
        super(LoggingThread, self).__init__()

    def logging_stream(self):
        """
        Capture the apps log stream and output it to webpage along with performing initial setup work
        """
        lthread_stop_event.clear()
        flask_handler = FlaskHandler(socketio)
        shongololos.start_up.start_up(flask_handler)
        # TODO shutdown

    def run(self):
        self.logging_stream()

@app.route('/')
def index():
    # only by sending this page first will the client be connected to the socketio instance
    my_list = ['one','two','three']
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
    global thread
    # Start the random number generator thread only if the thread has not been started before.
    if not thread.isAlive():
        print("Starting Thread")
        thread = RandomThread()
        #thread = ShongololosThread()
        thread.start()

@socketio.on('stop capture', namespace='/test')
def stop_capture():
    """Stop a data capture session"""
    thread_stop_event.set()



# Functions controlling whole system
@socketio.on('do setup', namespace='/test')
def do_setuplogging():
    """Do pre data capture setup and initialise application logging"""
    # Start application logging and print to screen
    print ("###### HERE ###########")
    global lthread
    if not lthread.isAlive():
        lthread = LoggingThread()
        lthread.start()

@socketio.on('shutdown app', namespace='/test')
def shutdown_app():
    """Shutdown whole application gracefully"""
    #TODO put app close down calls here
    lthread_stop_event.set()
    stop_capture()



if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0')
