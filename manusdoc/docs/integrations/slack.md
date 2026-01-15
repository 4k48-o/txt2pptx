# Slack

## Overview

The Manus Slack integration lets you create sessions directly from Slack channels or with the Manus bot.

***

## Requirements

* A Slack workspace where you have permission to install apps
* A Manus Account

***

## Installation

1. Go to **Manus Settings → Integrations → Slack**
2. Click **Connect**
3. Install the app and complete setup

<img src="https://mintcdn.com/manus-api/jYbGpArvQsxpaz_z/images/screenshot/integration_slack.png?fit=max&auto=format&n=jYbGpArvQsxpaz_z&q=85&s=3e8f66a4740d1dc1a7909da49409fbe1" alt="Slack Integraion" data-og-width="920" width="920" data-og-height="680" height="680" data-path="images/screenshot/integration_slack.png" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/manus-api/jYbGpArvQsxpaz_z/images/screenshot/integration_slack.png?w=280&fit=max&auto=format&n=jYbGpArvQsxpaz_z&q=85&s=9775eb07c72bf6826dbaa7496c792e77 280w, https://mintcdn.com/manus-api/jYbGpArvQsxpaz_z/images/screenshot/integration_slack.png?w=560&fit=max&auto=format&n=jYbGpArvQsxpaz_z&q=85&s=8c06afc63ce59592636915c166073aef 560w, https://mintcdn.com/manus-api/jYbGpArvQsxpaz_z/images/screenshot/integration_slack.png?w=840&fit=max&auto=format&n=jYbGpArvQsxpaz_z&q=85&s=6683ae922e64e93002b363660f9e6c92 840w, https://mintcdn.com/manus-api/jYbGpArvQsxpaz_z/images/screenshot/integration_slack.png?w=1100&fit=max&auto=format&n=jYbGpArvQsxpaz_z&q=85&s=c30818762705c3ac58757d8e55b1e44b 1100w, https://mintcdn.com/manus-api/jYbGpArvQsxpaz_z/images/screenshot/integration_slack.png?w=1650&fit=max&auto=format&n=jYbGpArvQsxpaz_z&q=85&s=96eae8ad42f336392ceae6c132d51427 1650w, https://mintcdn.com/manus-api/jYbGpArvQsxpaz_z/images/screenshot/integration_slack.png?w=2500&fit=max&auto=format&n=jYbGpArvQsxpaz_z&q=85&s=e73c85ffa339e91718e2747b071230f3 2500w" />

***

## Usage

* Tag @manus in threads in channel or send a direct message to the Manus bot
* Use `mute` or `unmute` to control thread activity

***

## Changelog

### November 27, 2025

We’ve updated Manus Slack App behavior based on user feedback.

| Scenario                                        | Previous Behavior                                                                 | Updated Behavior                                                            |
| ----------------------------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| **Direct @Manus in a channel**                  | Manus replies directly under the message and automatically starts a Manus thread. | *No change, behavior remains the same.*                                     |
| **@Manus in a reply within a non-Manus thread** | A new Manus thread would be created.                                              | Manus now replies directly under the message without creating a new thread. |
| **User reply behavior inside Manus threads**    | Manus proactively listens and replies within the thread.                          | Manus will only reply when explicitly mentioned.                            |


---

> To find navigation and other pages in this documentation, fetch the llms.txt file at: https://open.manus.ai/docs/llms.txt