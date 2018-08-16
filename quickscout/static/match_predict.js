$(function() {
    $('.qs-predict').click(function(e) {
        var $elem = $(this);
        e.preventDefault();
        var data = {
            color: $elem.data('color')
        }
        console.log(data);
        $.ajax({
            method: 'POST',
            data: JSON.stringify(data),
            url: '/api/predict/' + $elem.data('match'),
            contentType: 'application/json',
            dataType: 'json',
        }).always(function(data){
            $('.qs-predict').prop('disabled', true);
            var opp = $elem.data('color') == 'red' ? 'blue' : 'red';
            $('button.qs-predict[data-color=' + opp + ']')
                .removeClass('btn-primary')
                .removeClass('btn-danger')
                .addClass('btn-default');
        });

    });
});
