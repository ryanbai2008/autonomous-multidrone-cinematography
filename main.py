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
from customtello import myTello
from helper_algorithms import collision_avoidance as avoid
from helper_algorithms import drone_movement_recalculation as path_planner
from helper_algorithms import subject_tracking as tello_tracking_2
import logging
from wifi_bind import WifiBind
import helper_algorithms.PyGame_Interface as PyGame_Interface

lock = threading.Lock()

ADAPTER_IPs = []
adapter_idx = 1
while True:
    x = input(f"IP Adress of Adapter {adapter_idx}. type done to stop adding IPs")
    if x is None or x.lower() == "done":
        break
    ADAPTER_IPs.append(x)
    adapter_idx += 1

drone_name_idx = 1
DRONE_NAMES = []
while True:
    x = input(f"Type the name of drone {drone_name_idx}. type done to stop adding drone names")
    if x is None or x.lower() == "done":
        break
    DRONE_NAMES.append(x)
    drone_name_idx += 1

n_drones = min(len(ADAPTER_IPs), len(DRONE_NAMES))
ADAPTER_IPs = ADAPTER_IPs[:n_drones]
DRONE_NAMES = DRONE_NAMES[:n_drones]

base_port = 30000
TELLO_IP = "192.168.10.1"
WIFI_NAMES = ["Wi-Fi " + str(i + 1) for i in range(len(ADAPTER_IPs))]

DRONE_WIFIs = []
DRONE_OBJs = []
for idx, (adapter, wifi_name, drone_name) in enumerate(zip(ADAPTER_IPs, WIFI_NAMES, DRONE_NAMES)):
    wb = WifiBind(wifi_name, TELLO_IP, adapter)
    DRONE_WIFIs.append(wb)
    wb.connect_wifi(drone_name)
    wb.set_static_ip(adapter)
    wb.add_route(idx)
    drone_obj = myTello(adapter, base_port + idx)
    DRONE_OBJs.append(drone_obj)
    drone_obj.connect()

def start_keep_alive(drone):
    t = threading.Thread(target=drone.keep_alive, daemon=True)
    t.start()
    return t

DRONE_ALIVE_THREADS = [start_keep_alive(d) for d in DRONE_OBJs]

def is_safe_to_fly(BATTERIES, DRONES):
    for battery in BATTERIES:
        if battery is None or battery < 10:
            return False
    for d in DRONES:
        try:
            if not d.getConnected():
                logging.error("Drone not connected")
                return False
        except Exception:
            logging.error("Failed to verify connection")
            return False
    return True

BATTERIES = [None for _ in DRONE_OBJs]
HEIGHTS = [None for _ in DRONE_OBJs]
for idx, drone in enumerate(DRONE_OBJs):
    try: BATTERIES[idx] = drone.getBattery()
    except Exception: BATTERIES[idx] = None
    try: HEIGHTS[idx] = drone.getHeight()
    except Exception: HEIGHTS[idx] = None

pygame.init()
screen = pygame.display.set_mode([864, 586])
screen_width, screen_height = pygame.display.get_surface().get_size()
pygame.display.set_caption("Path Planning with Map (BRViz)")
screen.fill((255, 255, 255))

SPEED_Xs = []
SPEED_Zs = []
for drone in DRONE_OBJs:
    try: SPEED_Xs.append(drone.get_speed())
    except Exception: SPEED_Xs.append(0)
    try: SPEED_Zs.append(drone.get_AngularSpeed(0))
    except Exception: SPEED_Zs.append(0)

sizeCoeff = input("Distance per pixel in cm (N/A for default)")
try:
    sizeCoeff = float(sizeCoeff) if sizeCoeff.lower() != "n/a" else 531.3/57
except Exception:
    sizeCoeff = 531.3/57

def scaleImgDown(img, scale_factor):
    return PyGame_Interface.scaleImgDown(img, scale_factor)

startMap = map.initializeMap(screen, "Make Drone Paths")
battery1 = BATTERIES[0] if len(BATTERIES) > 0 else 0
battery2 = BATTERIES[1] if len(BATTERIES) > 1 else 0
speedx1 = SPEED_Xs[0] if len(SPEED_Xs) > 0 else 0
speedx2 = SPEED_Xs[1] if len(SPEED_Xs) > 1 else 0
speedz1 = SPEED_Zs[0] if len(SPEED_Zs) > 0 else 0
speedz2 = SPEED_Zs[1] if len(SPEED_Zs) > 1 else 0
height1 = HEIGHTS[0] if len(HEIGHTS) > 0 else 0
height2 = HEIGHTS[1] if len(HEIGHTS) > 1 else 0

startMap.start_screen(battery1, speedx1, speedz1, height1, battery2, speedx2, speedz2, height2)

