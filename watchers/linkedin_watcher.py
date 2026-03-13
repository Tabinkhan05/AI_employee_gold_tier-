#!/usr/bin/env python3
"""
LinkedIn Watcher - Gold Tier (Hybrid Mode)
Supports: Mock, Scrape, and API modes
"""

import json
import time
import os
from datetime import datetime
from pathlib import Path

class LinkedInWatcher:
    """Hybrid LinkedIn Watcher with multiple modes"""
    
    def __init__(self, vault_path, mode='mock', check_interval=300):
        """Initialize LinkedIn watcher
        
        Args:
            vault_path: Path to vault directory
            mode: 'mock', 'scrape', or 'api'
            check_interval: Check interval in seconds (default: 5 minutes)
        """
        self.vault_path = Path(vault_path)
        self.mode = mode
        self.needs_action = self.vault_path / 'Needs_Action'
        self.check_interval = check_interval
        
        # Mock mode inbox
        self.mock_inbox = self.vault_path / 'linkedin_inbox'
        
        # Create directories
        self.needs_action.mkdir(exist_ok=True)
        if mode == 'mock':
            self.mock_inbox.mkdir(exist_ok=True)
        
        # Processed cache
        self.cache_file = self.vault_path / '.processed_linkedin.json'
        self.processed_ids = self.load_processed_cache()
        
        print("\n" + "="*60)
        print("LINKEDIN WATCHER - Gold Tier AI Employee")
        print("="*60)
        print(f"[CONFIG] Mode: {mode.upper()}")
        print(f"[CONFIG] Vault Path: {self.vault_path}")
        print(f"[CONFIG] Needs_Action: {self.needs_action}")
        print(f"[CONFIG] Check Interval: {self.check_interval} seconds")
        
        if mode == 'mock':
            print(f"[CONFIG] Mock Inbox: {self.mock_inbox}")
        
        print("="*60 + "\n")
    
    def load_processed_cache(self):
        """Load processed message IDs"""
        if self.cache_file.exists():
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                print(f"[CACHE] Loaded {len(data)} processed message IDs")
                return set(data)
        return set()
    
    def save_processed_cache(self):
        """Save processed message IDs"""
        with open(self.cache_file, 'w') as f:
            json.dump(list(self.processed_ids), f)
    
    def get_messages_mock(self):
        """Get messages from mock inbox (JSON files)"""
        messages = []
        
        if not self.mock_inbox.exists():
            return messages
        
        for json_file in self.mock_inbox.glob('*.json'):
            try:
                with open(json_file, 'r') as f:
                    message = json.load(f)
                    messages.append(message)
            except Exception as e:
                print(f"[ERROR] Failed to read {json_file.name}: {e}")
        
        return messages
    
    def get_messages_scrape(self):
        """Get messages via web scraping (Selenium)"""
        print("[SCRAPE] Web scraping not yet implemented")
        print("[SCRAPE] This would use Selenium to monitor LinkedIn")
        return []
    
    def get_messages_api(self):
        """Get messages via LinkedIn API"""
        print("[API] LinkedIn API not yet authorized")
        print("[API] Waiting for API access approval")
        return []
    
    def get_messages(self):
        """Get messages based on mode"""
        if self.mode == 'mock':
            return self.get_messages_mock()
        elif self.mode == 'scrape':
            return self.get_messages_scrape()
        elif self.mode == 'api':
            return self.get_messages_api()
        else:
            print(f"[ERROR] Unknown mode: {self.mode}")
            return []
    
    def detect_priority(self, message):
        """Detect message priority"""
        body = message.get('body', '').lower()
        subject = message.get('subject', '').lower()
        combined = f"{subject} {body}"
        
        # HIGH priority keywords
        high_keywords = ['urgent', 'asap', 'immediately', 'important', 
                        'interview', 'job opportunity', 'offer']
        
        # MEDIUM priority keywords
        medium_keywords = ['meeting', 'call', 'discuss', 'connect', 
                          'network', 'collaboration']
        
        # Check for dollar amounts
        import re
        amounts = re.findall(r'\$[\d,]+', combined)
        if amounts:
            # Extract largest amount
            max_amount = max([int(amt.replace('$', '').replace(',', '')) 
                            for amt in amounts])
            if max_amount > 100000:
                return 'HIGH'
        
        # Check keywords
        if any(keyword in combined for keyword in high_keywords):
            return 'HIGH'
        elif any(keyword in combined for keyword in medium_keywords):
            return 'MEDIUM'
        
        return 'NORMAL'
    
    def create_message_file(self, message):
        """Create markdown file for LinkedIn message"""
        message_id = message.get('id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        filename = f"LINKEDIN_{message_id}_{timestamp}.md"
        filepath = self.needs_action / filename
        
        # Extract details
        sender = message.get('from', 'Unknown')
        sender_profile = message.get('from_profile', 'N/A')
        subject = message.get('subject', 'No subject')
        body = message.get('body', '')
        received = message.get('received', datetime.now().isoformat())
        msg_type = message.get('type', 'message')
        is_connection = message.get('connection_request', False)
        
        # Detect priority
        priority = self.detect_priority(message)
        
        # Create markdown content
        markdown_content = f"""---
type: linkedin_{msg_type}
from: "{sender}"
from_profile: {sender_profile}
subject: {subject}
received: {received}
priority: {priority}
linkedin_id: {message_id}
connection_request: {is_connection}
mode: {self.mode}
---

# LinkedIn Message: {subject}

## Sender
**Name:** {sender}  
**Profile:** {sender_profile}

## Received
{received}

## Priority
**{priority}**

## Type
{msg_type.upper()}{"(Connection Request)" if is_connection else ""}

## Message Content

{body}

---

## Suggested Actions
- [ ] Review message carefully
- [ ] {"Accept connection request" if is_connection else "Respond to message"}
- [ ] {"Schedule interview" if "interview" in body.lower() else "Follow up if needed"}
- [ ] Update Dashboard

## Analysis
- **Priority Level:** {priority}
- **Response Required:** {"Yes - Urgent" if priority == "HIGH" else "Yes - Normal" if priority == "MEDIUM" else "Optional"}
- **Detected Intent:** {"Job opportunity" if "job" in body.lower() or "position" in body.lower() else "Networking" if is_connection else "General inquiry"}
"""
        
        filepath.write_text(markdown_content)
        print(f"[FILE] Created: {filename}")
        
        return filepath
    
    def monitor(self):
        """Main monitoring loop"""
        print(f"[START] LinkedIn Watcher in {self.mode.upper()} mode")
        print("[INFO] Press Ctrl+C to stop\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                print(f"\n--- Iteration {iteration} ---")
                
                timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
                print(f"[MONITOR] Checking LinkedIn at {timestamp}")
                
                # Get messages based on mode
                messages = self.get_messages()
                
                if messages:
                    print(f"[MONITOR] Found {len(messages)} message(s)")
                    
                    new_messages = 0
                    for message in messages:
                        message_id = message.get('id')
                        
                        if message_id and message_id not in self.processed_ids:
                            self.create_message_file(message)
                            self.processed_ids.add(message_id)
                            new_messages += 1
                    
                    if new_messages > 0:
                        print(f"[MONITOR] Processed {new_messages} new message(s)")
                        self.save_processed_cache()
                    else:
                        print(f"[MONITOR] No new messages (all {len(messages)} already processed)")
                else:
                    print("[MONITOR] No messages found")
                
                print(f"[INFO] Next check in {self.check_interval} seconds...")
                time.sleep(self.check_interval)
        
        except KeyboardInterrupt:
            print("\n\n[SHUTDOWN] Received interrupt signal")
            print("[SHUTDOWN] Saving processed IDs cache...")
            self.save_processed_cache()
            print("[SHUTDOWN] LinkedIn Watcher stopped gracefully")

def main():
    """Main entry point"""
    import sys
    
    vault_path = Path.cwd()
    
    # Check if running from watchers directory
    if vault_path.name == 'watchers':
        vault_path = vault_path.parent
    
    # Get mode from command line or default to mock
    mode = sys.argv[1] if len(sys.argv) > 1 else 'mock'
    
    if mode not in ['mock', 'scrape', 'api']:
        print(f"[ERROR] Invalid mode: {mode}")
        print("Usage: python3 linkedin_watcher.py [mock|scrape|api]")
        sys.exit(1)
    
    watcher = LinkedInWatcher(
        vault_path=vault_path,
        mode=mode,
        check_interval=120  # 2 minutes for testing
    )
    
    watcher.monitor()

if __name__ == '__main__':
    main()
