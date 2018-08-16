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
from io import BytesIO
import json
import matplotlib; matplotlib.use('svg')  # noqa
import matplotlib.pyplot as plot
import numpy
import statistics

from . import models


class TeamSummary:
    data = [
        'auton_cross',
        'auton_switch_center',
        'auton_switch_same',
        'auton_switch_cross',
        'auton_scale',
        'auton_scale_cross',
        'auton_drop',
        'teleop_switch',
        'teleop_scale',
        'teleop_oswitch',
        'teleop_drop',
        'teleop_vault',
        'teleop_knockoff',
        'end_platform',
        'climb_success',
        'climb_time',
        'climb_failed',
        'climb_carried',
    ]
    bool_data = ['auton_cross', 'climb_success', 'climb_failed', 'end_platform', 'climb_carried']
    time_data = ['climb_time']

    tba_data = ['auton_cross']

    @classmethod
    def from_team_id(cls, team_id, before=9999):
        return cls(team_id,
                   models.MatchReport.query.filter(
                       models.MatchReport.team == team_id,
                       models.MatchReport.match < before
                   ).all(),
                   models.TbaMatchReport.query.filter(
                       models.TbaMatchReport.team == team_id,
                       models.TbaMatchReport.match < before
                   ).all(),
                   models.PitReport.query.filter_by(team=team_id).first(),
                   models.SuperScoutReport.query.filter_by(team=team_id).all())

    def __init__(self, team_id, reports: list, tba_reports: list, pit, superscouts: list):
        self.team_id = team_id
        self.reports = reports
        self.tba_reports = dict((r.match, r) for r in tba_reports)
        self.pit = pit
        self.superscouts = superscouts
        self._cache = {}

    def __getattr__(self, item):
        if not item.startswith(('avg_', 'min_', 'max_')):
            raise AttributeError
        if item in self._cache:
            return self._cache[item]

        type_, field = item.split('_', 1)
        values = []
        for report in self.reports:
            if field in self.tba_data:
                tba_report = self.tba_reports.get(report.match)
                if tba_report is None:
                    # Haven't imported TBA data yet?
                    continue
                val = tba_report.__getattribute__(field)
            else:
                val = report.__getattribute__(field)
            if field == 'climb_carried':
                # Normalize to boolean, since we just want to know if they
                # can buddy climb
                val = bool(val)
            if val is not None:
                values.append(int(val))

        if not values:
            if field in self.bool_data:
                val = '0%'
            elif field in self.bool_data:
                val = '10000s'
            else:
                val = 0
            self._cache[item] = val
            return val
        if type_ == 'avg':
            val = round(statistics.mean(values), 2)
        elif type_ == 'max':
            val = max(values)
        else:  # min
            val = min(values)

        if field in self.bool_data:
            val = str(round(val * 100)) + '%'
        elif field in self.time_data:
            val = str(round(val/1000, 2)) + 's'

        self._cache[item] = val
        return val

    @property
    def drivebase(self):
        return self.pit.drive.value if self.pit else '—'

    @property
    def speed(self):
        return self.pit.speed if self.pit else '—'

    @property
    def red_card(self):
        return ', '.join(sorted('Q%s' % r.match for r in self.tba_reports.values() if r.red_card))

    @property
    def died(self):
        return ', '.join('Q%s' % r.match for r in self.reports if r.died)

    @property
    def noshow(self):
        return ', '.join('Q%s' % r.match for r in self.reports if r.noshow)

    @property
    def drive_comments(self):
        return [{'user': r.user, 'text': r.drive_comments, 'match': r.match}
                for r in self.reports
                if r.drive_comments]

    @property
    def comments(self):
        return [{'user': r.user, 'text': r.comments, 'match': r.match}
                for r in self.reports
                if r.comments]

    @property
    def superscout_comments(self):
        return [{'user': r.user, 'text': r.info, 'match': r.match}
                for r in self.superscouts
                if r.info]

    def timedata(self, mode='teleop'):
        # Split by action, then by cubezone
        data = defaultdict(lambda: defaultdict(list))
        for report in self.reports:
            score_data = json.loads(report.time_scoring)
            for score in score_data:
                if score['mode'] != mode:
                    continue
                data[score['score']][int(score['zone'])].append(score['time'])

        return data

    @property
    def average_time_teleop_scale(self):
        data = self.timedata()['scale']
        merged = []
        merged.extend(data[2])
        merged.extend(data[4])
        if not merged:
            return ('-', 0)
        return (round(statistics.mean(merged)/1000, 2), len(merged))

    @property
    def average_time_teleop_switch(self):
        data = self.timedata()['switch']
        merged = []
        merged.extend(data[1])
        merged.extend(data[2])
        if not merged:
            return ('-', 0)
        return (round(statistics.mean(merged) / 1000, 2), len(merged))

    @property
    def average_time_teleop_oswitch(self):
        data = self.timedata()['oswitch']
        merged = []
        merged.extend(data[4])
        merged.extend(data[5])
        if not merged:
            return ('-', 0)
        return (round(statistics.mean(merged) / 1000, 2), len(merged))

    @property
    def average_time_teleop_vault(self):
        data = self.timedata()['vault']
        merged = []
        merged.extend(data[1])
        if not merged:
            return ('-', 0)
        return (round(statistics.mean(merged) / 1000, 2), len(merged))

    def histogram(self, action, mode='teleop'):
        data = self.timedata(mode=mode)[action]
        # Convert into normal seconds
        zones = [1, 2, 3, 4, 5]
        colors = {
            1: 'tab:blue',
            2: 'tab:orange',
            3: 'tab:green',
            4: 'tab:red',
            5: 'tab:purple',
        }
        fig, ax = plot.subplots()
        bar_width = 1
        x = numpy.arange(0, 31, step=5)
        has_data = False
        for multiplier, zone in enumerate(zones):
            if not data[zone]:
                continue
            has_data = True
            second_data = map(lambda x: x/1000, data[zone])
            bucketed = _bucket(second_data)
            y = []
            for k in x:
                y.append(bucketed[k])
            ax.bar(x + (multiplier*bar_width), y, bar_width, label='Zone %s' % zone, align='edge', color=colors[zone])

        if has_data:
            ax.legend()
        ax.set_xticks(x+(bar_width*2.5))
        labels = list(x)
        labels[len(x)-1] = '30+'
        ax.set_xticklabels(labels)
        plot.title('%s: %s in %s' % (self.team_id, action, mode))
        plot.ylabel('Occurrences')
        plot.xlabel('Time')
        f = BytesIO()
        plot.savefig(f, format='svg')
        plot.clf()
        plot.cla()
        plot.close()
        return f.getvalue()


def _bucket(data, size=5, max_=30):
    bucketed = defaultdict(int)
    for item in data:
        rounded = int(size*round(item/size))
        if rounded > max_:
            rounded = max_
        bucketed[rounded] += 1

    return bucketed
