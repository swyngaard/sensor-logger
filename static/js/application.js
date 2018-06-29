
let socket = null;
let numbers_received = [];

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
});

function start_logging(){
    socket.emit('my start');
    $('#startstopbutton').html('Stop');
    $('#log').html('');
    numbers_received = [];
}

function stop_logging(){
    socket.emit('my stop');
    $('#startstopbutton').html('Start');
}

function toggle_logging(){
    if($('#startstopbutton').text() === 'Start') {
        start_logging();
    } else {
        stop_logging();
    }
}
