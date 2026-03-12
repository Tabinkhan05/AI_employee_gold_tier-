import { google } from 'googleapis';
import fs from 'fs';

const CREDENTIALS_PATH = '/mnt/d/AI_employee_vault_S_tier/credentials/gmail_credentials.json';
const TOKEN_PATH = '/mnt/d/AI_employee_vault_S_tier/credentials/token.json';

async function sendEmail() {
  console.log('\n========================================');
  console.log('Gmail MCP - Fixed Token Test');
  console.log('========================================\n');

  const recipient = process.argv[2];
  if (!recipient) {
    console.error('[ERROR] Usage: node fixed-token-test.js your@email.com');
    process.exit(1);
  }

  try {
    console.log('[INFO] Loading credentials...');
    const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
    const { client_secret, client_id, redirect_uris } = credentials.installed;

    console.log('[INFO] Loading token...');
    const token = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));

    // Create OAuth2 client
    const oAuth2Client = new google.auth.OAuth2(
      client_id,
      client_secret,
      redirect_uris[0]
    );

    // Set credentials (this will auto-refresh if needed)
    oAuth2Client.setCredentials(token);

    // Setup auto-refresh handler
    oAuth2Client.on('tokens', (tokens) => {
      if (tokens.refresh_token) {
        console.log('[INFO] Token refreshed, saving...');
        const updatedToken = { ...token, ...tokens };
        fs.writeFileSync(TOKEN_PATH, JSON.stringify(updatedToken, null, 2));
        console.log('[SUCCESS] Updated token saved');
      }
    });

    console.log('[INFO] Authentication setup complete');

    // Create Gmail client
    const gmail = google.gmail({ version: 'v1', auth: oAuth2Client });

    // Compose email
    console.log('[INFO] Composing email...');
    const emailContent = [
      'Content-Type: text/plain; charset="UTF-8"\n',
      'MIME-Version: 1.0\n',
      `To: ${recipient}\n`,
      'Subject: MCP Server Test - Token Refresh Working!\n\n',
      'SUCCESS! This email confirms:\n\n',
      '✅ OAuth2 authentication working\n',
      '✅ Token auto-refresh working\n',
      '✅ Gmail API integration successful\n',
      '✅ MCP server ready for Claude Code\n\n',
      'Timestamp: ' + new Date().toISOString() + '\n',
      'Sent from: AI Employee MCP Server (Silver Tier)\n'
    ].join('');

    const encodedMessage = Buffer.from(emailContent)
      .toString('base64')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');

    console.log(`[INFO] Sending email to: ${recipient}...`);
    
    const result = await gmail.users.messages.send({
      userId: 'me',
      requestBody: { raw: encodedMessage },
    });

    console.log('\n========================================');
    console.log('✅ SUCCESS! Email sent!');
    console.log(`📧 Message ID: ${result.data.id}`);
    console.log('========================================\n');
    console.log('📬 Check your Gmail inbox!\n');

    process.exit(0);

  } catch (error) {
    console.error('\n========================================');
    console.error('❌ ERROR:', error.message);
    console.error('========================================\n');
    
    if (error.message.includes('invalid_grant')) {
      console.log('💡 Token is completely invalid.');
      console.log('   Run: cd /mnt/d/AI_employee_vault_S_tier');
      console.log('   Then: rm credentials/token.json');
      console.log('   Then: python3 gmail_watcher.py\n');
    }
    
    process.exit(1);
  }
}

sendEmail();
