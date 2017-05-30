#!/usr/bin/env python3
print("starting modem.py")
from systemd import journal
import dbus
from gi.repository import GObject as gobject
from enum import Enum
from dbus.mainloop.glib import DBusGMainLoop
from subprocess import run

#APN = "4g.tele2.ee"
APN = "internet.tele2.ee"

_real_print = print
def print(*args):
    journal.send("".join([str(s) for s in args]))
    _real_print(*args)


class MMModemState(Enum):
    MM_MODEM_STATE_FAILED = -1
    MM_MODEM_STATE_UNKNOWN = 0
    MM_MODEM_STATE_INITIALIZING = 1
    MM_MODEM_STATE_LOCKED = 2
    MM_MODEM_STATE_DISABLED = 3
    MM_MODEM_STATE_DISABLING = 4
    MM_MODEM_STATE_ENABLING = 5
    MM_MODEM_STATE_ENABLED = 6
    MM_MODEM_STATE_SEARCHING = 7
    MM_MODEM_STATE_REGISTERED = 8
    MM_MODEM_STATE_DISCONNECTING = 9
    MM_MODEM_STATE_CONNECTING = 10
    MM_MODEM_STATE_CONNECTED = 11

def find_a_modem():
    #  lets get the first modem in the list
    mm_obj = bus.get_object("org.freedesktop.ModemManager1",
                            "/org/freedesktop/ModemManager1")
    mm = dbus.Interface(mm_obj, "org.freedesktop.DBus.ObjectManager")
    modems = list(mm.GetManagedObjects().items())
    if not modems:
        print("no modems found")
        return None
    modem, modem_properties = list(mm.GetManagedObjects().items())[0]
    print("got modem {}".format(modem))
    # usefull for creating iptables rules
    net_port = [x for x in modem_properties["org.freedesktop.ModemManager1.Modem"]["Ports"] if x[1]==2][0][0]
    print("got net port {}".format(net_port))
    return (modem, net_port, modem_properties)


def connect(modem, net_port=None, modem_properties=None):
    #  get modem state and do a connect or disconnect
    mm_obj = bus.get_object("org.freedesktop.ModemManager1", modem)
    mm_simple = dbus.Interface(mm_obj, "org.freedesktop.ModemManager1.Modem.Simple")
    mm_modem = dbus.Interface(mm_obj, "org.freedesktop.ModemManager1.Modem")
    mm_properties = dbus.Interface(mm_obj, 'org.freedesktop.DBus.Properties')

    net_port = str([x for x in list(mm_properties.Get("org.freedesktop.ModemManager1.Modem", "Ports")) if x[1]==2][0][0])

    modem_state = MMModemState(mm_simple.GetStatus()["state"])
    print("state:", modem_state)
    if modem_state == MMModemState.MM_MODEM_STATE_CONNECTED:
        print("already connected")
        #exit(10)
        #print("Disconnecting")
        #bearer = modem_properties["org.freedesktop.ModemManager1.Modem"]["Bearers"][0]
        #mm_simple.Disconnect(bearer)
        #mm_modem.Reset()
    else:
        print("Connecting")
        mm_simple.Connect({"apn":APN})
        #exit(0)
        # systemd-networkd will take care of geting dhcp address from the wan interface
        if net_port:
            print("ip link set " + net_port + " down")
            run(["ip", "link", "set", net_port, "down"])
            print("ip link set " + net_port +" up")
            run(["ip", "link", "set", net_port, "up"])

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    #connect(modem_path)

    modem = find_a_modem()
    if modem:
        connect(modem[0], modem[1])

    def modem_state_change(old, new, reason, path=None):
        print("state change: {}, {}".format(path, MMModemState(new)))
        if MMModemState(new) == MMModemState.MM_MODEM_STATE_REGISTERED:
            bus.remove_signal_receiver(modem_state_change)
            connect(path)
        if MMModemState(new) == MMModemState.MM_MODEM_STATE_DISABLED:
            mm_obj = bus.get_object("org.freedesktop.ModemManager1", path)
            mm_modem = dbus.Interface(mm_obj, "org.freedesktop.ModemManager1.Modem")
            mm_modem.Enable(True)

    def modem_added(modem_path, modem_properties):
        print("modem added {}".format(modem_path))
        print("enabling modem")
        mm_obj = bus.get_object("org.freedesktop.ModemManager1", modem_path)
        mm_modem = dbus.Interface(mm_obj, "org.freedesktop.ModemManager1.Modem")
        mm_modem.Enable(True)
        print("waiting for network")


    bus.add_signal_receiver(modem_added,
                            dbus_interface="org.freedesktop.DBus.ObjectManager",
                            signal_name="InterfacesAdded",
                            bus_name="org.freedesktop.ModemManager1")

    bus.add_signal_receiver(modem_state_change,
                            dbus_interface="org.freedesktop.ModemManager1.Modem",
                            signal_name="StateChanged",
                            bus_name="org.freedesktop.ModemManager1",
                            path_keyword='path')

    print("waiting for a modem")
    loop = gobject.MainLoop()
    loop.run()
