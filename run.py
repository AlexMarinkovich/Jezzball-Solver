CANV_CELLS_WIDTH = 27
CANV_CELLS_HEIGHT = 19

MAX_BUILD_TIME = CANV_CELLS_WIDTH

BALLS = [(0, 0, 1, 1), 
         (5, 5, -1, 1), 
         (10, 10, 1, 1),
         (15, 15, 1, -1)]  # (x, y, x_vel, y_vel), subject to change

DIRECTIONS = ("north", "east", "south", "west")

from bauhaus import Encoding, proposition, constraint
from bauhaus.utils import count_solutions, likelihood

# These two lines make sure a faster SAT solver is used.
from nnf import config

config.sat_backend = "kissat"

# Encoding that will store all of your constraints
E = Encoding()


class Hashable:
    def __hash__(self):
        return hash(str(self))

    def __eq__(self, __value: object) -> bool:
        return hash(self) == hash(__value)

    def __repr__(self):
        return str(self)


########## PROPOSITION CLASSES ##########

# H – This is true if the horizontal orientation is selected
@proposition(E)
class Horizontal(Hashable):
    def __init__(self):
        pass

    def __str__(self) -> str:
        return "The mouse has a horizontal orientation."


# V – This is true if the vertical orientation is selected
@proposition(E)
class Vertical(Hashable):
    def __init__(self):
        pass

    def __str__(self) -> str:
        return "The mouse has a vertical orientation."


# M(x, y) – This is true if cell (x, y) is where the cursor/mouse is (i.e. the starting position of where the line is created)
@proposition(E)
class CursorPosition(Hashable):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"The cursor is at ({self.x}, {self.y})."


# C(x, y, t) – This is true if cell (x, y) is captured (i.e. the black cells) at time t
@proposition(E)
class CapturedCell(Hashable):
    def __init__(self, x, y, time):
        self.x = x
        self.y = y
        self.time = time

    def __str__(self) -> str:
        return f"The cell ({self.x}, {self.y}) is captured at time {self.time}."


# P(i, x, y, t) – This is true if ball i's position is at cell (x, y) at time t
@proposition(E)
class BallPosition(Hashable):
    def __init__(self, ball_id, x, y, time):
        self.ball_id = ball_id
        self.x = x
        self.y = y
        self.time = time

    def __str__(self) -> str:
        return f"Ball {self.ball_id} is at ({self.x}, {self.y}) at time {self.time}."


#Vx(i, t) – This is true if ball i is currently moving in the positive X direction at time t
@proposition(E)
class BallVelocityX(Hashable):
    def __init__(self, ball_id, time):
        self.ball_id = ball_id
        self.time = time

    def __str__(self) -> str:
        return f"Ball {self.ball_id} is moving in the positive X direction at time {self.time}."


#Vy(i, t) – This is true if ball i is currently moving in the positive Y direction at time t
@proposition(E)
class BallVelocityY(Hashable):
    def __init__(self, ball_id, time):
        self.ball_id = ball_id
        self.time = time

    def __str__(self) -> str:
        return f"Ball {self.ball_id} is moving in the positive Y direction at time {self.time}."


# B(D, x, y, t) – This is true if the builder of direction D (can be N, E, S, W) is at cell (x, y) at time t
@proposition(E)
class Builder(Hashable):
    def __init__(self, direction, x, y, time):
        self.direction = direction
        self.x = x
        self.y = y
        self.time = time

    def __str__(self) -> str:
        return f"The {self.direction} builder is at cell ({self.x}, {self.y}) at time {self.time}"


# L – This is true if the player will lose a life from creating a line
@proposition(E)
class LoseLife(Hashable):
    def __init__(self):
        pass

    def __str__(self) -> str:
        return "The player will lose a life from creating a line."


########## PROPOSITION INSTANCES ##########
horizontal_prop = Horizontal()
vertical_prop = Vertical()

cursor_pos_props = []
for y in range(CANV_CELLS_HEIGHT):
    for x in range(CANV_CELLS_WIDTH):
        cursor_pos_props.append(CursorPosition(x, y))

captured_cell_props = []
for t in range(MAX_BUILD_TIME):
    for y in range(CANV_CELLS_HEIGHT):
        for x in range(CANV_CELLS_WIDTH):
            captured_cell_props.append(CapturedCell(x, y, t))

ball_pos_props = []
ball_vel_x_props = []
ball_vel_y_props = []
for i in range(len(BALLS)):
    for t in range(MAX_BUILD_TIME):
        ball_vel_x_props.append(BallVelocityX(i, t))
        ball_vel_y_props.append(BallVelocityY(i, t))

        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                ball_pos_props.append(BallPosition(i, x, y, t))

builder_props = []
for D in DIRECTIONS:
    for t in range(MAX_BUILD_TIME):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                builder_props.append(Builder(D, x, y, t))

lose_prop = LoseLife()


########## CONSTRAINTS ##########
def theory():
    # The cursor's orientation can only be either vertical or horizontal, but not both
    E.add_constraint((Horizontal() & ~Vertical()) | (~Horizontal() & Vertical()))

    # The position of a ball cannot coincide with the position of a captured cell
    for i in range(len(BALLS)):
        for t in range(MAX_BUILD_TIME):
            for y in range(CANV_CELLS_HEIGHT):
                for x in range(CANV_CELLS_WIDTH):
                    E.add_constraint(BallPosition(i, x, y, t) >> ~CapturedCell(x, y, t))
        
    # There can't be both a horizontal builder and vertical builder
    for t in range(MAX_BUILD_TIME):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                E.add_constraint((Builder("north", x, y, t) | Builder("south", x, y, t)) >> ~(Builder("east", x, y, t) | Builder("west", x, y, t)))
                E.add_constraint((Builder("east", x, y, t) | Builder("west", x, y, t)) >> ~(Builder("north", x, y, t) | Builder("south", x, y, t)))

    return E

if __name__ == "__main__":
    T = theory()
    # Don't compile until you're finished adding all your constraints!
    T = T.compile()
    # After compilation (and only after), you can check some of the properties
    # of your model:
    print("\nSatisfiable: %s" % T.satisfiable())
    print("# Solutions: %d" % count_solutions(T))
    print("   Solution: %s" % T.solve())
    
    sol = T.solve()
    print(sol)