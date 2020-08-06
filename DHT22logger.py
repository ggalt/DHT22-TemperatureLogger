# Copyright (c) 2015
# Author: Janne Posio

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE

# This script is intended to use with Adafruit DHT22 temperature and humidity sensors
# and with sensor libraries that Adafruit provides for them. This script alone, without
# sensor/s to provide data for it doesn't really do anyting useful.
# For guidance how to create your own temperature logger that makes use of this script,
# Adafruit DHT22 sensors and raspberry pi, visit : 
# http://www.instructables.com/id/Raspberry-PI-and-DHT22-temperature-and-humidity-lo/

#!/usr/bin/python2
#coding=utf-8

import sys
import logging, logging.handlers
import RPi.GPIO as GPIO

from threading import Event
from Debugger.Logger import Logger
from Utility.MailSender import MailSender
from Utility.WeeklyAverages import WeeklyAverages
from Database.DbActionController import DbController
from Configurations.ConfigHandler import ConfigHandler
from Sensors.SensorDataHandler import SensorDataHandler
from Sensors.QuickSensorDataHandler import QuickSensorDataHandler
from Utility.MyTimer import *

import pygame
import sched
import os
from time import sleep
from time import time


BLACK = (0,0,0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

#labels
FREEZER_LBL = "Freezer:"
FRIDGE_LBL = "Fridge:"
FRIDGE_FREEZER_LBL = "Fridge-Freezer:"

#sensor GPIO pins
FREEZER = 4
FRIDGE_FREEZER = 22
FRIDGE = 23

FIVE_MINUTES = 15

channel = 16

GPIO.setmode(GPIO.BOARD)
GPIO.setup(channel, GPIO.IN)
GPIO.setup(channel, GPIO.IN, pull_up_down=GPIO.PUD_UP)

loggerStopFlag = Event()


def time2Go():
    print("######################## time to go ######################")
    loggerStopFlag.set()
    sleep(0.5)
    GPIO.cleanup()
    sys.exit()

GPIO.add_event_detect(channel, GPIO.BOTH, callback=time2Go, bouncetime=200)

def loggerMain(a='default'):
	logger = logging.getLogger('DHT22Logger')
	print("###############################################################################################################")

	# Read configurations from config.json. If this fails, no need to run further -> terminate.
	try:
		configurationHandler = ConfigHandler()
		configurations = configurationHandler.getFullConfiguration()
	except Exception as e:
		logger.error('Failed to get configurations:\n',exc_info=True)
		sys.exit(0)

	# Instantiate dbController with configurations
	try:
		dbControl = DbController(configurations)
	except Exception as e:
		logger.error("dbController instantiation failed:\n",exc_info=True)
		sys.exit(0)

	# Instantiate mail sender
	# If mail sender instantiation fails, mail warnings cannot be send. Logger to db should work though, so no need for terminating
	try:
		mailSender = MailSender(configurations, dbControl)
		mailSenderAvailable = True
	except Exception as e:
		mailSenderAvailable = False
		logger.error('MailSender instantiation failed:\n',exc_info=True)

	# Instantiate sensorHandler and use it to read and persist readings
	try:
		SensorDataHandler(configurations,dbControl,mailSender).readAndStoreSensorReadings()
	except Exception as e:
		logger.error('Sensor data handling failed:\n',exc_info=True)
		if mailSenderAvailable:
			try:
				mailSender.sendWarningEmail("Error with sensor data handling.\nError message: {0}".format(e.message))
			except:
				logger.error('Sending warning mail failed\n',exc_info=True)

	# Weekly average temperatures - Used to check that rpi and connection is still alive
	# Check if mail sended is available, if not, no need to continue
	if mailSenderAvailable:
		logger.info("Check if weekly averages need to be sended")

		# Check if weekly average sending is enabled in configurations
		if configurationHandler.isWeeklyAveragesConfigEnabled():
			# Instantiate Weekly averages that handles configuration check etc.
			averagesSender = WeeklyAverages(configurations,dbControl,mailSender)

			# Go through configurations to check if connection check is enabled
			try:			
				# Sending is enabled and it is time to send. Execute
				averagesSender.performWeeklyAverageMailSending()
			# Log exceptions raised and send warning email
			except Exception as e:
				logger.error('Failed to check weekly averages\n',exc_info=True)
				try:
					mailSender.sendWarningEmail("Failed to send weekly averages.\nError message: {0}\nCheck debug log from Raspberry for more information".format(e.message))
				except Exception as e:
					logger.error('Failed to send email\n',exc_info=True)

	# SQL dump
	#Check if sql dump is enabled in configurations and if it is time to do the dump
	if configurationHandler.isBackupDumpConfigEnabled():
		# Yes, SQL dump is needed
		logger.info("Starting sql backup dump")
		try:
			# Call create sql backup dump
			dbControl.createSqlBackupDump()
		except Exception as e:
			logger.error('Failed to create SQL backup dump')
			if mailSenderAvailable:
				logger.error('Exception in DbBackupControl\n',exc_info=True)
				try:
					mailSender.sendWarningEmail('SQL Backup dump failed. Check debug log from raspberrypi for information')
				except Exception as e:
					logger.error('Failed to send email:\n',exc_info=True)
		logger.info("Sql backup dump finished")

	logger.info("DHT22logger execution finished\n")

def main():
	# Create logger for debugging purposes
	global locked
	try:
		Logger()
		logger = logging.getLogger()
	# Print to console if logger instantiation failed and terminate. Execution will fail anyway in next logging attempt
	except Exception as e: 
		print('Logger initialization failed. Error:\n{0}\nTry adding write permission directly to root (DHT22-TemperatureLogger) folder with "sudo chmod -R 777"'.format(e))
		sys.exit(0)

	#  First log entry to indicate execution has started
	logger.info("DHT22logger execution started")

	# Read configurations from config.json. If this fails, no need to run further -> terminate.
	try:
		configurationHandler = ConfigHandler()
		configurations = configurationHandler.getFullConfiguration()
	except Exception as e:
		logger.error('Failed to get configurations:\n',exc_info=True)
		sys.exit(0)

	os.putenv('SDL_FBDEV', '/dev/fb1')
	pygame.init()
	pygame.mouse.set_visible(False)
	lcd = pygame.display.set_mode((320, 240))
	lcd.fill(BLACK)
	pygame.display.update()

	font_big = pygame.font.Font(None, 35)
 
	label_pos = {FREEZER:(10,30), FRIDGE_FREEZER:(10,90), FRIDGE:(10,150)}
	temp_pos = {FREEZER:(310,30), FRIDGE_FREEZER:(310,90), FRIDGE:(310,150)}
	temp_label = {FREEZER:FREEZER_LBL, FRIDGE_FREEZER:FRIDGE_FREEZER_LBL, FRIDGE:FRIDGE_LBL}
	keyConnect = {FREEZER:"Freezer", FRIDGE_FREEZER:"Fridge-Freezer", FRIDGE:"Fridge-Fridge"}

	counter = 1
 
	loggerTimer = MyTimer(15,loggerStopFlag,loggerMain)
	loggerTimer.start()

	while counter < 4:

		counter += 1

		tempsAndColors = {}

		if locked == False:
			locked = True
  			# Instantiate sensorHandler and use it to read and persist readings
			try:
				tempsAndColors = QuickSensorDataHandler(configurations).readAndStoreSensorReadings()
			except Exception as e:
				logger.error('Sensor data handling failed:\n',exc_info=True)
		
			lcd.fill((0,0,0))

			for k,v in label_pos.items():
				l = temp_label[k]
				text_surface = font_big.render('%s'%l, True, WHITE)
				rect = text_surface.get_rect(topleft=v)
				lcd.blit(text_surface, rect)

				myTemp,myColor = tempsAndColors[keyConnect[k]]

				temp_surface = font_big.render('%.2f*F'%myTemp, True, myColor)
				temp_rect = temp_surface.get_rect(topright=temp_pos[k])
				lcd.blit(temp_surface, temp_rect)

			locked = False
			pygame.display.update()
			sleep(5)
	loggerStopFlag.set()

     

if __name__ == "__main__":
	main()
