#!/usr/bin/env python3
"""
WhatsApp Watcher - Gold Tier (Hybrid Mode)
Supports: Mock and Selenium modes
"""

import json
import time
import re
from datetime import datetime
from pathlib import Path

class WhatsAppWatcher:
    """Hybrid WhatsApp Watcher"""
    
    def __init__(self, vault_path, mode='mock', check_interval=180):
        """Initialize WhatsApp watcher
        
        Args:
            vault_path: Path to vault directory
            mode: 'mock' or 'selenium'
            check_interval: Check interval in seconds (default: 3 minutes)
        """
        self.vault_path = Path(vault_path)
        self.mode = mode
        self.needs_action = self.vault_path / 'Needs_Action'
        self.check_interval = check_interval
        
        # Mock mode inbox
        self.mock_inbox = self.vault_path / 'whatsapp_inbox'
        
        # Create directories
        self.needs_action.mkdir(exist_ok=True)
        if mode == 'mock':
            self.mock_inbox.mkdir(exist_ok=True)
        
        # Processed cache
        self.cache_file = self.vault_path / '.processed_whatsapp.json'
        self.processed_ids = self.load_processed_cache()
        
        print("\n" + "="*60)
        print("WHATSAPP WATCHER - Gold Tier AI Employee")
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
        """Get messages from mock inbox"""
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
    
    def get_messages_selenium(self):
        """Get messages via Selenium (WhatsApp Web)"""
        print("[SELENIUM] WhatsApp Web automation not yet implemented")
        print("[SELENIUM] This would use Selenium to monitor WhatsApp Web")
        return []
    
    def get_messages(self):
        """Get messages based on mode"""
        if self.mode == 'mock':
            return self.get_messages_mock()
        elif self.mode == 'selenium':
            return self.get_messages_selenium()
        else:
            print(f"[ERROR] Unknown mode: {self.mode}")
            return []
    
    def detect_priority(self, message):
        """Detect message priority"""
        text = message.get('message', '').lower()
        
        # HIGH priority keywords
        high_keywords = ['urgent', 'asap', 'immediately', 'important', 
                        'payment', 'invoice', 'client']
        
        # MEDIUM priority keywords
        medium_keywords = ['meeting', 'call', 'tomorrow', 'schedule', 
                          'confirm', 'please']
        
        # Check for dollar amounts
        amounts = re.findall(r'\$[\d,]+', text)
        if amounts:
            max_amount = max([int(amt.replace('$', '').replace(',', '')) 
                            for amt in amounts])
            if max_amount > 1000:
                return 'HIGH'
        
        # Check keywords
        if any(keyword in text for keyword in high_keywords):
            return 'HIGH'
        elif any(keyword in text for keyword in medium_keywords):
            return 'MEDIUM'
        
        return 'NORMAL'
    
    def create_message_file(self, message):
        """Create markdown file for WhatsApp message"""
        message_id = message.get('id', 'unknown')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        filename = f"WHATSAPP_{message_id}_{timestamp}.md"
        filepath = self.needs_action / filename
        
        # Extract details
        from_number = message.get('from', 'Unknown')
        from_name = message.get('from_name', 'Unknown')
        text = message.get('message', '')
        received = message.get('timestamp', datetime.now().isoformat())
        chat_type = message.get('chat_type', 'individual')
        
        # Detect priority
        priority = self.detect_priority(message)
        
        # Create markdown content
        markdown_content = f"""---
type: whatsapp_{chat_type}
from: "{from_name}"
from_number: {from_number}
received: {received}
priority: {priority}
whatsapp_id: {message_id}
chat_type: {chat_type}
mode: {self.mode}
---

# WhatsApp Message from {from_name}

## Sender
**Name:** {from_name}  
**Number:** {from_number}  
**Chat Type:** {chat_type.upper()}

## Received
{received}

## Priority
**{priority}**

## Message

{text}

---

## Suggested Actions
- [ ] Review message
- [ ] Respond if urgent
- [ ] Update Dashboard
- [ ] {"Process payment confirmation" if "payment" in text.lower() else "Follow up as needed"}

## Analysis
- **Priority Level:** {priority}
- **Response Required:** {"Yes - Urgent" if priority == "HIGH" else "Yes - Soon" if priority == "MEDIUM" else "Optional"}
- **Contains Payment:** {"Yes" if "$" in text else "No"}
"""
        
        filepath.write_text(markdown_content)
        print(f"[FILE] Created: {filename}")
        
        return filepath
    
    def monitor(self):
        """Main monitoring loop"""
        print(f"[START] WhatsApp Watcher in {self.mode.upper()} mode")
        print("[INFO] Press Ctrl+C to stop\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                print(f"\n--- Iteration {iteration} ---")
                
                timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')
                print(f"[MONITOR] Checking WhatsApp at {timestamp}")
                
                # Get messages
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
            print("[SHUTDOWN] WhatsApp Watcher stopped gracefully")

def main():
    """Main entry point"""
    import sys
    
    vault_path = Path.cwd()
    
    if vault_path.name == 'watchers':
        vault_path = vault_path.parent
    
    mode = sys.argv[1] if len(sys.argv) > 1 else 'mock'
    
    if mode not in ['mock', 'selenium']:
        print(f"[ERROR] Invalid mode: {mode}")
        print("Usage: python3 whatsapp_watcher.py [mock|selenium]")
        sys.exit(1)
    
    watcher = WhatsAppWatcher(
        vault_path=vault_path,
        mode=mode,
        check_interval=120  # 2 minutes for testing
    )
    
    watcher.monitor()

if __name__ == '__main__':
    main()
