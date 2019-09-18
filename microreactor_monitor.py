#!/usr/bin/python
# -*- coding: cp1252 -*-
#############################################################################
##
##  Author:   Alexander Krabbe
##  Email: Alexander@krabbe.me
#############################################################################
"""
A monitor that plots live data using PythonQwt from PyExpLabSys.socket.

The monitor expects to receive data packets in the raw format

Code herited from mba7 (monta.bha@gmail.com) and Eli Bendersky (eliben@gmail.com)
License: This code is in the public domain
Last modified: 23.05.2019
"""

import random, sys, queue, serial, glob, os, csv, time, datetime

import qwt as Qwt
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from socket_monitor import SocketThread
from globals import *
#import pymysql as sql




class PlottingDataMonitor(QMainWindow):
    def __init__(self, parent=None):
        super(PlottingDataMonitor, self).__init__(parent)
#setting the path variable for icon
        self.setWindowTitle('Surfcat \u03BC-reactor monitor')
        self.setWindowIcon(QIcon('Surfcat_logo_Alexander.pdf'))
        self.resize(800, 600)

        self.port           = ""
        self.baudrate       = 9600
        self.monitor_active = False                 # on/off monitor state
        self.LiveValue_monitor    = None                  # monitor reception thread
        self.LiveValue_data_q     = None
        self.LiveValue_error_q    = None
        self.livefeed       = LiveDataFeed()
        self.timer          = QTimer()
        self.g_samples      = [[], [], []]
        self.LiveUpdate     = ['', '', '']
        self.start_time     = 0
        self.end_time       = -1
        self.curve          = [None]*3
        self.gcurveOn       = [1]*3                 # by default all curve are plotted
        self.csvdata        = []

        self.create_menu()
        self.create_main_frame()
        self.create_status_bar()

        # Activate start-stop button connections
        getattr(self.button_Connect,"clicked").connect(self.OnStart)
        getattr(self.button_Disconnect,"clicked").connect(self.OnStop)
#        self.connect(self.button_Connect, SIGNAL("clicked()"),
#                    self.OnStart)
#        self.connect(self.button_Disconnect, SIGNAL("clicked()"),
#                    self.OnStop)
#        self.CSVfilename.returnPressed.connect(self.button_Connect.click)
#        self.OnStart()

    #----------------------------------------------------------


    def create_LiveValueBox(self):
        """
        Purpose:   create groupbox for live values
        Return:    return a layout of the values to be shown
        """
        self.LiveValueBox = QGroupBox("Live Values Box")

        LiveValue_layout = QGridLayout()

#        self.radio9600     =    QRadioButton("9600")
#        self.radio9600.setChecked(1)
#        self.radio19200    =    QRadioButton("19200") #Select if 19200 is necessary
#        self.LiveValue_ComboBox  =    QComboBox()
#        self.CSVfilename = QLineEdit()
#        self.CSVfilename.setPlaceholderText('Enter Filename Here')
#        self.Start_time = QLineEdit()
#        self.Start_time.setPlaceholderText('Start x-axis [s]')
#        self.End_time = QLineEdit()
#        self.End_time.setPlaceholderText('End x-axis [s]')

