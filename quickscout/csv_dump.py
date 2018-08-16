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

import csv
from io import StringIO

from .models import Team
from .summary import TeamSummary


def dump():
    teams = Team.query.all()
    f = StringIO()
    attrs = []
    for attr in TeamSummary.data:
        attrs.append('avg_' + attr)
        attrs.append('min_' + attr)
        attrs.append('max_' + attr)
    fieldnames = ['team'] + attrs
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()

    for team in teams:
        summary = TeamSummary.from_team_id(team.id)
        data = {x: summary.__getattr__(x) for x in attrs}
        data['team'] = team.id
        writer.writerow(data)

    return f.getvalue()
