---
name: twilio
description: "Integrates Twilio for SMS, voice, WhatsApp, and verify API communications."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: backend
  triggers: Twilio, SMS, WhatsApp, phone, voice call, 2FA, Verify, messaging, notification, MFA, phone verification
  role: specialist
  scope: implementation
  output-format: code
  related-skills: sendgrid, fullstack-guardian, secure-code-guardian, test-master
---

# Twilio

Twilio communication specialist — integrates SMS, WhatsApp, voice calls, and Verify 2FA into web applications using the Twilio API, Twilio Client SDK, and webhook handlers.

## When to Use This Skill

- Implementing SMS or WhatsApp notification delivery (alerts, confirmations, marketing)
- Building phone verification or multi-factor authentication flows with Twilio Verify
- Adding voice call capabilities (outbound calls, IVR menus, conferencing)
- Handling incoming messages and calls via Twilio webhooks (StatusCallback, Messaging, Voice)
- Managing phone number inventory, purchasing numbers, or configuring messaging services

## Key Capabilities

- Send SMS and MMS messages via Twilio REST API with status callbacks
- Send and receive WhatsApp messages using Twilio's WhatsApp Business API sandbox or production sender
- Initiate, receive, and manage voice calls (TwiML, <Say>, <Gather>, <Record>, <Conference>)
- Implement 2FA/phone verification using Twilio Verify with one-time passcodes (SMS, voice, email)
- Handle inbound webhooks securely — validate Twilio signatures, parse TwiML requests, respond with TwiML instructions

## Best Practices

- Validate incoming Twilio webhook signatures using `twilio.requestValidator` to prevent request forgery
- Store Twilio credentials (account SID, auth token, API keys) in environment variables — never hardcode them
- Use Twilio Messaging Services for scaling SMS: enable geo-permission, A2P 10DLC registration, and fallback sender pools
