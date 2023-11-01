# CISC/CMPE 204 Modelling Team 20: JezzBall Lifesaver

**JezzBall** is a puzzle arcade game in which the player must capture parts of a rectangular space by dividing it with horizontal and vertical lines. These lines act as barriers to the balls. The objective is to capture at least 75% of the space.​

If a ball collides with a line while it is currently being built, the player loses a life, and that end of the line breaks.​

Our project aims to predetermine whether or not the player will lose a life if they build a line. The model will figure this out based on the current cursor position and cursor orientation (vertical or horizontal), as well as with a list of the current ball positions and velocities. It will also need a map of which cells have been captured already.​

## Structure         \*\*\*(***UPDATE LATER***)\*\*\*

* `documents`: Contains folders for both of your draft and final submissions. README.md files are included in both.
* `run.py`: General wrapper script that you can choose to use or not. Only requirement is that you implement the one function inside of there for the auto-checks.
* `test.py`: Run this file to confirm that your submission has everything required. This essentially just means it will check for the right files and sufficient theory size.
