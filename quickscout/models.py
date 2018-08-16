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

import enum
import json
import os

from . import app, db


class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    # JSON-encoded media info
    media = db.Column(db.Text)
    # Champs pit
    pit = db.Column(db.Text)

    def __repr__(self):
        return '<Team %s>' % self.id

    def has_any_pictures(self):
        return self.pictures() or list(self.tba_pictures())

    def tba_pictures(self):
        media = json.loads(self.media)
        for key in media['imgur']:
            yield {
                'full': 'https://i.imgur.com/%sl.jpg' % key,
                'thumb': 'https://i.imgur.com/%sl.jpg' % key
            }
        for key in media['cd']:
            url = 'http://www.chiefdelphi.com/media/img/%s' % key
            yield {
                'full': url,
                # Is this right??
                'thumb': url.replace('_l', '_m'),
            }

    def pictures(self):
        pics = []
        for fname in sorted(os.listdir(app.config['PICTURES'])):
            if not fname.startswith('%s_' % self.id):
                continue
            full = fname
            if os.path.exists(os.path.join(app.config['THUMBS'], fname)):
                thumb = fname
            else:
                thumb = None

            pics.append({
                'full': full,
                'thumb': thumb
            })

        return pics


class Drivebase(enum.Enum):
    westcoast = 'westcoast'
    mecanum = 'mecanum'
    omni = 'omni'
    swerve = 'swerve'
    hybrid = 'hybrid'


class ProgrammingLanguage(enum.Enum):
    labview = 'labview'
    java = 'java'
    cplusplus = 'cplusplus'
    python = 'python'
    other = 'other'


class PitReport(db.Model):
    __tablename__ = 'pit_reports'
    id = db.Column(db.Integer, unique=True, primary_key=True)
    # Team being scouted
    team = db.Column(db.Integer, db.ForeignKey('teams.id'), unique=True)
    # Person scouting
    scouter = db.Column(db.Integer)
    # Drivebase
    drive = db.Column(db.Enum(Drivebase))
    # Speed robot can go
    speed = db.Column(db.Text)
    wheels = db.Column(db.Text)
    drive_comments = db.Column(db.Text)
    programming_lang = db.Column(db.Enum(ProgrammingLanguage))
    # Auto functionality
    can_autocrossline = db.Column(db.Boolean)
    can_autoswitch = db.Column(db.Boolean)
    can_autoscale = db.Column(db.Boolean)
    auto_strategy = db.Column(db.Text)
    can_teleopscale = db.Column(db.Boolean)
    can_teleopswitch = db.Column(db.Boolean)
    teleop_strategy = db.Column(db.Text)
    # Can climb
    can_climb = db.Column(db.Boolean)
    # How they climb...?
    climb_design = db.Column(db.Text)
    # How many ramps if any
    climb_ramps = db.Column(db.Integer)
    # Arbitrary comments
    comments = db.Column(db.Text)

    teams = db.relationship(Team)

    def __repr__(self):
        return '<PitReport %s>' % self.team


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True)

    def __repr__(self):
        return '<User %s#%s>' % (self.name, self.id)


class Match(db.Model):
    __tablename__ = 'matches'
    # 15 == qm15
    id = db.Column(db.Integer, unique=True, primary_key=True)
    # fk to teams.id
    red1 = db.Column(db.Integer)
    red2 = db.Column(db.Integer)
    red3 = db.Column(db.Integer)
    blue1 = db.Column(db.Integer)
    blue2 = db.Column(db.Integer)
    blue3 = db.Column(db.Integer)

    def teams(self):
        return {
            'red': [self.red1, self.red2, self.red3],
            'blue': [self.blue1, self.blue2, self.blue3],
        }

    def is_playing(self, team_id):
        teams = self.teams()
        return team_id in teams['red'] or team_id in teams['blue']

    def color(self, team_id):
        return 'red' if team_id in self.teams()['red'] else 'blue'

    def position(self, team_id):
        return self.teams()[self.color(team_id)].index(team_id) + 1


class TbaCache(db.Model):
    __tablename__ = 'tbacaches'
    id = db.Column(db.Integer, primary_key=True)
    request = db.Column(db.Text, unique=True)
    modified = db.Column(db.Text)
    response = db.Column(db.Text)


class ScouterPosition(db.Model):
    __tablename__ = 'scouterpositions'
    id = db.Column(db.Integer, primary_key=True)
    # fk to users.id
    red1 = db.Column(db.Integer)
    red2 = db.Column(db.Integer)
    red3 = db.Column(db.Integer)
    blue1 = db.Column(db.Integer)
    blue2 = db.Column(db.Integer)
    blue3 = db.Column(db.Integer)

    def get_position(self, user_id):
        poss = ['red1', 'red2', 'red3', 'blue1', 'blue2', 'blue3']
        for pos in poss:
            if self.__getattribute__(pos) == user_id:
                return pos

        return None


class MatchEvent(db.Model):
    __tablename__ = 'matchevents'
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(20))
    time = db.Column(db.Integer)
    # Should mode be an enum?
    mode = db.Column(db.String(10))
    # fk to matches.id
    match = db.Column(db.Integer, db.ForeignKey('matches.id'))
    # fk to teams.id
    team = db.Column(db.Integer, db.ForeignKey('teams.id'))
    # fk to users.id
    user = db.Column(db.Integer, db.ForeignKey('users.id'))

    matches = db.relationship(Match)
    teams = db.relationship(Team)
    users = db.relationship(User)

    def __repr__(self):
        return '<MatchEvent q%s:%s:%s>' % (self.match, self.team, self.action)


