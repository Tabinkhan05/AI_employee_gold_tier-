#!/usr/bin/env node

/**
 * Test Script for Gmail MCP Server
 * 
 * Tests the Gmail email sending functionality.
 * 
 * Usage:
 *   node test.js <recipient-email>
 *   node test.js --help
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import readline from 'readline';

// =============================================================================
// Configuration
// =============================================================================

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SCOPES = [
  'https://www.googleapis.com/auth/gmail.readonly',
  'https://www.googleapis.com/auth/gmail.modify',
  'https://www.googleapis.com/auth/gmail.send'
];

const CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS || 
  path.resolve(__dirname, '../../credentials/gmail_credentials.json');

const TOKEN_PATH = path.resolve(__dirname, '../../credentials/token.json');

const TEST_SUBJECT = 'MCP Server Test - Silver Tier';
const TEST_BODY = 'This is a test email from the MCP server. If you receive this, the integration is working!';

// =============================================================================
// Logging
// =============================================================================

function log(level, message) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] [${level}] ${message}`);
}

const logInfo = (msg) => log('INFO', msg);
const logError = (msg) => log('ERROR', msg);
const logWarn = (msg) => log('WARN', msg);
const logSuccess = (msg) => log('SUCCESS', msg);

function printSeparator(char = '=', length = 70) {
  console.log(char.repeat(length));
}

// =============================================================================
// Prompt
// =============================================================================

function createReadlineInterface() {
  return readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
}

function prompt(rl, question) {
  return new Promise((resolve) => {
    rl.question(question, (answer) => resolve(answer));
  });
}

// =============================================================================
// Auth & Email (lazy-loaded)
// =============================================================================

let googleModule = null;

async function loadGoogle() {
  if (!googleModule) {
    googleModule = await import('googleapis');
  }
  return googleModule;
}

async function loadCredentials() {
  logInfo(`Loading credentials from: ${CREDENTIALS_PATH}`);
  
  if (!fs.existsSync(CREDENTIALS_PATH)) {
    throw new Error(
      `Credentials file not found at ${CREDENTIALS_PATH}. ` +
      'Please download gmail_credentials.json from Google Cloud Console.'
    );
  }
  
  return JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf-8'));
}

async function loadToken() {
  logInfo(`Loading token from: ${TOKEN_PATH}`);
  
  if (!fs.existsSync(TOKEN_PATH)) {
    throw new Error(
      `Token file not found at ${TOKEN_PATH}. ` +
      'Please run gmail_watcher.py first to authenticate.'
    );
  }
  
  return JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf-8'));
}

async function saveToken(token) {
  const tokenDir = path.dirname(TOKEN_PATH);
  if (!fs.existsSync(tokenDir)) {
    fs.mkdirSync(tokenDir, { recursive: true });
  }
  fs.writeFileSync(TOKEN_PATH, JSON.stringify(token, null, 2));
  logInfo('Token saved');
}

async function authenticate() {
  const google = await loadGoogle();
  const credentials = await loadCredentials();
  const token = await loadToken();
  
  const { client_secret, client_id, redirect_uris } = credentials.installed || credentials.web;
  
  const oauth2Client = new google.google.auth.OAuth2(
    client_id,
    client_secret,
    redirect_uris[0]
  );
  
  if (token) {
    oauth2Client.setCredentials(token);
    
    const { credentials: creds } = oauth2Client;
    if (!creds.expiry_date || Date.now() >= creds.expiry_date) {
      logInfo('Token expired, refreshing...');
      try {
        const { token: newToken } = await oauth2Client.refreshAccessToken();
        await saveToken(newToken);
        logSuccess('Token refreshed');
      } catch (error) {
        throw new Error('Authentication required. Run gmail_watcher.py to re-authenticate.');
      }
    } else {
      logSuccess('Using existing valid token');
    }
  }
  
  return oauth2Client;
}

function base64UrlEncode(str) {
  const base64 = Buffer.from(str, 'utf-8').toString('base64');
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function composeEmail({ to, subject, body, fromName }) {
  const date = new Date().toUTCString();
  const fromHeader = fromName 
    ? `From: "${fromName.replace(/"/g, '\\"')}" <me>`
    : 'From: me';
  
  return [
    fromHeader,
    `To: ${to}`,
    `Subject: ${subject}`,
    `Date: ${date}`,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset="UTF-8"',
    'Content-Transfer-Encoding: 7bit',
    '',
    body
  ].join('\r\n');
}

async function sendEmail(oauth2Client, { to, subject, body, fromName }) {
  const google = await loadGoogle();
  const rawEmail = composeEmail({ to, subject, body, fromName });
  const encodedEmail = base64UrlEncode(rawEmail);
  
  const gmail = google.google.gmail({ version: 'v1', auth: oauth2Client });
  
  const response = await gmail.users.messages.send({
    userId: 'me',
    requestBody: { raw: encodedEmail }
  });
  
  return {
    success: true,
    messageId: response.data.id,
    threadId: response.data.threadId
  };
}

// =============================================================================
// Tests
// =============================================================================

async function testAuthentication(oauth2Client) {
  printSeparator('-');
  console.log('TEST 1: Authentication');
  printSeparator('-');
  
  try {
    const google = await loadGoogle();
    const gmail = google.google.gmail({ version: 'v1', auth: oauth2Client });
    const profile = await gmail.users.getProfile({ userId: 'me' });
    
    logSuccess(`Authenticated as: ${profile.data.emailAddress}`);
    logInfo(`Display name: ${profile.data.displayName}`);
    
    console.log('✓ Authentication test PASSED\n');
    return { passed: true, email: profile.data.emailAddress };
  } catch (error) {
    logError(`Authentication FAILED: ${error.message}`);
    console.log('✗ Authentication test FAILED\n');
    return { passed: false, error: error.message };
  }
}

async function testSendEmail(oauth2Client, recipient) {
  printSeparator('-');
  console.log('TEST 2: Send Email');
  printSeparator('-');
  
  console.log(`To: ${recipient}`);
  console.log(`Subject: ${TEST_SUBJECT}`);
  console.log(`Body: ${TEST_BODY}\n`);
  
  try {
    logInfo('Sending test email...');
    
    const result = await sendEmail(oauth2Client, {
      to: recipient,
      subject: TEST_SUBJECT,
      body: TEST_BODY,
      fromName: 'MCP Server Test'
    });
    
    logSuccess(`Email sent! Message ID: ${result.messageId}`);
    console.log('✓ Send email test PASSED\n');
    
    return { passed: true, messageId: result.messageId };
  } catch (error) {
    logError(`Send email FAILED: ${error.message}`);
    console.log('✗ Send email test FAILED\n');
    return { passed: false, error: error.message };
  }
}

async function testVerifyEmail(oauth2Client, messageId) {
  printSeparator('-');
  console.log('TEST 3: Verify Email Sent');
  printSeparator('-');
  
  try {
    const google = await loadGoogle();
    const gmail = google.google.gmail({ version: 'v1', auth: oauth2Client });
    
    const message = await gmail.users.messages.get({
      userId: 'me',
      id: messageId
    });
    
    logSuccess(`Message verified! Labels: ${message.data.labelIds?.join(', ')}`);
    
    if (message.data.labelIds?.includes('SENT')) {
      logSuccess('Message has SENT label');
    }
    
    console.log('✓ Verification test PASSED\n');
    return true;
  } catch (error) {
    logError(`Verification FAILED: ${error.message}`);
    console.log('✗ Verification test FAILED\n');
    return false;
  }
}

// =============================================================================
// Main
// =============================================================================

function printUsage() {
  console.log(`
Gmail MCP Server Test Script
============================

Usage: node test.js <recipient-email>
       node test.js --help

Examples:
  node test.js user@example.com
  GMAIL_CREDENTIALS=/path/to/creds.json node test.js test@example.com
`);
}

async function main() {
  printSeparator('=');
  console.log('Gmail MCP Server - Test Suite');
  console.log('Silver Tier AI Employee Vault');
  printSeparator('=');
  console.log('');
  
  const args = process.argv.slice(2);
  
  if (args.includes('--help') || args.includes('-h')) {
    printUsage();
    process.exit(0);
  }
  
  let recipient = args[0];
  
  if (!recipient) {
    const rl = createReadlineInterface();
    recipient = await prompt(rl, 'Enter recipient email address: ');
    rl.close();
  }
  
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(recipient)) {
    logError(`Invalid email format: ${recipient}`);
    process.exit(1);
  }
  
  logInfo(`Test recipient: ${recipient}\n`);
  
  const results = { authentication: false, sendEmail: false, verify: false, recipient };
  
  try {
    logInfo('Starting authentication test...');
    const oauth2Client = await authenticate();
    const authResult = await testAuthentication(oauth2Client);
    results.authentication = authResult.passed;
    
    if (!results.authentication) {
      logError('Authentication failed.');
      printSummary(results);
      process.exit(1);
    }
    
    logInfo('Starting send email test...');
    const sendResult = await testSendEmail(oauth2Client, recipient);
    results.sendEmail = sendResult.passed;
    
    if (!results.sendEmail) {
      logError('Send email failed.');
      printSummary(results);
      process.exit(1);
    }
    
    logInfo('Starting verification test...');
    results.verify = await testVerifyEmail(oauth2Client, sendResult.messageId);
    
    printSummary(results);
    process.exit(results.verify ? 0 : 1);
    
  } catch (error) {
    logError(`Test suite failed: ${error.message}`);
    printSeparator('=');
    console.log('TEST SUITE FAILED');
    printSeparator('=');
    process.exit(1);
  }
}

function printSummary(results) {
  printSeparator('=');
  console.log('TEST SUMMARY');
  printSeparator('=');
  
  [
    { name: 'Authentication', passed: results.authentication },
    { name: 'Send Email', passed: results.sendEmail },
    { name: 'Verify Email', passed: results.verify }
  ].forEach(test => {
    const symbol = test.passed ? '✓' : '✗';
    console.log(`${symbol} ${test.name}: ${test.passed ? 'PASSED' : 'FAILED'}`);
  });
  
  printSeparator('=');
  
  if (results.authentication && results.sendEmail && results.verify) {
    console.log('ALL TESTS PASSED ✓');
    console.log(`Check inbox for "${results.recipient}"`);
  } else {
    console.log('SOME TESTS FAILED ✗');
  }
  
  printSeparator('=');
}

main();
