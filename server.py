from flask_socketio import SocketIO
from flask import Flask, render_template, request
from time import sleep
from threading import Thread, Event
from flask_autoindex import AutoIndex
import logging
import os

from shongololo import start_up as SU
from shongololo import sys_admin as SA
from shongololo import K30_serial as KS
from shongololo import Imet_serial as IS
#TODO enable following with pkg_resources module later
datadir = '/home/uvm/DATA/'
datafile = 'data.csv'
ihead= ",IMET_ID,  Latitude, Longitude, Altitude, Air Speed (m/s), Mode, Fixed Satellites, Avai    lable Satellites,voltage,current,level,id"
khead= ",K30_ID, CO2 ppm"
period = 0.5

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
        self.fd = None    #File handle

    def capture_data(self):
        """
        Start capturing data from sensore and writing it to file
        """
        sthread_stop_event.clear()
        # Access devices
        status, self.device_dict = SA.find_devices()

        # Connect to imets
        self.imet_sockets = IS.open_imets(self.device_dict["imets"])
        # Connect to CO2 meters
        self.k30_sockets = KS.open_k30s(self.device_dict["k30s"])

        # Start data log file
        status, ND = SA.mk_ND(datadir)
        if status !=0:
            error = "Failed to create directory for data logging, data will not be saved to file, try restarting the application"
            socketio.emit('newnumber', {'number': error}, namespace='/test')
            sys.exit()
        else:
            header = ""
            for c in range(len(self.device_dict["k30s"])):
                header = header + str(khead)
            for i in range(len(self.device_dict["imets"])):
                header = header + str(ihead)
            self.fd = SA.ini_datafile(str(ND) + datafile, header)

            socketio.emit('newnumber', {'number': "Starting log in {}".format(datafile)}, namespace='/test')
            socketio.emit('newnumber', {'number': header}, namespace='/test')
            self.fd.write(header)

            #Sample data until told to stop
            while not sthread_stop_event.isSet():
                pack = []
                dataline = ""
                print("LOGGING DATA>)))))))))))))))))))")
                try:
                    latest_idata, latest_kdata = SA.read_data(self.imet_sockets, self.k30_sockets)
                    print ("MANAGED TO  READ DATA")
                    # pack data
                    for count, k in zip(range(len(self.device_dict["k30s"])), self.device_dict["k30s"]):
                        pack.append(k[1] + "," + latest_kdata[count])

                    for count, i in zip(range(len(self.device_dict["imets"])), self.device_dict["imets"]):
                        pack.append(i[1] + "," + latest_idata[count])

                    for x in pack:
                        dataline = dataline + "," + x

                    print("HHHHHHHHHHHHH:emmitting"+dataline)
                    socketio.emit('newnumber', {'number': dataline}, namespace='/test')
                    print("HHHHHHHHHHHHH: writing data"+dataline)
                    self.fd.write("\n" + dataline)

                    sleep(self.delay)
                except:
                    if sthread.isAlive:
                        stop_capture()

                    # Close monitoring thread
                    SA.shutdown_monitor()
                    mthread_stop_event.set()


    def stop_capture(self):
        SA.close_sensors(self.imet_sockets+self.k30_sockets)
        self.fd.close()

    def run(self):
        self.capture_data()

class monitoring_thread(Thread):
    """Prints application log to webpage and carries out initial setup work"""
    def __init__(self):
        self.delay = 1
        self.imet_sockets = []
        self.k30_sockets = []
        self.device_dict = {}
        self.datafile = ""
        super(monitoring_thread, self).__init__()

    def setup_shongololo(self):
        """
        Capture the apps log stream and output it to webpage along with performing initial setup work
        """
        mthread_stop_event.clear()
        flask_handler = FlaskHandler(socketio)

        #Do startup sequence
        self.imets_sockets, self.k30_sockets, self.device_dict  = SU.start_up(flask_handler)

        #Test sensors
        SU.test_sensors(self.imets_sockets,self.k30_sockets)

        #Close sensor sockets
        SA.close_sensors(mthread.imet_sockets+mthread.k30_sockets)

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
    SA.shutdown_monitor()
    mthread_stop_event.set()

if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0')
