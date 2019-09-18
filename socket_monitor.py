
import queue, threading, time, serial
from globals            import *



class SocketThread(threading.Thread):
    """ A thread for monitoring a COM port. The COM port is
        opened when the thread is started.

        data_q:
            Queue for received data. Items in the queue are
            (data, timestamp) pairs, where data is a binary
            string representing the received data, and timestamp
            is the time elapsed from the thread's start (in
            seconds).

        error_q:
            Queue for error messages. In particular, if the
            serial port fails to open for some reason, an error
            is placed into this queue.

        port:
            The COM port to open. Must be recognized by the
            system.

        port_baud/stopbits/parity:
            Serial communication parameters

        port_timeout:
            The timeout used for reading the COM port. If this
            value is low, the thread will return data in finer
            grained chunks, with more accurate timestamps, but
            it will also consume more CPU.
    """
    def __init__(   self,
                    data_q, error_q,
                    port_num,
                    port_baud,
                    port_stopbits = serial.STOPBITS_ONE,
                    port_parity   = serial.PARITY_NONE,
                    port_timeout  = 0.01):
        threading.Thread.__init__(self)

        self.serial_port = None
        self.serial_arg  = dict( port      = port_num,
                                 baudrate  = port_baud,
                                 stopbits  = port_stopbits,
                                 parity    = port_parity,
                                 timeout   = port_timeout)

        self.data_q   = data_q
        self.error_q  = error_q

        self.alive    = threading.Event()
        self.alive.set()
    #------------------------------------------------------


    def run(self):
        try:
            if self.serial_port:
                self.serial_port.close()
            self.serial_port = serial.Serial(**self.serial_arg)
        except serial.SerialException as e:
            self.error_q.put(e.message)
            return

        # Restart the clock
        startTime = time.time() #Set timer till beginning of script

        while self.alive.isSet():
            while (self.serial_port.inWaiting()==0): #Wait till data is recieved
                pass
            Line = self.serial_port.readline()
            ArduinoLine = Line.decode('utf-8')[:-1] #decode line as utf-8 without b and /n
            dataArray = ArduinoLine.split(',')
#            print(dataArray)
#            print(Line)
#            print(dataArray)
            qdata = [0,0,0,0,0,0,0,0]
#            for i in len(dataArray):
#                qdata[i] = float(dataArray[i])
            for i in range(len(dataArray)):
                if dataArray[i] == '' or dataArray == '-':
                    dataArray[i] = 0
                qdata[i] = float(dataArray[i]) #NO conc

#            qdata[1] = float(dataArray[2]) #NO2 conc
 #           qdata[2] = float(dataArray[3]) #NOx conc
  #          qdata[3] = float(dataArray[4]) #Pressure NO
   #         qdata[4] = float(dataArray[5]) #Pressure NO2
    #        qdata[5] = float(dataArray[6]) #Pressure NOx
     #       qdata[6] = float(dataArray[7]) #Relative Humidity
      #      qdata[7] = float(dataArray[0]) #Random number


#            print(qdata)
            timestamp = time.clock()
#            print(startTime)
            print(timestamp)
            self.data_q.put((qdata, timestamp))



        # clean up
        if self.serial_port:
            self.serial_port.close()

    def join(self, timeout=None):
        self.alive.clear()
        threading.Thread.join(self, timeout)

