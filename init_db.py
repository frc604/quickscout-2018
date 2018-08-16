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

from quickscout import app, db
from quickscout import models


def main():
    db.create_all()
    for username in app.config['ADMINS'] + app.config['SCOUTERS']:
        if models.User.query.filter_by(name=username).first() is None:
            print('Adding %s\'s user' % username)
            db.session.add(models.User(
                name=username
            ))
    if models.ScouterPosition.query.first() is None:
        print('Initializing scouterpositions table')
        db.session.add(models.ScouterPosition())
    db.session.commit()
    print('Initialized database.')


if __name__ == '__main__':
    main()
