$(function() {
    $('button[data-pos]').click(function(e) {
        e.preventDefault();
        var $elem = $(this);
        if ($elem.prop('disabled')) {
            // Just ignore it
            return;
        }
        $.ajax({
            method: 'POST',
            url: '/api/position_remove/' + $elem.data('pos'),
        }).always(function(data){
            console.log(data);
            window.location.reload();
        });
    });
    $('.qs-promote[data-id]').click(function(e) {
        e.preventDefault();
        var $elem = $(this);
        if ($elem.prop('disabled')) {
            // Just ignore it
            return;
        }
        $.ajax({
            method: 'POST',
            url: '/api/superscout/' + $elem.data('id'),
        }).always(function(data){
            console.log(data);
            window.location.reload();
        });
    });

});
