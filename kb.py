#!/usr/bin/env python3

import time
import pigpio
import subprocess
import os
import queue
from abc import ABC, abstractmethod

# Project imports
import accel.accel as accel

"""
This bit just gets the pigpiod daemon up and running if it isn't already.
The pigpio daemon accesses the Raspberry Pi GPIO.  
"""
p = subprocess.Popen(['pgrep', '-f', 'pigpiod'], stdout=subprocess.PIPE)
out, err = p.communicate()

if len(out.strip()) == 0:
    os.system("sudo pigpiod")

# Set up the local Pi - i.e. whichever one it happens to be running on.
local_pi = pigpio.pi() # Set up the pigpio library.


# Key class sets up and manages buttons.  Could be made generic.
class Key(ABC):
    def __init__(self, name, char_to_output):
        self.name = name
        print("Setting up ", self.name)

        # Set up the character to ouput when the pin is activated.
        self.char_to_output = char_to_output

    # Check the state of the key - abstract method - must be overwritten.
    @abstractmethod
    def read_key(self):
        return None

    @abstractmethod
    def light_button(self, percent_pwm):
        pass

# Key class sets up and manages buttons.  Could be made generic.
class Button_Key(Key):
    def __init__(self, which_pi, name, input_bcm_pin, output_bcm_pin, char_to_output):
        self.pi = which_pi
        super(Button_Key, self).__init__(name, char_to_output)

        # Setting up the button.
        self.input_bcm_pin = input_bcm_pin
        self.pi.set_mode(self.input_bcm_pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.input_bcm_pin, pigpio.PUD_UP)

        # Set up the output pin - typically a LED.
        self.output_bcm_pin = output_bcm_pin
        self.pi.set_PWM_dutycycle(self.output_bcm_pin, 0)

    # Check the state of the key.
    def read_key(self):
        if self.pi.read(self.input_bcm_pin) is 0:
            print (self.name)
            return self.char_to_output
        else:
            return None

    # Light the button
    def light_button(self, percent_pwm):
        if percent_pwm < 0:
            percent_pwm = 0
        if percent_pwm > 100:
            percent_pwm = 100

        pwm_cycle = int(percent_pwm / 100.0 * 255)
        self.pi.set_PWM_dutycycle(self.output_bcm_pin, pwm_cycle)


# Define Accelerometer Based Key - triggers the key at a certain acceleration.
class AccelKey(Key):

    def __init__(self, name, char_to_output, trigger_accel):
        super(AccelKey, self).__init__(name, char_to_output)

        # Setting up the accelerometer.
        self.accelque = queue.Queue()

        self.accel = accel.Accelerometer(5, self.accelque, 0.005)

        # Start the Accel Thread.
        self.accel.start()

        self.trigger_accel = trigger_accel

    # Check the state of the key.
    def read_key(self):
        # Initial value that will get written over if trigger is met.
        return_value = None

        # Deplete the Queue - check each value against the trigger value - over-ride the return value if trigger met.
        while not self.accelque.empty():
            accel = self.accelque.get_nowait()
            if accel > int(self.trigger_accel):
                return_value = self.char_to_output

        return return_value

    # No button to light for this - yet.
    def light_button(self, percent_pwm):
        pass



# Assign the first key to the local pi - set some defaults for the others.
right_arrow = Button_Key(local_pi, "Right Arrow", 21, 4, 79)
left_arrow = None # Setting up defaults just so the logic works - set up properly after this.
up_arrow = None
down_arrow = None

# Setting up the remote buttons - handle any exceptions - might not be powered or connected for some reason.
try:
    remote_pi1 = pigpio.pi('192.168.2.183')
    left_arrow = Button_Key(remote_pi1, "Left Arrow", 12, 4, 80)

except:
    print("Exception setting up KirbyPiZeroW2 - not available?")

try:
    remote_pi2 = pigpio.pi('192.168.2.123')
    up_arrow = Button_Key(remote_pi2, "Up Arrow", 12, 4, 82)
    down_arrow = Button_Key(remote_pi2, "Down Arrow", 21, 17, 81)

except:
    print("Exception setting up KirbyPi3 - not available?")

# Set up accelerometer based Key
up_arrow2 = AccelKey("Up Arrow 2", 82, 2)

# Array of keys
keys= [right_arrow, left_arrow, up_arrow, down_arrow, up_arrow2]

NULL_CHAR = chr(0)


# Writes a report to the USB device
def write_report(report):
    with open('/dev/hidg0', 'rb+') as fd:
        fd.write(report.encode())


percent = 0

# Main Loop - check on the buttons and send the key as needed to the USB OTG connection.
while 1:
    # Go through all the keys - check to see if any pressed.  If pressed, then send as the key to the OTG.
    for key in keys:

        # key will be None if exception occurred when it was set up (Pi down, etc.).
        if key is not None:
            key_press = key.read_key()

            # key_press returns None if the button is not detected pressed.  If pressed, then send to the connected computer.
            if key_press is not None:
                write_report(NULL_CHAR * 2 + chr(key_press) + NULL_CHAR * 5)
                write_report(NULL_CHAR * 8)
                percent += 10

                if percent > 100:
                    percent = 0

                key.light_button(percent)

    time.sleep(0.10)
