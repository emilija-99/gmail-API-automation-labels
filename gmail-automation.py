#!/usr/bin/env python3
"""
STEP 1: Gmail Automation Script
Gmail Automation Script
- Extracts all senders from mailbox
- Auto-sorts emails into folders (trash, finance, inbox)
- Auto-deletes uncategorized emails after 1 month
"""

import os
import pickle
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any

# Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailAutomation:
    def __init__(self):
        self.service: Any = None
        self.authenticate()
        self.rules = self.load_rules()

    def authenticate(self):
        """Authenticate with Gmail API"""
        creds = None

        print("Checking for existing credentials...")
        # Load existing credentials
        if os.path.exists("client_secret.json"):
            try:
                with open("client_secret.json", "rb") as token:
                    print("Token file found: ", token)
                    creds = pickle.load(token)
                    print("Credentials loaded successfully.", creds)
            except PermissionError:
                print(
                    "Permission error while loading credentials. Please check file permissions."
                )
                return
            except Exception as e:
                print(f"Error loading credentials: {e}")
                return

        print("Credentials not valid.. Trying to refresh...")
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "client_secret.json", SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for future use
            with open("client_secret.json", "wb") as token:
                pickle.dump(creds, token)

        self.service = build("gmail", "v1", credentials=creds)
        print(" Successfully authenticated with Gmail")

    def get_all_senders(self):
        senders = {}
        file_path = Path("senders_list.json")
        if file_path.exists():
            print("Senders list already exists. Loading from file...")
            with open(file_path, "r") as f:
                senders = json.load(f)
            return senders

        else:
            """Extract all unique senders from mailbox"""
            print("\n Extracting all senders from your mailbox...")

            page_token = None
            message_count = 0

            try:
                while True:
                    results = (
                        self.service.users()
                        .messages()
                        .list(
                            userId="me",
                            pageToken=page_token,
                            maxResults=100,
                            q="from:*",
                        )
                        .execute()
                    )

                    messages = results.get("messages", [])

                    if not messages:
                        print("No messages found")
                        break

                    for message in messages:
                        try:
                            msg = (
                                self.service.users()
                                .messages()
                                .get(
                                    userId="me",
                                    id=message["id"],
                                    format="metadata",
                                    metadataHeaders=["From"],
                                )
                                .execute()
                            )

                            headers = msg["payload"].get("headers", [])
                            from_header = next(
                                (h["value"] for h in headers if h["name"] == "From"),
                                "Unknown",
                            )

                            # Extract email address from "Name <email@domain.com>" format
                            email = from_header.split("<")[-1].rstrip(">")

                            if email not in senders:
                                senders[email] = {
                                    "count": 0,
                                    "from_header": from_header,
                                }

                            senders[email]["count"] += 1
                            message_count += 1

                            if message_count % 50 == 0:
                                print(f"  Processed {message_count} messages...")

                        except Exception as e:
                            print(f"  Error processing message: {e}")
                            continue

                    page_token = results.get("nextPageToken")
                    if not page_token:
                        break

            except HttpError as error:
                print(f"An error occurred: {error}")
                return {}

            # Sort by message count
            sorted_senders = dict(
                sorted(senders.items(), key=lambda x: x[1]["count"], reverse=True)
            )
            self.save_senders_to_file(senders)
            print(f" Total messages processed: {message_count}\n")
        print(
            f"\n Found {len(sorted_senders) if sorted_senders else len(senders)} unique senders"
        )
        return sorted_senders

    def save_senders_to_file(self, senders):
        """Save senders list to JSON file for review"""
        with open("senders_list.json", "w") as f:
            # Convert for JSON serialization
            json_data = {email: count["count"] for email, count in senders.items()}
            json.dump(json_data, f, indent=2)

        print("Senders saved to 'senders_list.json' for your review")

    def load_rules(self):
        """Load categorization rules from file"""
        if not os.path.exists("gmail_rules.json"):
            print("ERROR: gmail_rules.json not found!")
            return {}

        try:
            with open("gmail_rules.json", "r") as f:
                rules = json.load(f)
            print(f"✓ Loaded rules:")
            for category, senders in rules.items():
                print(f"  - {category}: {len(senders)} senders")
            print()
            return rules
        except Exception as e:
            print(f"Error loading rules: {e}")
            return {}

    def create_label(self, label_name):
        """Create a Gmail label if it doesn't exist"""
        try:
            # Get existing labels
            results = self.service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])

            # Check if label exists
            for label in labels:
                if label["name"] == label_name:
                    print(f"  ✓ Label '{label_name}' already exists")
                    return label["id"]

            # Create new label
            label_body = {
                "name": label_name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            }

            created_label = (
                self.service.users()
                .labels()
                .create(userId="me", body=label_body)
                .execute()
            )

            print(f"  ✓ Created label: '{label_name}'")
            return created_label["id"]

        except HttpError as error:
            print(f"  Error creating label: {error}")
            return None

    def get_label_id(self, label_name):
        """Get ID of a label"""
        try:
            results = self.service.users().labels().list(userId="me").execute()
            labels = results.get("labels", [])

            for label in labels:
                if label["name"] == label_name:
                    return label["id"]

            return None
        except HttpError as error:
            print(f"Error getting label: {error}")
            return None

    def apply_labels(self):
        """Apply labels to emails based on rules"""
        print("=" * 60)
        print("APPLYING LABELS TO EMAILS")
        print("=" * 60 + "\n")

        # First, create all labels
        print("Creating labels...")
        label_ids = {}
        for category in self.rules.keys():
            label_id = self.create_label(category)
            if label_id:
                label_ids[category] = label_id

        print("\nApplying labels to emails...\n")

        total_labeled = 0

        # Apply labels to each category
        for category, senders in self.rules.items():
            if category not in label_ids:
                print(f"Skipping {category} - label not created")
                continue

            label_id = label_ids[category]
            category_count = 0

            print(f"  → {category.upper()}")

            for sender in senders:
                try:
                    # Find all emails from this sender
                    results = (
                        self.service.users()
                        .messages()
                        .list(userId="me", q=f"from:{sender}", maxResults=100)
                        .execute()
                    )

                    messages = results.get("messages", [])

                    if not messages:
                        continue

                    # Apply label to each message
                    for message in messages:
                        try:
                            self.service.users().messages().modify(
                                userId="me",
                                id=message["id"],
                                body={"addLabelIds": [label_id]},
                            ).execute()
                            category_count += 1
                            total_labeled += 1
                        except Exception as e:
                            print(f"    Error labeling message: {e}")
                            continue

                except HttpError as error:
                    print(f"    Error processing {sender}: {error}")
                    continue

            print(f"    ✓ Labeled {category_count} emails\n")

        print("=" * 60)
        print(f"✓ Total emails labeled: {total_labeled}")
        print("=" * 60 + "\n")

    def delete_old_uncategorized(self, days=30):
        """Delete uncategorized emails older than specified days"""
        print("🗑️  Checking for old uncategorized emails...\n")

        cutoff_date = datetime.now() - timedelta(days=days)

        try:
            # Build query to exclude all labeled emails
            exclude_labels = " ".join([f"-label:{cat}" for cat in self.rules.keys()])
            query = f'before:{cutoff_date.strftime("%Y/%m/%d")} {exclude_labels} -label:[Gmail]/Trash'

            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=100)
                .execute()
            )

            messages = results.get("messages", [])
            deleted_count = 0

            if messages:
                print(
                    f"Found {len(messages)} uncategorized emails older than {days} days\n"
                )

                for message in messages:
                    self.service.users().messages().trash(
                        userId="me", id=message["id"]
                    ).execute()
                    deleted_count += 1

                print(f"✓ Moved {deleted_count} old uncategorized emails to Trash\n")
            else:
                print(f"✓ No uncategorized emails older than {days} days found\n")

        except HttpError as error:
            print(f"Error deleting emails: {error}")


def main():
    """Main function"""
    print("=" * 60)
    print("GMAIL AUTOMATION SCRIPT")
    print("=" * 60)

    gmail = GmailAutomation()

    # Get all senders
    gmail.get_all_senders()

    # Apply labels to emails
    print("GMAIL LABELER - APPLY LABELS TO ALL EMAILS"); 
 
    if not gmail.rules:
         print("No rules found. Exiting.")
         return
 
    # Apply labels
    gmail.apply_labels()
 
    # Ask about deletion
    print("Delete old uncategorized emails (older than 30 days)? (y/n): ", end="")
    if input().lower() == 'y':
        gmail.delete_old_uncategorized(days=30)
 
    print("✓ Script completed!")


if __name__ == "__main__":
    main()
