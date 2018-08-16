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

from collections import defaultdict
import random
import statistics

from quickscout import db, models
from quickscout.summary import TeamSummary


def auton_cross_line(summaries, team_id):
    # Historical ability to cross the line multiplied by 80%
    prob_cross = int(summaries[team_id].avg_auton_cross[:-1]) / 100 * 0.8
    if not prob_cross:
        return False
    return random.random() < prob_cross


def main(debug_print=True):
    print('Running predictions...')
    results = dict((r.id, r) for r in models.MatchResult.query.all())
    matches = [m for m in models.Match.query.all() if m.id not in results]
    try:
        as_of = max(results)
    except ValueError:
        # No matches yet, data will be totally garbage
        as_of = 0
    last_prediction = models.RankingPrediction.query.first()
    if last_prediction is not None:
        if as_of == last_prediction.as_of:
            print('No new matches since last prediction run')
            return
    samples = 10000
    all_ranking_points = defaultdict(lambda: [0] * samples)
    all_rankings = defaultdict(lambda: [0] * samples)

    def prop(teams, prop_, mode='max'):
        if isinstance(prop_, list):
            return sum(prop(teams, i, mode) for i in prop_)
        return sum(summaries[team_id].__getattr__(mode + '_' + prop_) for team_id in teams)

    def face_the_boss(teams):
        prob_buddy_climb = max(int(summaries[team_id].avg_climb_carried[:-1]) / 100 for team_id in teams)
        if not prob_buddy_climb:
            return False
        return random.random() < prob_buddy_climb

    summaries = {}
    ranking_points = defaultdict(int)
    for match_id, result in results.items():
        match = models.Match.query.get(match_id)
        for team_id in match.teams()['red']:
            ranking_points[team_id] += result.red_rp
        for team_id in match.teams()['blue']:
            ranking_points[team_id] += result.blue_rp

    for team in models.Team.query.all():
        summaries[team.id] = TeamSummary.from_team_id(team.id)
    for i in range(samples):
        if i % 1000 == 0:
            print('Iteration %s...' % (i+1))
        for team_id, rp in ranking_points.items():
            all_ranking_points[team_id][i] = rp
        for match in matches:
            red_teams = match.teams()['red']
            blue_teams = match.teams()['blue']

            # TODO: We should reduce switch_same by 50% (and maybe double cross since it implies same)?
            red_auto_switch = 1 if \
                prop(red_teams, ['auton_switch_center', 'auton_switch_same', 'auton_switch_cross'], mode='avg') > 0.5\
                else 0
            blue_auto_switch = 1 if \
                prop(blue_teams, ['auton_switch_center', 'auton_switch_same', 'auton_switch_cross'], mode='avg') > 0.5\
                else 0
            red_auto_cross = sum(5 for team_id in red_teams if auton_cross_line(summaries, team_id))
            blue_auto_cross = sum(5 for team_id in blue_teams if auton_cross_line(summaries, team_id))
            red_auto_quest = red_auto_cross == 15 and red_auto_switch == 1
            blue_auto_quest = blue_auto_cross == 15 and blue_auto_switch == 1

            red_boss = face_the_boss(red_teams)
            blue_boss = face_the_boss(blue_teams)

            red_switch = 1 if prop(red_teams, 'teleop_switch') > prop(blue_teams, 'teleop_oswitch') else 0
            blue_switch = 1 if prop(blue_teams, 'teleop_switch') > prop(red_teams, 'teleop_oswitch') else 0
            scale_owner = 'red' if prop(red_teams, 'teleop_scale') > prop(blue_teams, 'teleop_scale') else 'blue'
            red_vault = prop(red_teams, 'teleop_vault', mode='avg')
            blue_vault = prop(blue_teams, 'teleop_vault', mode='avg')
            # Fix this
            red_scale = 1 if scale_owner == 'red' else 0
            blue_scale = 1 if scale_owner == 'blue' else 0

            red_p_score = (red_scale * 120) + (red_switch * 120) + (red_vault * 5)\
                + (red_auto_switch * 15) + red_auto_cross
            blue_p_score = (blue_scale * 120) + (blue_switch * 120) + (blue_vault * 5)\
                + (blue_auto_switch * 15) + blue_auto_cross
            # Ties? Oh well.
            predict_winner = 'red' if red_p_score > blue_p_score else 'blue'

            red_rp = int(red_auto_quest) + int(red_boss) + int(predict_winner == 'red')
            blue_rp = int(blue_auto_quest) + int(blue_boss) + int(predict_winner == 'blue')
            for team_id in red_teams:
                all_ranking_points[team_id][i] += red_rp
            for team_id in blue_teams:
                all_ranking_points[team_id][i] += blue_rp

        for rank, (team_id, _) in enumerate(sorted(all_ranking_points.items(), key=lambda x: x[1][i], reverse=True)):
            all_rankings[team_id][i] = rank + 1

    rankings = {}
    for team_id, team_rankings in all_rankings.items():
        ranking = models.RankingPrediction.query.filter_by(id=team_id).first()
        if ranking is None:
            ranking = models.RankingPrediction(id=team_id)
        ranking.avg = statistics.mean(team_rankings)
        ranking.min = min(team_rankings)
        ranking.median = statistics.median(team_rankings)
        ranking.max = max(team_rankings)
        ranking.avg_rp = statistics.mean(all_ranking_points[team_id])
        ranking.min_rp = min(all_ranking_points[team_id])
        ranking.max_rp = max(all_ranking_points[team_id])
        ranking.as_of = as_of
        if debug_print:
            rankings[team_id] = (
                ranking.avg,
                ranking.min,
                ranking.median,
                ranking.max,
                ranking.avg_rp,
                ranking.min_rp,
                ranking.max_rp,
            )
        db.session.add(ranking)
    db.session.commit()

    if debug_print:
        print('Team (avg/min/median/max/avg rp/min rp/max rp)')
        for team_id, breakdown in sorted(rankings.items(), key=lambda tb: tb[1][0]):
            print('{}: {}'.format(team_id, breakdown))


if __name__ == '__main__':
    main(debug_print=True)
