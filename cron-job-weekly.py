#!/usr/bin/env python3
"""
STEP 2: Weekly Automation - Label NEW emails + delete old uncategorized
Run this weekly via cron - it's lightweight and efficient
"""

import os
import pickle
import json
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from datetime import datetime, timedelta

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

logging.basicConfig(
    filename='/tmp/gmail_automation.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

class GmailWeeklyAutomation:
    def __init__(self):
        self.service = None
        self.authenticate()
        self.rules = self.load_rules()
        self.label_ids = {}

    def log(self, msg):
        """Log to both file and console"""
        logging.info(msg)
        print(msg)

    def authenticate(self):
        """Use existing credentials"""
        if not os.path.exists('client_secret.json'):
            self.log("ERROR: client_secret.json not found")
            self.log("   Please run '1_initial_setup.py' first")
            return False

        with open('client_secret.json', 'rb') as token:
            creds = pickle.load(token)

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        self.service = build('gmail', 'v1', credentials=creds)
        self.log("✓ Authenticated")
        return True

    def load_rules(self):
        """Load rules"""
        if not os.path.exists('gmail_rules.json'):
            self.log("ERROR: gmail_rules.json not found")
            return {}

        with open('gmail_rules.json', 'r') as f:
            return json.load(f)

    def get_label_id(self, label_name):
        """Get label ID"""
        if label_name in self.label_ids:
            return self.label_ids[label_name]

        try:
            results = self.service.users().labels().list(userId='me').execute()
            for label in results.get('labels', []):
                if label['name'] == label_name:
                    self.label_ids[label_name] = label['id']
                    return label['id']
        except:
            pass

        return None

    def label_new_emails(self):
        """Label new emails from known senders"""
        self.log("\n Labeling new emails...")
        total = 0

        for category, senders in self.rules.items():
            label_id = self.get_label_id(category)
            if not label_id:
                continue

            count = 0
            for sender in senders:
                try:
                    # Find emails without this label yet
                    results = self.service.users().messages().list(
                        userId='me',
                        q=f'from:{sender} -label:{category}',
                        maxResults=100
                    ).execute()

                    for msg in results.get('messages', []):
                        try:
                            self.service.users().messages().modify(
                                userId='me',
                                id=msg['id'],
                                body={'addLabelIds': [label_id]}
                            ).execute()
                            count += 1
                            total += 1
                        except:
                            pass
                except:
                    pass

            if count > 0:
                self.log(f"   • {category}: +{count} emails")

        return total

    def delete_old_uncategorized(self, days=30):
        """Delete old emails with no label"""
        self.log(f"\nCleaning old uncategorized (>{days} days)...")

        cutoff = datetime.now() - timedelta(days=days)
        exclude = ' '.join([f'-label:{cat}' for cat in self.rules.keys()])
        query = f'before:{cutoff.strftime("%Y/%m/%d")} {exclude} -label:[Gmail]/Trash'

        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=100
            ).execute()

            count = 0
            for msg in results.get('messages', []):
                try:
                    self.service.users().messages().trash(
                        userId='me', id=msg['id']).execute()
                    count += 1
                except:
                    pass

            if count > 0:
                self.log(f"   ✓ Moved {count} emails to Trash")
            else:
                self.log(f"   ✓ No old emails to delete")
        except:
            pass

    def run(self):
        """Run automation"""
        self.log("\n" + "="*60)
        self.log("WEEKLY GMAIL AUTOMATION")
        self.log("="*60)

        if not self.service or not self.rules:
            self.log("Setup incomplete. Run '1_initial_setup.py' first")
            return

        labeled = self.label_new_emails()
        self.delete_old_uncategorized(days=30)

        self.log("\n" + "="*60)
        self.log(f"Done! Labeled {labeled} emails")
        self.log("="*60 + "\n")

if __name__ == '__main__':
    automation = GmailWeeklyAutomation()
    automation.run()