---
layout: default
title: Notification Destinations
parent: User Guide
nav_order: 1
---

# Notification Destinations

This page explains what to enter in the **Destination** field when creating notification subscriptions for different platforms.

## Browser

Browser notifications appear as in-page toast messages. No destination is required for browser notifications.

## Email

Enter a valid email address where notifications should be sent.

**Example:** `you@example.com`

## Webhook Platforms

Webhook platforms send notifications to external services. The destination format depends on which service your site administrator has configured.

### Slack

Enter the full Slack webhook URL for your channel.

**Example:** `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`

To get a webhook URL:

1. Go to [Slack API Apps](https://api.slack.com/apps)
2. Create a new app or select an existing one
3. Enable "Incoming Webhooks" under Features
4. Add a new webhook to your workspace
5. Copy the Webhook URL

### Discord

Enter the full Discord webhook URL for your channel.

**Example:** `https://discord.com/api/webhooks/000000000000000000/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`

To get a webhook URL:

1. Open channel settings in Discord (click the gear icon next to the channel name)
2. Select "Integrations"
3. Click "Webhooks"
4. Create a new webhook or use an existing one
5. Copy the Webhook URL

### Telegram

Enter either a channel username (starting with `@`) or a numeric chat ID.

**Examples:**
- `@yourchannel`
- `123456789`
- `-1001234567890` (for groups/supergroups)

To find your chat ID:

1. Start a conversation with your bot
2. Send a message to the bot
3. Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find the `chat.id` value in the response

{: .note }
Telegram requires the site administrator to configure a bot token. Contact your site administrator if Telegram notifications are not available.

### Generic Webhook

For other webhook services, enter any valid HTTPS URL. The service will receive JSON data containing event details.

**Example:** `https://your-service.com/webhook/puzzlehunt`
