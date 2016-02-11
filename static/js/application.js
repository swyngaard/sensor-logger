
let socket = null;
let numbers_received = [];
let msgs_received = [];

$(document).ready(function(){
    //connect to the socket server.
    socket = io.connect('http://' + document.domain + ':' + location.port + '/test');

    //receive details from server
    socket.on('newnumber', function(msg) {
        console.log("Received number" + msg.number);
        numbers_received.push(msg.number);
        numbers_string = '';
        for (var i = 0; i < numbers_received.length; i++){
            numbers_string = numbers_string + '<p>' + numbers_received[i].toString() + '</p>';
        }
        $('#log').html(numbers_string);
    });
    socket.on('newmsg', function(msg) {
        console.log("Received log" + msg.lmsg);
        msgs_received.push(msg.lmsg);
        msg_string = '';
        for (var i = 0; i < msgs_received.length; i++){
            msg_string = msg_string + '<p>' + msgs_received[i].toString() + '</p>';
        }
        $('#applog').html(msg_string);
    });
});

//Functions for controlling sensors and data capture

//Download a data directory
function download_data(){
    socket.emit('download');
    $('#downloadbutton').html('Download');
}

//Start a data capture session
function start_capture(){
    socket.emit('start capture');
    //TODO add a visible timer
    $('#startstopbutton').html('Stop');
    $('#log').html('');
    numbers_received = [];
}

//Stop a data capture session
function stop_capture(){
    socket.emit('stop capture');
    $('#startstopbutton').html('Start');
}


// Functions controlling whole system

//Do pre data capture setup and initialise application logging
function setup_logging(){
    socket.emit('do setup');
    $('#setupbutton').html('Setup Logger');
    $('#aplog').html('');
    msgs_received = [];
}

//Shutdown whole application gracefully
function shutdown(){
    socket.emit('shutdown app');
    $('#startstopbutton').html('Start');
    msgs_received = [];
    numbers_received = [];
}

//Shutdown whole Pi gracefully
function Shutdown_Pi(){
    socket.emit('Shutdown Pi');
    $('#shutdownPibutton').html('ShutdownPi');
}
