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

from datetime import datetime
import hashlib
import json
import os
import shutil
import subprocess

from quickscout import app, charts, db, models, tba, rebuild_match_reports
from quickscout.models import Match, MatchResult, TbaMatchReport, Team, TeamRanking
from quickscout.summary import TeamSummary


def import_team_list(code):
    print('Grabbing team list...')
    data = tba.request('event/%s/teams' % code)
    with open(os.path.join(os.path.dirname(__file__), '2018cmptx_pits.json')) as f:
        pits = json.load(f)['locations']
    for info in data:
        # See if we already know about this team.
        team = Team.query.filter_by(id=info['team_number']).first()
        if team is None:
            print('Importing {team_number}...'.format(**info))
            team = Team(
                id=info['team_number'],
                name=info['nickname']
            )
        else:
            print('Updating {team_number}...'.format(**info))
            team.name = info['nickname']
        if info['key'] in pits:
            assert pits[info['key']]['div'] == app.config['EVENT_NAME']
            team.pit = pits[info['key']]['loc']
        # Grab team media
        media = tba.request('team/frc%s/media/%s' % (info['team_number'], datetime.now().year))
        if media is not None:
            new_media = {
                'imgur': [i['foreign_key'] for i in media if i['type'] == 'imgur'],
                'cd': [i['details']['image_partial'] for i in media if i['type'] == 'cdphotothread']
            }
            # Only if it's different update it, since JSON serialization
            # is not deterministic
            if not team.media or (json.loads(team.media) != new_media):
                print('Updating media for %s' % info['team_number'])
                team.media = json.dumps(new_media)
        db.session.add(team)
    db.session.commit()
    print('Finished team list.')


def strip_frc(i):
    assert i.startswith('frc')
    return int(i[3:])


def import_matches(code):
    print('Importing matches...')
    data = tba.request('event/%s/matches' % code)
    for info in data:
        if info['comp_level'] != 'qm':
            # Not a qual match
            continue
        match = Match.query.filter_by(id=info['match_number']).first()
        if match is None:
            print('Importing {match_number}...'.format(**info))
            match = Match(
                id=info['match_number'],
                red1=strip_frc(info['alliances']['red']['team_keys'][0]),
                red2=strip_frc(info['alliances']['red']['team_keys'][1]),
                red3=strip_frc(info['alliances']['red']['team_keys'][2]),
                blue1=strip_frc(info['alliances']['blue']['team_keys'][0]),
                blue2=strip_frc(info['alliances']['blue']['team_keys'][1]),
                blue3=strip_frc(info['alliances']['blue']['team_keys'][2]),
            )
            db.session.add(match)
        else:
            # Match schedule should never change
            print('Skipping {match_number}, already exists.'.format(**info))
        if info['score_breakdown']:
            result = MatchResult.query.filter_by(id=info['match_number']).first()
            if result is None:
                print('Importing results for {match_number}...'.format(**info))
                result = MatchResult(id=info['match_number'])
            else:
                print('Updating result for {match_number}...'.format(**info))
            # We could import more stuff if we cared about it?
            result.red_score = info['score_breakdown']['red']['totalPoints']
            result.blue_score = info['score_breakdown']['blue']['totalPoints']
            result.red_rp = info['score_breakdown']['red']['rp']
            result.red_autoquest = info['score_breakdown']['red']['autoQuestRankingPoint']
            result.red_facetheboss = info['score_breakdown']['red']['faceTheBossRankingPoint']
            result.blue_rp = info['score_breakdown']['blue']['rp']
            result.blue_autoquest = info['score_breakdown']['blue']['autoQuestRankingPoint']
            result.blue_facetheboss = info['score_breakdown']['blue']['faceTheBossRankingPoint']
            # Game data is same for both alliances
            result.gamedata = info['score_breakdown']['blue']['tba_gameData']
            db.session.add(result)

            for alliance in ['red', 'blue']:
                for team_id in match.teams()[alliance]:
                    tba_report = TbaMatchReport.query.filter_by(match=info['match_number'], team=team_id).first()
                    if tba_report is None:
                        tba_report = TbaMatchReport(match=info['match_number'], team=team_id)
                    auto_key = 'autoRobot%s' % match.position(team_id)
                    tba_report.auton_cross = info['score_breakdown'][alliance][auto_key] == 'AutoRun'
                    tba_report.red_card = 'frc%s' % team_id in info['alliances'][alliance]['dq_team_keys']
                    db.session.add(tba_report)
    db.session.commit()


def import_rankings(code):
    print('Importing rankings')
    data = tba.request('event/%s/rankings' % code)
    if data['rankings'] is None:
        return
    for info in data['rankings']:
        team_id = strip_frc(info['team_key'])
        ranking = TeamRanking.query.filter_by(id=team_id).first()
        if ranking is None:
            ranking = TeamRanking(id=team_id)
        ranking.rank = info['rank']
        ranking.rp = info['extra_stats'][0]
        ranking.played = info['matches_played']
        ranking.sort_orders = json.dumps(info['sort_orders'])
        db.session.add(ranking)
    db.session.commit()


def generate_histograms():
    print('Generating histograms...')
    teams = models.Team.query.all()
    for team in teams:
        for mode, action in charts():
            fname = '%s_%s_%s.svg' % (team.id, action, mode)
            print(fname)
            action = action.replace('-', '_')
            summary = TeamSummary.from_team_id(team.id)
            svg = summary.histogram(action, mode)
            with open(os.path.join(app.config['HISTOGRAMS'], fname), 'wb') as f:
                f.write(svg)



def _sha1_file(fname):
    sha1 = hashlib.sha1()
    with open(fname, 'rb') as f:
        sha1.update(f.read())

    return sha1.hexdigest()


def backup():
    database = os.path.join(os.path.dirname(__file__), 'quickscout/%s.db' % app.config['EVENT_ID'])
    last_backups = sorted((backup
                          for backup
                          in os.listdir(os.path.join(os.path.dirname(__file__), 'backups'))
                          if backup.startswith(app.config['EVENT_ID'])), reverse=True)
    if last_backups:
        last_backup = last_backups[0]
        last_backup = os.path.join(os.path.dirname(__file__), 'backups', last_backup)
        if _sha1_file(last_backup) == _sha1_file(database):
            print('Skipping backup of %s since no changes have ocurred since last backup' % database)
            return
    print('Backing up %s' % database)
    dt = str(datetime.utcnow()).split('.')[0].replace('-', '').replace(' ', '').replace(':', '')
    dst = os.path.join(os.path.dirname(__file__), 'backups/%s-%s.db' % (app.config['EVENT_ID'], dt))
    shutil.copy2(database, dst)
    print('Copied to %s' % dst)


def thumbnail():
    if not os.path.exists('/usr/bin/convert'):
        return
    teams = Team.query.all()
    for team in teams:
        pics = team.pictures()
        for pic in pics:
            if pic['thumb']:
                # Already thumbnailed
                continue
            fname = os.path.basename(pic['full'])
            print('Creating thumbnail of %s' % fname)
            subprocess.check_call([
                '/usr/bin/convert', os.path.join(app.config['PICTURES'], fname),
                '-format', 'jpg',
                '-auto-orient',
                '-thumbnail', '400',
                os.path.join(app.config['THUMBS'], fname),
            ])


def main():
    code = app.config['EVENT_ID']
    print('Importing {}:'.format(code))
    import_team_list(code)
    import_matches(code)
    import_rankings(code)
    rebuild_match_reports()
    generate_histograms()
    backup()
    thumbnail()


if __name__ == '__main__':
    main()