paths = []
angles = []
distancesInCm = []
distancesInPx = []
background_image = 'images/mymap.png'

for drone_idx in range(n_drones):
    startMap.changeInstruction(f"Make Drone {drone_idx+1} Path")
    startMap.start_screen(battery1, speedx1, speedz1, height1, battery2, speedx2, speedz2, height2)
    m = map.mapStart(sizeCoeff, screen, Background(background_image, [0, 105], 0.7))
    angle, distanceInCm, distanceInPx, path = m.createMap()
    if len(path) >= 2:
        start_pt = path[0]
        end_pt = path[-1]
        pygame.draw.line(screen, (0,0,0), start_pt, end_pt, 6)
        pygame.draw.circle(screen, (0,0,255), start_pt, 5)
        pygame.draw.circle(screen, (0,0,255), end_pt, 5)
    saveImg = pygame.Rect(0, 105, screen_width, screen_height-105)
    pathimg = screen.subsurface(saveImg).copy()
    out_name = f"images/pathPlanned_{drone_idx}.png"
    pygame.image.save(pathimg, out_name)
    background_image = out_name
    paths.append(path)
    angles.append(angle)
    distancesInCm.append(distanceInCm)
    distancesInPx.append(distanceInPx)

startMap.changeInstruction("Add the Subject")
startMap.start_screen(battery1, speedx1, speedz1, height1, battery2, speedx2, speedz2, height2)
personx, persony, personpospx = m.addPerson(sizeCoeff)
personpos = (personx, persony)

if not is_safe_to_fly(BATTERIES, DRONE_OBJs):
    logging.error("Safety check failed")
    sys.exit(1)

try:
    for idx, d in enumerate(DRONE_OBJs):
        d.streamon()
        d.start_video_stream(idx+1)
        d.takeoff()

    DRONE_PATH_PLAN_OBJs = []
    for i, path in enumerate(paths):
        if len(path) < 2:
            logging.error(f"Path for drone {i+1} too short")
            sys.exit(1)
        s, e = path[0], path[-1]
        DRONE_PATH_PLAN_OBJs.append(path_planner.PathPlan(s[0], e[0], s[1], e[1], 0))

    CV_objs = [tello_tracking_2.CV() for _ in DRONE_OBJs]
    avoider = avoid.Avoid(detect_collision_distance=200, height_change=50)

    drone_positions = {i+1:[p[0][0],p[0][1]] for i,p in enumerate(paths)}
    drone_heights = {i+1:200 for i in range(n_drones)}
    terminate_flags = [False]*n_drones

    while not all(terminate_flags):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate_flags = [True]*n_drones
                break

        frames = []
        for d in DRONE_OBJs:
            try:
                frame_obj = d.get_frame_read()
                frame = frame_obj.frame if hasattr(frame_obj, "frame") else frame_obj
                frames.append(frame)
            except Exception:
                frames.append(None)

        turns = []
        for i, frame in enumerate(frames):
            turn = 0
            if frame is not None:
                turn = CV_objs[i].center_subject(frame, i+1)
                if turn == 1: turn = 0
            turns.append(turn)

        for i, drone in enumerate(DRONE_OBJs):
            if terminate_flags[i]:
                continue

            x, y = drone_positions[i+1]
            goal = paths[i][-1]
            if math.dist([x,y], goal) < 20:
                terminate_flags[i] = True
                drone.send_rc(0,0,0,0)
                continue

            yaw = -1*drone.get_yaw()
            vel = DRONE_PATH_PLAN_OBJs[i].move_towards_goal(x, y, yaw, terminate_flags[i])

            collisions = avoider.detect_collisions(drone_positions)
            height_adjustments = avoider.assign_heights(collisions)
            z_vel = height_adjustments.get(i+1, 0)

            try:
                drone.send_rc(vel[0], vel[1], z_vel, turns[i])
                drone_positions[i+1][0] += vel[0]*0.1
                drone_positions[i+1][1] += vel[1]*0.1
                drone_heights[i+1] += z_vel*0.1
            except Exception:
                pass

        if cv2.waitKey(1) & 0xFF == ord('q'):
            terminate_flags = [True]*n_drones

        pygame.display.flip()

    time.sleep(5)
    cv2.destroyAllWindows()
    for d in DRONE_OBJs:
        d.land()
        d.streamoff()
    sys.exit(0)

except KeyboardInterrupt:
    for d in DRONE_OBJs:
        d.land()
        d.streamoff()
    sys.exit(1)

except Exception as e:
    logging.error(f"Error: {e}")
    for d in DRONE_OBJs:
        d.land()
        d.streamoff()
    sys.exit(1)
