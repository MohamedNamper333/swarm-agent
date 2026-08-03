---
name: stripe
description: Integrates Stripe payment processing including Checkout, PaymentIntents, webhooks, subscriptions, and Connect.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: payments
  triggers: Stripe, payment, Checkout, PaymentIntent, webhook, subscription, Connect, Stripe Elements, price, product
  role: specialist
  scope: implementation
  output-format: code
  related-skills: paypal, nextjs-developer, secure-code-guardian
---

# Stripe

Stripe is a global payment processor that offers a complete payment stack — Checkout (hosted payment page), PaymentIntents (custom flow), Elements (embedded UI), Billing (subscriptions and invoices), Connect (marketplace platform), and webhook event handling.

## When to Use This Skill

- Implementing a one-time payment flow using Stripe Checkout or PaymentIntents with a React/Next.js frontend
- Creating subscription plans (monthly, yearly, usage-based) with Stripe Billing and customer portal
- Building a marketplace or platform with Stripe Connect — account onboarding, split payments, direct charges
- Handling Stripe webhooks (e.g., `checkout.session.completed`, `invoice.paid`) to sync payment status to a local database
- Rendering custom payment forms with Stripe Elements — Card, Link, or wallet buttons (Apple Pay, Google Pay)

## Key Capabilities

- Checkout Sessions — Create a hosted payment page with `stripe.checkout.sessions.create()`; handle success/cancel redirects with minimal frontend code
- PaymentIntents — Build custom payment flows with `stripe.paymentIntents.create()` and confirm on the client with `stripe.confirmCardPayment()`
- Subscription management — Create products and prices, manage billing cycles, handle upgrades/downgrades, and redirect users to the customer portal
- Connect platform — Onboard connected accounts, accept `on_behalf_of` payments, split funds with `transfer_data`, and handle dispute workflows
- Webhook processing — Verify signatures with `stripe.webhooks.constructEvent()`, acknowledge events with 200 responses, and idempotently handle retries

## Best Practices

- Always verify Stripe webhook signatures in production — never trust raw request bodies without `stripe.webhooks.constructEvent()`
- Handle idempotency keys for all mutation requests to prevent duplicate charges from network retries
- Store only the Stripe Customer ID, PaymentIntent/Metadata, and subscription status in your database; never store raw card numbers or PCI-sensitive data
