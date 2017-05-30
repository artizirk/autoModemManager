# Automatic ModemManager 4G modem connector

This script uses ModemManager to automaticaly setup a Huawei 4G modem internet
connection by monitoring autoplug events from ModemManager, setting APN on
new modem detection and then letting systemd-networkd to obtain the ip address
for the modem interface.

# Requierments

You need Python 3 with `python-systemd`, `python-gobject`, `python-dbus` libraries

On the system side you have to install and enable ModemManager service and also
systemd-networkd and systemd-resolved. Sample config files that i used are
provided in `*.network` files
