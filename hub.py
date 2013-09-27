import MySQLdb
import serial
import string

hub_id = '1'
nodes  = [1,2,3,4]
locn   = '\'43.3333N:72.6666E\''
install_date = '\'2004/01/04\''

server = '10.129.154.129'
self   = 'localhost'

db1 = MySQLdb.connect(host=server, user='smart', passwd='smart', db='smartlight')
db2 = MySQLdb.connect(host=self, user='root', passwd='prashant#123j', db='node_history')

port = serial.Serial("/dev/ttyAMA0", baudrate=9600)

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
	
def sendRequest( port, nid, msg_breakup ):
	port.write("$H,%s,%s,2,%s#" %(hub_id,nid,msg_breakup))
	
def waitForResponse( port ):
	port.timeout = 5.0
	port = serial.Serial("/dev/ttyAMA0", baudrate=9600, timeout=2.0)
	
	rcv = port.read(1)
	res = ''
	while rcv.strip() != '':
		res = string.join(res,rcv)
		rcv = port.read(1)
	
	print res;
	return res;

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
	#if received msg is an event, process immidiately
	if rmsg[3].startsWith('1'):
		handleEvent( rmsg[:-1] )
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
		ins = "insert into node values()"
		cur = db2.cursor()
		cur.execute(ins)
		cur.execute("commit")
		cur.close()
		

def handleEvent( str ):
	print ("Event detected : breakup %b", str)
	bin = ' '.join(format(ord(x), 'b') for x in st).reverse()
	print bin
		


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
for node_id in nodes:
	sendRequest(port, node_id, 65)
	res = waitForResponse( port )
	processResponse(node_id, res, 65)

port.close()

db1.close()
db2.close()