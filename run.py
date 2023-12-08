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

@proposition(E)
class Horizontal(Hashable):
    '''
    H - This is true if the horizontal orientation is selected
    '''
    def __init__(self):
        pass

    def __str__(self) -> str:
        return "The mouse has a horizontal orientation"


@proposition(E)
class Vertical(Hashable):
    '''
    V - This is true if the vertical orientation is selected
    '''
    def __init__(self):
        pass

    def __str__(self) -> str:
        return "The mouse has a vertical orientation"


@proposition(E)
class CursorPosition(Hashable):
    '''
    M(x, y) - This is true if cell (x, y) is where the cursor/mouse is
    (i.e. the starting position of where the line is created)
    '''
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self) -> str:
        return f"The cursor is at ({self.x}, {self.y})"


@proposition(E)
class BuildingCell(Hashable):
    '''
    BC(D, x, y, t) - This is true if cell (x, y) is currently being built by the 
    builder of direction D at time t (and you'll lose a life if a ball collides with it)
    '''
    def __init__(self, direction, x, y, time):
        self.direction = direction
        self.x = x
        self.y = y
        self.time = time

    def __str__(self) -> str:
        return f"The cell at ({self.x}, {self.y}) is currently being built at time {self.time}"


@proposition(E)
class CapturedCell(Hashable):
    '''
    C(x, y, t) - This is true if cell (x, y) is captured (i.e. the black cells) at time t
    '''
    def __init__(self, x, y, time):
        self.x = x
        self.y = y
        self.time = time

    def __str__(self) -> str:
        return f"The cell ({self.x}, {self.y}) is captured at time {self.time}"


@proposition(E)
class BallPosition(Hashable):
    '''
    P(i, x, y, t) - This is true if ball i's position is at cell (x, y) at time t
    '''
    def __init__(self, ball_id, x, y, time):
        self.ball_id = ball_id
        self.x = x
        self.y = y
        self.time = time

    def __str__(self) -> str:
        return f"Ball {self.ball_id} is at ({self.x}, {self.y}) at time {self.time}"


@proposition(E)
class BallVelocityX(Hashable):
    '''
    Vx(i, t) - This is true if ball i is currently moving in the positive X direction at time t
    '''
    def __init__(self, ball_id, time):
        self.ball_id = ball_id
        self.time = time

    def __str__(self) -> str:
        return f"Ball {self.ball_id} is moving in the positive X direction at time {self.time}"


@proposition(E)
class BallVelocityY(Hashable):
    '''
    Vy(i, t) - This is true if ball i is currently moving in the positive Y direction at time t
    '''
    def __init__(self, ball_id, time):
        self.ball_id = ball_id
        self.time = time

    def __str__(self) -> str:
        return f"Ball {self.ball_id} is moving in the positive Y direction at time {self.time}"


@proposition(E)
class Builder(Hashable):
    '''
    B(D, x, y, t) - This is true if the builder of direction D (can be N, E, S, W) is at cell (x, y) at time t
    '''
    def __init__(self, direction, x, y, time):
        self.direction = direction
        self.x = x
        self.y = y
        self.time = time

    def __str__(self) -> str:
        return f"The {self.direction} builder is at cell ({self.x}, {self.y}) at time {self.time}"


@proposition(E)
class BuilderFinished(Hashable):
    '''
    BF(D, t) - This is true if the builder of direction D is finished building at time t 
    '''
    def __init__(self, direction, time):
        self.direction = direction
        self.time = time

    def __str__(self) -> str:
        return f"The {self.direction} builder is finished building at time {self.time}"


@proposition(E)
class LoseLife(Hashable):
    '''
    L - This is true if the player has lost a life from creating a line at time t or before
    '''
    def __init__(self, time):
        self.time = time

    def __str__(self) -> str:
        return f"The player will have lost a life from creating a line by time {self.time}"


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
            for d in DIRECTIONS:
                building_cell_props.append(BuildingCell(d, x, y, t))

ball_pos_props = []
ball_vel_x_props = []
ball_vel_y_props = []
for b in range(len(BALLS)):
    for t in range(MAX_BUILD_TIME):
        ball_vel_x_props.append(BallVelocityX(b, t))
        ball_vel_y_props.append(BallVelocityY(b, t))

        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                ball_pos_props.append(BallPosition(b, x, y, t))

builder_props = []
for d in DIRECTIONS:
    for t in range(MAX_BUILD_TIME):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                builder_props.append(Builder(d, x, y, t))

lose_props = []
for t in range(MAX_BUILD_TIME):
    lose_props.append(LoseLife(t))


########## EXPLORING THE MODEL ##########

# The position of a ball cannot coincide with the position of a captured cell
def ensure_no_overlap():
        for i in range(len(BALLS)):
            for t in range(MAX_BUILD_TIME):
                for y in range(CANV_CELLS_HEIGHT):
                    for x in range(CANV_CELLS_WIDTH):
                        E.add_constraint(BallPosition(i, x, y, t) >> ~CapturedCell(x, y, t))

