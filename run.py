from inputs import CURSOR_ORIENTATION, CURSOR_POSITION, BALLS, CANVAS

CANV_CELLS_WIDTH = len(CANVAS[0])
CANV_CELLS_HEIGHT = len(CANVAS)

MAX_BUILD_TIME = CANV_CELLS_WIDTH

DIRECTIONS = ("N", "E", "S", "W")

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
        return "The mouse has a horizontal orientation"


# V – This is true if the vertical orientation is selected
@proposition(E)
class Vertical(Hashable):
    def __init__(self):
        pass

    def __str__(self) -> str:
        return "The mouse has a vertical orientation"


# M(x, y) – This is true if cell (x, y) is where the cursor/mouse is (i.e. the starting position of where the line is created)
@proposition(E)
class CursorPosition(Hashable):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"The cursor is at ({self.x}, {self.y})"

# BC(x, y, t) - This is true if a cell (x, y) is currently being built at time t (and you'll lose a life if a ball collides with it)
@proposition(E)
class BuildingCell(Hashable):
    def __init__(self, x, y, time):
        self.x = x
        self.y = y
        self.time = time

    def __str__(self) -> str:
        return f"The cell at ({self.x}, {self.y}) is currently being built at {self.time}"


# C(x, y, t) – This is true if cell (x, y) is captured (i.e. the black cells) at time t
@proposition(E)
class CapturedCell(Hashable):
    def __init__(self, x, y, time):
        self.x = x
        self.y = y
        self.time = time

    def __str__(self) -> str:
        return f"The cell ({self.x}, {self.y}) is captured at time {self.time}"


# P(i, x, y, t) – This is true if ball i's position is at cell (x, y) at time t
@proposition(E)
class BallPosition(Hashable):
    def __init__(self, ball_id, x, y, time):
        self.ball_id = ball_id
        self.x = x
        self.y = y
        self.time = time

    def __str__(self) -> str:
        return f"Ball {self.ball_id} is at ({self.x}, {self.y}) at time {self.time}"


#Vx(i, t) – This is true if ball i is currently moving in the positive X direction at time t
@proposition(E)
class BallVelocityX(Hashable):
    def __init__(self, ball_id, time):
        self.ball_id = ball_id
        self.time = time

    def __str__(self) -> str:
        return f"Ball {self.ball_id} is moving in the positive X direction at time {self.time}"


#Vy(i, t) – This is true if ball i is currently moving in the positive Y direction at time t
@proposition(E)
class BallVelocityY(Hashable):
    def __init__(self, ball_id, time):
        self.ball_id = ball_id
        self.time = time

    def __str__(self) -> str:
        return f"Ball {self.ball_id} is moving in the positive Y direction at time {self.time}"


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


# BF(D, t) - This is true if the builder of direction D is finished building at time t 
@proposition(E)
class BuilderFinished(Hashable):
    def __init__(self, direction, time):
        self.direction = direction
        self.time = time

    def __str__(self) -> str:
        return f"The {self.direction} builder is finished building at time {self.time}"

# L – This is true if the player will lose a life from creating a line
@proposition(E)
class LoseLife(Hashable):
    def __init__(self):
        pass

    def __str__(self) -> str:
        return "The player will lose a life from creating a line"


########## PROPOSITION INSTANCES ##########
horizontal_prop = Horizontal()
vertical_prop = Vertical()

cursor_pos_props = []
for y in range(CANV_CELLS_HEIGHT):
    for x in range(CANV_CELLS_WIDTH):
        cursor_pos_props.append(CursorPosition(x, y))

captured_cell_props = []
building_cell_props = []
for t in range(MAX_BUILD_TIME):
    for y in range(CANV_CELLS_HEIGHT):
        for x in range(CANV_CELLS_WIDTH):
            captured_cell_props.append(CapturedCell(x, y, t))
            building_cell_props.append(BuildingCell(x, y, t))

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
for d in DIRECTIONS:
    for t in range(MAX_BUILD_TIME):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                builder_props.append(Builder(d, x, y, t))

lose_prop = LoseLife()


