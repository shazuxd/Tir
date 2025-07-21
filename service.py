import os
import re
import json
import requests
from datetime import datetime
from jnius import autoclass, PythonJavaClass, java_method
from android import mActivity

CONFIG_FILE = os.path.join(autoclass('android.content.Context').getFilesDir().getAbsolutePath(), 'otp_forwarder_config.json')

class SmsHandler:
    def __init__(self):
        self.config = self.load_config()
        self.regex_list = [pattern.strip() for pattern in self.config.get('regex_patterns', '').split(',')]

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE) as f:
                    return json.load(f)
        except:
            pass
        return {}

    def should_forward(self, message):
        for pattern in self.regex_list:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    def send_to_telegram(self, sender, message):
        if not self.config:
            return
            
        bot_token = self.config.get('bot_token')
        chat_id = self.config.get('chat_id')
        
        if not (bot_token and chat_id):
            return
            
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"OTP Alert!\nFrom: {sender}\nMessage: {message}",
            "parse_mode": "HTML"
        }
        
        try:
            requests.post(url, json=payload, timeout=10)
        except:
            pass

class SmsReceiver(PythonJavaClass):
    __javacontext__ = 'app'
    __javainterfaces__ = ['android/content/BroadcastReceiver']
    
    def __init__(self):
        super().__init__()
        self.handler = SmsHandler()
        
    @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
    def onReceive(self, context, intent):
        if intent.getAction() == "android.provider.Telephony.SMS_RECEIVED":
            pdus = intent.getExtras().get("pdus")
            for pdu in pdus:
                sms = autoclass('android.telephony.SmsMessage').createFromPdu(pdu)
                sender = sms.getDisplayOriginatingAddress()
                message = sms.getDisplayMessageBody()
                if self.handler.should_forward(message):
                    self.handler.send_to_telegram(sender, message)

def start_service():
    handler = SmsHandler()
    receiver = SmsReceiver()
    
    # Register SMS receiver
    IntentFilter = autoclass('android.content.IntentFilter')
    filter = IntentFilter()
    filter.addAction("android.provider.Telephony.SMS_RECEIVED")
    filter.setPriority(999)
    
    mActivity.registerReceiver(receiver, filter)

if __name__ == '__main__':
    start_service()
