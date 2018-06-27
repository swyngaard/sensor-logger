$(document).ready(function(){
});

let socket = null;

function start_logging(){
    //connect to the socket server.
    socket = io.connect('http://' + document.domain + ':' + location.port + '/test');
    var numbers_received = [];

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

    $('#startstopbutton').html('Stop');
}

function stop_logging(){
    socket.disconnect();
    socket = null;
    $('#startstopbutton').html('Start');
}

function toggle_logging(){
    if(socket === null) {
        start_logging();
    } else {
        stop_logging();
    }
}
