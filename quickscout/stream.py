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
from itertools import zip_longest
import json

from . import utils
from .models import StartPosition


class EventStream:
    def __init__(self, position, result=None):
        self.events = defaultdict(list)
        self.position = position
        self.result = result

    def add_event(self, event):
        self.events[event.action].append(event)

    def update_report(self, report):
        # Doesn't handle drive_comments and comments
        report.died = self.died
        report.noshow = self.noshow
        report.start_cube = self.start_cube
        report.auton_switch_center = self.auton_switch_center
        report.auton_switch_same = self.auton_switch_same
        report.auton_switch_cross = self.auton_switch_cross
        report.auton_scale = self.auton_scale
        report.auton_scale_cross = self.auton_scale_cross
        report.auton_drop = self.auton_drop
        report.teleop_switch = self.teleop_switch
        report.teleop_scale = self.teleop_scale
        report.teleop_oswitch = self.teleop_oswitch
        report.teleop_vault = self.teleop_vault
        report.teleop_drop = self.teleop_drop
        report.teleop_knockoff = self.teleop_knockoff
        report.end_platform = self.end_platform
        report.climb_success = self.climb_success
        report.climb_failed = self.climb_failed
        report.climb_time = self.climb_time
        report.climb_carried = self.climb_carried
        report.start_position = self.start_position
        report.time_scoring = json.dumps(self.time_scoring)

    @property
    def died(self):
        return 'died' in self.events

    @property
    def noshow(self):
        return 'noshow' in self.events

    @property
    def start_position(self):
        if 'start-far' in self.events:
            pos = 'far'
        elif 'start-middle' in self.events:
            pos = 'middle'
        else:  # start-close
            pos = 'close'
        # Translate start location (far/middle/close) to l/m/r
        position_map = {
            'middle': StartPosition.middle
        }
        if utils.is_on_left(self.position):
            # Team is on left side
            position_map['far'] = StartPosition.left
            position_map['close'] = StartPosition.right
        else:
            # Team is on right side
            position_map['far'] = StartPosition.right
            position_map['close'] = StartPosition.left

        return position_map.get(pos)

    @property
    def start_cube(self):
        return 'start-with-cube' in self.events

    def _filter_mode(self, gen, mode):
        for i in gen:
            if i.mode == mode:
                yield i

    def is_crossing_scale_in_auton(self):
        if self.result is None:
            # If we don't have the match result, we
            # don't know if it's crossing yet
            return False
        scale = {
            'L': StartPosition.left,
            'R': StartPosition.right
        }[self.result.gamedata[1]]
        return self.start_position != scale

    @property
    def _switch_auton_mode(self):
        if self.start_position == StartPosition.middle:
            return 'center'
        if self.result is None:
            # If we don't have the match result, we
            # don't know if it's crossing yet
            return 'center'
        switch = {
            'L': StartPosition.left,
            'R': StartPosition.right
        }[self.result.gamedata[0]]
        if switch == self.start_position:
            return 'same'
        else:
            return 'cross'

    @property
    def auton_switch_center(self):
        if self._switch_auton_mode != 'center':
            return 0
        return len(list(self._filter_mode(self.events['switch'], 'auton')))

    @property
    def auton_switch_same(self):
        if self._switch_auton_mode != 'same':
            return 0
        return len(list(self._filter_mode(self.events['switch'], 'auton')))

    @property
    def auton_switch_cross(self):
        if self._switch_auton_mode != 'cross':
            return 0
        return len(list(self._filter_mode(self.events['switch'], 'auton')))

    @property
    def auton_scale_cross(self):
        if not self.is_crossing_scale_in_auton():
            return 0
        return len(list(self._filter_mode(self.events['scale'], 'auton')))

    @property
    def auton_scale(self):
        if self.is_crossing_scale_in_auton():
            return 0
        return len(list(self._filter_mode(self.events['scale'], 'auton')))

    @property
    def auton_drop(self):
        return len(list(self._filter_mode(self.events['drop'], 'auton')))

    @property
    def teleop_switch(self):
        return len(list(self._filter_mode(self.events['switch'], 'teleop')))

    @property
    def teleop_scale(self):
        return len(list(self._filter_mode(self.events['scale'], 'teleop')))

    @property
    def teleop_oswitch(self):
        return len(list(self._filter_mode(self.events['oswitch'], 'teleop')))

    @property
    def teleop_vault(self):
        return len(list(self._filter_mode(self.events['vault'], 'teleop')))

    @property
    def teleop_drop(self):
        return len(list(self._filter_mode(self.events['drop'], 'teleop')))

    @property
    def teleop_knockoff(self):
        return len(list(self._filter_mode(self.events['knockoff'], 'teleop')))

    @property
    def end_platform(self):
        return 'endplatform' in self.events

    @property
    def climb_success(self):
        # If they climb success and then fall or something, make sure they
        # didn't have a failure too.
        return 'climbend' in self.events and 'climbfail' not in self.events

    @property
    def climb_failed(self):
        return 'climbfail' in self.events

    @property
    def climb_time(self):
        if not self.climb_success:
            return None

        if 'climbend' not in self.events:
            return 0
        if 'endplatform' not in self.events:
            return 0

        return self.events['climbend'][-1].time - self.events['endplatform'][-1].time

    @property
    def climb_carried(self):
        if 'climbcarry1' in self.events:
            return 1
        elif 'climbcarry2' in self.events:
            return 2
        else:  # climbcarry0
            return 0

    @property
    def time_scoring(self):
        timeline = []
        scores = []
        scoring_events = ('scale', 'switch', 'oswitch', 'vault', 'drop')
        for event, events in self.events.items():
            if event.startswith('cube-grab'):
                timeline.extend(events)
            elif event in scoring_events:
                timeline.extend(events)

        # Only use teleop data
        timeline.sort(key=lambda x: x.time)
        mode_timeline = {
            'auton': [],
            'teleop': [],
        }
        for event in timeline:
            mode_timeline[event.mode].append(event)
        for mode in ['auton', 'teleop']:
            # If the first action is scoring then ignore it since the cube is from a previous mode
            if mode_timeline[mode] and not mode_timeline[mode][0].action.startswith('cube-grab'):
                mode_timeline[mode].pop(0)
            # The sequence should be cube-grab / scoring / cube-grab / scoring / etc.
            for grab, score in grouper(mode_timeline[mode], 2):
                if score is None:
                    # They grabbed a cube and never did anything
                    # with it, maybe the match ended?
                    continue
                if mode == 'auton' and score.action == 'scale' and self.is_crossing_scale_in_auton():
                    action = 'scale_cross'
                elif mode == 'auton' and score.action == 'switch':
                    action = 'switch_' + self._switch_auton_mode
                else:
                    action = score.action
                # We use an ordered dict to make database serialization reproducible
                data = OrderedDict((
                    ('zone', grab.action[-1]),
                    ('score', action),
                    ('time', score.time - grab.time),
                    ('mode', score.mode),
                ))
                int(data['zone'])
                scores.append(data)

        return scores


# Via <https://docs.python.org/3/library/itertools.html#itertools-recipes>
def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)
