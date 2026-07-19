---
name: sendgrid
description: "Sends transactional and marketing emails using SendGrid with templates, dynamic data, and event tracking."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: backend
  triggers: SendGrid, email, transactional email, mail send, email template, email delivery, SMTP, email API, send email
  role: specialist
  scope: implementation
  output-format: code
  related-skills: twilio, fullstack-guardian, serverless, vercel-deploy
---

# SendGrid

SendGrid email specialist — delivers transactional and marketing emails using SendGrid's v3 Mail Send API, dynamic templates, attachment handling, suppression management, and event webhooks.

## When to Use This Skill

- Sending transactional emails (welcome emails, password resets, order confirmations, receipts)
- Building and rendering dynamic email templates with Handlebars placeholders and pre-header text
- Tracking email delivery events (opens, clicks, bounces, spam reports) via webhooks
- Managing sender authentication (SPF, DKIM, DMARC) and suppression lists (bounces, blocks, spam, unsubscribes)
- Sending emails from serverless functions (AWS Lambda, Vercel, Cloudflare Workers) using the SendGrid API

## Key Capabilities

- Send emails via SendGrid v3 Mail Send API with personalizations, attachments, categories, and custom headers
- Design and render dynamic transactional templates using SendGrid's Design Library with Handlebars substitution
- Configure and process event webhooks — parse JSON payloads for opens, clicks, bounces, deferred, delivered, dropped, spam reports, and unsubscribe events
- Manage suppression groups and unsubscribes — create groups, add/remove recipients, respect global and group-level suppressions
- Authenticate sending domains via Sender Authentication (DomainKeys, DKIM, SPF, DMARC) to improve deliverability

## Best Practices

- Use SendGrid dynamic templates stored in SendGrid instead of inline HTML — enables edits without code deploys
- Set up event webhooks to a dedicated endpoint and log delivery failures for alerting and retry workflows
- Segment email traffic by purpose (transactional vs marketing) using separate API keys and sender identities to avoid reputation cross-contamination
