$(document).ready(function() {
    setInterval(function() {
        $.ajax({
            url: '/counter',
            type: 'GET'
        }).done(function(last_response) {
            $('#counter').text('Masuk: ' + last_response.total_masuk + ' | Keluar: ' + last_response.total_keluar + ' | Total: ' + last_response.total_pengunjung);
        }).fail(function(error) {
            console.log(error);
        });
    }, 1000);
});