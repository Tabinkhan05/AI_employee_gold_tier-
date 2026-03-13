#!/usr/bin/env python3
"""
Gmail Watcher for Silver Tier AI Employee Vault

Monitors Gmail for unread/important emails and creates markdown files
in the Needs_Action folder for tracking and processing.
"""

import base64
import json
import os
import time
from datetime import datetime
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

# =============================================================================
# Configuration
# =============================================================================

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

CREDENTIALS_FILE = 'credentials/gmail_credentials.json'
TOKEN_FILE = 'credentials/token.json'

VAULT_PATH = Path.cwd()
NEEDS_ACTION = VAULT_PATH / 'Needs_Action'

CHECK_INTERVAL = 120  # 2 minutes

# Keywords for priority detection (case-insensitive)
HIGH_PRIORITY_KEYWORDS = [
    'urgent',
    'asap',
    'important',
    'action required'
]

# =============================================================================
# Authentication
# =============================================================================


def authenticate_gmail():
    """
    Authenticate with Gmail API using OAuth2 flow.
    
    Returns:
        Authorized Gmail API service object, or None if authentication fails.
    """
    creds = None
    
    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        print("[AUTH] Refreshing expired token...")
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"[AUTH ERROR] Token refresh failed: {e}")
            creds = None
    
    # Run OAuth flow if no valid credentials
    if not creds or not creds.valid:
        if not os.path.exists(CREDENTIALS_FILE):
            print(f"[AUTH ERROR] Credentials file not found: {CREDENTIALS_FILE}")
            print("[AUTH ERROR] Please download gmail_credentials.json from Google Cloud Console")
            print("[AUTH ERROR] and place it in the credentials/ folder")
            return None
        
        print("[AUTH] Starting OAuth flow...")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save token for future use
            with open(TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())
            print("[AUTH] Token saved successfully")
        except Exception as e:
            print(f"[AUTH ERROR] OAuth flow failed: {e}")
            return None
    
    # Build Gmail API service
    try:
        service = build('gmail', 'v1', credentials=creds)
        print("[AUTH] Gmail API authentication successful")
        return service
    except Exception as e:
        print(f"[AUTH ERROR] Failed to build Gmail service: {e}")
        return None


# =============================================================================
# Gmail Operations
# =============================================================================


def get_unread_messages(service, query='is:unread'):
    """
    Fetch unread messages matching the query.
    
    Args:
        service: Gmail API service object
        query: Gmail search query string
    
    Returns:
        List of message objects with id, threadId, and internalDate
    """
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=50
        ).execute()
        
        messages = results.get('messages', [])
        return messages
    except Exception as e:
        print(f"[GMAIL ERROR] Failed to fetch messages: {e}")
        return []


def get_message_details(service, message_id):
    """
    Get full message details including headers and body.
    
    Args:
        service: Gmail API service object
        message_id: Gmail message ID
    
    Returns:
        Dictionary with message details or None if failed
    """
    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        # Extract headers
        headers = message.get('payload', {}).get('headers', [])
        header_dict = {h['name']: h['value'] for h in headers}
        
        # Extract subject and from
        subject = header_dict.get('Subject', '(No Subject)')
        from_email = header_dict.get('From', 'Unknown')
        date = header_dict.get('Date', '')
        
        # Extract body (try different parts)
        body = extract_message_body(message)
        
        return {
            'id': message_id,
            'threadId': message.get('threadId'),
            'subject': subject,
            'from': from_email,
            'date': date,
            'snippet': message.get('snippet', ''),
            'body': body,
            'internalDate': message.get('internalDate')
        }
    except Exception as e:
        print(f"[GMAIL ERROR] Failed to get message {message_id}: {e}")
        return None


def extract_message_body(message):
    """
    Extract and decode the message body from Gmail API response.
    
    Args:
        message: Gmail message resource
    
    Returns:
        Decoded message body string
    """
    body = ""
    payload = message.get('payload', {})
    parts = payload.get('parts', [])
    
    # Try to find text/plain part
    if parts:
        for part in parts:
            mime_type = part.get('mimeType', '')
            if mime_type == 'text/plain':
                body_data = part.get('body', {}).get('data', '')
                if body_data:
                    body = decode_base64(body_data)
                    break
    else:
        # Message without parts (simple message)
        body_data = payload.get('body', {}).get('data', '')
        if body_data:
            body = decode_base64(body_data)
    
    return body


