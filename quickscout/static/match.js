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
            url: '/api/position_claim/' + $elem.data('pos'),
        }).always(function(data){
            console.log(data);
            window.location.reload();
        });
    });
});
