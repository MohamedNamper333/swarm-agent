---
name: paypal
description: Integrates PayPal payment processing including buttons, checkout, subscriptions, and webhooks.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: payments
  triggers: PayPal, payment, checkout, buttons, subscription, webhook, dispute, REST API, order, capture
  role: specialist
  scope: implementation
  output-format: code
  related-skills: stripe, nextjs-developer, secure-code-guardian
---

# PayPal

PayPal provides a suite of payment solutions including PayPal Buttons (client-side), Orders API (server-side), Subscriptions (billing agreements), and Dispute Resolution. The PayPal REST API covers OAuth 2.0 authentication, order creation and capture, webhook event handling, and identity (Login with PayPal).

## When to Use This Skill

- Adding PayPal as a payment option alongside credit cards using the JavaScript Buttons SDK
- Implementing a server-side Orders API flow — create order, authorize, capture, and refund — for custom checkout experiences
- Setting up recurring billing with PayPal Subscription plans and billing agreements
- Handling PayPal webhooks (e.g., `PAYMENT.CAPTURE.COMPLETED`, `BILLING.SUBSCRIPTION.*`) to reconcile payment state in your database
- Managing disputes and chargebacks via the PayPal REST API's dispute endpoints

## Key Capabilities

- PayPal Buttons SDK — Render a smart payment button with `paypal.Buttons()` that handles the entire checkout flow client-side
- Orders API — Create, authorize, capture, void, and refund orders via `POST /v2/checkout/orders` and `POST /v2/payments/captures`
- Subscription billing — Create billing plans and agreements for recurring payments; manage activation, suspension, and cancellation
- Webhook verification — Validate PayPal webhook events using signature verification (JWKs) and idempotent processing with `webhook-id` headers
- Dispute resolution — List, accept, and respond to customer disputes programmatically through the Customer Disputes API

## Best Practices

- Use the Orders API (v2) rather than the legacy Payments API — it supports the full capture flow, order patches, and better error reporting
- Always verify PayPal webhook signatures using the `POST /v1/notifications/verify-webhook-signature` endpoint before processing events
- Store the PayPal Order ID, status, and capture metadata in your database; use idempotency keys (`PayPal-Request-Id`) to prevent duplicate captures on retry
