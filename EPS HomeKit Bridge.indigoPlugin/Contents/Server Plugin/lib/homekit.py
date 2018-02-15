# lib.ui - Custom list returns and UI enhancements
#
# Copyright (c) 2018 ColoradoFourWheeler / EPS
#

import indigo
import logging

import ext
import dtutil

import sys, inspect


class HomeKit:

	#
	# Initialize the class
	#
	def __init__ (self, factory):
		self.logger = logging.getLogger ("Plugin.homekit")
		self.factory = factory
		
	#
	# Either map to the requested service class or figure out what this devices should be autodetected as
	#
	def getServiceObject (self, objId, serverId = 0, serviceClass = None, autoDetect = False, loadOptional = False, characterDict = {}, deviceActions = []):
		try:
			# Get all classes in this module
			clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
			serviceObj = None
			objId = int(objId) # Failsafe
			
			if serviceClass is None and autoDetect:
				serviceClass = self.detectHomeKitType (objId)
			
			# Find the class matching the name and instantiate the class
			for cls in clsmembers:
				if cls[0] == serviceClass:
					cclass = cls[1]
					serviceObj = cclass(self.factory, objId, serverId, characterDict, deviceActions, loadOptional)
					break
					
			if serviceObj is None: return None
			
			serviceObj = self._setIndigoDefaultValues (serviceObj)
			
			return serviceObj
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Return all service class names
	#
	def getHomeKitServices (self):
		try:
			classes = {}
			
			clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
			for cls in clsmembers:
				if "service_" in cls[0]:
					cclass = cls[1]
					#factory, objId, characterDict = {}, deviceActions = [], loadOptional = False
					obj = cclass (self.factory, 0)
					classes[cls[0]] = obj.desc
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return classes
			
	#
	# Detect a HomeKit type from an Indigo type
	#
	def detectHomeKitType (self, objId):
		try:
			if objId in indigo.actionGroups:
				return "service_Switch"
				
			dev = indigo.devices[objId]
				
			if dev.pluginId == "com.perceptiveautomation.indigoplugin.zwave" and dev.deviceTypeId == "zwLockType":
				return "service_LockMechanism"
			
			elif "brightnessLevel" in dev.states and "brightness" in dir(dev):
				return "service_Lightbulb"
			
			elif "Outlet" in dev.model:
				return "service_Outlet"
			
			elif "speedIndex" in dir(dev):
				return "service_Fanv2"
			
			elif "sensorInputs" in dir(dev):	
				if "protocol" in dir(dev) and unicode(dev.protocol) == "Insteon" and dev.model == "I/O-Linc Controller":
					return "service_GarageDoorOpener"
				
				else:
					return "service_GarageDoorOpener"
			
			elif "sensorValue" in dir(dev):
				if unicode(dev.protocol) == "Insteon" and "Motion Sensor" in dev.model: 
					return "service_MotionSensor"
				
				else:
					return "service_MotionSensor"
					
			elif "supportsCoolSetpoint" in dir(dev):
				return "service_Thermostat"
				
			else:
				# Fallback but only if there is an onstate, otherwise we return an unknown
				if "onState" in dir(dev):
					return "service_Switch"
				else:
					return "Dummy"
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
	
	
	
	################################################################################
	# DEVICE CONVERSIONS FROM INDIGO TO HOMEKIT
	################################################################################		
	#
	# Convert Indigo boolean to 0/1
	#
	def _homeKitBooleanAttribute (self, dev, attribute):
		try:
			curval = 0
			
			if attribute in dir(dev):
				obj = getattr (dev, attribute)
				if obj: 
					curval = 1
				else:
					curval = 0
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return curval
	
	#
	# Assign default values and actions for various device types
	#
	def _setIndigoDefaultValues (self, serviceObj):
		try:
			definedActions = []
			for a in serviceObj.actions:
				#definedActions.append (a["name"])
				definedActions.append (a.characteristic)
				
				
			if serviceObj.objId in indigo.actionGroups:
				# Always a switch object so set switch defaults
				if "On" not in serviceObj.characterDict: serviceObj.characterDict["On"] = False
				if "On" not in definedActions:
					serviceObj.actions.append (HomeKitAction("On", "equal", True, "actionGroup.execute", [serviceObj.objId], 0, {}))
										
				return serviceObj
						
			if serviceObj.objId not in indigo.devices: return
			
			dev = indigo.devices[serviceObj.objId]
				
			# Derive the service class to auto call the matching conversion function
			serviceClassName = str(type(serviceObj)).replace("<class 'lib.homekit.service_", "").replace("'>", "")
			if "_setIndigoDefaultValues_{}".format(serviceClassName) in dir(self):
				func = getattr (self, "_setIndigoDefaultValues_{}".format(serviceClassName))
				serviceObj =  func (serviceObj, definedActions, dev)
			
			return serviceObj
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return serviceObj
		
			
	#
	# Check for the presence of an attrib in indigo device and characteristic in the service and set the value if it's not been set
	#
	def _setServiceValueFromAttribute (self, serviceObj, dev, attribName, characteristic, value = None):
		try:
			if attribName in dir(dev) and characteristic not in serviceObj.characterDict: 
				if value is not None: 
					serviceObj.characterDict[characteristic] = value
				else:
					attrib = getattr (dev, attribName)
					serviceObj.characterDict[characteristic] = attrib
				
			return serviceObj		
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return serviceObj
		
	#
	# Check for the presence of a state in indigo device and characteristic in the service and set the value if it's not been set
	#
	def _setServiceValueFromState (self, serviceObj, dev, stateName, characteristic, value = None):
		try:
			if stateName in dev.states and characteristic not in serviceObj.characterDict: 
				if value is not None: 
					serviceObj.characterDict[characteristic] = value
				else:
					serviceObj.characterDict[characteristic] = dev.states[stateName]
				
			return serviceObj		
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
		return serviceObj	
		
	#
	# Auto convert temperature based on settings
	#
	def setTemperatureValue (self, serviceObj, value):
		try:
			if serviceObj.serverId != 0:
				server = indigo.devices[serviceObj.serverId]
				if "tempunits" in server.pluginProps:
					# If our source is celsius then that's what HomeKit wants, just return it
					if server.pluginProps["tempunits"] == "c": return value
					
					# If our source is fahrenheit then we need to convert it
					value = float(value)
					value = (value - 32) / 1.8000
					return round(value, 2)
					
					return (round(((value - 32.0) * 5.0 / 9.0) * 10.0) / 10.0)# - .5 # -1 to adjust it to be correct?
		
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
	# ==============================================================================
	# FAN V2 DEFAULTS
	# ==============================================================================
	def _setIndigoDefaultValues_Fanv2xxx (self, serviceObj, definedActions, dev):	
		try:
			if type(dev) == indigo.SpeedControlDevice:
				serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "Active", self._homeKitBooleanAttribute (dev, "onState"))
				#serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "CurrentFanState", self._homeKitBooleanAttribute (dev, "onState") + 1)
				#serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "TargetFanState", 0) # Not supported
				serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "speedLevel", "RotationSpeed")
				
				if "Active" not in definedActions:
					serviceObj.actions.append (HomeKitAction("Active", "equal", 0, "device.turnOff", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
					serviceObj.actions.append (HomeKitAction("Active", "equal", 1, "device.turnOn", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
				
				if "RotationSpeed" not in definedActions:
					serviceObj.actions.append (HomeKitAction("RotationSpeed", "between", 0, "speedcontrol.setSpeedLevel", [serviceObj.objId, "=value="], 100, {serviceObj.objId: "attr_speedLevel"}))

			if type(dev) == indigo.ThermostatDevice:
				serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "fanIsOn", "Active", self._homeKitBooleanAttribute (dev, "fanIsOn"))
				#serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "fanIsOn", "CurrentFanState", self._homeKitBooleanAttribute (dev, "fanIsOn") + 1)
				#serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "fanIsOn", "TargetFanState", 0)
				
				#if "TargetFanState" not in definedActions:
				#	serviceObj.actions.append (HomeKitAction("TargetFanState", "equal", 0, "thermostat.setFanMode", [serviceObj.objId, indigo.kFanMode.Auto], 0, {serviceObj.objId: "attr_fanIsOn"}))
				#	serviceObj.actions.append (HomeKitAction("TargetFanState", "equal", 1, "thermostat.setFanMode", [serviceObj.objId, indigo.kFanMode.AlwaysOn], 0, {serviceObj.objId: "attr_fanMode"}))
				
				if "Active" not in definedActions:
					serviceObj.actions.append (HomeKitAction("Active", "equal", 0, "thermostat.setFanMode", [serviceObj.objId, indigo.kFanMode.Auto], 0, {serviceObj.objId: "attr_fanIsOn"}))
					serviceObj.actions.append (HomeKitAction("Active", "equal", 1, "thermostat.setFanMode", [serviceObj.objId, indigo.kFanMode.AlwaysOn], 0, {serviceObj.objId: "attr_fanMode"}))
				
			if type(dev) == indigo.RelayDevice:
				serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "Active", self._homeKitBooleanAttribute (dev, "onState"))
				#serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "CurrentFanState", self._homeKitBooleanAttribute (dev, "onState") + 1)
				#serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "TargetFanState", 1)
				
				if "Active" not in definedActions:
					serviceObj.actions.append (HomeKitAction("Active", "equal", 0, "device.turnOff", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
					serviceObj.actions.append (HomeKitAction("Active", "equal", 1, "device.turnOn", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))

			if type(dev) == indigo.DimmerDevice:
				serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "Active", self._homeKitBooleanAttribute (dev, "onState"))
				serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "brightness", "RotationSpeed")
				
				if "Active" not in definedActions:
					serviceObj.actions.append (HomeKitAction("Active", "equal", 0, "device.turnOff", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
					serviceObj.actions.append (HomeKitAction("Active", "equal", 1, "device.turnOn", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))

				if "RotationSpeed" not in definedActions:
					serviceObj.actions.append (HomeKitAction("RotationSpeed", "between", 0, "dimmer.setBrightness", [serviceObj.objId, "=value="], 100, {serviceObj.objId: "attr_brightness"}))


			return serviceObj
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return serviceObj		
			
	# ==============================================================================
	# GARAGE DOOR OPENER DEFAULTS
	# ==============================================================================
	def _setIndigoDefaultValues_GarageDoorOpenerxxx (self, serviceObj, definedActions, dev):	
		try:
			# Insteon Multi I/O controller
			if "protocol" in dir(dev) and unicode(dev.protocol) == "Insteon" and dev.model == "I/O-Linc Controller":
				if "binaryInput1" in dev.states and "CurrentDoorState" not in serviceObj.characterDict: 
					serviceObj.characterDict["CurrentDoorState"] = 1 # Open
					if not dev.states["binaryInput1"]: serviceObj.characterDict["CurrentDoorState"] = 0 # Closed
					
				if "binaryInput1" in dev.states and "TargetDoorState" not in serviceObj.characterDict: 
					serviceObj.characterDict["TargetDoorState"] = 1 # Open
					if not dev.states["binaryInput1"]: serviceObj.characterDict["TargetDoorState"] = 0 # Closed	
					
				if "ObstructionDetected" not in serviceObj.characterDict: serviceObj.characterDict["ObstructionDetected"] = False # Unsupported but it's required right now
			
				#if "CurrentDoorState" not in definedActions:
				#	serviceObj.actions.append (HomeKitAction("CurrentDoorState", "equal", 0, "iodevice.setBinaryOutput", [serviceObj.objId, 1, True], 0, {serviceObj.objId: "state_binaryInput1"}))
				#	serviceObj.actions.append (HomeKitAction("CurrentDoorState", "equal", 1, "iodevice.setBinaryOutput", [serviceObj.objId, 1, True], 0, {serviceObj.objId: "state_binaryInput1"}))
					
				if "TargetDoorState" not in definedActions:
					serviceObj.actions.append (HomeKitAction("TargetDoorState", "equal", 0, "iodevice.setBinaryOutput", [serviceObj.objId, 0, True], 0, {serviceObj.objId: "state_binaryInput1"}))
					serviceObj.actions.append (HomeKitAction("TargetDoorState", "equal", 1, "iodevice.setBinaryOutput", [serviceObj.objId, 0, True], 0, {serviceObj.objId: "state_binaryInput1"}))	
		
			return serviceObj
		
		except Exception as e:
			serviceObj.logger.error (ext.getException(e))	
			return serviceObj			
						
			
	# ==============================================================================
	# LIGHTBULB DEFAULTS
	# ==============================================================================
	def _setIndigoDefaultValues_Lightbulbxxx (self, serviceObj, definedActions, dev):	
		try:
			serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "On")
			serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "brightness", "Brightness")
			
			if "On" not in definedActions:
				serviceObj.actions.append (HomeKitAction("On", "equal", False, "device.turnOff", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
				serviceObj.actions.append (HomeKitAction("On", "equal", True, "device.turnOn", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
				
			if "Brightness" not in definedActions:
				serviceObj.actions.append (HomeKitAction("Brightness", "between", 0, "dimmer.setBrightness", [serviceObj.objId, "=value="], 100, {serviceObj.objId: "attr_brightness"}))
	
			return serviceObj
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return serviceObj	
			
	# ==============================================================================
	# MOTION SENSOR DEFAULTS
	# ==============================================================================
	def _setIndigoDefaultValues_MotionSensorxxx (self, serviceObj, definedActions, dev):	
		try:
			serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "MotionDetected")
			
			if "batteryLevel" in dir(dev) and dev.batteryLevel is not None: 
				serviceObj.characterDict["StatusLowBattery"] = 0
				
				if "lowbattery" in self.factory.plugin.pluginPrefs:
					lowbattery = int(self.factory.plugin.pluginPrefs["lowbattery"])
					if lowbattery > 0: lowbattery = lowbattery / 100
					
					if dev.batteryLevel < ((100 * lowbattery) + 1): serviceObj.characterDict["StatusLowBattery"] = 1
					
			# Special consideration for Fibaro sensors that fill up a couple more Characteristics (if this grows we may need to call a function for these)
			if "model" in dir(dev) and "FGMS001" in dev.model:
				# See if we can find all the devices with this Zwave ID
				for idev in indigo.devices.iter("com.perceptiveautomation.indigoplugin.zwave.zwOnOffSensorType"):
					if idev.address == dev.address:
						# Same Fibaro model
						if "Tilt/Tamper" in idev.subModel:
							serviceObj.characterDict["StatusTampered"] = 0
							if idev.onState: serviceObj.characterDict["StatusTampered"] = 1
							
							# Make sure this gets added to our watch list
							serviceObj.actions.append (HomeKitAction("StatusTampered", "equal", False, "device.turnOff", [idev.id], 0, {idev.id: "attr_onState"}))
						
			
			# This is a read only device so it'll never need this but it must be here so when we get activity for this device we can tell
			# homekit to update, if this isn't here it'll never know that attr_onState should trigger an HK update
			serviceObj.actions.append (HomeKitAction("MotionDetected", "equal", False, "device.turnOff", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
			serviceObj.actions.append (HomeKitAction("StatusLowBattery", "equal", False, "device.turnOff", [serviceObj.objId], 0, {serviceObj.objId: "attr_batteryLevel"}))
				
			return serviceObj
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return serviceObj		
			
	# ==============================================================================
	# OUTLET DEFAULTS
	# ==============================================================================
	def _setIndigoDefaultValues_Outletxxx (self, serviceObj, definedActions, dev):	
		try:
			serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "On")
			serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "OutletInUse")
			
			if "On" not in definedActions:
				serviceObj.actions.append (HomeKitAction("On", "equal", False, "device.turnOff", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
				serviceObj.actions.append (HomeKitAction("On", "equal", True, "device.turnOn", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
			
			return serviceObj
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return serviceObj	
			
	# ==============================================================================
	# LOCK MECHANISM DEFAULTS
	# ==============================================================================
	def _setIndigoDefaultValues_LockMechanismxxx (self, serviceObj, definedActions, dev):	
		try:
			serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "LockCurrentState", self._homeKitBooleanAttribute (dev, "onState"))
			serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "LockTargetState", self._homeKitBooleanAttribute (dev, "onState"))
			
			if "LockTargetState" not in definedActions:
				serviceObj.actions.append (HomeKitAction("LockTargetState", "equal", 0, "device.turnOff", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
				serviceObj.actions.append (HomeKitAction("LockTargetState", "equal", 1, "device.turnOn", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
			
			return serviceObj
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return serviceObj								
			
	# ==============================================================================
	# SWITCH DEFAULTS
	# ==============================================================================
	def _setIndigoDefaultValues_Switchxxx (self, serviceObj, definedActions, dev):	
		try:
			if "onState" in dir(dev) and "On" not in serviceObj.characterDict: 
				serviceObj.characterDict["On"] = dev.onState	
			else:
				serviceObj.characterDict["On"] = False # Since all devices default to this type, this ensure that we never have NO characteristics
			
			if "On" not in definedActions:
				serviceObj.actions.append (HomeKitAction("On", "equal", False, "device.turnOff", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))
				serviceObj.actions.append (HomeKitAction("On", "equal", True, "device.turnOn", [serviceObj.objId], 0, {serviceObj.objId: "attr_onState"}))

			return serviceObj
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return serviceObj		

	# ==============================================================================
	# THERMOSTAT DEFAULTS
	# ==============================================================================
	def _setIndigoDefaultValues_Thermostat (self, serviceObj, definedActions, dev):	
		try:
			targettemp = 0
			
			if "TemperatureDisplayUnits" not in serviceObj.characterDict and serviceObj.serverId != 0:
				server = indigo.devices[serviceObj.serverId]
				if "tempunits" in server.pluginProps:
					if server.pluginProps["tempunits"] == "c":
						serviceObj.characterDict["TemperatureDisplayUnits"] = 0
					else:
						serviceObj.characterDict["TemperatureDisplayUnits"] = 1
						
				else:
					serviceObj.characterDict["TemperatureDisplayUnits"] = 0						
		
			serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "hvacMode", "CurrentHeatingCoolingState")
			if "CurrentHeatingCoolingState" in serviceObj.characterDict: 
				if str(serviceObj.characterDict["CurrentHeatingCoolingState"]) == "Heat": # Standard Indigo thermostat
					serviceObj.characterDict["CurrentHeatingCoolingState"] = 1
				elif str(serviceObj.characterDict["CurrentHeatingCoolingState"]) == "Cool": 
					serviceObj.characterDict["CurrentHeatingCoolingState"] = 2
				else:
					serviceObj.characterDict["CurrentHeatingCoolingState"] = 0 # Off
					
			if "TargetHeatingCoolingState" not in serviceObj.characterDict and "CurrentHeatingCoolingState" in serviceObj.characterDict: serviceObj.characterDict["TargetHeatingCoolingState"] = serviceObj.characterDict["CurrentHeatingCoolingState"]
			
			#serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "onState", "TargetHeatingCoolingState", self._homeKitBooleanAttribute (dev, "onState"))
			serviceObj = self._setServiceValueFromState (serviceObj, dev, "temperatureInput1", "CurrentTemperature", self.setTemperatureValue(serviceObj, dev.states["temperatureInput1"]))
			
			if "CurrentHeatingCoolingState" in serviceObj.characterDict and serviceObj.characterDict["CurrentHeatingCoolingState"] == 2: 
				serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "coolSetpoint", "TargetTemperature", self.setTemperatureValue(serviceObj, dev.coolSetpoint))
			else:
				serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "heatSetpoint", "TargetTemperature", self.setTemperatureValue(serviceObj, dev.heatSetpoint))
			
			serviceObj = self._setServiceValueFromState (serviceObj, dev, "humidityInput1", "CurrentRelativeHumidity")
			#serviceObj = self._setServiceValueFromState (serviceObj, dev, "humidityInput1", "TargetRelativeHumidity") # Only if they can set humidity
			#serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "coolSetpoint", "CoolingThresholdTemperature", self.setTemperatureValue(serviceObj, dev.coolSetpoint))
			#serviceObj = self._setServiceValueFromAttribute (serviceObj, dev, "heatSetpoint", "HeatingThresholdTemperature", self.setTemperatureValue(serviceObj, dev.heatSetpoint))
			
			if "TargetTemperature" not in definedActions:
				serviceObj.actions.append (HomeKitAction("TargetTemperature", "between", 0.0, "homekit.commandSetTargetThermostatTemperature", [serviceObj.objId, serviceObj.serverId, "=value="], 100.0, {serviceObj.objId: "attr_coolSetpoint"}))
			
			if "TargetHeatingCoolingState" not in definedActions: # Using various states/attribs for watching instead of using stubs since we have 4 of these
				serviceObj.actions.append (HomeKitAction("TargetHeatingCoolingState", "equal", 0, "thermostat.setHvacMode", [serviceObj.objId, indigo.kHvacMode.Off], 0, {serviceObj.objId: "attr_heatSetpoint"}))
				serviceObj.actions.append (HomeKitAction("TargetHeatingCoolingState", "equal", 1, "thermostat.setHvacMode", [serviceObj.objId, indigo.kHvacMode.Heat], 0, {serviceObj.objId: "state_temperatureInput1"}))
				serviceObj.actions.append (HomeKitAction("TargetHeatingCoolingState", "equal", 2, "thermostat.setHvacMode", [serviceObj.objId, indigo.kHvacMode.Cool], 0, {serviceObj.objId: "state_humidityInput1"}))
				serviceObj.actions.append (HomeKitAction("TargetHeatingCoolingState", "equal", 3, "thermostat.setHvacMode", [serviceObj.objId, indigo.kHvacMode.HeatCool], 0, {serviceObj.objId: "attr_hvacMode"}))

			

			# Stubs so we monitor for state changes
			#serviceObj.actions.append (HomeKitAction("STUB", "equal", True, "NULL", [serviceObj.objId], 0, {serviceObj.objId: "attr_heatSetpoint"}))
			#serviceObj.actions.append (HomeKitAction("STUB", "equal", True, "NULL", [serviceObj.objId], 0, {serviceObj.objId: "state_temperatureInput1"}))
			#serviceObj.actions.append (HomeKitAction("STUB", "equal", True, "NULL", [serviceObj.objId], 0, {serviceObj.objId: "state_humidityInput1"}))
			#serviceObj.actions.append (HomeKitAction("STUB", "equal", True, "NULL", [serviceObj.objId], 0, {serviceObj.objId: "attr_hvacMode"}))
			
			return serviceObj
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			return serviceObj			

################################################################################
# BASE SERVICE CLASS THAT ALL SERVICE CLASSES INHERIT
#
# Handles all functionality for each service type
################################################################################
class Service (object):

	#
	# Initialize the class (Won't happen unless called from child)
	#
	def __init__ (self, factory, hktype, desc, objId, serverId, deviceCharacteristics, deviceActions, loadOptional):
		self.logger = logging.getLogger ("Plugin.HomeKit.Service." + hktype)
		self.factory = factory
		
		try:
			self.type = hktype
			self.desc = desc
			self.objId = objId
			self.required = []
			self.optional = []
			self.native = True # Functions can map directly to Indigo or a plugin (see requiresPlugin) natively without any customization
			self.requiresPlugin = [] # For this device to work Indigo must have one or more plugins installed
			self.actions = []	
			self.characterDict = {}
			self.loadOptional = loadOptional # Create attributes for the optional fields
			self.serverId = serverId
			self.indigoType = "Unable to detect"
			
			# Get the indigo class for this object
			if objId in indigo.devices:
				#indigo.server.log("adding device type {}".format(indigo.devices[objId].name))
				self.indigoType = str(type(indigo.devices[objId])).replace("<class '", "").replace("'>", "")
			elif objId in indigo.actionGroups:
				self.indigoType = "indigo.actionGroup"
			
			# We have to append from here, if we were to set self.actions equal an outside list it would share among all instances of this class
			for d in deviceActions:
				self.actions.append (d)
		
			for k, v in deviceCharacteristics.iteritems():
				self.characterDict[k] = v
			
			self.deviceInitialize()
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	def __str__ (self):
		ret = ""
		
		ret += "Service : \n"
		
		ret += "\talias : {0}\n".format(self.alias.value)
		ret += "\tmodel : {0}\n".format(self.model.value)
		ret += "\tsubModel : {0}\n".format(self.subModel.value)
		ret += "\tindigoType : {0}\n".format(self.indigoType)
		
		ret += "\ttype : {0}\n".format(self.type)
		ret += "\tdesc : {0}\n".format(self.desc)
		ret += "\tobjId : {0}\n".format(unicode(self.objId))
		
		ret += "\trequired : (List)\n"
		for i in self.required:
			if i in dir(self):
				obj = getattr(self, i)
				ret += "\t\t{0} : {1}\n".format(i, unicode(obj.value))
			else:
				ret += "\t\t{0}\n".format(i)

		
		ret += "\toptional : (List)\n"
		for i in self.optional:
			if i in dir(self):
				obj = getattr(self, i)
				ret += "\t\t{0} : {1}\n".format(i, unicode(obj.value))
			else:
				ret += "\t\t{0}\n".format(i)
		
		ret += "\tnative : {0}\n".format(unicode(self.native))
		
		ret += "\trequiresPlugin : (List)\n"
		for i in self.requiresPlugin:
			ret += "\t\t{0}\n".format(i)
		
		ret += "\tactions : (List)\n"
		for i in self.actions:
			ret += "\t\tAction : (HomeKitAction)\n"
			ret += "\t\t\tCharacteristic : {0}\n".format(i.characteristic)
			ret += "\t\t\tWhen : {0}\n".format(i.whenvalueis)
			ret += "\t\t\tValue : {0} ({1})\n".format(unicode(i.whenvalue), str(type(i.whenvalue)).replace("<type '", "").replace("'>", "") )
			ret += "\t\t\tValue2 : {0} ({1})\n".format(unicode(i.whenvalue2), str(type(i.whenvalue)).replace("<type '", "").replace("'>", ""))
			ret += "\t\t\tCommand : {0}\n".format(unicode(i.command))
			ret += "\t\t\tArguments : {0}\n".format(unicode(i.arguments))
		
		ret += "\tloadOptional : {0}\n".format(unicode(self.loadOptional))
		
		ret += "\tcharacterDict : (Dict)\n"
		for i, v in self.characterDict.iteritems():
			ret += "\t\t{0} : {1}\n".format(i, unicode(v))
		
		return ret		
			
	#
	# Device startup to set various attributes
	#
	def deviceInitialize (self):
		try:
			self.model = characteristic_Name()
			self.subModel = characteristic_Name()
			self.alias = characteristic_Name()
			
			if self.objId == 0: 
				self.alias.value = "Invalid Indigo Object"
				return
			
			if self.objId in indigo.devices: 
				obj = indigo.devices[self.objId]
				self.model.value = obj.model
				self.model.value = obj.subModel
				
			if self.objId in indigo.actionGroups: 
				obj = indigo.actionGroups[self.objId]
				self.model.value = "Action Group"
			
			self.alias = characteristic_Name()
			self.alias.value = obj.name
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	
	#
	# Set device attributes from the required and optional parameters
	#
	def setAttributes (self):
		try:
			# Build a list of all classes in this module and turn it into a dict for lookup
			clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
			classes = {}
			for cls in clsmembers:
				classes[cls[0]] = cls[1]

			# Add all required characteristics
			for a in self.required:
				classname = "characteristic_{}".format(a)
				if classname in classes:
					self.logger.threaddebug ("Adding {} attribute to {}".format(a, self.alias.value))
					cclass = classes[classname]
					setattr (self, a, cclass())
					
			# Add optional characteristics if they were added by the call or if the loadOptional was set as true
			for a in self.optional:
				if a in self.characterDict or self.loadOptional:
					classname = "characteristic_{}".format(a)
					if classname in classes:
						self.logger.threaddebug ("Adding {} attribute to {}".format(a, self.alias.value))
						cclass = classes[classname]
						setattr (self, a, cclass())
						
			# If they passed values then use them, this also lets us audit to ensure no rogue values that don't apply get weeded out
			for key, value in self.characterDict.iteritems():
				if key in dir(self):
					self.setAttributeValue (key, value)
			
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Set device attributes from the required and optional parameters
	#
	def setAttributesv2 (self):
		try:
			# Use the previous method for actions since it handles it well
			if self.indigoType == "indigo.actionGroup": 
				# All action groups are switches, period, never anything else regardless of what someone may call them
				setattr (self, "On", characteristic_On())
				if "On" not in self.characterDict: self.characterDict["On"] = False
				if "On" not in self.actions:
					self.actions.append (HomeKitAction("On", "equal", True, "actionGroup.execute", [self.objId], 0, {}))
					
				return
				
			if self.objId == 0: return # We'll error out all over the place when we do fake instantiation for getting service defaults
			
			# Build a list of all classes in this module and turn it into a dict for lookup
			clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
			classes = {}
			for cls in clsmembers:
				classes[cls[0]] = cls[1]

			# Add all required characteristics
			self.detCharacteristicValues (classes, self.requiredv2)
			
			# Add all optional characteristics
			self.detCharacteristicValues (classes, self.optionalv2, True)
					
			
		except Exception as e:
			self.logger.error (ext.getException(e))		
			
	#
	# Set device attribute from service definition fields
	#
	def detCharacteristicValues (self, classes, sourceDict, isOptional = False):
		try:
			for characteristic, getters in sourceDict.iteritems():
				# While working on this, back out if there's no type
				if "indigoType" not in dir(self): 
					return
				
				# See if this type is in the getters
				getter = None
				if self.indigoType in getters:
					getter = getters[self.indigoType]
				elif "*" in getters:
					getter = getters["*"]
					
				if getter is None: 
					if isOptional: 
						continue # Nothing to do
					else:
						getter =  "attr_STUB" # we MUST pass all required items, so force this through the works and we'll continue out after it creates our attribute
				
				# See if this characteristic can get a value at all
				hasvalue = False
				if getter[0:5] == "attr_":
					if getter.replace("attr_", "") in dir(indigo.devices[self.objId]): hasvalue = True
					
				if getter[0:6] == "state_":
					obj = indigo.devices[self.objId]
					if "states" in dir(obj) and getter.replace("state_", "") in obj.states: hasvalue = True
					
				if getter[0:8] == "special_":
					hasvalue = True # Always force these through
					
				# Exit now if it's optional fields and we dont want them
				if isOptional:
					if characteristic in self.characterDict or self.loadOptional or hasvalue:
						pass
					else:
						return
			
				# Create the characteristic as an attribute
				classname = "characteristic_{}".format(characteristic)
				if classname in classes:
					self.logger.threaddebug ("Adding {} attribute to {}".format(characteristic, self.alias.value))
					cclass = classes[classname]
					setattr (self, characteristic, cclass())
					
					if getter == "attr_STUB":
						# Add the default value to the characterdict so it passes through to the API and then exit out
						if characteristic not in self.characterDict: self.characterDict[characteristic] = getattr (self, characteristic).value
						continue
					
				if getter[0:5] == "attr_":
					if getter.replace("attr_", "") in dir(indigo.devices[self.objId]): 
						obj = indigo.devices[self.objId]
						obj = getattr (obj, getter.replace("attr_", ""))
						self.setAttributeValue (characteristic, obj)
						if characteristic not in self.characterDict: self.characterDict[characteristic] = getattr (self, characteristic).value
						
						# Since we are here we can calculate the actions needed to change this attribute
						self.calculateDefaultActionsForAttribute (getter.replace("attr_", ""), characteristic)
						
				elif getter[0:6] == "state_":
					obj = indigo.devices[self.objId]
					if "states" in dir(obj) and getter.replace("state_", "") in obj.states: 
						if "states" in dir(obj) and getter.replace("state_", "") in obj.states:
							self.setAttributeValue (characteristic, obj.states[getter.replace("state_", "")])
							if characteristic not in self.characterDict: self.characterDict[characteristic] = getattr (self, characteristic).value
							
							# Since we are here we can calculate the actions needed to change this attribute
							self.calculateDefaultActionsForState (getter.replace("state_", ""), characteristic)
							
				else:
					# If we have a battery level then add this value
					if getter == "special_lowbattery":
						obj = indigo.devices[self.objId]
						if "batteryLevel" in dir(obj) and "lowbattery" in self.factory.plugin.pluginPrefs:
							lowbattery = int(self.factory.plugin.pluginPrefs["lowbattery"])
							if lowbattery > 0: lowbattery = lowbattery / 100
							if obj.batteryLevel < ((100 * lowbattery) + 1): 
								self.setAttributeValue (characteristic, 1)
								self.characterDict[characteristic] = 1
							else:
								self.setAttributeValue (characteristic, 0)
								self.characterDict[characteristic] = 0
								
							# So we get notified of any changes, add a trigger for this in actions, it won't do anything other than monitor
							self.actions.append (HomeKitAction(characteristic, "equal", False, "device.turnOff", [self.objId], 0, {self.objId: "attr_batteryLevel"}))
						
						else:
							self.characterDict[characteristic] = 0
						
					# Mostly for outlets, will read a load if supported and report as in use or will default to the onState
					if getter == "special_inuse":
						obj = indigo.devices[self.objId]
						if "energyCurLevel" in dir(obj) and obj.energyCurLevel is not None:
							# It supports energy reporting
							if obj.energyCurLevel > 0:
								self.setAttributeValue (characteristic, True)
								self.characterDict[characteristic] = True
							else:
								self.setAttributeValue (characteristic, False)
								self.characterDict[characteristic] = False
						else:
							if "onState" in dir(obj) and obj.onState:
								self.setAttributeValue (characteristic, True)
								self.characterDict[characteristic] = True
							else:
								self.setAttributeValue (characteristic, False)
								self.characterDict[characteristic] = False
							
							
		except Exception as e:
			self.logger.error (ext.getException(e) + "\nFor object id {} alias '{}'".format(str(self.objId), self.alias.value))		

			
	#
	# Calculate default actions based on the attribute value that is being changed
	#
	def calculateDefaultActionsForAttribute (self, attrib, characteristic):
		try:
			if characteristic in self.actions: return # The user has passed their own actions
			if characteristic not in dir(self): return # We need to reference the details, it should have been created by now
			
			a = getattr (self, characteristic)
			invalidType = False
			
			if a.readonly: 
				self.logger.threaddebug ("Not setting a default action for {} because that characteristic is read only".format(characteristic))
				return # There are no actions for readonly characteristics, why add unnecessary data?
			
			# Define some defaults
			minValue = 0
			maxValue = 100
			minStep = 1
			trueValue = True
			falseValue = False
			method = "UNKNOWN"
			if "minValue" in dir(a): minValue = a.minValue
			if "maxValue" in dir(a): maxValue = a.maxValue
			if "minStep" in dir(a): minStep = a.minStep
			
			# Determine which data method the characteristic is using (T/F, 0/1, Range)
			if type(a.value) == bool:
				method = "TF"
				
			elif "validValues" in dir(a) and len(a.validValues) == 2:
				method = "01"
				trueValue = 1
				falseValue = 0
								
			elif "validValues" in dir(a) and len(a.validValues) > 2:
				method = "RANGE"
				
			elif "validValues" not in dir(a) and "minValue" in dir(a):
				method = "RANGE"
			
			# MOST DEVICES
			if attrib == "onState":	
				if method == "TF" or method == "01":			
					self.actions.append (HomeKitAction(characteristic, "equal", falseValue, "device.turnOff", [self.objId], 0, {self.objId: "attr_onState"}))
					self.actions.append (HomeKitAction(characteristic, "equal", trueValue, "device.turnOn", [self.objId], 0, {self.objId: "attr_onState"}))
		
				elif method == "RANGE":
					self.actions.append (HomeKitAction(characteristic, "equal", minValue, "device.turnOff", [self.objId], 0, {self.objId: "attr_onState"}))
					self.actions.append (HomeKitAction(characteristic, "between", minValue + minStep, "device.turnOn", [self.objId], maxValue, {self.objId: "attr_onState"}))	
					
				else:
					invalidType = True
			
			# DIMMERS
			elif attrib == "brightness":
				cmd = "dimmer.setBrightness"
				if method == "TF" or method == "01":		
					self.actions.append (HomeKitAction(characteristic, "equal", falseValue, cmd, [self.objId, 0], 0, {self.objId: "attr_brightness"}))
					self.actions.append (HomeKitAction(characteristic, "equal", trueValue, cmd, [self.objId, 100], 0, {self.objId: "attr_brightness"}))
			
				elif method == "RANGE":
					self.actions.append (HomeKitAction(characteristic, "between", minValue, cmd, [self.objId, "=value="], maxValue, {self.objId: "attr_brightness"}))
				
				else:
					invalidType = True
			
			# SPEED CONTROL	
			elif attrib == "speedLevel":
				cmd = "speedcontrol.setSpeedLevel"
				if method == "TF" or method == "01":		
					self.actions.append (HomeKitAction(characteristic, "equal", falseValue, cmd, [self.objId, 0], 0, {self.objId: "attr_speedLevel"}))
					self.actions.append (HomeKitAction(characteristic, "equal", trueValue, cmd, [self.objId, 100], 0, {self.objId: "attr_speedLevel"}))
				
				elif method == "RANGE":	
					self.actions.append (HomeKitAction(characteristic, "between", minValue, cmd, [self.objId, "=value="], maxValue, {self.objId: "attr_speedLevel"}))	
				
				else:
					invalidType = True
			
			# THERMOSTAT	
			elif attrib == "fanIsOn":
				cmd = "thermostat.setFanMode"
				if method == "TF" or method == "01":	
					self.actions.append (HomeKitAction(characteristic, "equal", falseValue, cmd, [self.objId, indigo.kFanMode.Auto], 0, {self.objId: "attr_fanIsOn"}))
					self.actions.append (HomeKitAction(characteristic, "equal", trueValue, cmd, [self.objId, indigo.kFanMode.AlwaysOn], 0, {self.objId: "attr_fanMode"}))
				
				elif method == "RANGE":	
					self.actions.append (HomeKitAction(characteristic, "equal", 0, cmd, [self.objId, indigo.kFanMode.Auto], 0, {self.objId: "attr_fanIsOn"}))
					self.actions.append (HomeKitAction(characteristic, "between", minValue, cmd, [self.objId, indigo.kFanMode.AlwaysOn], maxValue, {self.objId: "attr_fanMode"}))	
				
				else:
					invalidType = True
					
			
				
		
			if invalidType:
				self.logger.warning ("Unable to create default action for {} attribute '{}', the characteristic '{}' data type is {} and we can't translate to that from '{}'".format(self.alias.value, attrib, characteristic, str(type(a.value)).replace("<type '", "").replace("'>", ""), attrib))
				return
		
		except Exception as e:
			self.logger.error (ext.getException(e))	
			
	#
	# Calculate default actions based on the attribute value that is being changed
	#
	def calculateDefaultActionsForState (self, state, characteristic):
		try:
			if characteristic in self.actions: return # The user has passed their own actions
			if characteristic not in dir(self): return # We need to reference the details, it should have been created by now
			
			a = getattr (self, characteristic)
			invalidType = False
			
			if a.readonly: 
				self.logger.threaddebug ("Not setting a default action for {} because that characteristic is read only".format(characteristic))
				return # There are no actions for readonly characteristics, why add unnecessary data?
			
			# Define some defaults
			minValue = 0
			maxValue = 100
			minStep = 1
			trueValue = True
			falseValue = False
			method = "UNKNOWN"
			if "minValue" in dir(a): minValue = a.minValue
			if "maxValue" in dir(a): maxValue = a.maxValue
			if "minStep" in dir(a): minStep = a.minStep
			
			# Determine which data method the characteristic is using (T/F, 0/1, Range)
			if type(a.value) == bool:
				method = "TF"
				
			elif "validValues" in dir(a) and len(a.validValues) == 2:
				method = "01"
				trueValue = 1
				falseValue = 0
								
			elif "validValues" in dir(a) and len(a.validValues) > 2:
				method = "RANGE"
				
			elif "validValues" not in dir(a) and "minValue" in dir(a):
				method = "RANGE"
			
			# MULTI-I/O (INPUTOUTPUT)	
			if state == "binaryOutput1":
				# NOTE: This is really only tuned to the garage door use of this, actual other uses of this will probably not work using this config since
				# we use only one command "turn on output" which is what we need to do to both open and close a garage door.  If users need more function
				# then we'll have to move some or all of this to the functions instead so we can do some tweaking
				
				cmd = "iodevice.setBinaryOutput"
				if method == "TF" or method == "01":	
					self.actions.append (HomeKitAction(characteristic, "equal", falseValue, cmd, [self.objId, 0, True], 0, {self.objId: "state_binaryOutput1"}))
					self.actions.append (HomeKitAction(characteristic, "equal", trueValue, cmd, [self.objId, 0, True], 0, {self.objId: "state_binaryOutput1"}))
				
				elif method == "RANGE":	
					self.actions.append (HomeKitAction(characteristic, "equal", 0, cmd, [self.objId, 0, True], 0, {self.objId: "state_binaryOutput1"}))
					self.actions.append (HomeKitAction(characteristic, "between", minValue, cmd, [self.objId, 0, True], maxValue, {self.objId: "state_binaryOutput1"}))	
				
				else:
					invalidType = True
					
			elif state == "binaryInput1":
				# NOTE: This is really only tuned to the garage door use of this, actual other uses of this will probably not work using this config since
				# we use only one command "turn on output" which is what we need to do to both open and close a garage door.  If users need more function
				# then we'll have to move some or all of this to the functions instead so we can do some tweaking
				
				cmd = "iodevice.setBinaryOutput"
				if method == "TF" or method == "01":	
					self.actions.append (HomeKitAction(characteristic, "equal", falseValue, cmd, [self.objId, 0, True], 0, {self.objId: "state_binaryOutput1"}))
					self.actions.append (HomeKitAction(characteristic, "equal", trueValue, cmd, [self.objId, 0, True], 0, {self.objId: "state_binaryOutput1"}))
				
				elif method == "RANGE":	
					self.actions.append (HomeKitAction(characteristic, "equal", 0, cmd, [self.objId, 0, True], 0, {self.objId: "state_binaryOutput1"}))
					self.actions.append (HomeKitAction(characteristic, "between", minValue, cmd, [self.objId, 0, True], maxValue, {self.objId: "state_binaryOutput1"}))	
				
				else:
					invalidType = True		
					
			
				
		
			if invalidType:
				self.logger.warning ("Unable to create default action for {} attribute '{}', the characteristic '{}' data type is {} and we can't translate to that from '{}'".format(self.alias.value, attrib, characteristic, str(type(a.value)).replace("<type '", "").replace("'>", ""), attrib))
				return
				
			#state_binaryOutput1
			
			
		except Exception as e:
			self.logger.error (ext.getException(e))				
			
	#
	# All devices point back to here to set an attribute value so we can do calculations and keep everything uniform across devices (and less coding)
	#	
	def setAttributeValue (self, attribute, value):
		try:
			ret = True
		
			if not attribute in dir(self):
				self.logger.error ("Cannot set {} value of {} because it is not an attribute".format(attribute, dev.Alias.value))
				return False
			
			obj = getattr (self, attribute)	
	
			if type(value) == type(obj.value):
				obj.value = value
				#indigo.server.log ("Set {} to {}".format(attribute, unicode(value)))
			else:
				# Try to do a basic conversion if possible
				vtype = str(type(value)).replace("<type '", "").replace("'>", "")
				atype = str(type(obj.value)).replace("<type '", "").replace("'>", "")
			
				converted = False
				if vtype == "bool": converted = self.convertFromBoolean (attribute, value, atype, vtype, obj)
				if vtype == "str" and atype == "unicode":
					obj.value = value
					converted = True
				if vtype == "int" and atype == "float":
					obj.value = float(obj.value)
					converted = True
			
				if not converted:
					indigo.server.log("Unable to set the value of {} on {} to {} because that attribute requires {} and it was given {}".format(attribute, self.alias.value, unicode(value), atype, vtype))
					return False
	
		except Exception as e:
			self.logger.error (ext.getException(e))	
			ret = False
		
		return ret			
		
	#
	# Convert from boolean
	#
	def convertFromBoolean (self, attribute, value, atype, vtype, obj):
		try:
			newvalue = None
	
			# Convert to integer
			if atype == "int":
				if value: newvalue = 1
				if not value: newvalue = 0
		
			if atype == "str":
				if value: newvalue = "true"
				if not value: newvalue = "false"	
		
			if "validValues" in dir(obj) and newvalue in obj.validValues: 
				obj.value = newvalue
				return True
		
			elif "validValues" in dir(obj) and newvalue not in obj.validValues: 
				indigo.server.log("Converted {} for {} from {} to {} but the coverted value of {} was not a valid value for this attribute and will not be accepted by HomeKit, it will remain at the current value of {}".format(attribute, dev.Alias.value, vtype, atype, unicode(newvalue), unicode(obj.value)))
				return False
	
		except Exception as e:
			self.logger.error (ext.getException(e))	
	
		return False		
			
################################################################################
# HOMEKIT ACTIONS
#
# Defines and executes actions associated with a characteristic
################################################################################	
class HomeKitAction ():
	def __init__(self, characteristic, whenvalueis = "equal", whenvalue = 0, command = "", arguments = [], whenvalue2 = 0, monitors = {}):
		try:
			self.logger = logging.getLogger ("Plugin.HomeKitAction")
			
			self.characteristic = characteristic
			self.whenvalueis = whenvalueis
			self.whenvalue = whenvalue
			self.whenvalue2 = whenvalue2
			self.command = command
			self.arguments = arguments
			self.monitors = monitors # Dict of objId: attr_* | state_* | prop_* that we will monitor for this action - partly for future use if we are tying multiple objects to different properties and actions but also so our subscribe to changes knows what will trigger an update
			
			# Determine the value data type by creating a mock object
			clsmembers = inspect.getmembers(sys.modules[__name__], inspect.isclass)
			for cls in clsmembers:
				if cls[0] == "characteristic_{}".format(characteristic):
					cclass = cls[1]
					break

			obj = cclass()
			self.valuetype = str(type(obj.value)).replace("<type '", "").replace("'>", "")
			
			self.validOperators = ["equal", "notequal", "greater", "less", "between"]
		
		except Exception as e:
			self.logger.error  (ext.getException(e))
			
	def xstr__(self):
		ret = ""
		
	def __str__ (self):
		ret = ""
		
		ret += "Action : (HomeKitAction)\n"
		ret += "\tCharacteristic : {0}\n".format(self.characteristic)
		ret += "\tWhen : {0}\n".format(self.whenvalueis)
		ret += "\tValue : {0} ({1})\n".format(unicode(self.whenvalue), str(type(self.whenvalue)).replace("<type '", "").replace("'>", "") )
		ret += "\tValue2 : {0} ({1})\n".format(unicode(self.whenvalue2), str(type(self.whenvalue)).replace("<type '", "").replace("'>", ""))
		ret += "\tCommand : {0}\n".format(unicode(self.command))
		ret += "\tArguments : {0}\n".format(unicode(self.arguments))
		
		return ret
		
	def run (self, value):
		try:
			# See if the value falls within the actions limitations and if it does then run the associated command
			#indigo.server.log(unicode(self))
		
			# Get the value type of the value so we can convert from string to that type
			if type(self.whenvalue) == bool:
				if value.lower() == "true": 
					value = True
				elif value.lower() == "false":
					value = False
					
			elif type(self.whenvalue) == int:
				value = int(value)
				
			elif type(self.whenvalue) == float:
				value = float(value)
				
			else:
				self.logger.error ("Unknown value for processAction: {}".format(str(type(self.whenvalue)).replace("<type '", "").replace("'>", "")))
				return False
				
			isValid = False
			
			if self.whenvalueis == "equal" and value == self.whenvalue:
				isValid = True
				
			elif self.whenvalueis == "between" and value >= self.whenvalue and value <= self.whenvalue2:
				isValid = True
			
			if isValid:
				# Try to run the command
				try:
					# Fix up the arguments for placeholders
					args = []
					for a in self.arguments:
						if unicode(a) == "=value=":
							args.append(value)
						else:
							args.append(a)
							
						#indigo.server.log (unicode(type(a)) + "\t" + unicode(a))
				
					cmd = self.command.split(".")
					func = indigo
					if self.command[0:8] == "homekit.":
						func = self
						cmd = self.command.replace("homekit.", "")
						cmd = cmd.split(".")
				
					for c in cmd:
						func = getattr(func, c)
				
					if len(args) > 0: 
						retval = func(*args)
					else:
						retval = func()
				
				except Exception as ex:
					self.logger.error (ext.getException(ex))
					return False
		
				return True
			
			else:
				return False
	
		except Exception as e:
			self.logger.error (ext.getException(e))
			return False
		
		return True			
		
	################################################################################
	# COMMAND STUBS
	################################################################################
	
	#
	# Change thermostat temperature
	#
	def commandSetTargetThermostatTemperature (self, devId, serverId, targetTemperature):
		try:
			server = indigo.devices[serverId]
			dev = indigo.devices[devId]
			if type(dev) != indigo.ThermostatDevice:
				self.logger.error ("Attempting to run {} as a thermostat with thermostat commands but it is not a thermostat".format(dev.name))
				return
			
			if "tempunits" in server.pluginProps:
				# If our source is celsius then that's what HomeKit wants, just return it
				if server.pluginProps["tempunits"] == "c":
					value = targetTemperature
				else:				
					# If our source is fahrenheit then we need to convert it
					value = float(targetTemperature)
					value = (value * 1.8000) + 32
					value = round(value, 0) # We fahrenheit users never use fractions - if someone requests it in the future we can add an option
				
			if unicode(dev.hvacMode) == "Heat":			
				#indigo.server.log ("Set heat set point of {} on server {} to {}".format(str(devId), str(serverId), str(value)))
				indigo.thermostat.setHeatSetpoint (devId, value)
				
			if unicode(dev.hvacMode) == "Cool":			
				#indigo.server.log ("Set cool set point of {} on server {} to {}".format(str(devId), str(serverId), str(value)))
				indigo.thermostat.setCoolSetpoint (devId, value)
		
		except Exception as e:
			self.logger.error (ext.getException(e))	

################################################################################
# HOMEKIT SERVICES
#
# Inherits the service class and defines the service
################################################################################	

# ==============================================================================
# DUMMY SERVICE WHEN WE CANNOT AUTODETECT
# ==============================================================================
class Dummy (Service):

	#
	# Initialize the class
	#
	def __init__ (self, factory, objId, serverId = 0, characterDict = {}, deviceActions = [], loadOptional = False):
		type = "Dummy"
		desc = "Invalid"
	
		super(Dummy, self).__init__ (factory, type, desc, objId, serverId, characterDict, deviceActions, loadOptional)
		
		self.required = ["On"]
		self.optional = []
					
		super(Dummy, self).setAttributes ()
				
		self.logger.debug ('{} started as a HomeKit {}'.format(self.alias.value, self.desc))	
		#self.logger.warning ('{} has no automatic conversion to HomeKit and will not be usable unless custom mapped'.format(self.alias.value))	

# ==============================================================================
# FAN V2
# ==============================================================================
class service_Fanv2 (Service):

	#
	# Initialize the class
	#
	def __init__ (self, factory, objId, serverId = 0, characterDict = {}, deviceActions = [], loadOptional = False):
		type = "Fanv2"
		desc = "Fan Version 2"

		super(service_Fanv2, self).__init__ (factory, type, desc, objId, serverId, characterDict, deviceActions, loadOptional)
	
		self.required = ["Active"]
		self.optional = ["CurrentFanState", "TargetFanState", "LockPhysicalControls", "Name", "RotationDirection", "RotationSpeed", "SwingMode"]
	
		self.requiredv2 = {}
		self.requiredv2["Active"] = {"*": "attr_onState", "indigo.ThermostatDevice": "attr_fanIsOn", "indigo.MultiIODevice": "state_binaryOutput1", "indigo.SprinklerDevice": "activeZone"}
	
		self.optionalv2 = {}
		self.optionalv2["CurrentFanState"] = {}
		self.optionalv2["TargetFanState"] = {}
		self.optionalv2["LockPhysicalControls"] = {}
		self.optionalv2["Name"] = {}
		self.optionalv2["RotationDirection"] = {}
		self.optionalv2["RotationSpeed"] = {"indigo.DimmerDevice": "attr_brightness", "indigo.SpeedControlDevice": "attr_speedLevel"}
		self.optionalv2["SwingMode"] = {}
				
		super(service_Fanv2, self).setAttributesv2 ()
		#super(service_Fanv2, self).setAttributes ()
			
		self.logger.debug ('{} started as a HomeKit {}'.format(self.alias.value, self.desc))

		
# ==============================================================================
# GARAGE DOOR OPENER
# ==============================================================================
class service_GarageDoorOpener (Service):

	#
	# Initialize the class
	#
	def __init__ (self, factory, objId, serverId = 0, characterDict = {}, deviceActions = [], loadOptional = False):
		type = "GarageDoorOpener"
		desc = "Garage Door Opener"
	
		super(service_GarageDoorOpener, self).__init__ (factory, type, desc, objId, serverId, characterDict, deviceActions, loadOptional)
		
		self.required = ["CurrentDoorState", "TargetDoorState", "ObstructionDetected"]
		self.optional = ["LockCurrentState", "LockTargetState", "Name"]
		
		self.requiredv2 = {}
		self.requiredv2["CurrentDoorState"] = {"*": "attr_onState", "indigo.MultiIODevice": "state_binaryInput1"}
		self.requiredv2["TargetDoorState"] = {"*": "attr_onState", "indigo.MultiIODevice": "state_binaryInput1"}
		self.requiredv2["ObstructionDetected"] = {}
	
		self.optionalv2 = {}
		self.optionalv2["LockCurrentState"] = {}
		self.optionalv2["LockTargetState"] = {}
		self.optionalv2["Name"] = {}
					
		super(service_GarageDoorOpener, self).setAttributesv2 ()			
		#super(service_GarageDoorOpener, self).setAttributes ()
						
		self.logger.debug ('{} started as a HomeKit {}'.format(self.alias.value, self.desc))		
		
# ==============================================================================
# LIGHT BULB
# ==============================================================================
class service_Lightbulb (Service):

	#
	# Initialize the class
	#
	def __init__ (self, factory, objId, serverId = 0, characterDict = {}, deviceActions = [], loadOptional = False):
		type = "Lightbulb"
		desc = "Lightbulb"
	
		super(service_Lightbulb, self).__init__ (factory, type, desc, objId, serverId, characterDict, deviceActions, loadOptional)
		
		self.required = ["On"]
		self.optional = ["Brightness", "Hue", "Saturation", "Name", "ColorTemperature"]
		
		self.requiredv2 = {}
		self.requiredv2["On"] = {"*": "attr_onState", "indigo.ThermostatDevice": "attr_fanIsOn", "indigo.MultiIODevice": "state_binaryOutput1", "indigo.SprinklerDevice": "activeZone"}
	
		self.optionalv2 = {}
		self.optionalv2["Brightness"] = {"indigo.DimmerDevice": "attr_brightness", "indigo.SpeedControlDevice": "attr_speedLevel"}
		self.optionalv2["Hue"] = {}
		self.optionalv2["Saturation"] = {}
		self.optionalv2["Name"] = {}
		self.optionalv2["ColorTemperature"] = {}
					
		super(service_Lightbulb, self).setAttributesv2 ()					
		#super(service_Lightbulb, self).setAttributes ()
				
		self.logger.debug ('{} started as a HomeKit {}'.format(self.alias.value, self.desc))		
		
# ==============================================================================
# MOTION SENSOR
# ==============================================================================
class service_MotionSensor (Service):

	#
	# Initialize the class
	#
	def __init__ (self, factory, objId, serverId = 0, characterDict = {}, deviceActions = [], loadOptional = False):
		type = "MotionSensor"
		desc = "Motion Sensor"
	
		super(service_MotionSensor, self).__init__ (factory, type, desc, objId, serverId, characterDict, deviceActions, loadOptional)
		
		self.required = ["MotionDetected"]
		self.optional = ["StatusActive", "StatusFault", "StatusTampered", "StatusLowBattery", "Name"]
		
		self.requiredv2 = {}
		self.requiredv2["MotionDetected"] = {"*": "attr_onState", "indigo.ThermostatDevice": "attr_fanIsOn", "indigo.MultiIODevice": "state_binaryOutput1", "indigo.SprinklerDevice": "activeZone"}
	
		self.optionalv2 = {}
		self.optionalv2["StatusActive"] = {}
		self.optionalv2["StatusFault"] = {}
		self.optionalv2["StatusTampered"] = {}
		self.optionalv2["StatusLowBattery"] = {"*": "special_lowbattery"}
		self.optionalv2["Name"] = {}
					
		super(service_MotionSensor, self).setAttributesv2 ()				
		#super(service_MotionSensor, self).setAttributes ()
				
		self.logger.debug ('{} started as a HomeKit {}'.format(self.alias.value, self.desc))		
		
# ==============================================================================
# OUTLET
# ==============================================================================
class service_Outlet (Service):

	#
	# Initialize the class
	#
	def __init__ (self, factory, objId, serverId = 0, characterDict = {}, deviceActions = [], loadOptional = False):
		type = "Outlet"
		desc = "Outlet"
	
		super(service_Outlet, self).__init__ (factory, type, desc, objId, serverId, characterDict, deviceActions, loadOptional)
		
		self.required = ["On", "OutletInUse"]
		
		self.requiredv2 = {}
		self.requiredv2["On"] = {"*": "attr_onState", "indigo.ThermostatDevice": "attr_fanIsOn", "indigo.MultiIODevice": "state_binaryOutput1", "indigo.SprinklerDevice": "activeZone"}
		self.requiredv2["OutletInUse"] = {"*": "special_inuse"}
	
		self.optionalv2 = {}
					
		super(service_Outlet, self).setAttributesv2 ()							
		#super(service_Outlet, self).setAttributes ()
				
		self.logger.debug ('{} started as a HomeKit {}'.format(self.alias.value, self.desc))		
		
# ==============================================================================
# LOCK MECHANISM
# ==============================================================================
class service_LockMechanism (Service):

	#
	# Initialize the class
	#
	def __init__ (self, factory, objId, serverId = 0, characterDict = {}, deviceActions = [], loadOptional = False):
		type = "LockMechanism"
		desc = "Lock Mechanism"
	
		super(service_LockMechanism, self).__init__ (factory, type, desc, objId, serverId, characterDict, deviceActions, loadOptional)
		
		self.required = ["LockCurrentState", "LockTargetState"]
		self.optional = ["Name"]
		
		self.requiredv2 = {}
		self.requiredv2["LockCurrentState"] = {"*": "attr_onState", "indigo.ThermostatDevice": "attr_fanIsOn", "indigo.MultiIODevice": "state_binaryOutput1", "indigo.SprinklerDevice": "activeZone"}
		self.requiredv2["LockTargetState"] = {"*": "attr_onState", "indigo.ThermostatDevice": "attr_fanIsOn", "indigo.MultiIODevice": "state_binaryOutput1", "indigo.SprinklerDevice": "activeZone"}
	
		self.optionalv2 = {}
		self.optionalv2["Name"] = {}
					
		super(service_LockMechanism, self).setAttributesv2 ()					
		#super(service_LockMechanism, self).setAttributes ()
				
		self.logger.debug ('{} started as a HomeKit {}'.format(self.alias.value, self.desc))								

# ==============================================================================
# SWITCH
# ==============================================================================
class service_Switch (Service):

	#
	# Initialize the class
	#
	def __init__ (self, factory, objId, serverId = 0, characterDict = {}, deviceActions = [], loadOptional = False):
		type = "Switch"
		desc = "Switch"
	
		super(service_Switch, self).__init__ (factory, type, desc, objId, serverId, characterDict, deviceActions, loadOptional)
		
		self.required = ["On"]
		
		self.requiredv2 = {}
		self.requiredv2["On"] = {"*": "attr_onState", "indigo.ThermostatDevice": "attr_fanIsOn", "indigo.MultiIODevice": "state_binaryOutput1", "indigo.SprinklerDevice": "activeZone"}
	
		self.optionalv2 = {}
					
		super(service_Switch, self).setAttributesv2 ()	
		#super(service_Switch, self).setAttributes ()
				
		self.logger.debug ('{} started as a HomeKit {}'.format(self.alias.value, self.desc))
		
# ==============================================================================
# THERMOSTAT
# ==============================================================================
class service_Thermostat (Service):

	#
	# Initialize the class
	#
	def __init__ (self, factory, objId, serverId = 0, characterDict = {}, deviceActions = [], loadOptional = False):
		type = "Thermostat"
		desc = "Thermostat"
	
		super(service_Thermostat, self).__init__ (factory, type, desc, objId, serverId, characterDict, deviceActions, loadOptional)
		
		self.required = ["CurrentHeatingCoolingState", "TargetHeatingCoolingState", "CurrentTemperature", "TargetTemperature", "TemperatureDisplayUnits"]
		self.optional = ["CurrentRelativeHumidity", "TargetRelativeHumidity", "CoolingThresholdTemperature", "HeatingThresholdTemperature", "Name"]
		
		super(service_Thermostat, self).setAttributes ()
				
		self.logger.debug ('{} started as a HomeKit {}'.format(self.alias.value, self.desc))		
		
	
		
################################################################################
# HOMEKIT CHARACTERISTICS
#
# 
################################################################################		
# ==============================================================================
# ACTIVE
# ==============================================================================
class characteristic_Active:	
	def __init__(self):
		self.value = 0 # inactive
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]
		
		self.readonly = False
		self.notify = True
		
# ==============================================================================
# BRIGHTNESS
# ==============================================================================
class characteristic_Brightness:
	def __init__(self):
		self.value = 0
		self.maxValue = 100
		self.minValue = 0
		self.minStep = 1
		
		self.readonly = False
		self.notify = True
		
# ==============================================================================
# COLOR TEMPERATURE
# ==============================================================================		
class characteristic_ColorTemperature:
	def __init__(self):
		self.value = 140
		self.minValue = 140
		self.maxValue = 500
		self.minStep = 1	
		
		self.readonly = False
		self.notify = True	
		
# ==============================================================================
# COOLING THRESHOLD TEMPERATURE
# ==============================================================================		
class characteristic_CoolingThresholdTemperature:
	def __init__(self):
		self.value = 0.0
		self.maxValue = 35
		self.minValue = 10
		self.minStep = 0.1

		self.readonly = False
		self.notify = True			
		
# ==============================================================================
# CURRENT DOOR STATE
# ==============================================================================
class characteristic_CurrentDoorState:	
	def __init__(self):
		self.value = 0 # open [closed, opening, closing, stopped]
		self.maxValue = 4
		self.minValue = 0
		
		self.validValues = [0, 1, 2, 3, 4]
		
		self.readonly = True
		self.notify = True			
		
# ==============================================================================
# CURRENT FAN STATE
# ==============================================================================
class characteristic_CurrentFanState:	
	def __init__(self):
		self.value = 0 # inactive [idle, blowing air]
		self.maxValue = 2
		self.minValue = 0
		
		self.validValues = [0, 1, 2]
		
		self.readonly = True
		self.notify = True		
		
# ==============================================================================
# CURRENT HEATING/COOLING STATE
# ==============================================================================
class characteristic_CurrentHeatingCoolingState:	
	def __init__(self):
		self.value = 0 # off [heat, cool]
		self.maxValue = 2
		self.minValue = 0
		
		self.validValues = [0, 1, 2]
		
		self.readonly = True
		self.notify = True		
		
# ==============================================================================
# CURRENT RELATIVE HUMIDITY
# ==============================================================================		
class characteristic_CurrentRelativeHumidity:
	def __init__(self):
		self.value = 0.0
		self.maxValue = 100
		self.minValue = 0
		self.minStep = 1

		self.readonly = True
		self.notify = True			
		
# ==============================================================================
# CURRENT TEMPERATURE
# ==============================================================================		
class characteristic_CurrentTemperature:
	def __init__(self):
		self.value = 0.0
		self.maxValue = 100
		self.minValue = 0
		self.minStep = 0.1

		self.readonly = True
		self.notify = True		
		
# ==============================================================================
# HEATING THRESHOLD TEMPERATURE
# ==============================================================================		
class characteristic_HeatingThresholdTemperature:
	def __init__(self):
		self.value = 0.0
		self.maxValue = 25
		self.minValue = 0
		self.minStep = 0.1

		self.readonly = False
		self.notify = True			
		
# ==============================================================================
# HUE
# ==============================================================================		
class characteristic_Hue:
	def __init__(self):
		self.value = 0.0
		self.maxValue = 360
		self.minValue = 0
		self.minStep = 1
		
		self.readonly = False
		self.notify = True
		
# ==============================================================================
# LOCK CURRENT STATE
# ==============================================================================
class characteristic_LockCurrentState:	
	def __init__(self):
		self.value = 0 # Unsecured [Secured, Jammed, Unknown]
		self.maxValue = 3
		self.minValue = 0
		
		self.validValues = [0, 1, 2, 3]		
		
		self.readonly = True
		self.notify = True
		
# ==============================================================================
# LOCK PHYSICAL CONTROLS
# ==============================================================================
class characteristic_LockPhysicalControls:	
	def __init__(self):
		self.value = 0 # lock disabled [lock enabled]
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]
		
		self.readonly = False
		self.notify = True		
		
# ==============================================================================
# LOCK TARGET STATE
# ==============================================================================
class characteristic_LockTargetState:	
	def __init__(self):
		self.value = 0 # Unsecured [Secured]
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]	
		
		self.readonly = False
		self.notify = True		

# ==============================================================================
# MOTION DETECTED
# ==============================================================================
class characteristic_MotionDetected:
	def __init__(self):
		self.value = False
		
		self.validValues = [True, False]
		
		self.readonly = True
		self.notify = False		
		
# ==============================================================================
# NAME
# ==============================================================================		
class characteristic_Name:
	def __init__(self):
		self.value = u""	
		
		self.readonly = False
		self.notify = False
		
# ==============================================================================
# OBSTRUCTION DETECTED
# ==============================================================================
class characteristic_ObstructionDetected:	
	def __init__(self):
		self.value = False
		
		self.validValues = [True, False]
		
		self.readonly = True
		self.notify = False				
		
# ==============================================================================
# ON
# ==============================================================================
class characteristic_On:
	def __init__(self):
		self.value = False
		
		self.validValues = [True, False]
		
		self.readonly = False
		self.notify = False		
		
# ==============================================================================
# OUTLET IN USE
# ==============================================================================
class characteristic_OutletInUse:
	def __init__(self):
		self.value = False
		
		self.validValues = [True, False]	
		
		self.readonly = True
		self.notify = True		
		
# ==============================================================================
# ROTATION DIRECTION
# ==============================================================================
class characteristic_RotationDirection:	
	def __init__(self):
		self.value = 0 # clockwise [counter-clockwise]
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]
		
		self.readonly = False
		self.notify = True		
		
# ==============================================================================
# ROTATION SPEED
# ==============================================================================
class characteristic_RotationSpeed:	
	def __init__(self):
		self.value = 0.0
		self.maxValue = 100
		self.minValue = 0
		self.minStep = 1
				
		self.readonly = False
		self.notify = True		
	
# ==============================================================================
# SATURATION
# ==============================================================================		
class characteristic_Saturation:
	def __init__(self):
		self.value = 0.0
		self.maxValue = 100
		self.minValue = 0
		self.minStep = 1

		self.readonly = False
		self.notify = True
		
# ==============================================================================
# STATUS ACTIVE
# ==============================================================================
class characteristic_StatusActive:
	def __init__(self):
		self.value = True
		
		self.validValues = [True, False]
		
		self.readonly = True
		self.notify = False			
		
# ==============================================================================
# STATUS FAULT
# ==============================================================================
class characteristic_StatusFault:	
	def __init__(self):
		self.value = 0 # no fault [fault]
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]
		
		self.readonly = True
		self.notify = True			
		
# ==============================================================================
# STATUS LOW BATTERY
# ==============================================================================
class characteristic_StatusLowBattery:	
	def __init__(self):
		self.value = 0 # normal [low]
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]
		
		self.readonly = True
		self.notify = True			
		
# ==============================================================================
# STATUS TAMPERED
# ==============================================================================
class characteristic_StatusTampered:	
	def __init__(self):
		self.value = 0 # not tampered [tampered]
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]
		
		self.readonly = True
		self.notify = True			
		
# ==============================================================================
# SWING MODE
# ==============================================================================
class characteristic_SwingMode:	
	def __init__(self):
		self.value = 0 # disabled [enabled]
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]
		
		self.readonly = False
		self.notify = True		
		
