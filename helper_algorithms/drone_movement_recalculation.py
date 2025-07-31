import math

class PathPlan:
    def __init__(self, X_start, X_end, Y_start, Y_end, angle_start):
        self.X_start = X_start
        self.X_end = X_end
        self.Y_start = Y_start
        self.Y_end = Y_end
        self.angle_start = angle_start
        self.original_magnitude_diff = math.sqrt((X_end - X_start) ** 2 + (Y_end - Y_start) ** 2)
    
    def dot_product(self, u, v):
        return (u[0] * v[0] + u[1] * v[1])
    
    def magnitude(self, u):
        return math.sqrt(u[0] ** 2 + u[1] ** 2)

    def move_towards_goal(self, X_current, Y_current, angle_curr, terminate):
        #skip if drone has already reached position
        if terminate:
            return [0, 0]
        
        #calculate vectors u and v
        angle_curr_radians = math.radians(angle_curr)
        u = [math.cos(angle_curr_radians), math.sin(angle_curr_radians)]
        v = [self.X_end - X_current, self.Y_end - Y_current]

        #calculate x and y |velocity| values
        proj_u_v = [(self.dot_product(u, v) / self.dot_product(u, u)) * element for element in u]
        v_minus_proj_u_v = [(v_element - proj_element) for v_element, proj_element in zip(v, proj_u_v)]
        X_velocity = self.magnitude(v_minus_proj_u_v)
        Y_velocity = self.magnitude(proj_u_v)

        #calculate the sign of velocity values
        a = u[0] * proj_u_v[0]
        w = [math.sin(angle_curr_radians), -math.cos(angle_curr_radians)]
        b = w[0] * v_minus_proj_u_v[0]

        #adjust sign of velocity values
        if a < 0:
            Y_velocity *= -1
        if b < 0:
            X_velocity *= -1

        return [int(X_velocity), int(Y_velocity)] #right, forward
