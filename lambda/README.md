# Lambda Function - CnResLexLLMOrchestrator

This Lambda function serves as the fulfillment code hook for the CnResLLMOnlyTest001 Lex bot, handling restaurant ordering conversations using Amazon Bedrock.

## Function Information

**Lambda Function ARN:**
```
arn:aws:lambda:us-east-1:495599767527:function:CnResLexLLMOrchestrator
```

**Code Hook Interface Version:** 1.0

## Configuration

- **Runtime:** Python 3.11
- **Handler:** `lex_llm_orchestrator.lambda_handler`
- **Memory:** 256 MB
- **Timeout:** 30 seconds
- **Architecture:** x86_64
- **Role:** arn:aws:iam::495599767527:role/CnResLexLLMRole

## Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `MODEL_ID` | `openai.gpt-oss-20b-1:0` | Bedrock model ID (hard-coded for cost control) |
| `RESTAURANT_ID` | `CnResNJLLMONLYTEST` | Restaurant identifier |
| `SESSION_TABLE` | `CnResSessions` | DynamoDB table for session storage |
| `MENU_TABLE` | `CnResMenu` | DynamoDB table for menu items |

## Files

- `lex_llm_orchestrator.py` - Main Lambda function code
- `configuration.json` - Complete Lambda configuration
- `requirements.txt` - Python dependencies (boto3 only)

## How It Works

### Intent Routing

The function handles two intents:

1. **MainIntent** - Full ordering flow with menu
   - Handles greetings, menu inquiries, and food orders
   - Shows menu with prices
   - Tracks orders across conversation turns
   - Accumulates items in session storage

2. **FallbackIntent** - Catches unrecognized input
   - Also routes to full ordering flow (since complex orders may not match MainIntent)
   - Provides conversational flexibility

### Key Features

1. **Amazon Bedrock Integration**
   - Uses OpenAI GPT-OSS-20B model via Bedrock
   - Hard-coded model ID for cost control
   - Constructs conversational prompts with menu and order context

2. **DynamoDB Session Management**
   - Stores conversation history in `CnResSessions` table
   - Maintains current order state across turns
   - Loads menu items from `CnResMenu` table

3. **Order Tracking**
   - Extracts structured order data from LLM responses using JSON tags
   - Accumulates items across multiple conversation turns
   - Cleans response text to hide internal JSON from users

4. **Menu Management**
   - Dynamically loads menu from DynamoDB
   - Falls back to hard-coded menu if table unavailable
   - Always includes prices in responses

### Cost Controls

The function includes hard-coded cost controls:
- Model locked to `openai.gpt-oss-20b-1:0`
- Will reject requests if MODEL_ID is changed
- Token limits set to 1000 max tokens per call

### Response Flow

1. Extract user input from Lex event
2. Retrieve conversation history from DynamoDB
3. Load restaurant menu
4. Construct contextualized prompt for Bedrock
5. Call Bedrock with OpenAI model
6. Extract order JSON (if present)
7. Merge new items with existing order
8. Clean response text (remove JSON/reasoning tags)
9. Save updated session and order to DynamoDB
10. Return formatted response to Lex

## DynamoDB Tables

### CnResSessions Table
Stores conversation state and orders.

**Schema:**
```json
{
  "sessionId": "string (partition key)",
  "history": [
    {
      "user": "string",
      "bot": "string",
      "timestamp": "ISO 8601",
      "intent": "string (optional)"
    }
  ],
  "currentOrder": {
    "items": [
      {
        "name": "string",
        "quantity": number,
        "price": "string",
        "notes": "string"
      }
    ],
    "confirmed": boolean
  },
  "lastUpdated": "ISO 8601"
}
```

### CnResMenu Table
Stores menu items.

**Schema:**
```json
{
  "name": "string (partition key)",
  "price": "string",
  "description": "string (optional)"
}
```

**Fallback Menu:**
If the table is unavailable, uses:
- Mapo Tofu ($12)
- Fried Rice ($8)
- Kung Pao Chicken ($14)
- Spring Rolls ($6)

## IAM Permissions Required

The Lambda execution role needs:
- `bedrock:InvokeModel` for Bedrock API calls
- `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:Scan` for DynamoDB operations
- Standard Lambda execution permissions (CloudWatch Logs)

## Deployment

To deploy this Lambda function:

```bash
# Package the function
zip function.zip lex_llm_orchestrator.py

# Create or update the function
aws lambda update-function-code \
  --function-name CnResLexLLMOrchestrator \
  --zip-file fileb://function.zip \
  --region us-east-1

# Update configuration if needed
aws lambda update-function-configuration \
  --function-name CnResLexLLMOrchestrator \
  --runtime python3.11 \
  --handler lex_llm_orchestrator.lambda_handler \
  --memory-size 256 \
  --timeout 30 \
  --environment Variables="{MODEL_ID=openai.gpt-oss-20b-1:0,RESTAURANT_ID=CnResNJLLMONLYTEST,SESSION_TABLE=CnResSessions,MENU_TABLE=CnResMenu}" \
  --region us-east-1
```

## Testing

Test the function locally using sample Lex events:

```python
event = {
    "sessionId": "test-session-123",
    "inputTranscript": "I want to order fried rice",
    "sessionState": {
        "intent": {
            "name": "MainIntent"
        }
    },
    "invocationSource": "FulfillmentCodeHook"
}
```

## Logging

Logs are available in CloudWatch Logs:
- **Log Group:** `/aws/lambda/CnResLexLLMOrchestrator`
- Includes debug information about Bedrock calls and DynamoDB operations

## Notes

- Both `prod` and `TestBotAlias` Lex aliases use this function
- Function uses cost control measures to prevent unauthorized model usage
- All responses are conversational and hide internal JSON/reasoning from users
- Order state persists across conversation turns via DynamoDB