#        LiveValue_layout.addWidget(self.LiveValue_ComboBox,0,0,1,2)
#        LiveValue_layout.addWidget(self.CSVfilename,1,0,1,4)
#        LiveValue_layout.addWidget(self.Start_time,0,2,1,1)
#        LiveValue_layout.addWidget(self.End_time,0,3,1,1)
#        LiveValue_layout.addWidget(self.radio9600,0,2)
#        LiveValue_layout.addWidget(self.radio19200,0,3) #Select if 19200 is necessary
#        self.fill_ports_combobox()


        self.button_Connect      =   QPushButton("Start")
        self.button_Disconnect   =   QPushButton("Stop")
        self.button_Disconnect.setEnabled(False)

        LiveValue_layout.addWidget(self.button_Connect,0,0,1,2)
        LiveValue_layout.addWidget(self.button_Disconnect,1,0,1,2)

        self.LiveValuesCom =   [self.create_LiveValues_box('Main'),
                                self.create_LiveValues_box('Containment'),
                                self.create_LiveValues_box('Reactor'),
                                self.create_LiveValues_box('Buffer')
                                ]

        LiveValue_layout.addWidget(self.LiveValuesCom[0],0,2,1,1)
        LiveValue_layout.addWidget(self.LiveValuesCom[1],0,3,1,1)
        LiveValue_layout.addWidget(self.LiveValuesCom[2],0,4,1,1)
        LiveValue_layout.addWidget(self.LiveValuesCom[3],0,5,1,1)

        self.gCheckBoxCom =   [self.create_checkbox("Main", Qt.green, self.activate_curve, 0),
                               self.create_checkbox("Containment", Qt.red, self.activate_curve, 1),
                               self.create_checkbox("Reactor", Qt.blue, self.activate_curve, 2),
                               self.create_checkbox("Buffer", Qt.yellow, self.activate_curve, 3)
                              ]

        LiveValue_layout.addWidget(self.gCheckBoxCom[0],1,2)
        LiveValue_layout.addWidget(self.gCheckBoxCom[1],1,3)
        LiveValue_layout.addWidget(self.gCheckBoxCom[2],1,4)
        LiveValue_layout.addWidget(self.gCheckBoxCom[3],1,5)

        return LiveValue_layout
    #---------------------------------------------------------------------


    def create_plot(self):
        """
        Purpose:   create the pyqwt plot
        Return:    return a list containing the plot and the list of the curves
        """
        plot = Qwt.QwtPlot(self)
        plot.setCanvasBackground(Qt.black)
        plot.setAxisTitle(Qwt.QwtPlot.xBottom, 'Time [s]')
        plot.setAxisScale(Qwt.QwtPlot.xBottom, 0, 100, 5)
        plot.setAxisTitle(Qwt.QwtPlot.yLeft, 'Concentration [ppm]')
        plot.setAxisScale(Qwt.QwtPlot.yLeft, YMIN, YMAX, (YMAX-YMIN)/10)
        plot.replot()

        curve = [None]*3
        pen = [QPen(QColor('limegreen')), QPen(QColor('red')) ,QPen(QColor('blue')) ]
        for i in range(3):
            curve[i] =  Qwt.QwtPlotCurve('')
            curve[i].setRenderHint(Qwt.QwtPlotItem.RenderAntialiased)
            pen[i].setWidth(2)
            curve[i].setPen(pen[i])
            curve[i].attach(plot)

        return plot, curve
    #---------------------------------------------------


#    def create_knob(self):
        """
        Purpose:   create a knob
        Return:    return a the knob widget
        """
#        knob = Qwt.QwtKnob(self)
#        knob.setRange(0, 180, 0, 1)
#        knob.setScaleMaxMajor(10)
#        knob.setKnobWidth(50)
#        knob.setValue(10)
#        return knob
    #---------------------------------------------------


    def create_status_bar(self):
        self.status_text = QLabel('Monitor idle')
        self.statusBar().addWidget(self.status_text, 1)
    #---------------------------------------------------


    def create_checkbox(self, label, color, connect_fn, connect_param):
        """
        Purpose:    create a personalized checkbox
        Input:      the label, color, activated function and the transmitted parameter
        Return:     return a checkbox widget
        """
        checkBox = QCheckBox(label)
        checkBox.setChecked(1)
        checkBox.setFont( QFont("Arial", pointSize=12, weight=QFont.Bold ) )
        green = QPalette()
        green.setColor(QPalette.Foreground, color)
        checkBox.setPalette(green)
        getattr(checkBox,"clicked").connect(connect_fn,connect_param)
#        self.connect(checkBox, SIGNAL("clicked()"), partial(connect_fn,connect_param))
        return checkBox
        #---------------------------------------------------




    def create_LiveValues_box(self,name):
        LineRead = QLineEdit()
        LineRead.setReadOnly(True)
        LineRead.setPlaceholderText(name)
        LineRead.setMaximumWidth(75)
        font = LineRead.font()
        font.setPointSize(16)
        LineRead.setFont(font)
        return LineRead



    def create_main_frame(self):
        """
        Purpose:    create the main frame Qt widget
        """
        # Serial communication combo box
        portname_layout = self.create_LiveValueBox()
        self.LiveValueBox.setLayout(portname_layout)

        # Update speed knob
#        self.updatespeed_knob = self.create_knob()
#        self.connect(self.updatespeed_knob, SIGNAL('valueChanged(double)'),
#            self.on_knob_change)
#        self.knob_l = QLabel('Update speed = %s (Hz)' % self.updatespeed_knob.value())
#        self.knob_l.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Create the plot and curves
        self.plot, self.curve = self.create_plot()

        # Create the configuration horizontal panel
        self.max_spin    = QSpinBox()
        self.max_spin.setMaximum(1000)
        self.max_spin.setValue(1000)
        spins_hbox      = QHBoxLayout()
        spins_hbox.addWidget(QLabel('Save every'))
        spins_hbox.addWidget(self.max_spin)
        spins_hbox.addWidget( QLabel('Lines'))
        #spins_hbox.addStretch(1)

