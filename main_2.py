import pygame
import json
import math
import cv2 
import time
from time import sleep
import numpy as np
import threading
import sys
from mapBackground import Background
import map
from localizeIRT import localizer
import socket
import os
#from customtello import VideoProxyServer
from customtello import myTello

import path_planner
import tello_tracking_2
import collision
import logging
import platform
import subprocess
import avoid
import re
from wifi_bind import WifiBind
from interface import DroneInterface

lock = threading.Lock()
# Define the IP addresses of the two Wi-Fi adapters
WIFI_ADAPTER_1_IP = "192.168.10.2"  # IP address of Wi-Fi Adapter 1 (connected to Drone 1)
WIFI_ADAPTER_2_IP = "192.168.10.3"  # IP address of Wi-Fi Adapter 2 (connected to Drone 2)

drone_ips = [WIFI_ADAPTER_1_IP, WIFI_ADAPTER_2_IP]
base_port = 30000
TELLO_IP = "192.168.10.1"

# Adapter names
WIFI_1 = "Wi-Fi"
WIFI_2 = "Wi-Fi 2"

drone_1_wifi = WifiBind(WIFI_1, TELLO_IP, WIFI_ADAPTER_1_IP)
drone_2_wifi = WifiBind(WIFI_2, TELLO_IP, WIFI_ADAPTER_2_IP)

# Connect to Tello networks
drone_1_wifi.connect_wifi("TELLO-D06F9F")
drone_2_wifi.connect_wifi("TELLO-EE4263 2")

# Assign static IPs
drone_1_wifi.set_static_ip(WIFI_ADAPTER_1_IP)
drone_2_wifi.set_static_ip(WIFI_ADAPTER_2_IP)

# Add route if necessary
drone_1_wifi.add_route(0)
drone_2_wifi.add_route(1)

#proxy_server = VideoProxyServer(drone_ips, server_ip, base_port)
#proxy_server.start_proxy()

drone1 = myTello(WIFI_ADAPTER_1_IP, base_port)
drone2 = myTello(WIFI_ADAPTER_2_IP, base_port + 1)

drone1.connect()
drone2.connect()


def start_keep_alive(drone):
    keep_alive_thread = threading.Thread(target=drone.keep_alive, daemon=True)
    keep_alive_thread.start()
    return keep_alive_thread
keep_alive_thread1 = start_keep_alive(drone1)
keep_alive_thread2 = start_keep_alive(drone2)

def is_safe_to_fly():
    # Check battery levels (both drones should have more than 20% battery)
    battery1 = drone1.getBattery()
    battery2 = drone2.getBattery()
    if battery1 < 10 or battery2 < 10:
        logging.warning(f"Low battery: Drone 1 ({battery1}%) or Drone 2 ({battery2}%)")
        return False

    # Check if drones are connected
    if not drone1.getConnected() or not drone2.getConnected():
        logging.error("One or both drones are not connected")
        return False

    # Additional checks can be added, such as GPS status, temperature, etc.

    return True

battery1 = drone1.getBattery()
battery2 = drone2.getBattery()

height1 = drone1.getHeight()
height2 = drone2.getHeight()

print(battery1)
print(battery2)

def updateScreen():
    with lock:
        startingyaw1 = 0
        startingyaw2 = 0
         
        speedx1 = drone1.get_speed()
        speedx2 = drone2.get_speed()
        speedz1  = drone1.get_AngularSpeed(startingyaw1)
        speedz2 = drone2.get_AngularSpeed(startingyaw2)

        battery1 = drone1.getBattery()
        battery2 = drone2.getBattery()

        height1 = drone1.getHeight()
        height2 = drone2.getHeight()

        startMap.start_screen(battery1, speedx1, speedz1, height1, battery2, speedx2, speedz2, height2)
        sleep(0.5) #updates every 10 seconds, just gets data doesnt need to be too often or too much cpu

#creates a map of the environment on pygame
pygame.init()
screen = pygame.display.set_mode([864, 586])
screen_width, screen_height = pygame.display.get_surface().get_size()
pygame.display.set_caption("Path Planning with Map (BRViz)")
screen.fill((255, 255, 255))

