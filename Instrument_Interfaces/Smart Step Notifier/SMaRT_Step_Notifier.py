# -*- coding: utf-8 -*-
"""
Created on Fri Jun 24 17:36:49 2022

@author: labadmin
"""

# Import smtplib for the actual sending function
import smtplib
import argparse

# Import the email modules we'll need
from email.mime.text import MIMEText

parser = argparse.ArgumentParser(description="Send an email with new temperature")
parser.add_argument('-t', '-T', '--temp', '--temperature', dest='step_temp', nargs='?', default=-999, type=float,
                    help='Provide the value of the current temperature step to customize the notification message.')
parser.add_argument('-f', '-F', '--freq', '--frequency', dest='step_freq', nargs='?', default=-999, type=float,
                    help='Provide the value of the frequency step to customize the notification message.')
parser.add_argument('--sample', dest='sample_str', type=str,
                    help='Provide sample name to customize notification message.')
parser.add_argument('--message', '--msg', dest='msg_str', nargs='?', default="No Message", type=str,
                    help='Provide extra message to customize notification.')
parser.add_argument('--to_addr', '--to', dest='to_addr', type=str,
                    help='Provide the recipient email address.')

args = parser.parse_args()

# Hardcoded values for sending from Ian's email address
sender_email = "iguanian.axis878@gmail.com"
sender_password = "cuiisnafgtnxwofd"

recipient_email = args.to_addr

if args.step_temp != -999 and args.step_freq != -999:
    change_str = "Temp and Freq"
    value_str = "{} C and {} Hz".format(args.step_temp, args.step_freq)
elif args.step_temp != -999:
    change_str = "Temp"
    value_str = "{} C".format(args.step_temp)
elif args.freq_temp != -999:
    change_str = "Freq"
    value_str = "{} Hz".format(args.step_freq)
else:
    change_str = ""
    value_str = ""

new_condition = value_str = "New condition: " + value_str

subject = "Notification of SMaRT Measurement {} Change".format(change_str)

body = """
<html>
  <body>
    <p>The SMaRT measurement has changed {} step settings. {}</p>
    <p> <b>Other Message:</b></p>
    <p> {} </p>
  </body>
</html>
""".format(change_str, new_condition, args.msg_str)

html_message = MIMEText(body, 'html')
html_message['Subject'] = subject
html_message['From'] = sender_email
html_message['To'] = recipient_email
with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
   server.login(sender_email, sender_password)
   server.sendmail(sender_email, recipient_email, html_message.as_string())
