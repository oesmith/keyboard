#!/usr/bin/env python

import dbus
import evdev
from select import select
import time
import keymap

class Keyboard():

  def __init__(self):
    # Eight modifiers
    # - Right Super
    # - Right Alt
    # - Right Shift
    # - Right Control
    # - Left Super
    # - Left Alt
    # - Left Shift
    # - Left Control
    self.modifier_state = 0
    # Up to six keys can be depressed at once.
    self.key_state = [0,0,0,0,0,0]

    # Hook up DBus
    bus = dbus.SystemBus()
    service = bus.get_object("xyz.olly.simkeyboard", "/xyz/olly/simkeyboard")
    self.iface = dbus.Interface(service, "xyz.olly.simkeyboard")

    # Get the keyboard device
    while True:
      devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
      if len(devices) > 0:
        self.devices = {dev.fd: dev for dev in devices}
        print "Found keyboard"
        return
      print "Keyboard not found, sleeping.."
      time.sleep(3)

  def event_loop(self):
    while True:
      r, w, x = select(self.devices, [], [])
      for fd in r:
        for event in self.devices[fd].read():
          if event.type == evdev.ecodes.EV_KEY and event.value < 2:
              self.update(event)
              self.send_input()

  def update(self, event):
    code = evdev.ecodes.KEY[event.code]
    modkey = keymap.modkey(code)
    if modkey > 0:
      self.modifier_state ^= 1 << (7 - modkey)
    else:
      key = keymap.convert(code)
      for i in range(len(self.key_state)):
        if self.key_state[i] == 0 and event.value == 1:
          self.key_state[i] = key
          break
        elif self.key_state[i] == key and event.value == 0:
          self.key_state[i] = 0

  def send_input(self):
    self.iface.send_keys(self.modifier_state, self.key_state)

if __name__ == "__main__":
  kb = Keyboard()
  print "Starting event loop"
  kb.event_loop()
