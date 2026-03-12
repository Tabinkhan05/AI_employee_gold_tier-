#!/usr/bin/env node
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { google } from 'googleapis';
import fs from 'fs';
import path from 'path';

// Paths
const CREDENTIALS_PATH = process.env.GMAIL_CREDENTIALS || '/mnt/d/AI_employee_vault_S_tier/credentials/gmail_credentials.json';
const TOKEN_PATH = process.env.TOKEN_PATH || '/mnt/d/AI_employee_vault_S_tier/credentials/token.json';

// Create MCP server
const server = new Server(
  {
    name: 'email-mcp-server',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Gmail client setup
async function getGmailClient() {
  const credentials = JSON.parse(fs.readFileSync(CREDENTIALS_PATH, 'utf8'));
  const token = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));
  
  const { client_secret, client_id, redirect_uris } = credentials.installed;
  const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirect_uris[0]);
  
  oAuth2Client.setCredentials(token);
  
  // Auto-refresh handler
  oAuth2Client.on('tokens', (tokens) => {
    if (tokens.refresh_token) {
      const updatedToken = { ...token, ...tokens };
      fs.writeFileSync(TOKEN_PATH, JSON.stringify(updatedToken, null, 2));
    }
  });
  
  return google.gmail({ version: 'v1', auth: oAuth2Client });
}

// List tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'send_email',
        description: 'Send an email via Gmail API',
        inputSchema: {
          type: 'object',
          properties: {
            to: {
              type: 'string',
              description: 'Recipient email address',
            },
            subject: {
              type: 'string',
              description: 'Email subject',
            },
            body: {
              type: 'string',
              description: 'Email body (plain text)',
            },
          },
          required: ['to', 'subject', 'body'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === 'send_email') {
    const { to, subject, body } = request.params.arguments;
    
    try {
      const gmail = await getGmailClient();
      
      const emailContent = [
        `To: ${to}`,
        `Subject: ${subject}`,
        'Content-Type: text/plain; charset=utf-8',
        '',
        body,
      ].join('\n');
      
      const encodedMessage = Buffer.from(emailContent)
        .toString('base64')
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');
      
      const result = await gmail.users.messages.send({
        userId: 'me',
        requestBody: { raw: encodedMessage },
      });
      
      return {
        content: [
          {
            type: 'text',
            text: `✅ Email sent successfully!\n📧 Message ID: ${result.data.id}\n📬 Sent to: ${to}\n📝 Subject: ${subject}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `❌ Failed to send email: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
  
  throw new Error(`Unknown tool: ${request.params.name}`);
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Email MCP server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