speedx1 = drone1.get_speed()
speedx2 = drone2.get_speed()
speedz1 = drone1.get_AngularSpeed(0)
speedz2 = drone2.get_AngularSpeed(0)
battery1 = drone1.getBattery()
battery2 = drone2.getBattery()
height1 = drone1.getHeight()
height2 = drone2.getHeight()

isRunning = True
sizeCoeff = 531.3/57 # actual distance/pixel distance in cm (CHANGE THIS VALUE IF YOUR CHANGING THE MAP)

def scaleImgDown(img, scale_factor):
    original_width, original_height = img.get_size()
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    img = pygame.transform.smoothscale(img, (new_width, new_height))# Scale the image
    return img

startMap = map.initializeMap(screen, "Make Drone 1 Path")
startMap.start_screen(battery1, speedx1, speedz1, height1, battery2, speedx2, speedz2, height2)

#DRONE 1 MAPPING
map1 = map.mapStart(sizeCoeff, screen, Background('mymap.png', [0, 105], 0.7))
angle, distanceInCm, distanceInPx, path = map1.createMap()
pygame.draw.line(screen, (0, 0, 0), path[1], path[2], 6) #creates a line as the edges                
pygame.draw.circle(screen, (0, 0, 255), path[1], 5) #To note where the nodes are
pygame.draw.circle(screen, (0, 0, 255), path[2], 5) #To note where the nodes are

# Define the area you want to save (x, y, width, height)
saveImg = pygame.Rect(0, 105, screen_width, screen_height-105)
# Create a new Surface to store the part of the screen
path1img = screen.subsurface(saveImg).copy()
pygame.image.save(path1img, "pathPlanned.png") #Saves new background with path

startMap.changeInstruction("Make Drone 2 Path")
startMap.start_screen(battery1, speedx1, speedz1, height1, battery2, speedx2, speedz2, height2)

#DRONE 2 Mapping
map2 = map.mapStart(sizeCoeff, screen, Background('pathPlanned.png', [0, 105], 1))
angle2, distanceInCm2, distanceInPx2, path2 = map2.createMap()
startMap.changeInstruction("Add the Subject")
pygame.draw.line(screen, (0, 0, 0), path2[1], path2[2], 6) #creates a line as the edges                
pygame.draw.circle(screen, (0, 0, 255), path2[1], 5) #To note where the nodes are
pygame.draw.circle(screen, (0, 0, 255), path2[2], 5) #To note where the nodes are

startMap.start_screen(battery1, speedx1, speedz1, height1, battery2, speedx2, speedz2, height2)
pygame.display.update()

personx, persony, personpospx = map2.addPerson(sizeCoeff)
personpos = (personx, persony)

print("HELLO")
startMap.changeInstruction("Moving Drones...")
startMap.start_screen(battery1, speedx1, speedz1, height1, battery2, speedx2, speedz2, height2)

print(angle)
print(distanceInCm)
print(distanceInPx)
print(path)


print(angle2)
print(distanceInCm2)
print(distanceInPx2)
print(path2)
path.pop(0)
path2.pop(0)

point1 = path[0] 
point2 = path[1] 
point3 = path2[0]
point4 = path2[1]

x1 = point1[0]
x2 = point2[0]
x3 = point3[0]
x4 = point4[0]
y1 = point1[1]
y2 = point2[1]
y3 = point3[1]
y4 = point4[1]

def line_intersection(x1, y1, x2, y2, x3, y3, x4, y4):
    # Calculate the coefficients of the lines
    A1 = y2 - y1
    B1 = x1 - x2
    C1 = A1 * x1 + B1 * y1

    A2 = y4 - y3
    B2 = x3 - x4
    C2 = A2 * x3 + B2 * y3

    # Calculate the determinant of the system
    determinant = A1 * B2 - A2 * B1

    if determinant == 0:
        # Lines are parallel
        return None

    # Calculate the intersection point
    x = (B2 * C1 - B1 * C2) / determinant
    y = (A1 * C2 - A2 * C1) / determinant

    # Check if the intersection point is within the segment bounds
    if min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2) and min(x3, x4) <= x <= max(x3, x4) and min(y3, y4) <= y <= max(y3, y4):
        return (x, y)
    else:
        return None
    
