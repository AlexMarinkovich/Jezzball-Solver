# CISC/CMPE 204 Modelling Team 20: JezzBall Lifesaver

**JezzBall** is a puzzle arcade game in which the player must capture parts of a rectangular space by dividing it with horizontal and vertical lines. These lines act as barriers to the balls. The objective is to capture at least 75% of the space.​

If a ball collides with a line while it is currently being built, the player loses a life, and that end of the line breaks.​

Our project aims to predetermine whether or not the player will lose a life if they build a line. The model will figure this out based on the current cursor position and cursor orientation (vertical or horizontal), as well as with a list of the current ball positions and velocities. It will also need a map of which cells have been captured already.​

## Structure    

* `documents`: Contains the folders for our draft and final submissions.
* `run.py`: General wrapper script.
* `test.py`: Run this file to confirm that the submission has everything required.
* `inputs.py`: Contains the user's inputs to the model.
