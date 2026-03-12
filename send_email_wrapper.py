#!/usr/bin/env python3
import sys
import json
import subprocess

def send_email(to, subject, body):
    """Wrapper to call Node.js email sender"""
    
    # Create temp script
    script = f"""
import {{ google }} from 'googleapis';
import fs from 'fs';

const CREDS = '/mnt/d/AI_employee_vault_S_tier/credentials/gmail_credentials.json';
const TOKEN = '/mnt/d/AI_employee_vault_S_tier/credentials/token.json';

async function send() {{
  const creds = JSON.parse(fs.readFileSync(CREDS, 'utf8'));
  const token = JSON.parse(fs.readFileSync(TOKEN, 'utf8'));
  
  const {{ client_secret, client_id, redirect_uris }} = creds.installed;
  const auth = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);
  auth.setCredentials(token);
  
  const gmail = google.gmail({{ version: 'v1', auth }});
  
  const msg = [
    'To: {to}',
    'Subject: {subject}',
    '',
    '{body}'
  ].join('\\n');
  
  const encoded = Buffer.from(msg).toString('base64').replace(/\\+/g, '-').replace(/\\//g, '_').replace(/=+$/, '');
  
  const result = await gmail.users.messages.send({{
    userId: 'me',
    requestBody: {{ raw: encoded }}
  }});
  
  console.log(JSON.stringify({{ success: true, messageId: result.data.id }}));
}}

send().catch(err => {{
  console.error(JSON.stringify({{ success: false, error: err.message }}));
  process.exit(1);
}});
"""
    
    # Write temp file
    with open('/tmp/send_email_temp.mjs', 'w') as f:
        f.write(script)
    
    # Execute
    result = subprocess.run(['node', '/tmp/send_email_temp.mjs'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        data = json.loads(result.stdout)
        print(f"✅ Email sent! Message ID: {data['messageId']}")
        return 0
    else:
        print(f"❌ Error: {result.stderr}")
        return 1

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python3 send_email_wrapper.py TO SUBJECT BODY")
        sys.exit(1)
    
    sys.exit(send_email(sys.argv[1], sys.argv[2], sys.argv[3]))
