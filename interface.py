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
from map import mapStart
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

class DroneInterface:
    def __init__(self, path, personpospx, distanceInCm, angle, screen, droneimg, map):
        self.path = path
        self.personpospx = personpospx
        self.distanceInCm = distanceInCm
        self.angle = angle
        self.screen = screen
        self.droneimg = droneimg
        self.map = map
        self.yaw = 0
        self.target_yaw = None
        self.initial_yaw = None
        self.dronecurrent_pos = None
        self.dronenum_steps = None
        self.dx = None
        self.dy = None
        self.dronepoints = []
        self.droneangle_num_steps = 100
        self.start_pos = None
        self.end_pos = None
        self.rotating = True
        self.step = 0

    def drawPoints(self, screen, points, droneimg, yaw):
        screen_width, screen_height = pygame.display.get_surface().get_size()
        font = pygame.font.SysFont('Times',25)

        for point in points:
            pygame.draw.circle(screen, (255, 0, 0), point, 3) #draws a red dot/line for the visited nodes/area
        # Rotate the image based on the yaw angle and draw it on the screen
        rotated_image = pygame.transform.rotate(droneimg, -yaw)
        image_rect = rotated_image.get_rect(center=(points[-1][0], points[-1][1]))
        screen.blit(rotated_image, image_rect.topleft)

        pygame.draw.circle(screen, (0, 255, 0), points[-1], 3) #green dot on the image for tracking

        #adds positional text data, (0,0) is bottom left corner
        x_cord = (int)((points[-1][0]))
        y_cord  = (int)((screen_height  - points[-1][1]))
        position_text = font.render(f'({x_cord}, {y_cord})cm', True, (255, 0, 0))
        screen.blit(position_text, (points[-1][0] + 10, points[-1][1] + 10))

    def localize(self, updateTime = 0.004, angleUpdateTime = 0.005):
        x,y = 0, 0 # origin

        self.dronepoints = [(x, y)]

        self.start_pos = self.path[0]
        self.end_pos = self.path[1]

        # Initialize the current position
        self.dronecurrent_pos = list(self.start_pos)

        linearSpeed = 200
        angularSpeed = 50

        timeDur = self.distanceInCm/linearSpeed
        rotationDur = self.angle/angularSpeed

        self.dronenum_steps = int(timeDur / updateTime)
        self.droneangle_num_steps = 100

        # Calculate the increments in x and y directions
        self.dx = (self.end_pos[0] - self.start_pos[0]) / self.dronenum_steps
        self.dy = (self.end_pos[1] - self.start_pos[1]) / self.dronenum_steps

        self.initial_yaw = 0  # Initial yaw angle in 
        self.target_yaw = self.map.get_angle(self.path[0], self.personpospx, (self.path[0][0], self.path[0][1]+10))
        print(self.target_yaw)

        self.dronepoints.append(self.dronecurrent_pos)

        #start_time = pygame.time.get_ticks()  # Get the start time
        #rotation_done = False
        self.drawPoints(self.screen, self.dronepoints, self.droneimg, self.yaw)


    def update(self):
        if self.rotating:
            if self.yaw != self.target_yaw:
                if self.yaw < 0:
                    self.yaw += 360
                    # Ensure clockwise rotation
                if self.yaw > 180:
                    self.yaw -= 360
                self.yaw += abs(((self.target_yaw) - self.initial_yaw) / self.droneangle_num_steps)
                if abs(self.yaw - self.target_yaw) < 1:
                    self.yaw = self.target_yaw  # Snap to target yaw if close
                    self.rotating = False
        else:
            self.yaw = self.map.get_angle(self.dronecurrent_pos, self.personpospx, (self.dronecurrent_pos[0], self.dronecurrent_pos[1]+10))
            if self.step <= self.dronenum_steps:
                self.dronecurrent_pos[0] += self.dx
                self.dronecurrent_pos[1] += self.dy
                self.dronepoints.append(tuple(self.dronecurrent_pos))
                # Increment yaw angle
                self.dronepoints.append((int(self.dronecurrent_pos[0]), int(self.dronecurrent_pos[1])))
                self.step += 1
        self.drawPoints(self.screen, self.dronepoints, self.droneimg, self.yaw)

    def ensure_end(self):        
        self.dronecurrent_pos = self.end_pos
        self.dronepoints.append(tuple(self.dronecurrent_pos))
