import smtplib, ssl
import yagmail
import logging

port = 25  # For SSL

class Email(object):
    def __init__(self, config, receiver, body, subject):
        self.config = config
        self.receiver = receiver
        self.body = body
        self.sender = self.config.get('QMServer', 'SendMail')
        self.pwd = self.config.get('QMServer', 'SecKey')
        self.subject = subject

    def sendMail(self):
        receiver = self.receiver
        body = self.body

        yag = yagmail.SMTP(self.config.get('QMServer', 'SendMail'), self.config.get('QMServer', 'SecKey'))
        yag.send(
            to=receiver,
            subject=self.subject,
            contents=body
        )