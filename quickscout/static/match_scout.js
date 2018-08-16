$(function() {
    var mode = 'prematch';
    var events = [];
    var html = null;
    var startWithCube = false;
    function record_event(action) {
        event = {
            action: action,
            time: Date.now(),
            mode: mode,
        };
        events.push(event);
        console.log(event);
        // Set up undo
        html = $('#qs-everything').html();
        $('#qs-undo').prop('disabled', false);
    }

    function setMode(newmode) {
        var oldmode = mode;
        mode = newmode;
        if ( newmode != 'review' ) {
            record_event('mode-' + newmode);
        }
        var map = {
            'prematch': 'Pre-match',
            'auton': 'Autonomous',
            'teleop': 'Teleoperated',
            'endgame': 'End game',
            'review': 'Review',
        };
        $('.qs-mode').text(map[mode]);
        // We hide the old one first and then show the
        // new one so that auton+teleop sharing the same
        // form works.
        $('.qs-form-' + oldmode).addClass('hide');
        $('.qs-form-' + mode).removeClass('hide');
        $('.qs-mode-only').addClass('hide');
        $('.qs-' + mode + '-only').removeClass('hide');
        // Switching modes can't go back w/ undo
        $('#qs-undo').prop('disabled', true);
        if (newmode == 'auton') {
            setTimeout(flashbuttonoff, 15000);
        }
    }

    function flashbuttonon() {
        if (mode !== 'auton') {
            return;
        }
        $('.qs-enter-mode[data-newmode=teleop]').addClass('btn-info').removeClass('btn-default');
        setTimeout(flashbuttonoff, 250);
    }

    function flashbuttonoff() {
        if (mode !== 'auton') {
            return;
        }
        $('.qs-enter-mode[data-newmode=teleop]').addClass('btn-default').removeClass('btn-info');
        setTimeout(flashbuttonon, 250);
    }

    function button_green($btn) {
        $btn.removeClass('btn-default');
        $btn.addClass('btn-success');
    }

    function unbutton_green($btn) {
        $btn.removeClass('btn-success');
        $btn.addClass('btn-default');
    }

    function button_press(e) {
        var $elem = $(this);
        var action = $elem.data('event');
        if (!action) {
            return;
        }
        record_event(action);
        e.preventDefault();
        button_green($elem);
        var $count = $('#' + action + '-count');
        if ( $count.length ) {
            var current = $count.text();
            $count.text(parseInt(current) + 1);
        }
        if (action == 'start-with-cube') {
            startWithCube = true;
        }
        if ($elem.hasClass('qs-startpos')) {
            $('button.qs-startpos').prop('disabled', true);
        }
    }

    $('#qs-everything').on('click', 'button.qs-auto', button_press);
    $('#qs-everything').on('click', '.qs-enter-mode', function(e) {
        var newmode = $(this).data('newmode');
        setMode(newmode);
        if (newmode == 'auton' && startWithCube) {
            var zone = match_info.on_left ? '1' : '5'
            $('button[data-cube-zone=' + zone + ']').click();
        }
        e.preventDefault();
    });

    $('#qs-everything').on('click', 'button[data-cube-zone]', function(e) {
        var $elem = $(this);
        var zone = $elem.data('cube-zone');
        record_event('cube-grab'+zone);
        $('.qs-cube-actions button').prop('disabled', false);
        button_green($elem);
        $('button[data-cube-zone]').prop('disabled', true);
    });

    $('#qs-everything').on('click', '.qs-cube-actions button[data-event]', function(e) {
        var $elem = $(this);
        var action = $elem.data('event');
        record_event(action);
        $('.qs-cube-actions button').prop('disabled', true);
        $('button[data-cube-zone]').prop('disabled', false);
        unbutton_green($('button[data-cube-zone]'));
    });
    $('#qs-undo').click(function(e){
        $('#qs-everything').html(html);
        $('#qs-undo').prop('disabled', true);
        var popped = events.pop();
        console.log('Undid ' + JSON.stringify(popped));
    });
    $('#qs-everything').on('click', '.qs-submit', function(e) {
        var data = {
            comments: $('#comments').val(),
            drive_comments: $('#drive_comments').val(),
            events: events,
        }
        $('.qs-submit').text('Submitting...');
        $.ajax({
            method: 'POST',
            url: '/api/match_event/' + match_info.match,
            data: JSON.stringify(data),
            contentType: 'application/json',
            dataType: 'json',
        }).done(function(resp){
            console.log(resp);
            $('.qs-submit').text('Submitted!');
            setTimeout( function() {
                window.location.href = '/match/' + (match_info.match+1)
            }, 2000 );
        });
        // TODO we might want an error handler that dumps the JSON
        // on the page so they can copy/paste it for later manual
        // entry
    });

});