# Balls move based on their velocities after a step in time to next cell if that cell isn't captured
def ball_movement():
    for b in range(len(BALLS)):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                for t in range(MAX_BUILD_TIME):
                    E.add_constraint(BallPosition(b, x, y, t) & BallVelocityX(b, t) & BallVelocityY(b, t) & ~CapturedCell(x+1, y+1, t) >> BallPosition(b, x+1, y+1, t+1))
                    E.add_constraint(BallPosition(b, x, y, t) & ~BallVelocityX(b, t) & BallVelocityY(b, t) & ~CapturedCell(x-1, y+1, t) >> BallPosition(b, x-1, y+1, t+1))
                    E.add_constraint(BallPosition(b, x, y, t) & BallVelocityX(b, t) & ~BallVelocityY(b, t) & ~CapturedCell(x+1, y-1, t) >> BallPosition(b, x+1, y-1, t+1))
                    E.add_constraint(BallPosition(b, x, y, t) & ~BallVelocityX(b, t) & ~BallVelocityY(b, t) & ~CapturedCell(x-1, y-1, t) >> BallPosition(b, x-1, y-1, t+1))

# The full exploration of how builders could move and create building cells 
def explore_builders():
    # A builder creates a building cell and moves to the next cell after a step in time
    for t in range(MAX_BUILD_TIME-1):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                if y > 0:
                    # The builder will move on to the next cell if it is empty
                    E.add_constraint(Builder("N", x, y, t) & ~CapturedCell(x, y-1, t) >> Builder("N", x, y-1, t+1))

                    # The builder will finish building if it runs into a captured cell
                    E.add_constraint(Builder("N", x, y, t) & CapturedCell(x, y-1, t) >> BuilderFinished("N", t+1))
                else:

                    # The builder finishes building if it runs into the canvas border
                    E.add_constraint(Builder("N", x, y, t) >> BuilderFinished("N", t+1))

                if y < CANV_CELLS_HEIGHT - 1:
                    E.add_constraint(Builder("S", x, y, t) & ~CapturedCell(x, y+1, t) >> Builder("S", x, y+1, t+1))
                    E.add_constraint(Builder("S", x, y, t) & CapturedCell(x, y+1, t) >> BuilderFinished("S", t+1))
                else:
                    E.add_constraint(Builder("S", x, y, t) >> BuilderFinished("S", t+1))

                if x > 0:
                    E.add_constraint(Builder("W", x, y, t) & ~CapturedCell(x-1, y, t) >> Builder("W", x-1, y, t+1))
                    E.add_constraint(Builder("W", x, y, t) & CapturedCell(x-1, y, t) >> BuilderFinished("W", t+1))
                else:
                    E.add_constraint(Builder("W", x, y, t) >> BuilderFinished("W", t+1))

                if x < CANV_CELLS_WIDTH - 1:
                    E.add_constraint(Builder("E", x, y, t) & ~CapturedCell(x+1, y, t) >> Builder("E", x+1, y, t+1))
                    E.add_constraint(Builder("E", x, y, t) & CapturedCell(x+1, y, t) >> BuilderFinished("E", t+1))
                else:
                    E.add_constraint(Builder("E", x, y, t) >> BuilderFinished("E", t+1))

                for d in DIRECTIONS:
                    # Each builder creates a building cell at its location
                    E.add_constraint(Builder(d, x, y, t) >> BuildingCell(d, x, y, t))

