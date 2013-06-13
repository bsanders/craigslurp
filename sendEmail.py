#! /usr/bin/env python

import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

class smtp():
	username = ""
	password = ""
	
	# The class constructor just takes a username and password
	def __init__(self, username, password):
		self.username = username
		self.password = password


	# hardcoded to use gmail's smtp server
	# sends an email with body to one or more addresses, with optional attachments
	def sendEmail(self, to, subject, text, files=[], debug=False):
		username = self.username
		password = self.password

		# start building the messsage to send
		msg = MIMEMultipart()
		msg['from'] = username
		msg['to'] = COMMASPACE.join(to) # support multiple people in the 'to' field
		msg['Date'] = formatdate(localtime=True)
		msg['Subject'] = subject

		# attach the actual text of the email "the body"
		msg.attach( MIMEText(text) )

		# loop over the files passed in, encoding to base64 and attaching to the message
		for filename in files:
			part = MIMEBase('application', "octet-stream")
			part.set_payload( open(filename,"rb").read() )
			Encoders.encode_base64(part)
			part.add_header('Content-Disposition', 'attachment; filename="{0}"'.format(os.path.basename(filename))
			msg.attach(part)

		# finally, create the connection
		server = smtplib.SMTP('smtp.gmail.com', 587)
		# for debugging this info can be useful, but there's a ton of it
		if debug:
			server.set_debuglevel(1)
		server.ehlo()
		server.starttls()
		server.login(username, password)
		server.sendmail(username, to, msg.as_string())
		server.quit()
