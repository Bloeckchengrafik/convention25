import turtle
import math

# --- Main Simulation Configuration ---
# Overall drawing speed in units per second. This is a conceptual value
# that determines the time taken to draw each line segment.
# Turtle's speed() is for animation and is a separate setting.
OVERALL_DRAWING_SPEED = 10

# --- Function to draw a line segment ---
def draw_line(t, dx, dy, v):
    """
    Simulates a line being drawn by an XY plotter.

    Args:
        t (turtle.Turtle): The turtle object used for drawing.
        dx (float): The change in the x-coordinate.
        dy (float): The change in the y-coordinate.
        v (float): The overall drawing speed in units per second.
    """
    # 1. Calculate total distance and angle
    distance = math.sqrt(dx**2 + dy**2)

    # Avoid division by zero if there's no movement
    if distance == 0:
        return

    # Calculate the angle of movement in radians, which is needed for the math formulas.
    # The atan2 function correctly handles all quadrants.
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)

    # 2. Calculate speeds for each axis based on the provided formulas
    # Note: sin(alpha) / tan(alpha) simplifies to cos(alpha)
    vx = v * math.cos(angle_rad)
    vy = v * math.sin(angle_rad)

    print(f"Drawing line (dx={dx}, dy={dy})")
    print(f"  - Total Distance: {distance:.2f} units")
    print(f"  - Calculated Axis Speeds: vx={vx:.2f} units/s, vy={vy:.2f} units/s")

    # 3. Simulate the drawing with the turtle
    # The turtle's speed is for animation purposes, not a physical speed.
    # We set its heading to the calculated angle and then move it forward
    # by the total distance.
    t.setheading(angle_deg)
    t.forward(distance)

# --- Simulation Setup ---
def setup_simulation():
    """Sets up the turtle screen and plotter objects."""
    # Set up the screen
    screen = turtle.Screen()
    screen.title("XY Plotter Simulation")
    screen.bgcolor("#f0f0f0")
    screen.setup(width=800, height=600)

    # Create the plotter "device" turtle
    plotter = turtle.Turtle()
    plotter.shape("circle")
    plotter.color("#333333")
    plotter.penup()
    plotter.speed(5) # Set animation speed for smooth movement

    # Create a small dot to indicate the starting point
    start_dot = turtle.Turtle()
    start_dot.hideturtle()
    start_dot.penup()
    start_dot.goto(0, 0)
    start_dot.dot(10, "green")

    return screen, plotter

def main():
    """Runs the main simulation logic."""
    screen, plotter = setup_simulation()

    # Move to the starting position (optional)
    plotter.goto(0,0)
    plotter.pendown()

    # A list of drawing commands (dx, dy)
    drawing_commands = [
        (100, 200),    # Diagonal line down and left
    ]

    # Draw the lines
    for dx, dy in drawing_commands:
        draw_line(plotter, dx, dy, OVERALL_DRAWING_SPEED)

    # Hide the turtle at the end
    plotter.hideturtle()

    # Keep the window open
    screen.mainloop()

if __name__ == "__main__":
    main()
