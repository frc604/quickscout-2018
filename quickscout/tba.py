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

import json
import requests

from . import app, db
from .models import TbaCache

session = requests.Session()


def request(path):
    cache = TbaCache.query.filter_by(request=path).first()
    if cache is not None:
        headers = {'if-modified-since': cache.modified}
    else:
        headers = {}
    url = 'https://www.thebluealliance.com/api/v3/' + path
    r = session.get(url, params={'X-TBA-Auth-Key': app.config['TBA-Auth-Key']}, headers=headers)
    r.raise_for_status()
    if r.status_code == 304:
        return json.loads(cache.response)
    # Save the last-modified value for next time
    if cache is None:
        cache = TbaCache(request=path)
    cache.modified = r.headers['Last-Modified']
    cache.response = json.dumps(r.json())
    db.session.add(cache)
    db.session.commit()
    return r.json()
