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

#proxy_server = VideoProxyServer(drone_ips, server_ip, base_port)
#proxy_server.start_proxy()

drone1 = myTello(WIFI_ADAPTER_1_IP, base_port)
drone2 = myTello(WIFI_ADAPTER_2_IP, base_port + 1)



#creates a map of the environment on pygame
pygame.init()
screen = pygame.display.set_mode([864, 586])
screen_width, screen_height = pygame.display.get_surface().get_size()
pygame.display.set_caption("Path Planning with Map (BRViz)")
screen.fill((255, 255, 255))

isRunning = True
sizeCoeff = 531.3/57 # actual distance/pixel distance in cm (CHANGE THIS VALUE IF YOUR CHANGING THE MAP)

def scaleImgDown(img, scale_factor):
    original_width, original_height = img.get_size()
    new_width = int(original_width * scale_factor)
    new_height = int(original_height * scale_factor)
    img = pygame.transform.smoothscale(img, (new_width, new_height))# Scale the image
    return img

startMap = map.initializeMap(screen, "Make Drone 1 Path")
startMap.start_screen(0, 0, 9, 0, 0, 0, 0, 0)

#DRONE 1 MAPPING
map1 = map.mapStart(sizeCoeff, screen, Background('images/mymap.png', [0, 105], 0.7))
angle, distanceInCm, distanceInPx, path = map1.createMap()
pygame.draw.line(screen, (0, 0, 0), path[1], path[2], 6) #creates a line as the edges                
pygame.draw.circle(screen, (0, 0, 255), path[1], 5) #To note where the nodes are
pygame.draw.circle(screen, (0, 0, 255), path[2], 5) #To note where the nodes are

# Define the area you want to save (x, y, width, height)
saveImg = pygame.Rect(0, 105, screen_width, screen_height-105)
# Create a new Surface to store the part of the screen
path1img = screen.subsurface(saveImg).copy()
pygame.image.save(path1img, "images/pathPlanned.png") #Saves new background with path

startMap.changeInstruction("Make Drone 2 Path")
startMap.start_screen(0, 0, 9, 0, 0, 0, 0, 0)

#DRONE 2 Mapping
map2 = map.mapStart(sizeCoeff, screen, Background('images/pathPlanned.png', [0, 105], 1))
angle2, distanceInCm2, distanceInPx2, path2 = map2.createMap()
startMap.changeInstruction("Add the Subject")
pygame.draw.line(screen, (0, 0, 0), path2[1], path2[2], 6) #creates a line as the edges                
pygame.draw.circle(screen, (0, 0, 255), path2[1], 5) #To note where the nodes are
pygame.draw.circle(screen, (0, 0, 255), path2[2], 5) #To note where the nodes are

startMap.start_screen(0, 0, 9, 0, 0, 0, 0, 0)
pygame.display.update()

personx, persony, personpospx = map2.addPerson(sizeCoeff)
personpos = (personx, persony)

print("HELLO")
startMap.changeInstruction("Moving Drones...")
startMap.start_screen(0, 0, 9, 0, 0, 0, 0, 0)

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
pygame.image.save(screen, "images/pathPlanned2.png") #Saves new background with path


#Makes the drone image on a path
drone1Img = pygame.image.load('images/tello3.png')  # Replace with your image file path
drone1Img = scaleImgDown(drone1Img, 0.085) #Scale down to 8.5%

drone2Img = pygame.image.load('images/tello2.png')  # Replace with your image file path
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

background = Background('images/pathPlanned2.png', [0, 0], 1)
updateTime = 0.004
interface1 = DroneInterface(path, personpospx, distanceInCm, angle, screen, drone1Img, map1)
interface2 = DroneInterface(path2, personpospx, distanceInCm2, angle2, screen, drone2Img, map2)

interface1.localize()
interface2.localize()

def updateInterface():
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False    
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

