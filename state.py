#!/usr/bin/python

"""
__author__    = "Leon Fedden"
__copyright__ = "Copyright (C) 2016 Leon Fedden

"""

from gpiozero import MCP3008, Button
import sys
import smbus
import math
import time
import types

class State(object):

    """Manages state of glove.

    This reads the available sensors and calls the appropriate method set by
    the user where she binds the user-defined function to the appropriate
    callback method.

    """

    def __init__(self, button1_pin, button2_pin):
        """__init__ method

        Args:
            button1_pin (int): The pin number needed to get button 1.
            button2_pin (int): The pin number needed to get button 2.

        """
        self.button1 = Button(button1_pin)
        self.button2 = Button(button2_pin)
        self.flex0 = MCP3008(0)
        self.flex1 = MCP3008(1)
        self.flex2 = MCP3008(2)
        self.flex3 = MCP3008(3)
        self.flex4 = MCP3008(4)
        self.button1_lock = False
        self.button2_lock = False
        self.button1_start_time = 0
        self.button2_start_time = 0
        self.button_timer_length = 800
        self.button1.when_released = self.button1_released
        self.button1.when_pressed  = self.button1_pressed
        self.button2.when_released = self.button2_released
        self.button2.when_pressed  = self.button2_pressed
        self.sensor_data = [0.0] * 13
        self.get_change = lambda speed, threshold : speed > threshold
        self.absolute_velocity  = 0
        self.velocity_threshold = 50
        self.timer_started = False
        self.timer_start_time = 0
        self.timer_threshold = 300
        self.get_millis = lambda: int(round(time.time() * 1000))
        self.is_gesture = False
        self.power_mgmt_1 = 0x6b
        self.power_mgmt_2 = 0x6c
        self.bus = smbus.SMBus(1)
        self.address = 0x68
        # self.bus.write_byte_data(self.address, self.power_mgmt_1, 0)
        self.state = "Idle"

    def button1_pressed(self):
        self.button1_lock = True
        self.button1_start_time = self.get_millis()

    def button2_pressed(self):
        """Button 2 Pressed"""
        #self.button2_lock = True
        #self.button2_start_time = self.get_millis()

    def button1_released(self):
        button1_stop_time = self.get_millis()
        long_press = False
        if button1_stop_time - self.button1_start_time > self.button_timer_length:
            long_press = True
        self.button1_lock = False
        if long_press:
            self.__red_long()
        else:
            self.__red_short()

    def button2_released(self):
        self.__save_recording_callback()
        #button2_stop_time = self.get_millis()
        #long_press = False
        #if button2_stop_time - self.button2_start_time > self.button_timer_length:
        #    long_press = True
        #self.button2_lock = False
        #if long_press:
        #    self.__black_long()
        #else:
        #    self.__black_short()

    def set_button_callbacks(self, black_short, black_long, red_short, red_long):
        self.__black_short = types.MethodType(black_short, self, State)
        self.__black_long  = types.MethodType(black_long, self, State)
        self.__red_short   = types.MethodType(red_short, self, State)
        self.__red_long    = types.MethodType(red_long, self, State)

    def get_sensor_data(self):
        """Returns the data from the sensors as a list.

        Return:
            list of floats:
            list[0:4]  = flex[0:4]
            list[ 5]   = gyro_x
            list[ 6]   = gyro_y
            list[ 7]   = gyro_z
            list[ 8]   = accel_x
            list[ 9]   = accel_y
            list[10]   = accel_z
            list[11]   = rotation_x
            list[12]   = rotation_y
        """
        return self.sensor_data

    def update(self):
        """Calculates sensor data and manages system state.

        This will ensure the appropriate callback function
        is being called.

        """

        self.sensor_data[0]  = self.flex0.value
        self.sensor_data[1]  = self.flex1.value
        self.sensor_data[2]  = self.flex2.value
        self.sensor_data[3]  = self.flex3.value
        self.sensor_data[4]  = self.flex4.value
        self.sensor_data[5]  = 0#self.read_word_2c(0x43) / 131
        self.sensor_data[6]  = 0#self.read_word_2c(0x45) / 131
        self.sensor_data[7]  = 0#self.read_word_2c(0x47) / 131
        self.sensor_data[8]  = 0#self.read_word_2c(0x3b) / 16384.0
        self.sensor_data[9]  = 0#self.read_word_2c(0x3d) / 16384.0
        self.sensor_data[10] = 0#self.read_word_2c(0x3f) / 16384.0
        self.sensor_data[11] = self.get_x_rotation(self.sensor_data[ 8],
                                                   self.sensor_data[ 9],
                                                   self.sensor_data[10])
        self.sensor_data[12] = self.get_y_rotation(self.sensor_data[ 8],
                                                   self.sensor_data[ 9],
                                                   self.sensor_data[10])
        self.absolute_velocity = 0
        self.absolute_velocity += abs(self.sensor_data[5])
        self.absolute_velocity += abs(self.sensor_data[6])
        self.absolute_velocity += abs(self.sensor_data[7])

        if self.button2.is_pressed:
            self.__recording_callback()
        else:
            self.__idle_callback()

        #if (self.get_change(self.absolute_velocity, self.velocity_threshold) and
        #    self.timer_started == False):

        #    self.timer_started = True
        #    self.timer_start_time = self.get_millis()

        #elif (self.get_change(self.absolute_velocity, self.velocity_threshold) == False and
        #      self.timer_started == True):

        #    self.timer_started = False

        #elif (self.get_change(self.absolute_velocity, self.velocity_threshold) and
        #      self.timer_started and
        #      self.get_millis() - self.timer_start_time > self.timer_threshold):

        #    self.timer_started = False
        #    self.is_gesture = not self.is_gesture

        #    if self.is_gesture == True:
        #        self.state = "Recording"
        #        self.get_change = lambda speed, threshold : speed < threshold
        #    else:
        #        self.state = "Idle"
        #        self.get_change = lambda speed, threshold : speed >= threshold
        #        self.__save_recording_callback()

        #if self.is_gesture == True:
        #    self.__recording_callback()
        #else:
        #    self.__idle_callback()

    def try_io(self, call, tries=10):
        """Tries to re-call the memory reading functions
        if they throw an error.

        Uncomment to throw error if it can't get the value.

        """
        assert tries > 0
        error = None
        result = None

        while tries:
            try:
                result = call()
            except IOError as e:
                error = e
                tries -= 1
            else:
                break
        #if not tries:
            #raise error

        return result

    def read_byte(self, adr):
        """Reads a byte from the given address."""
        return self.try_io(lambda: self.bus.read_byte_data(self.address, adr))

    def read_word(self, adr):
        high = self.try_io(lambda: self.bus.read_byte_data(self.address, adr))
        low = self.try_io(lambda: self.bus.read_byte_data(self.address, adr + 1))
        val = (high << 8) + low
        return val

    def read_word_2c(self, adr):
        val = self.read_word(adr)
        if (val >= 0x8000):
            return -((65535 - val) + 1)
        else:
            return val

    def dist(self, a, b):
        return math.sqrt((a*a)+(b*b))

    def get_y_rotation(self, x, y, z):
        radians = math.atan2(x, self.dist(y,z))
        return -math.degrees(radians)

    def get_x_rotation(self, x, y, z):
        radians = math.atan2(y, self.dist(x,z))
        return math.degrees(radians)

    def set_recording_callback(self, method):
        self.__recording_callback = method

    def set_idle_callback(self, method):
        self.__idle_callback = method

    def set_save_recording_callback(self, method):
        self.__save_recording_callback = method