intersection = line_intersection(x1, y1, x2, y2, x3, y3, x4, y4)

if intersection:
    font = pygame.font.SysFont('Times',25)
    intersectx = (int)((intersection[0]))
    intersecty = (int)((screen_height  - intersection[1]))
    position_text = font.render(f'({intersectx}, {intersecty})cm', True, (128, 0, 128))
    screen.blit(position_text, intersection)
    pygame.draw.circle(screen, (128, 0, 128), intersection, 6) #purple dot at intesection 
    intersection = (intersectx, intersecty)
    collisiondetect = collision(path2[0], intersection, 500, 500)
    collisiondetect.get_vertex() 
    intersection = True
print(intersection)
print(personpos)


def move_parabolic(self, drone, speed, time, distance):
    drone2.send_rc(0, 0, 0, int(speed))
    drone.send_rc(0, 0, 0, int(speed))

#Saves the screen to be blitted
saveImg = pygame.Rect(0, 100, screen_width, screen_height-105)
# Create a new Surface to store the part of the screen
path1img = screen.subsurface(saveImg).copy()
pygame.image.save(screen, "pathPlanned2.png") #Saves new background with path


#Makes the drone image on a path
drone1Img = pygame.image.load('tello3.png')  # Replace with your image file path
drone1Img = scaleImgDown(drone1Img, 0.085) #Scale down to 8.5%

drone2Img = pygame.image.load('tello2.png')  # Replace with your image file path
drone2Img = scaleImgDown(drone2Img, 0.03) # Scale down to 3%

#position values for path planning
start_pos1X, start_pos1Y = path[0]
end_pos1X, end_pos1Y = path[1]
start_pos2X, start_pos2Y = path2[0]
end_pos2X, end_pos2Y = path2[1]

#drones current position values
drone_1_pos = [start_pos1X, start_pos1Y, 0] #initial angle of 0
drone_2_pos = [start_pos2X, start_pos2Y, 0] #initial angle of 0
drone_1_movement = [0, 0]
drone_2_movement = [0, 0]


#path planning objects and CV objects
#drone_1_path_plan = path_planner.PathPlan(start_pos1X, end_pos1X, start_pos1Y, end_pos1Y, drone_1_pos[2]) #########place both drones facing to the right facing horizontally
#drone_2_path_plan = path_planner.PathPlan(start_pos2X, end_pos2X, start_pos2Y, end_pos2Y, drone_2_pos[2])
#drone1_CV = tello_tracking.CV()
#drone2_CV = tello_tracking.CV()


#has goal been reached for drones
drone_1_terminate = False
drone_2_terminate = False


#how frequently the position is updated
sleep_time = 0
timer = 0
iter = 0

background = Background('pathPlanned2.png', [0, 0], 1)
updateTime = 0.004
interface1 = DroneInterface(path, personpospx, distanceInCm, angle, screen, drone1Img, map1)
interface2 = DroneInterface(path2, personpospx, distanceInCm2, angle2, screen, drone2Img, map2)

interface1.localize()
interface2.localize()

def updateInterface():
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False    
        updateScreen()
        screen.blit(background.image, (0, 0))    

        interface1.update()
        interface2.update()

        pygame.display.update()
        
        pygame.time.delay(int(updateTime*1000))


    pygame.quit()
    sys.exit()

    interface1.ensure_end()
    interface2.ensure_end()

    pygame.display.flip()

localizeThread = threading.Thread(target=updateInterface)
localizeThread.start()
# screenThread = threading.Thread(target=updateScreen)
# screenThread.start()
# if(not is_safe_to_fly()):
#     logging.error("Safety check failed. Drones will not take off.")
#     sys.exit(1)
normal_height = 200


