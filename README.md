quickscout
==========

== Setup ==
```
$ git clone ...
$ virtualenv -p python3 venv
$ source venv/bin/activate
$ pip install -r requirements.txt
$ pip install -e .
$ ./init_db.py
$ ./cron.py
$ FLASK_APP=quickscout FLASK_DEBUG=true flask run --host 0.0.0.0
```

The final `--host` command makes it so flask will listen to requests
besides just localhost. And debug mode enables automatic reloading.

If you install imagemagick, then thumbnails can be created for photos.

== Deploying ==
```
$ ssh root@scouting.604robotics.com
# # Pull new code, restart the service, and follow logs
# ./pull.sh
# ^C
```

Viewing logs: `journalctl -u quickscout` and add `-f` to tail and follow.

Messing with things manually:
```
# su scouting
$ cd ~/quickscout
```
