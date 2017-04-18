#!/usr/bin/env python

import os
import sys
from bluetooth import BluetoothSocket, L2CAP
import dbus
import dbus.service
import gobject
from dbus.mainloop.glib import DBusGMainLoop

PROFILE = "org.bluez.Profile1"
ADDRESS = "B8:27:EB:EC:E9:95"
DEVICE_NAME = "PiZero"

PROFILE_DBUS_PATH = "/bluez/olly/simkeyboard"
CONTROL_PORT = 17
INTERRUPT_PORT = 19
SDP_RECORD_PATH = sys.path[0] + "/sdp_record.xml"
UUID="00001124-0000-1000-8000-00805f9b34fb"

def read_service_record():
  with open(SDP_RECORD_PATH, "r") as f:
    return f.read()

class KeyboardProfile(dbus.service.Object):
  fd = -1

  @dbus.service.method(PROFILE, in_signature="", out_signature="")
  def Release(self):
    print "Release"
    mainloop.quit()

  @dbus.service.method(PROFILE, in_signature="", out_signature="")
  def Cancel(self):
    print "Cancel"

  @dbus.service.method(PROFILE, in_signature="oha{sv}", out_signature="")
  def NewConnection(self, path, fd, properties):
    self.fd = fd.take()
    print "NewConnection(%s, %d)" % (path, self.fd)
    for key in properties.keys():
      if key == "Version" or key == "Features":
        print "  %s = 0x%04x" % (key, properties[key])
      else:
        print "  %s = %s" % (key, properties[key])

  @dbus.service.method(PROFILE, in_signature="o", out_signature="")
  def RequestDisconnection(self, path):
    print "RequestDisconnection(%s)" % path
    if self.fd > 0:
      os.close(self.fd)
      self.fd = -1

  def __init__(self, bus, path):
    dbus.service.Object.__init__(self, bus, path)


class SimulatedKeyboardDevice:

  def __init__(self):
    os.system("hciconfig hci0 up")
    os.system("hciconfig hci0 class 0x002540")
    os.system("hciconfig hci0 name " + DEVICE_NAME)
    os.system("hciconfig hci0 piscan")

    opts = {
      "ServiceRecord": read_service_record(),
      "Role": "server",
      "RequireAuthentication": False,
      "RequireAuthorization": False,
    }

    bus = dbus.SystemBus()
    manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")
    profile = KeyboardProfile(bus, PROFILE_DBUS_PATH)
    manager.RegisterProfile(PROFILE_DBUS_PATH, UUID, opts)

    self.control_socket = BluetoothSocket(L2CAP)
    self.interrupt_socket = BluetoothSocket(L2CAP)
    self.control_socket.setblocking(0)
    self.interrupt_socket.setblocking(0)
    self.control_socket.bind(("", CONTROL_PORT))
    self.interrupt_socket.bind(("", INTERRUPT_PORT))

  def listen(self):
    print "Waiting for a connection"
    self.control_socket.listen(1)
    self.interrupt_socket.listen(1)
    self.control_channel = None
    self.interrupt_channel = None
    gobject.io_add_watch(
            self.control_socket.fileno(), gobject.IO_IN, self.accept_control)
    gobject.io_add_watch(
            self.interrupt_socket.fileno(), gobject.IO_IN,
            self.accept_interrupt)

  def accept_control(self, source, cond):
    self.control_channel, cinfo = self.control_socket.accept()
    print "Got a connection on the control channel from " + cinfo[0]
    return True

  def accept_interrupt(self, source, cond):
    self.interrupt_channel, cinfo = self.interrupt_socket.accept()
    print "Got a connection on the interrupt channel from " + cinfo[0]
    return True

  def send(self, message):
    if self.interrupt_channel is not None:
      self.interrupt_channel.send(message)

class KeyboardService(dbus.service.Object):

  def __init__(self):
    bus_name = dbus.service.BusName("xyz.olly.simkeyboard", bus=dbus.SystemBus())
    dbus.service.Object.__init__(self, bus_name, "/xyz/olly/simkeyboard")
    self.device = SimulatedKeyboardDevice()
    self.device.listen()

  @dbus.service.method("xyz.olly.simkeyboard", in_signature="yay")
  def send_keys(self, modifier, keys):
    cmd_str = ""
    cmd_str += chr(0xa1)
    cmd_str += chr(0x1)
    cmd_str += chr(modifier)
    cmd_str += chr(0)

    count = 0
    for key_code in keys:
      if count < 6:
        cmd_str += chr(key_code)
      count += 1

    self.device.send(cmd_str)

if __name__ == "__main__":
  if not os.geteuid() == 0:
    sys.exit("Must run as root")
  DBusGMainLoop(set_as_default=True)
  service = KeyboardService()
  gobject.threads_init()
  mainloop = gobject.MainLoop()
  mainloop.run()

