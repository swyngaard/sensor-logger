from flask_socketio import SocketIO
from flask import Flask, render_template
from random import random
from time import sleep
from threading import Thread, Event

app = Flask(__name__)

# turn the flask app into a socketio app
socketio = SocketIO(app)

# random number Generator Thread
thread = Thread()
thread_stop_event = Event()


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


@app.route('/')
def index():
    # only by sending this page first will the client be connected to the socketio instance
    return render_template('index.html')


@socketio.on('connect', namespace='/test')
def test_connect():
    print('Client connected')


@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')


@socketio.on('my start', namespace='/test')
def start_running():
    global thread
    # Start the random number generator thread only if the thread has not been started before.
    if not thread.isAlive():
        print("Starting Thread")
        thread = RandomThread()
        thread.start()


@socketio.on('my stop', namespace='/test')
def stop_running():
    thread_stop_event.set()


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0')