# ==============================================================================
# TARGET DOOR STATE
# ==============================================================================
class characteristic_TargetDoorState:	
	def __init__(self):
		self.value = 0 # open [closed]
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]
		
		self.readonly = False
		self.notify = True			

# ==============================================================================
# TARGET FAN STATTE
# ==============================================================================
class characteristic_TargetFanState:	
	def __init__(self):
		self.value = 0 # manual [auto]
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]
		
		self.readonly = False
		self.notify = True
		
# ==============================================================================
# TARGET HEATING/COOLING STATE
# ==============================================================================
class characteristic_TargetHeatingCoolingState:	
	def __init__(self):
		self.value = 0 # off [heat, cool, auto]
		self.maxValue = 3
		self.minValue = 0
		
		self.validValues = [0, 1, 2, 3]
		
		self.readonly = False
		self.notify = True		
		
# ==============================================================================
# TARGET TEMPERATURE
# ==============================================================================		
class characteristic_TargetTemperature:
	def __init__(self):
		self.value = 0.0
		self.maxValue = 35
		self.minValue = 10
		self.minStep = 0.1

		self.readonly = False
		self.notify = True			

# ==============================================================================
# TARGET RELATIVE HUMIDITY
# ==============================================================================		
class characteristic_TargetRelativeHumidity:
	def __init__(self):
		self.value = 0.0
		self.maxValue = 100
		self.minValue = 0
		self.minStep = 1

		self.readonly = False
		self.notify = True	
		
# ==============================================================================
# TEMPERATURE DISPLAY UNITS
# ==============================================================================
class characteristic_TemperatureDisplayUnits:	
	def __init__(self):
		self.value = 0 # celsius [fahrenheit]
		self.maxValue = 1
		self.minValue = 0
		
		self.validValues = [0, 1]
		
		self.readonly = False
		self.notify = True		
				
				