########## CONSTRAINTS ##########
def theory():
    # initialize cursor orientation
    if CURSOR_ORIENTATION == "H":
        E.add_constraint(Horizontal())
    else:
        E.add_constraint(Vertical())

    # The cursor's orientation can only be either vertical or horizontal, but not both
    E.add_constraint((Horizontal() & ~Vertical()) | (~Horizontal() & Vertical()))

    # intialize builders
    x, y = CURSOR_POSITION
    E.add_constraint(Horizontal() >> (Builder("E", x, y, 0) & Builder("W", x, y, 0)))
    E.add_constraint(Vertical() >> (Builder("N", x, y, 0) & Builder("S", x, y, 0)))
    
    # initialize balls and ball velocities
    for i, (x, y, x_vel, y_vel) in enumerate(BALLS):
        E.add_constraint(BallPosition(i, x, y, 0))

        if x_vel > 0:
            E.add_constraint(BallVelocityX(i, 0))
        else:
            E.add_constraint(~BallVelocityX(i, 0))

        if y_vel > 0:
            E.add_constraint(BallVelocityY(i, 0))
        else:
            E.add_constraint(~BallVelocityY(i, 0))

    # initialize captured cells
    for y in range(len(CANVAS)):
        for x in range(len(CANVAS[0])):
            if CANVAS[y][x] == 1:
                E.add_constraint(CapturedCell(x, y, 0))
            else:
                E.add_constraint(~CapturedCell(x, y, 0))
    
    # A captured cell stays captured
    for t in range(MAX_BUILD_TIME-1):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                E.add_constraint(CapturedCell(x, y, t) >> CapturedCell(x, y, t+1))

    # A builder creates a building cell and moves to the next cell after a step in time
    for t in range(MAX_BUILD_TIME):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                if y > 0:
                    E.add_constraint(Builder("N", x, y, t) >> Builder("N", x, y-1, t))

                if y < CANV_CELLS_HEIGHT - 1:
                    E.add_constraint(Builder("S", x, y, t) >> Builder("S", x, y+1, t))

                if x > 0:
                    E.add_constraint(Builder("W", x, y, t) >> Builder("W", x, x-1, t))

                if x < CANV_CELLS_WIDTH - 1:
                    E.add_constraint(Builder("E", x, y, t) >> Builder("E", x+1, y, t))

                for d in DIRECTIONS:
                    E.add_constraint(Builder(d, x, y, t) >> BuildingCell(x, y, t))

    # A building cell stays until the builders are done
    for t in range(MAX_BUILD_TIME-1):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                ...

    # The position of a ball cannot coincide with the position of a captured cell (BUGS UNTIL LOGIC IS IMPLEMENTED)
    # for i in range(len(BALLS)):
    #     for t in range(MAX_BUILD_TIME):
    #         for y in range(CANV_CELLS_HEIGHT):
    #             for x in range(CANV_CELLS_WIDTH):
    #                 E.add_constraint(BallPosition(i, x, y, t) >> ~CapturedCell(x, y, t))
        
    # There can't be both a horizontal builder and vertical builder
    for t in range(MAX_BUILD_TIME):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                E.add_constraint((Builder("N", x, y, t) | Builder("S", x, y, t)) >> ~(Builder("E", x, y, t) | Builder("W", x, y, t)))
                E.add_constraint((Builder("E", x, y, t) | Builder("W", x, y, t)) >> ~(Builder("N", x, y, t) | Builder("S", x, y, t)))


    # TEMPORARY:
    E.add_constraint(LoseLife())

    return E

if __name__ == "__main__":
    T = theory()
    # Don't compile until you're finished adding all your constraints!
    T = T.compile()
    # After compilation (and only after), you can check some of the properties of your model:
    print("\nSatisfiable: %s" % T.satisfiable())
    # print("# Solutions: %d" % count_solutions(T))
    # print("   Solution: %s" % T.solve())
    
    sol = T.solve()
    # print(sol)
    if sol["The player will lose a life from creating a line"]:
        print("You will lose a life")
    else:
        print("You won't lose a life")