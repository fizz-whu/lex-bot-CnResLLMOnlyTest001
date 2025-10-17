import json
import boto3
import os
from datetime import datetime

# Initialize AWS clients
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Environment variables
MENU_TABLE = os.environ.get('MENU_TABLE', 'CnResMenu')
SESSION_TABLE = os.environ.get('SESSION_TABLE', 'CnResSessions')
# Hard-coded to gpt-oss-20b for cost control - DO NOT CHANGE
MODEL_ID = 'openai.gpt-oss-20b-1:0'

def load_menu():
    """Load menu items from DynamoDB"""
    try:
        table = dynamodb.Table(MENU_TABLE)
        response = table.scan()
        items = response.get('Items', [])

        menu_text = "Restaurant Menu:\n"
        for item in items:
            menu_text += f"- {item['name']} (${item['price']}) - {item.get('description', '')}\n"

        return menu_text if items else "Menu: Mapo Tofu ($12), Fried Rice ($8), Kung Pao Chicken ($14), Spring Rolls ($6)"
    except Exception as e:
        print(f"Error loading menu: {e}")
        # Fallback menu
        return "Menu: Mapo Tofu ($12), Fried Rice ($8), Kung Pao Chicken ($14), Spring Rolls ($6)"

def get_session_context(session_id):
    """Retrieve conversation history from DynamoDB"""
    try:
        table = dynamodb.Table(SESSION_TABLE)
        response = table.get_item(Key={'sessionId': session_id})

        if 'Item' in response:
            return response['Item'].get('history', [])
        return []
    except Exception as e:
        print(f"Error getting session context: {e}")
        return []

def save_session_context(session_id, history, order_data=None):
    """Save conversation history and order to DynamoDB"""
    try:
        table = dynamodb.Table(SESSION_TABLE)
        item = {
            'sessionId': session_id,
            'history': history,
            'lastUpdated': datetime.utcnow().isoformat()
        }

        if order_data:
            item['currentOrder'] = order_data

        table.put_item(Item=item)
    except Exception as e:
        print(f"Error saving session: {e}")

def call_bedrock_llm(prompt):
    """Call Amazon Bedrock with OpenAI gpt-oss-20b model only"""
    try:
        # OpenAI gpt-oss-20b request format - LOCKED for cost control
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.7
        }

        # Call OpenAI gpt-oss-20b via Bedrock
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())

        # Extract response from OpenAI format
        if 'choices' in response_body:
            return response_body['choices'][0]['message']['content']
        else:
            return "I'm sorry, I couldn't process that request."

    except Exception as e:
        print(f"Error calling Bedrock: {e}")
        return f"I apologize, I'm having technical difficulties. Error: {str(e)}"

def extract_order_json(llm_response):
    """Extract JSON order data from LLM response if present"""
    try:
        # Look for JSON block in response
        if '<json>' in llm_response and '</json>' in llm_response:
            json_start = llm_response.index('<json>') + 6
            json_end = llm_response.index('</json>')
            json_str = llm_response[json_start:json_end].strip()
            return json.loads(json_str)
    except Exception as e:
        print(f"No valid JSON found in response: {e}")

    return None

def lambda_handler(event, context):
    """Main Lambda handler for Lex bot - routes based on intent"""

    print(f"Received event: {json.dumps(event)}")

    # Cost control validation - ensure only gpt-oss-20b is used
    if MODEL_ID != 'openai.gpt-oss-20b-1:0':
        error_msg = f"BLOCKED: Attempted to use unauthorized model {MODEL_ID}. Only openai.gpt-oss-20b-1:0 is allowed."
        print(error_msg)
        return {
            'sessionState': {
                'dialogAction': {'type': 'Close'},
                'intent': {
                    'name': event['sessionState']['intent']['name'],
                    'state': 'Failed'
                }
            },
            'messages': [{'contentType': 'PlainText', 'content': 'Service temporarily unavailable.'}]
        }

    # Extract user input and session info
    user_message = event.get('inputTranscript', '')
    session_id = event['sessionId']
    intent_name = event['sessionState']['intent']['name']
    invocation_source = event.get('invocationSource', 'FulfillmentCodeHook')

    print(f"Intent: {intent_name}, InvocationSource: {invocation_source}")

    # Route based on intent type
    # FallbackIntent should use WITH MENU (not without) since it catches ordering phrases
    if intent_name == 'FallbackIntent':
        # FallbackIntent catches complex ordering phrases, so use FULL menu
        return handle_ordering(user_message, session_id, event)
    else:
        # MainIntent - full ordering flow with menu
        return handle_ordering(user_message, session_id, event)