def decode_base64(data):
    """
    Decode base64url encoded data (Gmail API uses URL-safe base64).
    
    Args:
        data: Base64url encoded string
    
    Returns:
        Decoded UTF-8 string
    """
    try:
        # Gmail uses URL-safe base64 encoding (- and _ instead of + and /)
        # Add padding if needed
        padding = 4 - len(data) % 4
        if padding != 4:
            data += '=' * padding
        
        # Convert URL-safe to standard base64
        data = data.replace('-', '+').replace('_', '/')
        
        decoded = base64.b64decode(data)
        return decoded.decode('utf-8', errors='replace')
    except Exception as e:
        print(f"[DECODE ERROR] Failed to decode message body: {e}")
        return ""


def mark_message_read(service, message_id):
    """
    Mark a Gmail message as read by removing the UNREAD label.
    
    Args:
        service: Gmail API service object
        message_id: Gmail message ID
    
    Returns:
        True if successful, False otherwise
    """
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        return True
    except Exception as e:
        print(f"[GMAIL ERROR] Failed to mark message {message_id} as read: {e}")
        return False


# =============================================================================
# Priority Detection
# =============================================================================


def detect_priority(subject, body):
    """
    Auto-detect email priority based on subject and body content.
    
    Args:
        subject: Email subject line
        body: Email body content
    
    Returns:
        Priority string: 'HIGH' or 'NORMAL'
    """
    # Combine subject and body for keyword search
    content = f"{subject} {body}".lower()
    
    for keyword in HIGH_PRIORITY_KEYWORDS:
        if keyword.lower() in content:
            return 'HIGH'
    
    return 'NORMAL'


# =============================================================================
# File Creation
# =============================================================================


def create_email_file(message, processed_ids):
    """
    Create a markdown file in Needs_Action folder for the email.
    
    Args:
        message: Dictionary with message details
        processed_ids: Set of already processed message IDs
    
    Returns:
        True if file created, False if skipped or failed
    """
    message_id = message['id']
    
    # Skip if already processed
    if message_id in processed_ids:
        return False
    
    # Ensure Needs_Action directory exists
    NEEDS_ACTION.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"EMAIL_{message_id}_{timestamp}.md"
    filepath = NEEDS_ACTION / filename
    
    # Detect priority
    priority = detect_priority(message['subject'], message['body'])
    
    # Format timestamp for YAML
    try:
        internal_date = int(message['internalDate']) / 1000
        received_dt = datetime.fromtimestamp(internal_date)
        received_str = received_dt.isoformat()
    except (ValueError, TypeError):
        received_str = datetime.now().isoformat()
    
    # Generate suggested actions based on content
    suggested_actions = generate_suggested_actions(message['subject'], message['body'])
    
    # Build markdown content
    content = f"""---
type: email
from: {escape_yaml_value(message['from'])}
subject: {escape_yaml_value(message['subject'])}
received: {received_str}
priority: {priority}
gmail_id: {message_id}
---

# Email: {message['subject']}

## Sender
{message['from']}

## Received
{received_str}

## Priority
**{priority}**

## Preview
{message['snippet']}

## Content
{message['body'] if message['body'] else '(No plain text content available)'}

---

## Suggested Actions
{suggested_actions}

---
*Created by Gmail Watcher on {datetime.now().isoformat()}*
"""
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[FILE] Created: {filename}")
        return True
    except Exception as e:
        print(f"[FILE ERROR] Failed to create file {filename}: {e}")
        return False


def escape_yaml_value(value):
    """
    Escape special characters for YAML values.
    
    Args:
        value: String value to escape
    
    Returns:
        Escaped string safe for YAML
    """
    if not value:
        return ""
    
    # Escape quotes and backslashes
    value = value.replace('\\', '\\\\').replace('"', '\\"').replace("'", "\\'")
    
    # If value contains special YAML characters, wrap in quotes
    if any(c in value for c in [':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`']):
        return f'"{value}"'
    
    return value


def generate_suggested_actions(subject, body):
    """
    Generate suggested action checklist based on email content.
    
    Args:
        subject: Email subject
        body: Email body
    
    Returns:
        Formatted checklist string
    """
    content = f"{subject} {body}".lower()
    
    actions = ["- [ ] Review email content"]
    
    # Add context-specific suggestions
    if 'meeting' in content:
        actions.append("- [ ] Add to calendar if action required")
    
    if 'invoice' in content or 'payment' in content or 'bill' in content:
        actions.append("- [ ] Process payment/invoice")
    
    if 'question' in content or 'ask' in content:
        actions.append("- [ ] Prepare response")
    
    if 'deadline' in content or 'due' in content:
        actions.append("- [ ] Note deadline and schedule work")
    
    if 'attachment' in content:
        actions.append("- [ ] Review attachments")
    
    if 'urgent' in content or 'asap' in content:
        actions.append("- [ ] Prioritize for immediate action")
    
    # Always add completion option
    actions.append("- [ ] Move to appropriate folder when done")
    
    return "\n".join(actions)


