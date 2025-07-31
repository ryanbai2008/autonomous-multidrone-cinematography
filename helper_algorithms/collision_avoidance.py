import math

def list_permutations(drone_list):
    drone_permutations = []
    for idx, drone_name_1 in enumerate(drone_list):
        for drone_name_2 in drone_list[idx + 1 : ]:
            drone_permutations.append((drone_name_1, drone_name_2))
    return drone_permutations

class Avoid:
    def __init__(self, detect_collision_distance, height_change):
        self.detect_collision_distance = detect_collision_distance # how close do the drones need to be to consider a possible collision
        self.height_change = height_change

    def drone_distance(self, drone_name_1, drone_name_2, drone_dict): # drone_dict should be {1 : [x1, y1], 2 : [x2, y2], etc.} where "i" is drone i
        drone_1_pos = drone_dict[drone_name_1]
        drone_2_pos = drone_dict[drone_name_2]
        return math.sqrt((drone_1_pos[0] - drone_2_pos[0]) ** 2 + (drone_1_pos[1] - drone_2_pos[1]) ** 2)

    def detect_collisions(self, drone_dict): # drone_dict should be {1 : [x1, y1], 2 : [x2, y2], etc.} where "i" is drone i
        drone_collisions = []
        drone_permutations = list_permutations(drone_dict.keys())
        for drone_name_1, drone_name_2 in drone_permutations:
            if self.drone_distance(drone_name_1, drone_name_2, drone_dict) < self.detect_collision_distance:
                # check if drone is already in collision with other drones
                # if not we will create a new list in drone_collisions
                already_in_collision = False
                for idx, collision_list in enumerate(drone_collisions):
                    if drone_name_1 in collision_list:
                        drone_collisions[idx].append(drone_name_2)
                        already_in_collision = True
                    elif drone_name_2 in collision_list:
                        drone_collisions[idx].append(drone_name_1)
                        already_in_collision = True
                if not already_in_collision:
                    drone_collisions.append([drone_name_1, drone_name_2])
        return drone_collisions

    def assign_heights(self, drone_collisions):
        drone_height_adjustments = {}
        for collision_group in drone_collisions:
            collision_group.sort()
            for height_scalar, drone in enumerate(collision_group):
                drone_height_adjustments[drone] = height_scalar * self.height_change
        return drone_height_adjustments # dictionary with key drone and value of neccesary height change
        
