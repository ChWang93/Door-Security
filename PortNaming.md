- Get arduino idVendor, idProduct, serial
	udevadm info --name=/dev/ttyACM{Port arduino is currently on} --attribute-walk | grep serial

- Navigate to /etc/udev/rules.d/99-usb-serial.rules

- Add system link rule to file
	SUBSYSTEM=="tty", ATTRS{idVendor}=="{idVendor number}", ATTRS{idProduct}=="{idProduct number}", ATTRS{serial}=="{serial number}", SYMLINK+="{Name of link}"