#        self.gCheckBox   =  [   self.create_checkbox("NO", Qt.green, self.activate_curve, 0),
#                                self.create_checkbox("NO2", Qt.red, self.activate_curve, 1),
#                                self.create_checkbox("NOx", Qt.blue, self.activate_curve, 2)
#                            ]

#        self.LiveValues =   [   self.create_LiveValues_box('NO'),
#                                self.create_LiveValues_box('NO2'),
#                                self.create_LiveValues_box('NOx')
#                            ]



#        self.button_clear      =   QPushButton("Clear screen")

#        self.connect(self.button_clear, SIGNAL("clicked()"),
#                    self.clear_screen)

        # Place the horizontal panel widget
        plot_layout = QGridLayout()
        plot_layout.addWidget(self.plot,0,0,7,7)
#        plot_layout.addWidget(self.gCheckBox[0],0,8)
#        plot_layout.addWidget(self.gCheckBox[1],2,8)
#        plot_layout.addWidget(self.gCheckBox[2],4,8)
#        plot_layout.addWidget(self.LiveValues[0],1,8,1,1)
#        plot_layout.addWidget(self.LiveValues[1],3,8,1,1)
#        plot_layout.addWidget(self.LiveValues[2],5,8,1,1)
#        plot_layout.addWidget(self.button_clear,3,8)
#        plot_layout.addLayout(spins_hbox,4,8)
#        plot_layout.addWidget(self.updatespeed_knob,10,10)
#        plot_layout.addWidget(self.knob_l,9,9)

        plot_groupbox = QGroupBox('Live plot of NOx measurement')
        plot_groupbox.setLayout(plot_layout)


        # Place the main frame and layout
        self.main_frame = QWidget()
        main_layout     = QGridLayout()
        main_layout.addWidget(self.LiveValueBox,0,0,1,1)
        main_layout.addWidget(plot_groupbox,1,0,8,1)
        self.main_frame.setLayout(main_layout)

        self.setCentralWidget(self.main_frame)
    #----------------------------------------------------------------------


    def clear_screen(self):
        g_samples[0] = []
    #-----------------------------


    def activate_curve(self, axe):
        if self.gCheckBoxCom[axe].isChecked():
            self.gcurveOn[axe]  = 1
        else:
            self.gcurveOn[axe]  = 0
    #---------------------------------------


    def create_menu(self):
        self.file_menu = self.menuBar().addMenu("&File")

        selectport_action = self.create_action("Select COM &Port...",
            shortcut="Ctrl+P", slot=self.on_select_port, tip="Select a COM port")
        self.start_action = self.create_action("&Start monitor",
            shortcut="Ctrl+M", slot=self.OnStart, tip="Start the data monitor")
        self.stop_action = self.create_action("&Stop monitor",
            shortcut="Ctrl+T", slot=self.OnStop, tip="Stop the data monitor")
        exit_action = self.create_action("E&xit", slot=self.close,
            shortcut="Ctrl+X", tip="Exit the application")

        self.start_action.setEnabled(False) #Set to false from beginning of script
        self.stop_action.setEnabled(False)

        self.add_actions(self.file_menu,
            (   selectport_action, self.start_action, self.stop_action,
                None, exit_action))

        self.help_menu = self.menuBar().addMenu("&Help")
        about_action = self.create_action("&About",
            shortcut='F1', slot=self.on_about,
            tip='About the monitor')

        self.add_actions(self.help_menu, (about_action,))
    #----------------------------------------------------------------------


    def set_actions_enable_state(self):
        if self.portname.text() == '':
            start_enable = stop_enable = False
        else:
            start_enable = not self.monitor_active
            stop_enable = self.monitor_active

        self.start_action.setEnabled(start_enable)
        self.stop_action.setEnabled(stop_enable)
    #-----------------------------------------------


    def on_about(self):
        msg = __doc__
        QMessageBox.about(self, "About the demo", msg.strip())
    #-----------------------------------------------



    def on_select_port(self):

        ports = enumerate_serial_ports()

        if len(ports) == 0:
            QMessageBox.critical(self, 'No ports',
                'No serial ports found')
            return

        item, ok = QInputDialog.getItem(self, 'Select a port',
                    'Serial port:', ports, 0, False)

        if ok and not item.isEmpty():
            self.portname.setText(item)
            self.set_actions_enable_state()
    #-----------------------------------------------


    def fill_ports_combobox(self):
        """ Purpose: rescan the serial port com and update the combobox
        """
        vNbCombo = ""
        self.LiveValue_ComboBox.clear()
        self.AvailablePorts = enumerate_serial_ports()
        for value in self.AvailablePorts:
            self.LiveValue_ComboBox.addItem(value)
            vNbCombo += value + " - "
        vNbCombo = vNbCombo[:-3]

        debug(("--> Les ports series disponibles sont: %s " % (vNbCombo)))
    #----------------------------------------------------------------------


    def OnStart(self):
        """ Start the monitor: LiveValue_monitor thread and the update timer
            IF and ONLY if filename is uniqe
        """
