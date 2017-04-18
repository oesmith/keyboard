import evdev
import gobject
from select import select
import time
import keymap

class Keyboard():

  def __init__(self, service):
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

    self.service = service

    # Get the keyboard device
    while True:
      self.devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
      if len(self.devices) > 0:
        for device in self.devices:
          gobject.io_add_watch(device.fd, gobject.IO_IN, self.read, device)
        print "Found keyboard"
        return
      print "Keyboard not found, sleeping.."
      time.sleep(3)

  def read(self, source, cond, device):
    for event in device.read():
      if event.type == evdev.ecodes.EV_KEY and event.value < 2:
          self.update(event)
          self.send_input()
    return True

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
    self.service.send_keys(self.modifier_state, self.key_state)
