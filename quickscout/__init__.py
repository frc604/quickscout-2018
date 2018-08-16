#!/usr/bin/env python3
"""
A FRC Scouting application
Copyright (C) 2018 Kunal Mehta <legoktm@member.fsf.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from collections import defaultdict, OrderedDict
from flask import Flask, jsonify, make_response, redirect, render_template, request, send_from_directory, url_for
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, UserMixin, current_user, login_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
import os
import statistics
import time

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TBA-Auth-Key'] = '' # TheBlueAlliance API Key
app.config['BOOTSTRAP_SERVE_LOCAL'] = True
app.config['EVENT_ID'] = '' # Used for storing data without conflicts
app.config['EVENT_NAME'] = '' # Visible name
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///%s.db' % app.config['EVENT_ID']
app.config['SECRET_KEY'] = ''  # FIXME REMOVE
app.config['PASSWORD'] = '' # Login password for all scouters
app.config['EVENT_LEFT'] = '' # Which color is the left side of the field
app.config['PICTURES'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'pictures')
app.config['THUMBS'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'thumbs')
app.config['HISTOGRAMS'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'histogram')
app.config['ADMINS'] = [] # Can control status of other scouters
app.config['SCOUTERS'] = []

db = SQLAlchemy(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from . import csv_dump, models, utils  # noqa
from .stream import EventStream  # noqa
from .summary import TeamSummary  # noqa


@app.context_processor
def inject_to_templates():
    return {
        'user_name': _user_name,
        'round': round,
    }


@app.route('/')
def main():
    return render_template('index.html')


class LoginUser(UserMixin):
    def __init__(self, id_):
        self.id = id_
        self._name = None
        self._is_superscout = None
        self._dark_theme = None

    @property
    def name(self):
        if self._name is None:
            self._name = _user_name(self.id)

        return self._name

    @property
    def is_admin(self):
        return self.name in app.config['ADMINS']

    @property
    def is_superscout(self):
        if self._is_superscout is None:
            self._is_superscout = models.SuperScouters.query.filter_by(user=self.id).first() is not None
        return self._is_superscout

    @property
    def role(self):
        if _get_position(self.id) is not None:
            return 'matchscout'
        elif self.is_superscout:
            return 'superscout'
        else:
            return None

    @property
    def dark_theme(self):
        if self._dark_theme is None:
            self._dark_theme = models.DarkMode.query.filter_by(user=self.id).first() is not None
        return self._dark_theme


@app.route('/login', methods=('GET', 'POST'))
def login():
    msg = None
    success = False
    if request.method == 'POST':
        username = request.form.get('name')
        password = request.form.get('password')
        user = models.User.query.filter_by(name=username).first()
        if user is not None:
            if password == app.config['PASSWORD']:
                success = True
                luser = LoginUser(user.id)
                login_user(luser, remember=True)
            else:
                msg = 'Login failed.'
        else:
            msg = 'Login failed.'

    if success:
        return redirect(url_for('main'))

    return render_template('login.html', msg=msg)


@login_manager.user_loader
def load_user(user_id):
    user = models.User.query.filter_by(id=user_id).first()
    if user is not None:
        return LoginUser(user.id)
    else:
        return None


@app.route('/logout')
@login_required
def logout():
    # Un-assign from position if any
    position = models.ScouterPosition.query.first()
    pos = position.get_position(current_user.id)
    if pos:
        position.__setattr__(pos, None)
        db.session.add(position)
        db.session.commit()
    logout_user()
    return redirect(url_for('main'))


@app.route('/release')
@login_required
def release():
    position = models.ScouterPosition.query.first()
    pos = position.get_position(current_user.id)
    if pos:
        position.__setattr__(pos, None)
        db.session.add(position)
        db.session.commit()
    return redirect(url_for('main'))


@app.route('/toggle_dark')
@login_required
def toggle_dark():
    dark = models.DarkMode.query.filter_by(user=current_user.id).first()
    if dark is not None:
        db.session.delete(dark)
    else:
        db.session.add(models.DarkMode(user=current_user.id))
    db.session.commit()
    return redirect(url_for('main'))


@app.route('/team')
@login_required
def team():
    teams = sorted(models.Team.query.all(), key=lambda x: x.id)
    return render_template('team.html', teams=teams)


@app.route('/team/<team_id>')
@login_required
def team_team(team_id):
    team = models.Team.query.filter_by(id=team_id).first_or_404()
    pit_report = models.PitReport.query.filter_by(team=team_id).first()
    summary = TeamSummary.from_team_id(team_id)
    return render_template('team_team.html', team=team, pit_report=pit_report, summary=summary, charts=charts())


# URL is served via Apache for performance
@app.route('/pictures/<fname>')
@login_required
def serve_teampics(fname):
    return send_from_directory(app.config['PICTURES'], fname)


# URL is served via Apache for performance
@app.route('/thumbs/<fname>')
@login_required
def serve_teampics_thumbs(fname):
    return send_from_directory(app.config['THUMBS'], fname)


@app.route('/team/<team_id>/pics', methods=('GET', 'POST'))
@login_required
def team_pics(team_id):
    team = models.Team.query.filter_by(id=team_id).first_or_404()
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            exists = True
            count = 0
            while exists:
                count += 1
                fname = os.path.join(app.config['PICTURES'], '%s_%s.jpg' % (team.id, count))
                exists = os.path.exists(fname)
            file.save(fname)
    return render_template('team_pics.html', team=team, include_tba=True)


@app.route('/batch_upload')
@login_required
def batch_upload():
    teams = models.Team.query.all()
    return render_template('batch_upload.html', teams=teams, include_tba=False)


@app.route('/histogram/<team_id>_<action>_<mode>.svg')
@login_required
def histogram_chart(team_id, action, mode):
    fname = '%s_%s_%s.svg' % (team_id, action, mode)
    return send_from_directory(app.config['HISTOGRAMS'], fname)


@app.route('/pit')
@login_required
def pit():
    teams = sorted(models.Team.query.all(), key=lambda x: x.id)
    reports = {}
    for report in models.PitReport.query.all():
        reports[report.team] = report

    return render_template('pit.html', teams=teams, reports=reports)


@app.route('/pit/<team_id>', methods=('GET', 'POST'))
@login_required
def pit_team(team_id):
    team = models.Team.query.filter_by(id=team_id).first_or_404()
    report = models.PitReport.query.filter_by(team=team.id).first()
    msg = False
    # TODO: conflict detection??
    if request.method == 'POST':
        print(request.form)
        if report is None:
            report = models.PitReport()
        report.scouter = current_user.id
        report.team = team.id
        bools = {
            'can_autocrossline', 'can_autoswitch',
            'can_autoscale', 'can_climb',
            'can_teleopscale', 'can_teleopswitch'
        }
        for prop, value in request.form.items():
            report.__setattr__(prop, value)
        for prop in bools:
            report.__setattr__(prop, prop in request.form)
        db.session.add(report)
        db.session.commit()
        msg = 'Pit report saved.'
    if report is None:
        report = models.PitReport()
    print(report.can_autocrossline)
    return render_template('pit_team.html', team=team, report=report, msg=msg, drive=models.Drivebase,
                           plang=models.ProgrammingLanguage)


_is_left_red = utils.is_left_red


def _user_name(user_id):
    if user_id:
        return models.User.query.filter_by(id=user_id).first().name
    else:
        return ''


def _get_position(user_id=None):
    if user_id is None:
        user_id = current_user.id
    position = models.ScouterPosition.query.first()
    assert position is not None
    return position.get_position(user_id)


@app.route('/match')
@login_required
def match():
    mode = request.args.get('mode', 'role')
    filter_ = request.args.get('filter')
    matches = sorted(models.Match.query.all(), key=lambda x: x.id)
    position = models.ScouterPosition.query.first()
    assert position is not None
    real_position = {}
    if _is_left_red():
        real_position['left1'] = _user_name(position.red1)
        real_position['left2'] = _user_name(position.red2)
        real_position['left3'] = _user_name(position.red3)
        real_position['right1'] = _user_name(position.blue1)
        real_position['right2'] = _user_name(position.blue2)
        real_position['right3'] = _user_name(position.blue3)
    else:
        real_position['left1'] = _user_name(position.blue1)
        real_position['left2'] = _user_name(position.blue2)
        real_position['left3'] = _user_name(position.blue3)
        real_position['right1'] = _user_name(position.red1)
        real_position['right2'] = _user_name(position.red2)
        real_position['right3'] = _user_name(position.red3)

    can_claim = _get_position() is None
    show_position = True
    if mode != 'role':
        link_target = mode
        # If we wanted an absolute destination, we know what we want,
        # and don't need to show the position chart
        show_position = False
    elif current_user.role == 'matchscout':
        # Assigned a position!
        link_target = 'match_scout'
    elif current_user.role == 'superscout':
        link_target = 'match_superscout'
        # XXX: Should super scouts be able to normal scout? Probably
        # in case of an emergency...
        # can_claim = False
    else:
        link_target = 'match_info'

    if filter_:
        matches = [match for match in matches if match.is_playing(int(filter_))]

    played = [result.id for result in models.MatchResult.query.all()]

    return render_template(
        'match.html',
        matches=matches,
        position=real_position,
        link_target=link_target,
        can_claim=can_claim,
        show_position=show_position,
        played=played,
        **_left_right_colors(),
    )


def _left_right_colors():
    if _is_left_red():
        return {
            'left': 'red',
            'right': 'blue',
            'left_color': 'btn-danger',
            'right_color': 'btn-primary',
        }
    else:
        return {
            'left': 'blue',
            'right': 'red',
            'left_color': 'btn-primary',
            'right_color': 'btn-danger',
        }


@app.route('/match/admin')
@login_required
def match_admin():
    position = models.ScouterPosition.query.first()
    assert position is not None
    real_position = {}
    if _is_left_red():
        real_position['left1'] = _user_name(position.red1)
        real_position['left2'] = _user_name(position.red2)
        real_position['left3'] = _user_name(position.red3)
        real_position['right1'] = _user_name(position.blue1)
        real_position['right2'] = _user_name(position.blue2)
        real_position['right3'] = _user_name(position.blue3)
    else:
        real_position['left1'] = _user_name(position.blue1)
        real_position['left2'] = _user_name(position.blue2)
        real_position['left3'] = _user_name(position.blue3)
        real_position['right1'] = _user_name(position.red1)
        real_position['right2'] = _user_name(position.red2)
        real_position['right3'] = _user_name(position.red3)

    scouters = defaultdict(int)
    # Populate everyone at zero
    for user in models.User.query.all():
        scouters[user.id] = 0
    reports = models.MatchReport.query.all()
    for report in reports:
        scouters[report.user] += 1
    super_reports = models.SuperScoutReport.query.all()
    # Count number of matches scouted by super scouters, but
    # we need to deduplicate the reports for matches, use a set for that
    super_counts = defaultdict(set)
    for super_report in super_reports:
        super_counts[super_report.user].add(super_report.match)
    for user_id, super_matches in super_counts.items():
        scouters[user_id] += len(super_matches)

    super_scouters = [scouter.user
                      for scouter in models.SuperScouters.query.all()]

    return render_template(
        'match_admin.html',
        position=real_position,
        # Want sort by number of matches, then by name if tied. So sort
        # ascending, but make the number negative so bigger sorts first
        scouters=sorted(scouters.items(), key=lambda x: (-x[1], _user_name(x[0]))),
        super_scouters=super_scouters,
        **_left_right_colors(),
    )


@app.route('/match/<match_id>')
@login_required
def match_scout(match_id):
    position = _get_position()
    if not position:
        return redirect(url_for('match'))
    match = models.Match.query.filter_by(id=match_id).first_or_404()
    on_left = (_is_left_red() and position.startswith('red')) or\
              (not _is_left_red() and position.startswith('blue'))
    exists = models.MatchEvent.query.filter_by(
        match=match_id,
        team=match.__getattribute__(position),
        action='mode-endgame'
    ).first() is not None
    return render_template(
        'match_scout.html',
        position=position,
        match=match,
        on_left=on_left,
        match_id=match.id,
        exists=exists,
        match_info={
            'match': match.id,
            'on_left': on_left,
        },
        **_left_right_colors(),
    )


@app.route('/match/<match_id>/superscout', methods=('GET', 'POST'))
@login_required
def match_superscout(match_id):
    # Validate match_id first
    match = models.Match.query.filter_by(id=match_id).first_or_404()
    # Now load existing data
    comments = models.SuperScoutReport.query.filter_by(match=match_id, user=current_user.id).all()
    for c in comments:
        print(c.team)
    teams = match.teams()
    # Fill in empty strings for all teams
    data = dict((team, models.SuperScoutReport(match=match_id, user=current_user.id, team=team))
                for team in teams['blue']+teams['red'])
    # Overwrite with comments
    for comment in comments:
        data[comment.team] = comment

    if request.method == 'POST':
        print(request.form)
        for team, info in request.form.items():
            team = int(team)
            if team in data:
                data[team].info = info
                db.session.add(data[team])
        db.session.commit()

    return render_template(
        'match_superscout.html',
        match_id=match_id,
        data=data,
        match=match,
        **_left_right_colors()
    )


def charts():
    return (
        ('teleop', 'scale'),
        ('teleop', 'switch'),
        ('teleop', 'vault'),
        ('teleop', 'oswitch'),
        ('auton', 'scale'),
        ('auton', 'scale-cross'),
        ('auton', 'switch-center'),
        ('auton', 'switch-same'),
        ('auton', 'switch-cross'),
    )


@app.route('/team_compare', methods=['GET', 'POST'])
@login_required
def team_compare():
    if request.method == 'POST':
        teams = []
        for i in range(0, 20):
            if request.form.get('team%s' % i):
                teams.append(request.form.get('team%s' % i))
        print(teams)
        return redirect(url_for('match_info', match_id=0, teams=','.join(teams)))
    return render_template('team_compare.html')


@app.route('/match/<match_id>/info')
@login_required
def match_info(match_id):
    if match_id == '0':
        match_id = 0
        team_ids = request.args.get('teams').split(',')
    else:
        match = models.Match.query.filter_by(id=match_id).first_or_404()
        team_ids = match.teams()['red'] + match.teams()['blue']
    summaries = {}
    teams = {}
    for team_id in team_ids:
        teams[team_id] = models.Team.query.get(team_id)
        summaries[team_id] = TeamSummary.from_team_id(team_id)
    colors = {}
    for team_id in team_ids:
        if match_id == 0:
            colors[team_id] = 'info'
        else:
            colors[team_id] = 'danger' if match.color(team_id) == 'red' else 'info'

    def prop(name):
        return lambda x: x.__getattribute__(name)

    def min_avg_max(label, name):
        def builder(x):
            return ' <span class="hidden-xs">/</span><span class="visible-xs-block"></span> '.join(
                '%s' % x.__getattr__(attr+'_'+name) for attr in ['min', 'avg', 'max']
            )
        return label + ' (min/avg/max)', builder

    data = OrderedDict((
        ('General', OrderedDict((
            ('Pit', lambda x: teams[x.team_id].pit),
            ('Drivebase', prop('drivebase')),
            ('Self-reported speed', prop('speed')),
        ))),
        ('Auton', OrderedDict((
            min_avg_max('Baseline', 'auton_cross'),
            min_avg_max('Scale', 'auton_scale'),
            min_avg_max('Scale (cross)', 'auton_scale_cross'),
            min_avg_max('Switch (center)', 'auton_switch_center'),
            min_avg_max('Switch (same)', 'auton_switch_same'),
            min_avg_max('Switch (cross)', 'auton_switch_cross'),
        ))),
        ('Teleop', OrderedDict((
            min_avg_max('Scale', 'teleop_scale'),
            min_avg_max('Switch', 'teleop_switch'),
            min_avg_max('OSwitch', 'teleop_oswitch'),
            min_avg_max('Vault', 'teleop_vault'),
        ))),
        ('Climb', OrderedDict((
            min_avg_max('Platform', 'end_platform'),
            min_avg_max('Climb', 'climb_success'),
            min_avg_max('Carry', 'climb_carried')
        ))),
        ('Charts', OrderedDict((
            ('', lambda x: ''),
        ))),
        ('Pictures', OrderedDict((
            ('', lambda x: ''),
        ))),
    ))

    return render_template(
        'match_info.html',
        match_id=match_id,
        data=data,
        summaries=summaries,
        team_ids=team_ids,
        colors=colors,
        teams=teams,
        charts=charts()
    )


@app.route('/gamedata')
@login_required
def gamedata():
    counts = defaultdict(int)
    total = 0
    for result in models.MatchResult.query.all():
        counts[result.gamedata] += 1
        total += 1
    counts = OrderedDict(sorted(counts.items(), key=lambda x: x[1], reverse=True))
    return render_template('gamedata.html', counts=counts, total=total)


@app.route('/rankings')
@app.route('/rankings/<sort_mode>')
@login_required
def rankings(sort_mode='teleop_scale'):
    print("Sorting teams via " + sort_mode)
    teams = models.Team.query.all()
    data = {}
    datapoints = [point for point in TeamSummary.data
                  if point.startswith(('auton', 'teleop')) and not point.endswith(('drop', 'knockoff'))]
    # Sort auto first
    datapoints.sort(key=lambda x: (not x.startswith('auton'), TeamSummary.data.index(x)))
    datapoints += ['time_teleop_scale', 'time_teleop_switch', 'time_teleop_oswitch', 'time_teleop_vault']

    if sort_mode not in datapoints:
        sort_mode = 'teleop_scale'

    def default_sort(x):
        if sort_mode.startswith('time_'):
            val = x[1].__getattribute__('average_'+sort_mode)[0]
            if val == '-':
                return 9999999999
            else:
                return val
        else:
            return x[1].__getattr__('avg_'+sort_mode)
    sorts = {
        # Use numerical sort, drop the %
        'auton_cross': lambda x: int(default_sort(x)[:-1])
    }

    for team in teams:
        data[team.id] = TeamSummary.from_team_id(team.id)

    rev = not request.args.get('reverse')
    data = OrderedDict(sorted(
        data.items(),
        key=sorts.get(sort_mode, default_sort),
        reverse=rev
    ))

    team_rankings = dict((r.id, r.rank) for r in models.TeamRanking.query.all())

    return render_template(
        'rankings.html',
        data=data,
        sort_mode=sort_mode,
        datapoints=datapoints,
        team_rankings=team_rankings,
        revd=request.args.get('reverse')
    )


@app.route('/predict_rankings')
@login_required
def predict_rankings():
    predict_rankings = models.RankingPrediction.query.all()
    predict_rankings.sort(key=lambda x: x.avg)
    team_rankings = dict((r.id, r.rank) for r in models.TeamRanking.query.all())
    matches_left = defaultdict(int)
    matches = models.Match.query.all()
    match_results = set(r.id for r in models.MatchResult.query.all())
    for match in matches:
        if match.id not in match_results:
            for team_id in match.teams()['red'] + match.teams()['blue']:
                matches_left[team_id] += 1

    return render_template('predict_rankings.html', predict_rankings=predict_rankings, team_rankings=team_rankings, matches_left=matches_left)


@app.route('/raw')
@login_required
def raw():
    matches = models.Match.query.all()

    reports = defaultdict(lambda: defaultdict(int))
    for report in models.MatchReport.query.all():
        reports[report.match][report.team] += 1

    return render_template('raw.html', matches=matches, reports=reports)


@app.route('/raw/<match_id>/<team_id>')
@login_required
def raw_team(match_id, team_id):
    match = models.Match.query.get(match_id)
    team_id = int(team_id)
    team = models.Team.query.get(team_id)
    events = models.MatchEvent.query.filter_by(match=match_id, team=team_id).all()
    start_time = None
    for event in events:
        if event.action == 'mode-auton':
            start_time = event.time
            break

    print(events)
    return render_template('raw_team.html', match=match, team=team, events=events, start_time=start_time)


@app.route('/predict')
@login_required
def predict():
    results = set([result.id for result in models.MatchResult.query.all()])
    matches = sorted(
        (match for match in models.Match.query.all() if match.id not in results),
        key=lambda x: x.id
    )
    predicted = set([
        predict.match for predict
        in models.Predictions.query.filter_by(user=current_user.id).all()
    ])
    print(predicted)

    return render_template('predict.html', matches=matches, predicted=predicted)


@app.route('/predict/<match_id>')
@login_required
def predict_match(match_id):
    match = models.Match.query.get(match_id)
    red_teams = ', '.join(str(t) for t in match.teams()['red'])
    blue_teams = ', '.join(str(t) for t in match.teams()['blue'])
    return render_template(
        'match_predict.html',
        match_id=match_id,
        red_teams=red_teams,
        blue_teams=blue_teams,
        **_left_right_colors()
    )


@app.route('/predictions')
@login_required
def predictions():
    results = models.MatchResult.query.all()
    users = defaultdict(int)
    user_totals = defaultdict(int)
    for result in results:
        match_id = result.id
        auton_start = [m.time for m
                       in models.MatchEvent.query.filter_by(match=match_id, action='mode-auton').all()]
        if not auton_start:
            continue
        match_start_ms = statistics.mean(auton_start)
        match_start = round(match_start_ms/1000)

        predicts = models.Predictions.query.filter_by(match=match_id).all()
        for prediction in predicts:
            # Give 20 grace seconds for clock skew
            if prediction.time > (match_start + 20):
                print('Skipping %s by %s (off by %ss)'
                      % (match_id, _user_name(prediction.user), prediction.time - match_start))
                # Lateeeeee
                #continue
            expected = result.winner() == 'red'
            user_totals[_user_name(prediction.user)] += 1
            if prediction.winner == expected:
                users[_user_name(prediction.user)] += 1

    # Sort
    users = OrderedDict(sorted(users.items(), key=lambda x: x[1]/user_totals[x[0]], reverse=True))
    return render_template('predictions.html', users=users, user_totals=user_totals)


_is_on_left = utils.is_on_left


@app.route('/api/match_event/<match_id>', methods=('POST',))
@login_required
def api_match_event(match_id):
    user_id = current_user.id
    data = request.get_json()
    match = models.Match.query.filter_by(id=match_id).first()
    position = _get_position()
    team_id = match.__getattribute__(position)
    # Check to see if there's existing data we should overwrite
    models.MatchEvent.query.filter_by(match=match_id, team=team_id).delete()
    print(data)
    events = []
    for info in data['events']:
        if not _is_on_left(position):
            # If they're on the right, we need to remap the zones to
            # be on the left perspective
            zone_map = {
                'cube-grab1': 'cube-grab5',
                'cube-grab2': 'cube-grab4',
                'cube-grab3': 'cube-grab3',
                'cube-grab4': 'cube-grab2',
                'cube-grab5': 'cube-grab1',
            }
            if info['action'] in zone_map:
                info['action'] = zone_map[info['action']]
        event = models.MatchEvent(
            user=user_id,
            match=match_id,
            team=team_id,
            **info
        )
        events.append(event)
        db.session.add(event)
    db.session.commit()

    create_match_report(match_id, team_id, position, events, data=data, user_id=user_id)

    return jsonify(success=True)


def rebuild_match_reports():
    print('Rebuilding match reports...')
    matches = models.Match.query.all()
    for match in matches:
        result = models.MatchResult.query.filter_by(id=match.id).first()
        for alliance in ['red', 'blue']:
            for team_id in match.teams()[alliance]:
                position = '%s%s' % (alliance, match.position(team_id))
                events = models.MatchEvent.query.filter_by(match=match.id, team=team_id).all()
                if not events:
                    continue
                # Stupid hack to filter out double POSTs in old, bad data
                real_events = []
                found_start = False
                for event in events:
                    if event.action == 'mode-auton':
                        if found_start:
                            break
                        found_start = True
                    real_events.append(event)
                create_match_report(match.id, team_id, position, real_events, result=result)


def create_match_report(match_id, team_id, position, events, data=None, user_id=None, result=None):
    stream = EventStream(position, result)
    for event in events:
        stream.add_event(event)

    report = models.MatchReport.query.filter_by(match=match_id, team=team_id).first()
    if report is None:
        report = models.MatchReport(
            match=match_id,
            team=team_id
        )
    stream.update_report(report)
    if user_id is not None:
        report.user = user_id
    if data:
        report.comments = data['comments']
        report.drive_comments = data['drive_comments']
    db.session.add(report)
    db.session.commit()


@app.route('/api/position_claim/<pos>', methods=('POST',))
@login_required
def api_position_claim(pos):
    position = models.ScouterPosition.query.first()
    if position.__getattribute__(pos) is not None:
        return jsonify(success=False)

    position.__setattr__(pos, current_user.id)
    db.session.add(position)
    db.session.commit()
    return jsonify(success=True)


@app.route('/api/position_remove/<pos>', methods=('POST',))
@login_required
def api_position_remove(pos):
    position = models.ScouterPosition.query.first()
    position.__setattr__(pos, None)
    db.session.add(position)
    db.session.commit()
    return jsonify(success=True)


@app.route('/api/predict/<match_id>', methods=('POST',))
@login_required
def api_predict_match(match_id):
    # Don't let people predict if the match is already over...
    result = models.MatchResult.query.get(match_id)
    if result is not None:
        return jsonify(success=False)
    print(request.get_json())
    prediction = models.Predictions.query.filter_by(user=current_user.id, match=match_id).first()
    # true for red, false for blue
    winner = request.get_json().get('color') == 'red'
    if prediction is None:
        prediction = models.Predictions(
            match=match_id,
            user=current_user.id,
            winner=winner,
            time=time.time()
        )
    else:
        prediction.winner = winner
        prediction.time = time.time()
    db.session.add(prediction)
    db.session.commit()
    return jsonify(success=True)


@app.route('/api/superscout/<user_id>', methods=('POST',))
@login_required
def api_superscout(user_id):
    # Toggle state
    row = models.SuperScouters.query.filter_by(user=user_id).first()
    if row is not None:
        db.session.delete(row)
    else:
        db.session.add(models.SuperScouters(user=user_id))
    db.session.commit()
    return jsonify(success=True)


@app.route('/csv')
@login_required
def csv():
    resp = make_response(csv_dump.dump())
    if not request.args.get('view'):
        resp.headers['Content-Disposition'] = 'attachment; filename=export.csv'
        resp.headers['Content-type'] = 'text/csv'
    return resp


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