#        is_filename_uniqe = self.CSVfilename.text() +'.csv'
        while True:
            if self.CSVfilename.text() == '':
                print(self.CSVfilename.text())
                self.StartIfFileNameIsUniqe()
                break
            elif os.path.isfile(os.path.join(os.pardir,self.CSVfilename.text()+'.csv')):
                print(self.CSVfilename.text())
                text, ok = QInputDialog.getText(self, 'Alert!!',
                            'New filename please:',QLineEdit.Normal,self.CSVfilename.text())

                if ok and not os.path.isfile(os.path.join(os.pardir,text+'.csv')):
                    self.CSVfilename.setText(text)
                    self.StartIfFileNameIsUniqe()
                    break
                elif ok and os.path.isfile(os.path.join(os.pardir,text+'.csv')):
                    self.CSVfilename.setText(text)
                elif not ok:
                    break
            elif not os.path.isfile(self.CSVfilename.text() +'.csv'):
                self.StartIfFileNameIsUniqe()
                break
#        elif:
#            self.StartIfFileNameIsUniqe()


    def StartIfFileNameIsUniqe(self):

        self.CSVfilename.setEnabled(False)

        self.newcsvfile = open(os.path.join(os.pardir,self.CSVfilename.text()+'.csv'),'w')

        if self.radio19200.isChecked():
            self.baudrate = 19200
            print("--> baudrate is 19200 bps")
        if self.radio9600.isChecked():
            self.baudrate = 9600
            print("--> baudrate is 9600 bps")



        vNbCombo    = self.LiveValue_ComboBox.currentIndex()
        self.port   = self.AvailablePorts[vNbCombo]

        self.button_Connect.setEnabled(False)
        self.button_Disconnect.setEnabled(True)
        self.LiveValue_ComboBox.setEnabled(False)
        self.data_q      =  queue.Queue()
        self.error_q     =  queue.Queue()
        self.LiveValue_monitor =  ComMonitorThread(
                                            self.data_q,
                                            self.error_q,
                                            self.port,
                                            self.baudrate)

        self.LiveValue_monitor.start()
#        print(self.data_q)
        LiveValue_error = get_item_from_queue(self.error_q)
        if LiveValue_error is not None:
            QMessageBox.critical(self, 'ComMonitorThread error',
                LiveValue_error)
            self.LiveValue_monitor = None

        self.monitor_active = True
        getattr(self.timer,"timeout").connect(self.on_timer)
#        self.connect(self.timer, SIGNAL('timeout()'), self.on_timer)

#        update_freq = self.updatespeed_knob.value()
        update_freq = 100
        if update_freq > 0:
            self.timer.start(1000.0 / update_freq)
#        self.timer.start(5000)

        self.status_text.setText('Monitor running')
        debug('--> Monitor running')
    #------------------------------------------------------------


    def OnStop(self):
        """ Stop the monitor
        """
        #print("stopping")
        if self.LiveValue_monitor is not None:
            #print('self.LiveValue_monitor not NOne')
            #self.LiveValue_monitor.join(1000)
            self.LiveValue_monitor = None
        #print("still stopping")
        self.CSVfilename.setEnabled(True)
        self.monitor_active = False
        self.button_Connect.setEnabled(True)
        self.button_Disconnect.setEnabled(False)
        self.LiveValue_ComboBox.setEnabled(True)
        self.timer.stop()
        self.status_text.setText('Monitor idle')
        ## Close CSV file
        self.newcsvfile.close()
        debug('--> Monitor idle')
        if self.CSVfilename.text() == '':
            pass
        else:
            try:
                conn = sql.connect(user='nox', password='kB7INF7OPn94SOCu!',host='192.168.1.201',database='nox_iso')
                cursor = conn.cursor()
                # filename skal defineres
                csv_data = csv.reader(open(os.path.join(os.pardir,self.CSVfilename.text()+'.csv')))
                for row in csv_data:
                    row.append(str(self.CSVfilename.text()))
                    cursor.execute("INSERT INTO nox_2017 (datetime,t,no,no2,nox,flow_no,flow_dry,flow_wet,rh,name) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", row)

                #close the connection to the database.
                conn.commit()
                cursor.close()
            except:
                print('Offline')

    #-----------------------------------------------


    def on_timer(self):
        """ Executed periodically when the monitor update timer
            is fired.
        """
        self.read_serial_data()
        self.update_monitor()
	#-----------------------------------------------


    def on_knob_change(self):
        """ When the knob is rotated, it sets the update interval
            of the timer.
        """
