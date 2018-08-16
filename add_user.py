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

import sys

from quickscout import db
from quickscout.models import User


def main():
    to_create = sys.argv[1:]
    for name in to_create:
        print('Creating {}'.format(name))
        euser = User.query.filter_by(name=name).first()
        if euser is None:
            nuser = User(name=name)
            db.session.add(nuser)
        else:
            print('...but they already exist!')

    db.session.commit()


if __name__ == '__main__':
    main()
