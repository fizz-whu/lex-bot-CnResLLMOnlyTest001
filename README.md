# CnResLLMOnlyTest001 - Lex Bot Export

LLM-only restaurant ordering bot using Amazon Bedrock.

## Bot Information

- **Bot ID:** BCBFZ3NILB
- **Bot Name:** CnResLLMOnlyTest001
- **Region:** us-east-1
- **Status:** Available
- **Latest Version:** 7
- **Last Updated:** 2025-10-05 20:26:26

## Directory Structure

```
lex-bot-CnResLLMOnlyTest001/
├── intents/                      # Intent definitions
│   ├── MainIntent.json          # Main conversational intent
│   └── FallbackIntent.json      # Fallback intent (AMAZON.FallbackIntent)
├── slot-types/                   # Custom slot types (none defined)
├── bot-definition/               # Bot configuration and metadata
│   ├── CnResLLMOnlyTest001.json # Main bot definition
│   ├── en_US-locale.json        # English (US) locale configuration
│   ├── versions.json            # Bot version history
│   └── aliases.json             # Bot aliases (prod, TestBotAlias)
├── lambda/                       # Lambda function information
│   └── README.md                # Details about the Lambda fulfillment function
├── deployment/                   # Deployment scripts (placeholder)
└── README.md                    # This file
```

## Configuration Details

### Locales
- **en_US** (English - US)
  - Voice: Joanna (standard engine)
  - NLU Confidence Threshold: 0.2
  - Intents: 2
  - Custom Slot Types: 0

### Intents

#### MainIntent
- **Intent ID:** B48ZZHVFH9
- **Sample Utterances:** 15 utterances including greetings, ordering phrases, and menu inquiries
- **Fulfillment:** Uses Lambda code hook with initial response code hook
- **Behavior:** Invokes dialog code hook, then fulfills intent

#### FallbackIntent
- **Intent ID:** FALLBCKINT
- **Parent:** AMAZON.FallbackIntent
- **Fulfillment:** Uses Lambda code hook
- **Behavior:** Handles unrecognized user input

### Aliases

#### prod
- **Alias ID:** FURK575RGN
- **Bot Version:** 7
- **Lambda Function:** CnResLexLLMOrchestrator
- **Status:** Available

#### TestBotAlias
- **Alias ID:** TSTALIASID
- **Bot Version:** DRAFT
- **Lambda Function:** CnResLexLLMOrchestrator
- **Status:** Available

### Bot Versions
The bot has 8 versions (1-7 plus DRAFT):
- Version 7 (latest, used by prod alias)
- Version 6-1 (previous versions)
- DRAFT (used by TestBotAlias)

## Lambda Integration

Both aliases use the Lambda function:
```
arn:aws:lambda:us-east-1:495599767527:function:CnResLexLLMOrchestrator
```

See `lambda/README.md` for details on accessing the Lambda function code.

## Session Configuration

- **Idle Session TTL:** 300 seconds (5 minutes)
- **Child Directed:** false

## Importing This Bot

To import this bot into another AWS account or recreate it:

1. Create the bot using the configuration in `bot-definition/CnResLLMOnlyTest001.json`
2. Configure the locale using `bot-definition/en_US-locale.json`
3. Create intents from the JSON files in `intents/`
4. Create or configure the Lambda function (see `lambda/README.md`)
5. Create aliases using the configuration in `bot-definition/aliases.json`

## Notes

- This is an LLM-only bot, meaning it uses Amazon Bedrock for natural language understanding
- The bot relies heavily on Lambda code hooks for both initial response and fulfillment
- No custom slot types are defined; the bot uses LLM capabilities for entity extraction
- All conversations end after fulfillment or on error/timeout

## Export Date

Exported on: 2025-10-16
