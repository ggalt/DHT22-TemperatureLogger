import logging
import sys

from Sensors.QuickSensorReader import QuickSensorReader
from Utility.MeasurementCompare import MeasurementCompare

class QuickSensorDataHandler():
	' Class for handling Sensors and data gathered from sensors. Reads data, persists it to database and performs comparisons to see if temperature or humidity has changed more than set threshold allows'

	def __init__(self, configurations):
		self.logger = logging.getLogger(__name__)
		self.logger.info("QuickSensorDataHandler instantiation started")

		# Set passed in data to variables for further usage
		self.configurations = configurations
		# Instantiate sensor reader
		self.quickSensorReader = QuickSensorReader(self.configurations)
		# Instantiate mesurement comparer
		self.compareMeasurements = MeasurementCompare(self.configurations)
		# Create empty list for readings
		self.readingsFromSensors = {}
		self.failedSensors = []
		self.sensorTempsAndColors = {}

		self.logger.info("QuickSensorDataHandler instantiated")

	def readAndStoreSensorReadings(self):
		# Store sensor temperature and humidity readings with other relevant data
		try:
			self.readingsFromSensors, self.failedSensors = self.quickSensorReader.getSensorReadings()
			self.logger.info('Successfully read: %s sensors. Failed to read: %s sensor(s)',len(self.readingsFromSensors),len(self.failedSensors))
		except Exception as e:
			self.logger.error("Sensor reading raised exception",exc_info=True)
			raise

		# Check if measured values are beyond set limits
		try:
			self.sensorTempsAndColors = self._compareReadValuesWithSetLimits()
		except:
			self.logger.error("Failed to compare read value with set limits", exc_info=True)
			raise

		return self.sensorTempsAndColors

	def _compareReadValuesWithSetLimits(self):
		BLACK = (0, 0, 0)
		WHITE = (255, 255, 255)
		RED = (255, 0, 0)
		GREEN = (0, 255, 0)
		BLUE = (0, 0, 255)

		for key, value in self.readingsFromSensors.iteritems():

			self.logger.info('Perform delta check compare against previously measured results for sensor %s', key)

			myTemp = value.get('temperature')
			loTemp = value.get('temperatureLowLimit')
			hiTemp = value.get('temperatureHighLimit')

			if myTemp > hiTemp:
				self.sensorTempsAndColors[key] = (myTemp, RED)
			elif myTemp < loTemp:
				self.sensorTempsAndColors[key] = (myTemp, BLUE)
			else:
				self.sensorTempsAndColors[key] = (myTemp, GREEN)