class MatchResult(db.Model):
    __tablename__ = 'matchresults'
    # fk to matches.id
    id = db.Column(db.Integer, primary_key=True)
    red_score = db.Column(db.Integer)
    blue_score = db.Column(db.Integer)
    red_rp = db.Column(db.Integer)
    red_autoquest = db.Column(db.Boolean)
    red_facetheboss = db.Column(db.Boolean)
    blue_rp = db.Column(db.Integer)
    blue_autoquest = db.Column(db.Boolean)
    blue_facetheboss = db.Column(db.Boolean)
    gamedata = db.Column(db.Text)
    # Do we care about anything else?

    def winner(self):
        # Yes this doesn't handle ties but this is only used in the
        # prediction game which doesn't support ties
        return 'red' if self.red_score > self.blue_score else 'blue'


class RankingPrediction(db.Model):
    __tablename__ = 'rankingpredictions'
    # fk to teams.id
    id = db.Column(db.Integer, primary_key=True)
    avg = db.Column(db.Float)
    min = db.Column(db.Integer)
    median = db.Column(db.Float)
    max = db.Column(db.Integer)
    avg_rp = db.Column(db.Float)
    min_rp = db.Column(db.Integer)
    max_rp = db.Column(db.Integer)
    # Last match rankings were calculated with
    as_of = db.Column(db.Integer)


class TeamRanking(db.Model):
    __tablename__ = 'teamrankings'
    # fk to teams.id
    id = db.Column(db.Integer, primary_key=True)
    rank = db.Column(db.Integer)
    rp = db.Column(db.Integer)
    played = db.Column(db.Integer)
    # JSON-encoded
    sort_orders = db.Column(db.Text)

    def get_sort_orders(self):
        return json.loads(self.sort_orders)


class StartPosition(enum.Enum):
    left = 'left'
    middle = 'middle'
    right = 'right'


class MatchReport(db.Model):
    __tablename__ = 'matchreports'
    id = db.Column(db.Integer, primary_key=True)
    # fk to matches.id
    match = db.Column(db.Integer, db.ForeignKey('matches.id'))
    # fk to teams.id
    team = db.Column(db.Integer, db.ForeignKey('teams.id'))
    # fk to users.id
    user = db.Column(db.Integer, db.ForeignKey('users.id'))

    drive_comments = db.Column(db.Text)
    comments = db.Column(db.Text)

    died = db.Column(db.Boolean)
    noshow = db.Column(db.Boolean)

    start_position = db.Column(db.Enum(StartPosition))
    start_cube = db.Column(db.Boolean)

    auton_switch_center = db.Column(db.Integer)
    auton_switch_same = db.Column(db.Integer)
    auton_switch_cross = db.Column(db.Integer)
    auton_scale = db.Column(db.Integer)
    auton_scale_cross = db.Column(db.Integer)
    auton_drop = db.Column(db.Integer)

    teleop_switch = db.Column(db.Integer)
    teleop_scale = db.Column(db.Integer)
    teleop_oswitch = db.Column(db.Integer)
    teleop_vault = db.Column(db.Integer)
    teleop_drop = db.Column(db.Integer)
    teleop_knockoff = db.Column(db.Integer)

    end_platform = db.Column(db.Boolean)
    climb_success = db.Column(db.Boolean)
    climb_time = db.Column(db.Integer)
    climb_failed = db.Column(db.Boolean)
    climb_carried = db.Column(db.Integer)

    time_scoring = db.Column(db.Text)

    matches = db.relationship(Match)
    teams = db.relationship(Team)
    users = db.relationship(User)


class TbaMatchReport(db.Model):
    __tablename__ = 'tbamatchreports'
    id = db.Column(db.Integer, primary_key=True)
    # fk to matches.id
    match = db.Column(db.Integer, db.ForeignKey('matches.id'))
    # fk to teams.id
    team = db.Column(db.Integer, db.ForeignKey('teams.id'))

    auton_cross = db.Column(db.Boolean)
    red_card = db.Column(db.Boolean)

    matches = db.relationship(Match)
    teams = db.relationship(Team)


class Predictions(db.Model):
    __tablename__ = 'predictions'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey('users.id'))
    match = db.Column(db.Integer, db.ForeignKey('matches.id'))
    # true = red, false = blue
    winner = db.Column(db.Boolean)
    # Time prediction was submitted
    time = db.Column(db.Integer)

    users = db.relationship(User)
    matches = db.relationship(Match)


class SuperScoutReport(db.Model):
    __tablename__ = 'superscoutreports'
    id = db.Column(db.Integer, primary_key=True)
    match = db.Column(db.Integer, db.ForeignKey('matches.id'))
    team = db.Column(db.Integer, db.ForeignKey('teams.id'))
    user = db.Column(db.Integer, db.ForeignKey('users.id'))
    info = db.Column(db.Text)

    matches = db.relationship(Match)
    teams = db.relationship(Team)
    users = db.relationship(User)


class SuperScouters(db.Model):
    __tablename__ = 'superscouters'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey('users.id'))

    users = db.relationship(User)


class DarkMode(db.Model):
    __tablename__ = 'darkmodes'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey('users.id'))

    users = db.relationship(User)
