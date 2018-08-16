quickscout was designed to replace 604's paper scouting system. After the 2017
season, we had felt that we had pushed paper scouting to the limits. Paper
was holding us back, without many benefits. Our scouting meetings would often
be delayed by an hour while scouts finished transcribing data.

The main requirements were:
* Collects all data we would have on paper, and incorporates extra data
  like photographs
* Fully usable on a mobile phone, including a touch-friendly UI
* Intuitive for scouters
* Consumes as little bandwith as possible
* Uses as little battery as possible
* All collected data is fully accountable to individual scouters

Additional requests involved:

* Collect timing data
* Make data immediately usable by strategy/drive team
* Export data to spreadsheets/CSV

Technology
==========

* Debian as the base operating system
* flask for web server, for ease of bootstrapping as well as strong jinja2
  integration
* SQLAlchemy for ORM and database abstraction, and nice flask integration
* Bootstrap for building the UI with easy to use and touch-friendly
  components
* matplotlib/numpy for making charts

With the exception of SQLAlchemy, all of the above were chosen over other
alternatives mostly due to author's familiarity and preference.


Data collection
===============
Pit scouting is a basic HTML form with the different data points that we want
to collect. Existing data is preloaded in the form, so it's trivial to edit
and amend a pit scouting report.

Match scouting is a JavaScript-based, interactive page that scouters can
record each action as it happens, in real time. We record times for each
button press to estimate cycle times. All of the HTML is served when the page
is loaded, but each game mode (prematch, auton, teleop, endgame, review) is
hidden with CSS until its necessary. Data is only stored on the phone until it
is submitted at the very end of the match, allowing for an undo option, and
reducing bandwith.

Since there are many places to get cubes from this year, and just as many
places to score cubes, to get accurate cycle times, we had to record both
the location of where the cube came from, and where it was scored. For the
former, we split the field up into five zones, and recorded the starting zone.

The interface is designed to be as intuitive as possible by flipping button
locations if the blue alliance is on the right side, and transitioning a
"far/middle/close" starting position into a "left/middle/right", as seen from
the driver station.

To make it easier to use, the page should be compact enough to avoid scrolling
on most devices.
