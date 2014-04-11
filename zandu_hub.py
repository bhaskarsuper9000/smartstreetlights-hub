#!/usr/bin/python
import threading
import serial
import sys
import string
import MySQLdb

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
'''if con.isOpen():
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
'''

#Prev hub initializations
hub_id = '1'
nodes  = [1,2,3,4]
nodes_response = [0,0,0,0]

locn   = '\'43.3333N:72.6666E\''
install_date = '\'2004/01/04\''

server = '10.129.156.27'
self_server   = 'localhost'

db1 = MySQLdb.connect(host=server, user='root', passwd='', db='smartlight')
db2 = MySQLdb.connect(host=self_server, user='root', passwd='prashant#123j', db='node_history')

#port = serial.Serial("/dev/ttyAMA0", baudrate=9600)

""" If entry exists on server,update else insert
    ie. Send an SQL query to server to notify hub is up

"""

def chkAndInsert( db, sel_query, upd_query, ins_query ):
	cur = db.cursor()

	numrows = cur.execute("SELECT * FROM hub where id=%s"%hub_id)
	print "Selected %s rows" % numrows
	
	if numrows == 0:
		cur.execute(ins_query)
	elif numrows == 1:
		cur.execute(upd_query)
	else:
		print("[HUB %s]This should not happen" % hub_id)

	cur.execute("commit")	
	cur.close()
	
def sendRequest( nid, msg_breakup ):
	write("$H,%s,%s,2,%s#" %(hub_id,nid,msg_breakup))
	
def processResponse( node_id, response, msg_breakup ):
	if response.strip() == '':
		nodestatus = 0
		upd = "update node set nodestatus = 0 where id=%s and hubid=%s" %(node_id,hub_id);
		cur = db1.cursor()
		cur.execute(upd)
		cur.execute("commit")
		cur.close()
		print "[Hub %s]nodestatus(%s) set to false"%(hub_id,node_id)
		return;
	
	rmsg = response.split(",")
	print rmsg
	#if received msg is an event, process immidiately
	if rmsg[3].startsWith('1'):
		handleEvent( node_id, rmsg[:-1] )
	else:
		ldrstatus = rmsg[0][1:]
		lightstatus = rmsg[1]
		emergencylight = rmsg[2]
		pirstatus = rmsg[3]
		current = rmsg[4]
		voltage = rmsg[5]
		#nodestatus = 1 #(hard update)
		
		#Perform update in remote db
		upd = "update node set ldrstatus=%s,lightstatus=%s,emergencylight=%s,pirstatus=%s,current=%s,voltage=%s,nodestatus=1 where id=%s and hubid=%s" %(ldrstatus,lightstatus,emergencylight,pirstatus,current,voltage,node_id,hub_id)
		print upd
		cur = db1.cursor()
		cur.execute(upd)
		cur.execute("commit")
		cur.close()
		
		#Perform insert in our local database
		#Can be user later by ETL tools
		ins = "insert into history values(%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)"%(node_id,ldrstatus,pirstatus,current,voltage,nodestatus)
		cur = db2.cursor()
		cur.execute(ins)
		cur.execute("commit")
		cur.close()
	
def sendCommand(node_id, cmd):
	toSend = "$H,%s,%s,1,%s,#"%(hub_id,node_id,cmd)
	write(toSend)
	
	upd = "update node set ldrstatus=%s,lightstatus=%s,emergencylight=%s,pirstatus=%s,current=%s,voltage=%s,nodestatus=1 where id=%s and hubid=%s" %(ldrstatus,lightstatus,emergencylight,pirstatus,current,voltage,node_id,hub_id)
	print upd
	cur = db1.cursor()
	cur.execute(upd)
	cur.execute("commit")
	cur.close()


def handleEvent( st ):
	print ("Event detected : breakup %b", st)
	binary = ' '.join(format(ord(x), 'b') for x in st).reverse()
	print binary
	
	#[Yet to be done] Here lies some basic intelligence to save power
	#This works by ckecking the data received by a node n deciding
	#if a command is to be sent to the node or not

	pir = binary[0]		#0 off, 1 on
	pvalid = binary[1]		#0 invalid, 1 valid
	tod = pin[2]		#0 day, 1 night
	ldrvalid = binary[3] 	#0 invalid, 1 valid
	dim = binary[4]		#0 not dim, 1 dim

	if ldrvalid == '1' and tod == '0':
		sendCommand(node_id, 0);
	elif tod == '0' and pvalid == '1' and pir == '0' and dim == '0':
		sendCommand(node_id, 1);
	elif pvalid == '1' and pir == '1' and tod == '1':
		sendCommand(node_id, 2);
		


""" Steps in the execution cycle of hub
    1. Hub Initialization : chk & insert hub info
    
    2a. For each node in nodes send request packet
    	 Wait for 2 timeouts..if success, update to server
    	 If it fails, set active flag in server to false
    	
    2b. If data received in 2a. is an event, respond immediately
    
"""

sel = "select * from hub where id = %s" % (hub_id)
upd = "update hub set status=1 where id=%s" % (hub_id)
ins = "insert into hub values(%s,%s,%s,%s,1)"% (hub_id,locn,install_date,len(nodes))

#print ins
chkAndInsert( db1, sel, upd, ins )


#part 2a
if con.isOpen():
	#reader thread started
	thread1 = serial_reader_thread(1);
	thread1.start();

	while True:
		m = max(nodes_response)
		for node_id in nodes:
			sendRequest(node_id, 0)
			#res = waitForResponse( port )
			#processResponse(node_id, res, 0)
			#sleep(1000)
			if processFlag == 1:
				packet = "".join(s)
				s = ""
				startFlag = 0
				processFlag = 0
				packet = string.replace(packet,"\n","")
				packet = packet.strip()
				print "Processing data: " + packet
				processResponse(node_id, packet, 0)
			
			if abs(m,nodes_response[i]) > 100 :
				processResponse(i, "", 0)
		

con.close()

db1.close()
db2.close()

