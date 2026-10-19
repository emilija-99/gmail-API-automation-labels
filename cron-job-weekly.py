#!/usr/bin/env python3
"""
STEP 2: Weekly Automation - Label NEW emails + delete old uncategorized
Run this weekly via cron - it's lightweight and efficient
"""

import os
import json
import logging
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from auth import get_service, AuthError

logging.basicConfig(
    filename='/tmp/gmail_automation.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

class GmailWeeklyAutomation:
    def __init__(self, dry_run=False):
        self.service = get_service(interactive=False)  # raises AuthError
        self.rules = self.load_rules()
        self.label_ids = {}
        self.dry_run = dry_run
        self.errors = 0

    def log(self, msg):
        """Log to both file and console"""
        logging.info(msg)
        print(msg)

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
        except HttpError as e:
            self.errors += 1
            self.log(f"   ERROR: {e}")

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
                        q=f'from:{sender} has:nouserlabels -in:trash',
                        maxResults=100
                    ).execute()

                    ids = [m['id'] for m in results.get('messages', [])]
                    if ids and not self.dry_run:
                        self.service.users().messages().batchModify(
                            userId='me',
                            body={'ids': ids, 'addLabelIds': [label_id]}
                        ).execute()
                    count += len(ids)
                    total += len(ids)
                except HttpError as e:
                    self.errors += 1
                    self.log(f"   ERROR: {e}")

            if count > 0:
                self.log(f"   • {category}: +{count} emails")

        return total

    def delete_old_uncategorized(self, days=30):
        """Delete old emails with no label"""
        self.log(f"\nCleaning old uncategorized (>{days} days)...")

        cutoff = datetime.now() - timedelta(days=days)
        query = f'before:{cutoff.strftime("%Y/%m/%d")} has:nouserlabels -in:trash'

        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=100
            ).execute()

            ids = [m['id'] for m in results.get('messages', [])]

            if self.dry_run:
                self.log(f"   DRY RUN: {len(ids)} emails WOULD be moved to Trash:")
                for mid in ids[:25]:
                    m = self.service.users().messages().get(
                        userId='me', id=mid, format='metadata',
                        metadataHeaders=['From', 'Subject']).execute()
                    h = {x['name']: x['value'] for x in m['payload']['headers']}
                    self.log(f"     {h.get('From', '?')[:40]} | {h.get('Subject', '?')[:60]}")
                return

            if ids:
                self.service.users().messages().batchModify(
                    userId='me',
                    body={'ids': ids, 'addLabelIds': ['TRASH']}
                ).execute()
                self.log(f"   ✓ Moved {len(ids)} emails to Trash")
        except HttpError as e:
            self.errors += 1
            self.log(f"   ERROR: {e}")

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
    import sys
    try:
        automation = GmailWeeklyAutomation(dry_run='--dry-run' in sys.argv)
        automation.run()
    except AuthError as e:
        logging.error(f"AUTH FAILED: {e}")
        sys.exit(2)
    if automation.errors:
        sys.exit(1)