########## CONSTRAINTS ##########
def theory():
    # Intitialize the lose life proposition to be false at time 0:
    E.add_constraint(~LoseLife(0))

    # Initialize the cursor's orientation based of off the input
    if CURSOR_ORIENTATION == "H":
        E.add_constraint(Horizontal())
    else:
        E.add_constraint(Vertical())

    # The cursor's orientation can only be either vertical or horizontal, but not both
    E.add_constraint((Horizontal() & ~Vertical()) | (~Horizontal() & Vertical()))

    # Intialize builders with their position and orientation based of off the input
    x, y = CURSOR_POSITION
    E.add_constraint(Horizontal() >> (Builder("E", x, y, 0) & Builder("W", x, y, 0)))
    E.add_constraint(Vertical() >> (Builder("N", x, y, 0) & Builder("S", x, y, 0)))

    # There can only be 2 builders
    for t in range(MAX_BUILD_TIME):
        constraint.add_at_most_k(E, 2, [Builder(d, x, y, t) 
                                        for x in range(CANV_CELLS_WIDTH) 
                                        for y in range(CANV_CELLS_HEIGHT)
                                        for d in DIRECTIONS])

    # Initialize balls and ball velocities
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
    
    # There can only be the amount of balls entered into the input at 
    for t in range(MAX_BUILD_TIME):
        constraint.add_at_most_k(E, len(BALLS), [BallPosition(b, x, y, t) 
                                        for x in range(CANV_CELLS_WIDTH) 
                                        for y in range(CANV_CELLS_HEIGHT) 
                                        for b in range(len(BALLS))])

    # Functionality for balls bouncing
    for b in range(len(BALLS)):
        for t in range(MAX_BUILD_TIME):
            for y in range(CANV_CELLS_HEIGHT):
                for x in range(CANV_CELLS_WIDTH):
                    if x > 0:
                        # A ball bounces off of a captured cell
                        E.add_constraint(BallPosition(b, x, y, t) & ~BallVelocityX(b, t-1) & CapturedCell(x-1, y, t) >> BallVelocityX(b, t))
                    else:
                        # A ball bounces off of the canvas border
                        E.add_constraint(BallPosition(b, x, y, t) & ~BallVelocityX(b, t-1) >> BallVelocityX(b, t))

                    if x < CANV_CELLS_WIDTH - 1:
                        E.add_constraint(BallPosition(b, x, y, t) & BallVelocityX(b, t-1) & CapturedCell(x+1, y, t) >> ~BallVelocityX(b, t))
                    else:
                        E.add_constraint(BallPosition(b, x, y, t) & BallVelocityX(b, t-1) >> ~BallVelocityX(b, t))

                    if y > 0:
                        E.add_constraint(BallPosition(b, x, y, t) & ~BallVelocityY(b, t-1) & CapturedCell(x, y-1, t) >> BallVelocityY(b, t))
                    else:
                        E.add_constraint(BallPosition(b, x, y, t) & ~BallVelocityY(b, t-1) >> BallVelocityY(b, t))
                    
                    if y < CANV_CELLS_HEIGHT - 1:
                        E.add_constraint(BallPosition(b, x, y, t) & BallVelocityY(b, t-1) & CapturedCell(x, y+1, t) >> ~BallVelocityY(b, t))
                    else:
                        E.add_constraint(BallPosition(b, x, y, t) & BallVelocityY(b, t-1) >> ~BallVelocityY(b, t))
    
    # When a ball collides with a building cell, the player loses a life
    for y in range(CANV_CELLS_HEIGHT):
        for x in range(CANV_CELLS_WIDTH):
            for t in range(MAX_BUILD_TIME):
                for b in range(len(BALLS)):
                    for d in DIRECTIONS:
                        E.add_constraint((BallPosition(b, x, y, t) & BuildingCell(d, x, y, t)) >> LoseLife(t+1))
                        E.add_constraint(~(BallPosition(b, x, y, t) & BuildingCell(d, x, y, t)) & ~LoseLife(t) >> ~LoseLife(t+1))
    
    # If the player will have lost a life at a certain point in time, remember it for the end result
    for t in range(MAX_BUILD_TIME-1):
        E.add_constraint(LoseLife(t) >> LoseLife(t+1))

    # Initialize captured cells
    for y in range(CANV_CELLS_HEIGHT):
        for x in range(CANV_CELLS_WIDTH):
            if CANVAS[y][x] == 1:
                E.add_constraint(CapturedCell(x, y, 0))
            else:
                E.add_constraint(~CapturedCell(x, y, 0))

    # A building cell stays until its builder is done, in which case it will turn into a captured cell
    for t in range(MAX_BUILD_TIME-1):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                for d in DIRECTIONS:
                    E.add_constraint(BuildingCell(d, x, y, t) & ~BuilderFinished(d, t) >> BuildingCell(d, x, y, t+1))
                    E.add_constraint(BuildingCell(d, x, y, t) & BuilderFinished(d, t) >> CapturedCell(x, y, t+1))

    # A captured cell stays captured
    for t in range(MAX_BUILD_TIME-1):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                E.add_constraint(CapturedCell(x, y, t) >> CapturedCell(x, y, t+1))

    # A noncaptured cell stays noncaptured if nothing happens to it
    for t in range(MAX_BUILD_TIME-1):
        for y in range(CANV_CELLS_HEIGHT):
            for x in range(CANV_CELLS_WIDTH):
                for d in DIRECTIONS:
                    E.add_constraint(~(BuildingCell(d, x, y, t) & BuilderFinished(d, t)) & ~CapturedCell(x, y, t) >> ~CapturedCell(x, y, t+1))
    
    ensure_no_overlap()
    ball_movement()
    explore_builders()
    
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
    # for a,b in sol.items():
    #     print(a,b)

    # Prints out a mapping of the canvas for each step in time
    for t in range(MAX_BUILD_TIME):
        final_map = [[int(sol[f"The cell ({x}, {y}) is captured at time {0}"])
                    for x in range(CANV_CELLS_WIDTH)] 
                    for y in range(CANV_CELLS_HEIGHT)]
        
        for y in range(len(final_map)):
            for x in range(len(final_map[0])):
                for d in DIRECTIONS:
                    if sol[f"The {d} builder is at cell ({x}, {y}) at time {0}"]:
                        final_map[y][x] = 2

        print(f'{t=}')
        print(*final_map, sep='\n')
        print()

    # Prints out the result of whether or not the player will lose a life
    if sol[f"The player will have lost a life from creating a line by time {MAX_BUILD_TIME}"]:
        print("You will lose a life if you create the line")
    else:
        print("You won't lose a life if you create the line")