# =============================================================================
# Main Monitoring Loop
# =============================================================================


def load_processed_ids():
    """
    Load set of already processed message IDs from cache file.
    
    Returns:
        Set of processed message IDs
    """
    cache_file = VAULT_PATH / '.processed_emails.json'
    
    try:
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                data = json.load(f)
                # Keep only recent IDs (last 1000) to prevent unbounded growth
                processed = set(data.get('ids', [])[-1000:])
                print(f"[CACHE] Loaded {len(processed)} processed message IDs")
                return processed
    except Exception as e:
        print(f"[CACHE ERROR] Failed to load cache: {e}")
    
    return set()


def save_processed_ids(processed_ids):
    """
    Save processed message IDs to cache file.
    
    Args:
        processed_ids: Set of processed message IDs
    """
    cache_file = VAULT_PATH / '.processed_emails.json'
    
    try:
        with open(cache_file, 'w') as f:
            json.dump({'ids': list(processed_ids)[-1000:]}, f)
    except Exception as e:
        print(f"[CACHE ERROR] Failed to save cache: {e}")


def monitor_gmail(service, processed_ids):
    """
    Run one iteration of Gmail monitoring.
    
    Args:
        service: Gmail API service object
        processed_ids: Set of already processed message IDs
    
    Returns:
        Updated set of processed message IDs
    """
    print(f"\n[MONITOR] Checking for new emails at {datetime.now().isoformat()}")
    
    # Query for unread important or inbox emails
    query = 'is:unread is:important OR is:unread label:inbox'
    
    messages = get_unread_messages(service, query)
    
    if not messages:
        print("[MONITOR] No unread messages found")
        return processed_ids
    
    print(f"[MONITOR] Found {len(messages)} unread message(s)")
    
    new_count = 0
    
    for msg in messages:
        message_id = msg['id']
        
        # Skip if already processed
        if message_id in processed_ids:
            continue
        
        # Get full message details
        details = get_message_details(service, message_id)
        
        if not details:
            print(f"[MONITOR] Skipping message {message_id} - failed to fetch details")
            continue
        
        # Create file in Needs_Action
        if create_email_file(details, processed_ids):
            processed_ids.add(message_id)
            new_count += 1
            
            # Optional: Mark as read after processing
            # Uncomment the next line to enable auto-mark-as-read
            # mark_message_read(service, message_id)
    
    print(f"[MONITOR] Processed {new_count} new email(s)")
    
    return processed_ids


def main():
    """
    Main entry point - runs the Gmail watcher continuously.
    """
    print("=" * 60)
    print("GMAIL WATCHER - Silver Tier AI Employee Vault")
    print("=" * 60)
    print(f"[CONFIG] Vault Path: {VAULT_PATH}")
    print(f"[CONFIG] Needs_Action: {NEEDS_ACTION}")
    print(f"[CONFIG] Check Interval: {CHECK_INTERVAL} seconds")
    print("=" * 60)
    
    # Authenticate with Gmail
    service = authenticate_gmail()
    
    if not service:
        print("[FATAL] Authentication failed. Exiting.")
        return 1
    
    # Load processed message IDs cache
    processed_ids = load_processed_ids()
    
    print(f"\n[START] Beginning continuous monitoring...")
    print(f"[INFO] Press Ctrl+C to stop\n")
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            # Check if credentials need refresh
            if not service:
                print("[AUTH] Re-authenticating...")
                service = authenticate_gmail()
                if not service:
                    print("[WARN] Re-authentication failed, waiting before retry...")
                    time.sleep(CHECK_INTERVAL)
                    continue
            
            # Run monitoring iteration
            processed_ids = monitor_gmail(service, processed_ids)
            
            # Save cache periodically
            if iteration % 5 == 0:
                save_processed_ids(processed_ids)
            
            # Wait for next check
            print(f"[INFO] Next check in {CHECK_INTERVAL} seconds...")
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\n[SHUTDOWN] Received interrupt signal")
        print("[SHUTDOWN] Saving processed IDs cache...")
        save_processed_ids(processed_ids)
        print("[SHUTDOWN] Gmail Watcher stopped gracefully")
    
    except Exception as e:
        print(f"\n[FATAL ERROR] Unexpected error: {e}")
        save_processed_ids(processed_ids)
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