#        update_freq = self.updatespeed_knob.value()
#        self.knob_l.setText('Update speed = %s (Hz)' % self.updatespeed_knob.value())

        if self.timer.isActive():
            update_freq = max(0.01, update_freq)
            self.timer.setInterval(1000.0 / update_freq)
    #-----------------------------------------------


    def update_monitor(self):
        """ Updates the state of the monitor window with new
            data. The livefeed is used to find out whether new
            data was received since the last update. If not,
            nothing is updated.
        """
        if self.livefeed.has_new_data:
            data = self.livefeed.read_data()

            self.csvdata.append([data['timestamp'], data['gx'], data['gy'], data['gz']] )
            if len(self.csvdata) > self.max_spin.value():
#                f = open(time.strftime("%H%M%S")+".csv", 'wt')
#                try:
#                    writer = csv.writer(f)
#                    for i in range(self.max_spin.value()):
#                        writer.writerow( self.csvdata[i] )
#                    print('transfert data to csv after 1000 samples')
#                finally:
#                    f.close()
                self.csvdata = []

            self.g_samples[0].append(
                (data['timestamp'], data['gx']))
            if len(self.g_samples[0]) > 1800:
                self.g_samples[0].pop(0)

            self.g_samples[1].append(
                (data['timestamp'], data['gy']))
            if len(self.g_samples[1]) > 1800:
                self.g_samples[1].pop(0)

            self.g_samples[2].append(
                (data['timestamp'], data['gz']))
            if len(self.g_samples[2]) > 1800:
                self.g_samples[2].pop(0)

            tdata = [s[0] for s in self.g_samples[2]]

            for i in range(3):
                self.LiveValuesCom[i].setText(str(self.g_samples[i][-1][1]))
                data[i] = [s[1] for s in self.g_samples[i]]
                if self.gcurveOn[i]:
                    self.curve[i].setData(tdata, data[i])

            """
            debug("xdata", data[0])
            debug("ydata", data[1])
            debug("tdata", data[2])
            """
######### Start og Slut x-tid #######
            try:
                self.start_time = int(self.Start_time.text())
            except:
                self.start_time = tdata[0]
            if self.start_time > tdata[-1] or self.start_time > self.end_time or self.start_time < tdata[0]:
                self.start_time = tdata[0]

            try:
                self.end_time = int(self.End_time.text())
            except:
                self.end_time = tdata[-1]
            if self.end_time > tdata[-1] or self.end_time < self.start_time or self.end_time < 1:
                self.end_time = tdata[-1]
#            print(self.start_time)
#            print(self.end_time)
            self.plot.setAxisScale(Qwt.QwtPlot.xBottom, self.start_time, max(5, self.end_time) )

            self.plot.replot()
    #-----------------------------------------------


    def read_serial_data(self):
        """ Called periodically by the update timer to read data
            from the serial port.
        """
        qdata = list(get_all_from_queue(self.data_q))

        # get just the most recent data, others are lost
#        print(qdata)
        if len(qdata) > 0:
            data = dict(timestamp=qdata[-1][1],
                        gx=qdata[-1][0][1],
                        gy=qdata[-1][0][2],
                        gz=qdata[-1][0][3]
                        )
            self.livefeed.add_data(data)
            qdata[-1][0][0]=qdata[-1][1]
            line = ','.join(str(x) for x in qdata[-1][0])
            line_to_write = str(datetime.datetime.now())+','+line
            self.newcsvfile.write(line_to_write+'\n')


    #-----------------------------------------------



    # The following two methods are utilities for simpler creation
    # and assignment of actions
    #
    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)
    #-----------------------------------------------


    def create_action(  self, text, slot=None, shortcut=None,
                        icon=None, tip=None, checkable=False,
                        signal="triggered"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
#            self.connect(action, SIGNAL(signal), slot)
            getattr(action, signal).connect(slot)
        if checkable:
            action.setCheckable(True)
        return action
    #-----------------------------------------------



def main():
    app = QApplication(sys.argv)
    form = PlottingDataMonitor()
    form.show()
    app.exec_()


if __name__ == "__main__":
    main()
