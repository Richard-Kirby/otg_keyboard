#!/usr/bin/env python3

import time
import pigpio
import subprocess
import os

"""
This bit just gets the pigpiod daemon up and running if it isn't already.
The pigpio daemon accesses the Raspberry Pi GPIO.  
"""
p = subprocess.Popen(['pgrep', '-f', 'pigpiod'], stdout=subprocess.PIPE)
out, err = p.communicate()

if len(out.strip()) == 0:
    os.system("sudo pigpiod")


local_pi = pigpio.pi() # Set up the pigpio library.

class Key:
    def __init__(self, which_pi, name, input_bcm_pin, output_bcm_pin, char_to_output):
        self.name = name
        self.pi = which_pi
        print("Setting up ", self.name)
        self.input_bcm_pin = input_bcm_pin
        self.pi.set_mode(self.input_bcm_pin, pigpio.INPUT)
        self.pi.set_pull_up_down(self.input_bcm_pin, pigpio.PUD_UP)
        self.char_to_output = char_to_output

        self.output_bcm_pin = output_bcm_pin
        self.pi.set_PWM_dutycycle(self.output_bcm_pin, 0)

    def read_key(self):
        if self.pi.read(self.input_bcm_pin)is 0:
            print (self.name)
            return self.char_to_output
        else:
            return None

    def light_button(self, percent_pwm):
        if percent_pwm < 0:
            percent_pwm = 0
        if percent_pwm > 100:
            percent_pwm = 100
        print(percent_pwm)

        pwm_cycle = int(percent_pwm/100.0 * 255)
        print(pwm_cycle)
        self.pi.set_PWM_dutycycle(self.output_bcm_pin, pwm_cycle)


# Assign the first key to the local pi - set some defaults for the others.
right_arrow = Key(local_pi, "Right Arrow", 21, 4, 79)
left_arrow = None
up_arrow = None
down_arrow = None

try:
    remote_pi1 = pigpio.pi('KirbyPiZeroW2')
    left_arrow = Key(remote_pi1, "Left Arrow", 12, 4, 80)

except:
    print("Exception setting up KirbyPiZeroW2 - not available?")

try:
    remote_pi2 = pigpio.pi('KirbyPi3')
    up_arrow = Key(remote_pi2, "Up Arrow", 12, 4, 82)
    down_arrow = Key(remote_pi2, "Down Arrow", 21, 17, 81)

except:
    print("Exception setting up KirbyPi3 - not available?")

keys= [right_arrow, left_arrow, up_arrow, down_arrow]

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

        if key is not None:
            key_press = key.read_key()

            if key_press is not None:
                write_report(NULL_CHAR * 2 + chr(key_press) + NULL_CHAR * 5)
                write_report(NULL_CHAR * 8)
                percent += 10

                if percent > 100:
                    percent = 0

                key.light_button(percent)
                print("p{}".format(percent))

    time.sleep(0.10)