#!/usr/bin/env python
import sys
import ldap
import socket
import re
import subprocess

ldapDomain = ''
ldapUser = ''
ldapPass = ''
ldapDN = '' # OU=GROUPS,DC=domain,DC=tld'
haproxyConf = '/usr/local/etc/haproxy.conf'
action = sys.argv[2]

if action == 'restart':
	restart()
if action == 'group':
	groupName = sys.argv[2]
	getADGroups()
	

# Get users from Active Directory Groups and store it to files
def getADGroups():
	l = ldap.open(ldapDomain)
	l.simple_bind_s(ldapUser,ldapPass)
	f = open('/usr/local/etc/haproxy/' + groupName,'w')

	results = l.search_s("cn=%s, %s" % (groupName, ldapDN), ldap.SCOPE_BASE)
	for result in results:
		result_dn = result[0]
		result_attrs = result[1]
	 	if "member" in result_attrs:
			for member in result_attrs["member"]:
				f.write(member.split(',')[0].split('=')[1] + '\n')
	f.close()
	restart()


# Searching stik-tables to save it and to restore after reload
def restart():
	backends = [] 	
	with open(haproxyConf) as f:
		for line in f:
			lines = line.split(' ')
			if lines[0] == 'backend':
				backends.append(lines[1].strip('\n'))
	for backend in backends:
		getDataTables(backend)
	rebootHa()
	for backend in backends:
		insertDataTables(backend)


# Writes data from stik-tables to external files
def getDataTables(table):
	print table
	tmp_f = open('/tmp/tmp.' + table,'w')
	tableVal = {}
	c = socket.socket( socket.AF_UNIX )
	c.connect("/var/run/haproxy.sock")
	c.send("prompt\r\n")
	c.send("show table " + table + "\r\n")
	d = c.recv(10240)
	for line in d.split('\n'):
		if re.search('^[a-zA-Z_0-9]',line):
			line =  line.split(' ')
			del line[0]
			for item in line:
				key = item.split('=')[0]
				val = item.split('=')[1]
				tableVal[key] = val
			print tableVal['key']
			print tableVal['server_id']
			tmp_f.write(tableVal['key'] + ',' + tableVal['server_id'] + '\n')
	tmp_f.close()


def rebootHa():
	#pass
	subprocess.call("/usr/local/etc/rc.d/haproxy reload", shell=True)
 

# Writes data from files to stik-tables
def insertDataTables(table):
	#pass
	tmp_f = open('/tmp/tmp.' + table,'r')
	#tableVal = {}
	c = socket.socket( socket.AF_UNIX )
	c.connect("/var/run/haproxy.sock")
	c.send("prompt\r\n")
	for line in tmp_f:
		line = line.split(',')
		print "set table " + table + " key " + line[0] + " data.server_id " + line[1]
		c.send("set table " + table + " key " + line[0] + " data.server_id " + line[1]  +"\r\n")
		c.recv(10240)
	c.close()


#getADGroups()
#restart()
