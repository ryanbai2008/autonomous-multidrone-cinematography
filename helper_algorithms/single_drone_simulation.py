import path_planner
import matplotlib.pyplot as plt
import time
import math

# path of drone
start_1_X, start_1_Y, end_1_X, end_1_Y = 120, 120, 60, 120
path1 = [start_1_X, start_1_Y, end_1_X, end_1_Y]

# drone current values
drone_1_pos = [path1[0], path1[1], 0]

# all current and previous position data, for display purposes with plt
X_pos_data = [start_1_X]
Y_pos_data = [start_1_Y]
angle_pos_data = [0]

# drone movement
drone_1_movement = [0, 0, 0]  # (delta X, delta Y, delta angle)

# path planning and CV objects
drone_1_path_plan = path_planner.PathPlan(drone_1_pos[0], path1[2], drone_1_pos[1], path1[3], drone_1_pos[2])

# timer for position updates
sleep_time = 0
timer = 0
iteration = 0
time_counter = 0

# total time elapsed
start_time = time.time()
total_time = 0

# human position (subject)
human_position = [[70, 20], [75, 20], [80, 20]]
idx = 0

# position update variables
theta_x_component = 0
theta_y_component = 0
delta_x = 0
delta_y = 0
turn_1 = 0
drone_1_movement = [0, 0]

# plot
fig, ax = plt.subplots()

# goal reached?
drone_1_terminate = False

# change how fast the drone reaches destination, on actual program would be changed by user through pygame interface
scale_movement = 0.1

while total_time < 200:
    # update total time
    total_time = time.time() - start_time

    # update timer
    if iteration == 0:
        sleep_time = 0  # do not update positions for the first loop
        iteration += 1
    else:
        sleep_time = 1

    if not drone_1_terminate:
        # calculate new angle
        print(f"updating position, pos currently at {drone_1_pos}")

        # calculate new position
        theta_x_component_change = 1
        if drone_1_movement[0] > 0:
            theta_x_component_change = -1
        theta_x_component = (drone_1_pos[2] + 90 * theta_x_component_change) % 360
        theta_y_component = (drone_1_pos[2]) % 360
        print("calculating drones x direction angle and y direction angle")
        print(f"theta X: {theta_x_component}")
        print(f"theta Y: {theta_y_component}")

        delta_x = abs(drone_1_movement[0]) * math.cos(math.radians(theta_x_component)) + drone_1_movement[1] * math.cos(math.radians(theta_y_component))
        delta_y = abs(drone_1_movement[0]) * math.sin(math.radians(theta_x_component)) + drone_1_movement[1] * math.sin(math.radians(theta_y_component))
        print("Calculating the change in coordinates")
        print(f"delta x: {delta_x}")
        print(f"delta y: {delta_y}")
        drone_1_pos[0] += delta_x * scale_movement
        drone_1_pos[1] += delta_y * scale_movement

        drone_1_pos[2] += turn_1
        drone_1_pos[2] = drone_1_pos[2] % 360

        # update data for plot usage
        X_pos_data.append(drone_1_pos[0])
        Y_pos_data.append(drone_1_pos[1])
        angle_pos_data.append(drone_1_pos[2])

        print(f"updated position: {drone_1_pos}")
    else:
        drone_1_pos[2] += turn_1
        drone_1_pos[2] = drone_1_pos[2] % 360

        # update data for plot usage
        angle_pos_data.append(drone_1_pos[2])

    # path planning
    drone_1_movement = drone_1_path_plan.move_towards_goal(drone_1_pos[0], drone_1_pos[1], drone_1_pos[2], drone_1_terminate)
    print("Calculating drone movement")
    print(f"drone movement: {drone_1_movement}\n")
    if drone_1_movement[0] == 0.1:
        drone_1_terminate = True
        print("\n\n\nnow stopping drone movement\n\n\n")
        drone_1_movement[0], drone_1_movement[1] = 0, 0

    # CV
    drone_direction_vec = [math.cos(math.radians(drone_1_pos[2])), math.sin(math.radians(drone_1_pos[2]))]
    vec_to_goal = [end_1_X - drone_1_pos[0], end_1_Y - drone_1_pos[1]]
    vec_to_man = [human_position[idx][0] - drone_1_pos[0], human_position[idx][1] - drone_1_pos[1]]
    
    # change human position to simulate moving human subject
    idx += 1
    idx %= 3

    print("Calculating angle between drone direction and vector to man")
    desired_angle = math.degrees(math.atan2(vec_to_man[1], vec_to_man[0]))
    
    angle_diff = (desired_angle - drone_1_pos[2] + 360) % 360
    if angle_diff > 180:
        angle_diff -= 360 
    turn_1 = angle_diff

    # plot w/ direction vectors (using quiver)
    ax.clear()
    ax.set_xlim(0, 200)
    ax.set_ylim(0, 200)

    # scatter plot for the drone's path
    ax.scatter(X_pos_data, Y_pos_data, color='g', label="Drone Path")

    # add direction vectors (heading arrows)
    for i in range(len(X_pos_data)):
        direction_x = math.cos(math.radians(angle_pos_data[i])) * 15
        direction_y = math.sin(math.radians(angle_pos_data[i])) * 15
        ax.quiver(X_pos_data[i], Y_pos_data[i], direction_x, direction_y, angles='xy',
                scale_units='xy', scale=1, color='r', label="Drone Direction" if i == 0 else "")

    # plot the subject (human) position
    ax.scatter(human_position[idx][0], human_position[idx][1], color='b', label="Subject")
    ax.text(human_position[idx][0], human_position[idx][1], "Subject", fontsize=12, fontname='Times New Roman', fontweight='normal', color='black', ha='right')

    # set equal aspect ratio
    ax.set_aspect('equal')

    # add legend
    ax.legend(loc="upper right")
    time_display = ax.text(0.5, 1.03, f"Time = {time_counter}", transform=ax.transAxes, ha='center', fontsize=12, fontname='Times New Roman', fontweight='normal', color='black')

    time_counter += 1 
    plt.draw()
    plt.pause(0.01)
    plt.savefig(f"freq_updates_drone_simulation_frame_{time_counter}.png", dpi=300, bbox_inches='tight')

    time.sleep(3)