try:
    #turn on drones cameras
    drone1.streamon()
    drone2.streamon()
    drone1.start_video_stream(1)
    drone2.start_video_stream(2)
    drone1.takeoff()
    drone2.takeoff()

    #path
    start_1_X, start_1_Y, end_1_X, end_1_Y = path[0][0], path[0][1], path[1][0], path[1][1]
    path1 = [start_1_X, start_1_Y, end_1_X, end_1_Y]

    #other drone path
    path_2 = [path2[0][0],path2[0][1], path2[1][0], path2[1][1]]

    #drone current values
    drone_1_pos = [path1[0], path1[1], 0] #(X, Y, angle), STARTING ANGLE MUST BE 0 DEGREES
    drone_2_pos = [path_2[0], path_2[1], 0]

    #drone movement
    drone_1_movement = [0, 0, 0] #(delta X, delta Y, delta angle)

    #path planning and CV and collision objects
    drone_1_path_plan = path_planner.PathPlan(path1[0], path1[2], path1[1], path1[3], drone_1_pos[2])
    drone_2_path_plan = path_planner.PathPlan(path_2[0], path_2[2], path_2[1], path_2[3], drone_2_pos[2])
    drone_1_CV = tello_tracking_2.CV()
    drone_2_CV = tello_tracking_2.CV()

    drone_collision = avoid.Avoid(path1, path_2)

    #goal reached for drones?
    drone_1_terminate = False
    drone_2_terminate = False

    #turn on drone

    drone1.send_rc(0, 0, 40, 0)
    drone2.send_rc(0, 0, 40, 0)
    time.sleep(1.5)
    drone_height = 60
    normal_height = 60
    go_up = 0
    drone1.send_rc(0, 0, 0, 0)
    drone2.send_rc(0, 0, 0, 0)

    #timer for position updates
    sleep_time = 0
    timer = 0
    iter = 0
    iter_2 = 0

    #total time elapsed
    total_time = 0

    ##############################
    ##Drone initial orientation###
    ##############################
    facing_human_1 = False
    facing_human_2 = False
    while (not facing_human_1) or (not facing_human_2):
        #CV
        img1 = drone1.get_frame_read()
        img2 = drone2.get_frame_read()

        if (img1 is not None) and (img2 is not None):
            logging.debug("Processed frame for drones")
            turn_1 = drone_1_CV.center_subject(img1, 1)
            turn_2 = drone_2_CV.center_subject(img2, 2)

            #turn 1
            if turn_1 == 0: #if no human detected, continue turning
                turn_1 = 20
            elif turn_1 == 1: #human centered
                facing_human_1 = True
                turn_1 = 0
            #turn 2
            if turn_2 == 0: #if no human detected, continue turning
                turn_2 = 20
            elif turn_2 == 1: #human centered
                facing_human_2 = True
                turn_2 = 0
                
            drone1.send_rc(0, 0, 0, turn_1)
            drone2.send_rc(0, 0, 0, turn_2)
        else:
            logging.debug("No frame recieved for drones")
            
       
        

    print("\n\n\nnow moving paths\n\n\n")
    ##############################
    #########Path Planning########
    ##############################
    drone_1_pos[2] = -1 * drone1.get_yaw()
    drone_2_pos[2] = -1 * drone2.get_yaw()
    
    #get the start time
    start_time = time.time()

    #movement starts
    while total_time < 60:
        #update total time
        total_time = time.time() - start_time

        #CV
        img1 = drone1.get_frame_read()
        img2 = drone2.get_frame_read()

        if (img1 is not None) and (img2 is not None):
            logging.debug("Processed frame for drones")
            
            turn_1 = drone_1_CV.center_subject(img1, 1)
            if turn_1 == 1:
                turn_1 = 0 #if subject centered, no turn
                
            turn_2 = drone_2_CV.center_subject(img2, 2)
            if turn_2 == 1:
                turn_2 = 0 #if subject centered, no turn
            
            #update timer
            if iter == 0:
                sleep_time = 0 #do not update positions for the first loop
                iter += 1
            else:
                sleep_time = time.time() - timer
                
            if (not drone_1_terminate) or (not drone_2_terminate):
                
                #calculate new angle
                drone_1_pos[2] = -1 * drone1.get_yaw()
                #update drone 2 position
                drone_2_pos[2] = -1 * drone2.get_yaw()
              
                #calculate new position
                theta_x_component_change = 0
                if drone_1_movement[0] > 0:
                    theta_x_component_change = -1
                else:
                    theta_x_component_change = 1
                theta_x_component = (drone_1_pos[2] + 90 * theta_x_component_change) % 360
                theta_y_component = (drone_1_pos[2]) % 360
                delta_x = abs(drone_1_movement[0]) * math.cos(math.radians(theta_x_component)) + drone_1_movement[1] * math.cos(math.radians(theta_y_component))
                delta_y = abs(drone_1_movement[0]) * math.sin(math.radians(theta_x_component)) + drone_1_movement[1] * math.sin(math.radians(theta_y_component))
                drone_1_pos[0] += delta_x * sleep_time
                drone_1_pos[1] += delta_y * sleep_time

                #calculate new position
                theta_x_component_change = 0
                if drone_2_movement[0] > 0:
                    theta_x_component_change = -1
                else:
                    theta_x_component_change = 1
                theta_x_component = (drone_2_pos[2] + 90 * theta_x_component_change) % 360
                theta_y_component = (drone_2_pos[2]) % 360
                delta_x = abs(drone_2_movement[0]) * math.cos(math.radians(theta_x_component)) + drone_2_movement[1] * math.cos(math.radians(theta_y_component))
                delta_y = abs(drone_2_movement[0]) * math.sin(math.radians(theta_x_component)) + drone_2_movement[1] * math.sin(math.radians(theta_y_component))
                drone_2_pos[0] += delta_x * sleep_time
                drone_2_pos[1] += delta_y * sleep_time

                
                #detect collision and manage heights
                drone_height += go_up * sleep_time
                print(f"drone height: {drone_height}, normal height: {normal_height}")
                collision_check = drone_collision.detect_collision(drone_1_pos[0], drone_1_pos[1])
                if collision_check == "collision":
                    go_up = 40
                elif collision_check == "no collision" and drone_height > normal_height * 1.1: #buffer
                    go_up = -20
                elif collision_check == "no collision" and drone_height < normal_height * 1.1: #buffer
                    go_up = 20
                else:
                    go_up = 0
                
                if drone_height > 250:
                    drone1.land()
                    drone2.land()
                    
                    
            #path planning
            drone_1_movement = drone_1_path_plan.move_towards_goal(drone_1_pos[0], drone_1_pos[1], drone_1_pos[2], drone_1_terminate)
            drone_2_movement = drone_2_path_plan.move_towards_goal(drone_2_pos[0], drone_2_pos[1], drone_2_pos[2], drone_2_terminate)

            #reached goal?
            if drone_1_movement[0] == 0.1:
                drone_1_terminate = True
                print("\n\n\nnow stopping drone movement drone 1\n\n\n")
                drone_1_movement[0], drone_1_movement[1] = 0, 0
                
            if drone_2_movement[0] == 0.1:
                drone_2_terminate = True
                print("\n\n\nnow stopping drone movement drone 2\n\n\n")
                drone_2_movement[0], drone_2_movement[1] = 0, 0
            
            #move drone and update values, already considered if drone terminated
            drone1.send_rc(drone_1_movement[0], drone_1_movement[1], go_up, turn_1)
            drone2.send_rc(drone_2_movement[0], drone_2_movement[1], 0, turn_2)
            timer = time.time() #time for keeping track of how much to update drones positions
            # print(f"Drone 1 Position: {drone_1_pos}, Movement: {drone_1_movement}")
            # print(f"Drone 2 Position: {drone_2_pos}, Movement: {drone_2_movement}")
            
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    
    #clean up
    time.sleep(5)
    cv2.destroyAllWindows()
    drone1.land()
    drone2.land()
    drone1.streamoff()
    drone2.streamoff()




except KeyboardInterrupt:
    logging.info("KeyboardInterrupt received. Landing the drones...")
    drone1.land()
    drone2.land()
    drone1.streamoff()
    drone2.streamoff()
   
    sys.exit(1)
        #drone1.end()
        #drone2.end()

except Exception as e:
    logging.error(f"An error occurred: {e}")
    drone1.land()
    drone2.land()
    drone1.streamoff()
    drone2.streamoff()
 
    sys.exit(1)  # Ensure the script exits
