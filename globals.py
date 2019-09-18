
import  random, sys, queue, serial, glob, os, csv, time

# ADXL345 constants
EARTH_GRAVITY_MS2   = 9.80665
SCALE_MULTIPLIER    = 0.0078

YMAX				=	 1.100
YMIN				=   0.000

ktrace = 0

class LiveDataFeed(object):
    """ A simple "live data feed" abstraction that allows a reader 
        to read the most recent data and find out whether it was 
        updated since the last read. 
        
        Interface to data writer:
        
        add_data(data):
            Add new data to the feed.
        
        Interface to reader:
        
        read_data():
            Returns the most recent data.
            
        has_new_data:
            A boolean attribute telling the reader whether the
            data was updated since the last read.    
    """
    def __init__(self):
        self.cur_data = None
        self.has_new_data = False
    
    def add_data(self, data):
        self.cur_data = data
        self.has_new_data = True
    
    def read_data(self):
        self.has_new_data = False
        return self.cur_data
#-----------------------------------------------

def debug(message1, message2=None, message3=None):
    if ktrace:
        print(message1+','+ message2+','+ message3)

#===============================================================================
# partial: very useful function needed when using a connection to a function and 
# we need to transmit a variable
#===============================================================================
if sys.version_info[:2] < (2, 5):
    def partial(func, arg):
        def callme():
            return func(arg)
        return callme
else:
    from functools import partial
#----------------------------------------------------------------------

def get_all_from_queue(Q):
    """ Generator to yield one after the others all items 
        currently in the queue Q, without any waiting.
    """
    try:
        while True:
            yield Q.get_nowait( )
    except queue.Empty:
        raise StopIteration
#------------------------------------------------------------

def get_item_from_queue(Q, timeout=0.01):
    """ Attempts to retrieve an item from the queue Q. If Q is
        empty, None is returned.
        
        Blocks for 'timeout' seconds in case the queue is empty,
        so don't use this method for speedy retrieval of multiple
        items (use get_all_from_queue for that).
    """
    try: 
        item = Q.get(True, 0.01)
    except queue.Empty: 
        return None
    return item
#------------------------------------------------------------

def enumerate_serial_ports():
    """ 
    Purpose:        scan for available serial ports
    Return:         return a list of of the availables ports names
    """
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result_port = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result_port.append(port)
        except (OSError, serial.SerialException):
            pass
    return result_port
#----------------------------------------------------------------------
