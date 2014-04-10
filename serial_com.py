#!/usr/bin/python
import threading
import serial
import sys
import string

#declarations for threaded serial read/write
startFlag = 0
processFlag = 0
s = ""

class serial_reader_thread (threading.Thread):
	def __init__(self, threadID):
		threading.Thread.__init__(self)
		self.threadID = threadID;
	def run(self):
		print "Starting " + str(self.threadID);
		read();
		print "Exiting " + str(self.threadID);
def read():
	try:
		while 1:
			rec_data = con.read(1);
			if rec_data == "$":
				global startFlag
				startFlag = 1
			elif rec_data == "#":
				global processFlag
				processFlag = 1
			if startFlag == 1 :
				global s
				s += rec_data
			if len(s) >= 100 :	#reset
				s = ""
		#print rec_data
		
		'''
		sys.stdout.write(rec_data);
			sys.stdout.flush();
	'''
	except serial.SerialException:
		print "connection error";
	 
def write(s): 
	try:
		con.write(s);
	except serial.SerialException:
		print "connection error";	

#con = serial.Serial(port = "/dev/ttyAMA0", baudrate=9600);
con = serial.Serial(port = "/dev/ttyUSB0", baudrate=9600);
con.close();
con.open();
if con.isOpen():
	thread1 = serial_reader_thread(1);
	thread1.start();
	write("a");
	while 1:
		if processFlag == 1:
			packet = "".join(s)
			s = ""
			startFlag = 0
			processFlag = 0
			packet = string.replace(packet,"\n","")
			packet = packet.strip()
			print "Processing data: " + packet
con.close()
