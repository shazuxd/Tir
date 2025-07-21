import re
import threading
from datetime import datetime
import requests
import json
import os

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.clock import Clock, mainthread
from android.permissions import request_permissions, Permission, check_permission
from android.storage import app_storage_path
from jnius import autoclass, cast

# Android Java components
PythonService = autoclass('org.kivy.android.PythonService')
Telephony = autoclass('android.provider.Telephony')
SmsManager = autoclass('android.telephony.SmsManager')
Context = autoclass('android.content.Context')
Intent = autoclass('android.content.Intent')
PendingIntent = autoclass('android.app.PendingIntent')
BroadcastReceiver = autoclass('android.content.BroadcastReceiver')
Environment = autoclass('android.os.Environment')
File = autoclass('java.io.File')

# Load KV layout
Builder.load_string('''
<MainUI>:
    orientation: 'vertical'
    padding: 30
    spacing: 15
    
    Label:
        text: 'OTP Forwarder'
        font_size: '24sp'
        bold: True
        size_hint_y: None
        height: 50
        
    BoxLayout:
        orientation: 'vertical'
        spacing: 10
        
        Label:
            text: 'Telegram Bot Token:'
            size_hint_y: None
            height: 30
            
        TextInput:
            id: token
            text: root.bot_token
            multiline: False
            size_hint_y: None
            height: 50
            
    BoxLayout:
        orientation: 'vertical'
        spacing: 10
        
        Label:
            text: 'Chat ID:'
            size_hint_y: None
            height: 30
            
        TextInput:
            id: chat_id
            text: root.chat_id
            multiline: False
            size_hint_y: None
            height: 50
            
    BoxLayout:
        orientation: 'vertical'
        spacing: 10
        
        Label:
            text: 'Regex Patterns (comma separated):'
            size_hint_y: None
            height: 30
            
        TextInput:
            id: regex
            text: root.regex_patterns
            multiline: False
            size_hint_y: None
            height: 50
            
    Button:
        text: 'Save Settings'
        size_hint_y: None
        height: 60
        on_press: root.save_settings()
        
    Label:
        id: status
        text: root.status_text
        color: 0.2, 0.7, 0.3, 1
        size_hint_y: None
        height: 40
''')

CONFIG_FILE = os.path.join(app_storage_path(), 'otp_forwarder_config.json')

class SmsReceiver(BroadcastReceiver):
    def __init__(self, callback, **kwargs):
        super().__init__()
        self.callback = callback

    def onReceive(self, context, intent):
        if intent.getAction() == Telephony.Sms.Intents.SMS_RECEIVED_ACTION:
            pdus = intent.getExtras().get("pdus")
            for pdu in pdus:
                sms = Telephony.Sms.Message.createFromPdu(pdu)
                sender = sms.getDisplayOriginatingAddress()
                message = sms.getDisplayMessageBody()
                timestamp = sms.getTimestampMillis()
                self.callback(sender, message, timestamp)

class MainUI(BoxLayout):
    bot_token = StringProperty("")
    chat_id = StringProperty("")
    regex_patterns = StringProperty("")
    status_text = StringProperty("Status: Idle")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_config()
        self.service = None
        self.sms_receiver = None

    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE) as f:
                    config = json.load(f)
                    self.bot_token = config.get('bot_token', '')
                    self.chat_id = config.get('chat_id', '')
                    self.regex_patterns = config.get('regex_patterns', '')
        except Exception as e:
            self.status_text = f"Error: {str(e)}"

    def save_config(self):
        config = {
            'bot_token': self.ids.token.text,
            'chat_id': self.ids.chat_id.text,
            'regex_patterns': self.ids.regex.text
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f)

    def save_settings(self):
        self.save_config()
        self.status_text = "Settings saved! Restart service if running."
        self.start_service()

    def start_service(self):
        if not all([self.ids.token.text, self.ids.chat_id.text, self.ids.regex.text]):
            self.status_text = "Error: All fields required!"
            return

        if not check_permission(Permission.RECEIVE_SMS):
            request_permissions([Permission.RECEIVE_SMS])
            self.status_text = "Requesting permissions..."
            Clock.schedule_once(lambda dt: self._start_service_after_perms(), 2)
        else:
            self._start_service()

    def _start_service_after_perms(self):
        if check_permission(Permission.RECEIVE_SMS):
            self._start_service()
        else:
            self.status_text = "Permission denied!"

    def _start_service(self):
        PythonService.start(
            autoclass('org.renpy.pservice.PService').getService(),
            'service'
        )
        self.status_text = "Service started!"

class OTPForwarderApp(App):
    def build(self):
        return MainUI()

    def on_start(self):
        self.root.start_service()

if __name__ == '__main__':
    OTPForwarderApp().run()
