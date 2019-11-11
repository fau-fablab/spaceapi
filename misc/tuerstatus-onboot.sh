echo "2" > /sys/class/gpio/export
echo "27" > /sys/class/gpio/export
echo "in" > /sys/class/gpio/gpio2/direction 
echo "out" > /sys/class/gpio/gpio27/direction 
echo "0" > /sys/class/gpio/gpio27/value
echo "onboot done" > ~/gpiosetuplog
