
// timeslots
function showtimes() {
    if ( document.getElementById("frequency").value == 0 ) $('.times').hide(); else $('.times').show();
    return false;
}

function showplusminus(n) {
    document.getElementById('slotminus').style.visibility = ( n > 1 ? 'visible' : 'hidden' );
    document.getElementById('slotplus').style.visibility = ( n < max_slots ? 'visible' : 'hidden' );
}

function addslot(e) {
    e.preventDefault();
    var n = parseInt(document.getElementById('num_slots').value)+1;
    document.getElementById('num_slots').value = '' + n;
    if ( n <= 2 ) {
        document.getElementById('weekday'+(n-1)).style.visibility = 'visible';
        document.getElementById('time_slot'+(n-1)).style.visibility = 'visible';
    } else {
        document.getElementById('weekday'+(n-1)).style.display = 'block';
        document.getElementById('time_slot'+(n-1)).style.display = 'block';
    }
    showplusminus(n);
    return true;
}

function removeslot(e) {
    e.preventDefault();
    var n = parseInt(document.getElementById('num_slots').value)-1;
    document.getElementById('num_slots').value = '' + n;
    document.getElementById('weekday'+n).value = '';
    document.getElementById('time_slot'+n).value ='';
    if ( n < 2 ) {
        document.getElementById('weekday'+n).style.visibility = 'hidden';
        document.getElementById('time_slot'+n).style.visibility = 'hidden';
    } else {
        document.getElementById('weekday'+n).style.display = 'none';
        document.getElementById('time_slot'+n).style.display = 'none';
    }
    showplusminus(n);
    return true;
}

function showslots() {
    var n = parseInt(document.getElementById('num_slots').value);
    if ( n <= 0 ) document.getElementById('num_slots').value = '' + (n=1);
    for ( var i = 0 ; i < n ; i++ ) {
        if ( i < 2) {
            document.getElementById('weekday'+i).style.visibility = 'visible';
            document.getElementById('time_slot'+i).style.visibility = 'visible';
        } else {
            document.getElementById('weekday'+i).style.display = 'block';
            document.getElementById('time_slot'+i).style.display = 'block';
        }
    }
    $('.times').show();
    showplusminus(n);
}

function setupslots() {
    $("a.slotplus").click(addslot);
    $("a.slotminus").click(removeslot);
    showslots();
}