def handle_fallback(user_message, session_id, event):
    """Handle FallbackIntent - NO MENU (saves tokens)"""

    # Get conversation history
    history = get_session_context(session_id)

    # Build conversation context (minimal)
    context_text = ""
    for entry in history[-3:]:  # Last 3 exchanges only
        context_text += f"Customer: {entry.get('user', '')}\nAssistant: {entry.get('bot', '')}\n"

    # Construct prompt WITHOUT menu
    prompt = f"""You are a helpful assistant for a Chinese restaurant.

This is a GENERAL inquiry, NOT a food order. The customer might be asking about:
- Hours of operation
- Location/directions
- Payment methods
- General questions
- Small talk

If they want to ORDER FOOD or see the MENU, politely tell them to say:
"I want to order" or "Show me the menu"

Conversation so far:
{context_text}

Customer: {user_message}

Respond briefly and helpfully (2-3 sentences max)."""

    # Call LLM with reduced tokens
    llm_response = call_bedrock_llm(prompt)
    clean_response = llm_response.strip()

    # Update history
    history.append({
        'user': user_message,
        'bot': clean_response,
        'timestamp': datetime.utcnow().isoformat(),
        'intent': 'FallbackIntent'
    })

    save_session_context(session_id, history)

    return {
        'sessionState': {
            'dialogAction': {'type': 'Close'},
            'intent': {
                'name': event['sessionState']['intent']['name'],
                'state': 'Fulfilled'
            }
        },
        'messages': [{'contentType': 'PlainText', 'content': clean_response}]
    }

def handle_ordering(user_message, session_id, event):
    """Handle MainIntent - WITH MENU (full ordering flow)"""

    # Get conversation history and existing order
    history = get_session_context(session_id)

    # Get existing order from session
    try:
        table = dynamodb.Table(SESSION_TABLE)
        response = table.get_item(Key={'sessionId': session_id})
        existing_order = response.get('Item', {}).get('currentOrder', {'items': []})
    except:
        existing_order = {'items': []}

    # Load menu
    menu = load_menu()

    # Build conversation context
    context_text = ""
    for entry in history[-5:]:  # Last 5 exchanges
        context_text += f"Customer: {entry.get('user', '')}\nAssistant: {entry.get('bot', '')}\n"

    # Build order context for LLM
    order_context = ""
    if existing_order and existing_order['items']:
        order_context = "\n\nCurrent Order in Progress:\n"
        for item in existing_order['items']:
            order_context += f"- {item['quantity']}x {item['name']} (${item.get('price', 'TBD')})"
            if item.get('notes'):
                order_context += f" - {item['notes']}"
            order_context += "\n"

    # Construct prompt for LLM
    prompt = f"""You are a friendly assistant for a Chinese restaurant taking orders.

{menu}
{order_context}

Guidelines:
- If customer says just "hello" or "hi", respond briefly with a simple greeting
- If they ask about the menu, show relevant items WITH PRICES
- When discussing items, ALWAYS mention the price (e.g., "Chicken Fried Rice is $5.35")
- When adding NEW items, output ONLY the NEW item in JSON (system will accumulate them)
- When they say "that's all" or finish ordering, provide a complete order summary with ALL items and total
- Always output order data in JSON format inside <json></json> tags (this will be hidden from customer)
- Keep responses warm, natural, and conversational

JSON Format (output ONLY the new item being added):
<json>{{"items":[{{"name":"Chicken Fried Rice","quantity":1,"notes":"","price":"5.35"}}],"confirmed":true}}</json>

Important:
- The JSON will be automatically removed from your response - customers won't see it
- Focus on natural, friendly language in your main response
- ALWAYS mention prices when discussing or confirming items
- For final order confirmation, list ALL items from "Current Order in Progress" plus any new items
- Format final confirmation like this:
  "Perfect! Here's your complete order:
   • 1 Moo Shu Chicken (extra chicken) - $10.95
   • 1 Chicken Fried Rice - $5.35

   Subtotal: $16.30

   We'll have that ready for you! What's the best phone number to reach you?"

Conversation so far:
{context_text}

Customer: {user_message}"""

    # Call Bedrock LLM
    llm_response = call_bedrock_llm(prompt)

    # Extract order data if present
    new_order_data = extract_order_json(llm_response)

    # Merge new items with existing order
    if new_order_data and 'items' in new_order_data:
        # Add new items to existing order
        for new_item in new_order_data['items']:
            existing_order['items'].append(new_item)
        existing_order['confirmed'] = new_order_data.get('confirmed', False)
        order_data = existing_order
    else:
        order_data = existing_order if existing_order['items'] else None

    # Clean response for user (remove JSON tags and reasoning)
    import re
    clean_response = llm_response

    # Remove <reasoning> tags and content
    clean_response = re.sub(r'<reasoning>.*?</reasoning>', '', clean_response, flags=re.DOTALL)

    # Remove <json> tags and their content completely
    clean_response = re.sub(r'<json>.*?</json>', '', clean_response, flags=re.DOTALL)

    # Remove any remaining JSON objects (backup cleanup)
    clean_response = re.sub(r'\{[^{}]*"items"[^{}]*\}', '', clean_response)
    clean_response = re.sub(r'\{[^{}]*"name"[^{}]*\}', '', clean_response)

    # Remove standalone commas
    clean_response = re.sub(r'^\s*,\s*', '', clean_response)
    clean_response = re.sub(r'\s*,\s*$', '', clean_response)

    # Clean up extra whitespace and newlines
    clean_response = re.sub(r'\s+', ' ', clean_response).strip()

    # Update conversation history
    history.append({
        'user': user_message,
        'bot': clean_response,
        'timestamp': datetime.utcnow().isoformat()
    })

    # Save session with accumulated order
    save_session_context(session_id, history, order_data)

    # Return response to Lex
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'Close'
            },
            'intent': {
                'name': event['sessionState']['intent']['name'],
                'state': 'Fulfilled'
            }
        },
        'messages': [
            {
                'contentType': 'PlainText',
                'content': clean_response
            }
        ]
    }
