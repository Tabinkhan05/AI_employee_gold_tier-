#!/usr/bin/env python3
"""
Human-in-the-Loop Approval Dashboard
Gold Tier - AI Employee System
"""

from flask import Flask, render_template, request, jsonify
from pathlib import Path
import json
from datetime import datetime
import os

app = Flask(__name__)

# Configuration
VAULT_PATH = Path(__file__).parent.parent
NEEDS_ACTION = VAULT_PATH / 'Needs_Action'
PENDING_APPROVAL = VAULT_PATH / 'Pending_Approval'
APPROVED = VAULT_PATH / 'Approved'
REJECTED = VAULT_PATH / 'Rejected'

# Create directories
PENDING_APPROVAL.mkdir(exist_ok=True)
APPROVED.mkdir(exist_ok=True)
REJECTED.mkdir(exist_ok=True)

def get_all_messages():
    """Get all messages from Needs_Action and Pending_Approval"""
    messages = []
    
    # Check both folders
    folders = [NEEDS_ACTION, PENDING_APPROVAL]
    
    for folder in folders:
        if not folder.exists():
            continue
            
        for md_file in folder.glob('*.md'):
            try:
                content = md_file.read_text()
                
                # Parse frontmatter
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1].strip()
                        body = parts[2].strip()
                        
                        # Parse frontmatter into dict
                        metadata = {}
                        for line in frontmatter.split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                metadata[key.strip()] = value.strip().strip('"')
                        
                        # Determine channel
                        filename = md_file.name
                        if filename.startswith('EMAIL_'):
                            channel = 'Gmail'
                            icon = '📧'
                        elif filename.startswith('LINKEDIN_'):
                            channel = 'LinkedIn'
                            icon = '💼'
                        elif filename.startswith('WHATSAPP_'):
                            channel = 'WhatsApp'
                            icon = '💬'
                        else:
                            channel = 'Unknown'
                            icon = '❓'
                        
                        messages.append({
                            'filename': md_file.name,
                            'path': str(md_file),
                            'folder': folder.name,
                            'channel': channel,
                            'icon': icon,
                            'from': metadata.get('from', 'Unknown'),
                            'subject': metadata.get('subject', 'No subject'),
                            'priority': metadata.get('priority', 'NORMAL'),
                            'received': metadata.get('received', ''),
                            'type': metadata.get('type', ''),
                            'preview': body[:200] + '...' if len(body) > 200 else body,
                            'full_content': content
                        })
            except Exception as e:
                print(f"Error reading {md_file.name}: {e}")
    
    # Sort by priority (HIGH first)
    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'NORMAL': 2, 'LOW': 3}
    messages.sort(key=lambda x: priority_order.get(x['priority'], 999))
    
    return messages

@app.route('/')
def dashboard():
    """Main dashboard"""
    messages = get_all_messages()
    
    # Calculate statistics
    stats = {
        'total': len(messages),
        'high': sum(1 for m in messages if m['priority'] == 'HIGH'),
        'medium': sum(1 for m in messages if m['priority'] == 'MEDIUM'),
        'low': sum(1 for m in messages if m['priority'] in ['NORMAL', 'LOW']),
        'gmail': sum(1 for m in messages if m['channel'] == 'Gmail'),
        'linkedin': sum(1 for m in messages if m['channel'] == 'LinkedIn'),
        'whatsapp': sum(1 for m in messages if m['channel'] == 'WhatsApp'),
    }
    
    return render_template('dashboard.html', messages=messages, stats=stats)

@app.route('/api/approve', methods=['POST'])
def approve_message():
    """Approve a message"""
    data = request.json
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'success': False, 'error': 'No filename provided'})
    
    # Find file
    source_paths = [NEEDS_ACTION / filename, PENDING_APPROVAL / filename]
    source_path = None
    
    for path in source_paths:
        if path.exists():
            source_path = path
            break
    
    if not source_path:
        return jsonify({'success': False, 'error': 'File not found'})
    
    # Move to Approved
    dest_path = APPROVED / filename
    source_path.rename(dest_path)
    
    # Log action
    log_approval_action(filename, 'APPROVED', data.get('comment', ''))
    
    return jsonify({'success': True, 'message': f'{filename} approved'})

@app.route('/api/reject', methods=['POST'])
def reject_message():
    """Reject a message"""
    data = request.json
    filename = data.get('filename')
    
    if not filename:
        return jsonify({'success': False, 'error': 'No filename provided'})
    
    # Find file
    source_paths = [NEEDS_ACTION / filename, PENDING_APPROVAL / filename]
    source_path = None
    
    for path in source_paths:
        if path.exists():
            source_path = path
            break
    
    if not source_path:
        return jsonify({'success': False, 'error': 'File not found'})
    
    # Move to Rejected
    dest_path = REJECTED / filename
    source_path.rename(dest_path)
    
    # Log action
    log_approval_action(filename, 'REJECTED', data.get('comment', ''))
    
    return jsonify({'success': True, 'message': f'{filename} rejected'})

@app.route('/api/message/<filename>')
def get_message(filename):
    """Get full message content"""
    # Search in all folders
    folders = [NEEDS_ACTION, PENDING_APPROVAL, APPROVED, REJECTED]
    
    for folder in folders:
        file_path = folder / filename
        if file_path.exists():
            content = file_path.read_text()
            return jsonify({'success': True, 'content': content})
    
    return jsonify({'success': False, 'error': 'File not found'})

def log_approval_action(filename, action, comment=''):
    """Log approval/rejection action"""
    log_file = VAULT_PATH / 'Logs' / 'approval_log.txt'
    log_file.parent.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] {action}: {filename}"
    if comment:
        log_entry += f" - Comment: {comment}"
    log_entry += "\n"
    
    with open(log_file, 'a') as f:
        f.write(log_entry)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("APPROVAL DASHBOARD - Gold Tier AI Employee")
    print("="*60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Dashboard URL: http://localhost:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
