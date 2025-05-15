import os
import uuid
import logging
import datetime
import json
from flask import Flask, render_template, request, jsonify, session

# Import sandbox module
from sandbox import execute_code, format_result_as_html

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Helper function to get current timestamp
def get_timestamp():
    return datetime.datetime.now().isoformat()

@app.route('/')
def index():
    """Render the main page with a new chat ID."""
    # Initialize session storage if not already
    if 'chats' not in session:
        session['chats'] = {}
    
    # Generate a new chat ID if none exists
    if 'current_chat_id' not in session:
        new_chat_id = str(uuid.uuid4())
        session['current_chat_id'] = new_chat_id
        # Initialize the new chat
        session['chats'][new_chat_id] = {
            'name': 'Nouveau chat',
            'created_at': get_timestamp(),
            'ephemeral': False,
            'messages': []
        }
        session.modified = True
    
    return render_template('index.html', chat_id=session['current_chat_id'])

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages, create new chats, and process special modes."""
    data = request.json
    
    # Initialize session storage if not already
    if 'chats' not in session:
        session['chats'] = {}
    
    # Handle new chat creation
    if data.get('new_chat'):
        new_chat_id = str(uuid.uuid4())
        session['current_chat_id'] = new_chat_id
        
        # Create a new chat in session
        session['chats'][new_chat_id] = {
            'name': 'Nouveau chat',
            'created_at': get_timestamp(),
            'ephemeral': False,
            'messages': []
        }
        session.modified = True
        logging.debug(f"Created new chat with ID: {new_chat_id}")
        
        return jsonify({
            'success': True,
            'chat_id': new_chat_id
        })
    
    # Handle regular message processing
    chat_id = data.get('chat_id')
    message = data.get('message', '')
    deep_search = data.get('deep_search', False)
    deep_think = data.get('deep_think', False)
    has_image = data.get('has_image', False)
    confirmation = data.get('confirmation')
    
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    
    # Ensure chat exists
    if chat_id not in session['chats']:
        session['chats'][chat_id] = {
            'name': 'Nouveau chat',
            'created_at': get_timestamp(),
            'ephemeral': False,
            'messages': []
        }
    
    # Store user message
    if message or has_image:
        message_id = str(uuid.uuid4())
        session['chats'][chat_id]['messages'].append({
            'id': message_id,
            'content': message,
            'sender': 'user',
            'has_image': has_image,
            'timestamp': get_timestamp()
        })
        session.modified = True
    
    # Process bot response
    response = ""
    require_confirmation = False
    
    # Handle different modes
    if deep_think:
        if confirmation == 'Y':
            response = "Je vais chercher plus d'informations sur ce sujet. Voici ce que j'ai trouvé..."
        elif confirmation == 'N':
            response = "D'accord, je ne chercherai pas plus loin. En quoi puis-je vous aider d'autre ?"
        else:
            require_confirmation = True
            return jsonify({
                'require_confirmation': True,
                'message': "Je ne suis pas encore au courant de ces concepts, voulez-vous que je cherche ailleurs ?"
            })
    elif deep_search:
        response = "Voici les résultats de ma recherche approfondie sur ce sujet..."
    elif has_image:
        response = "J'ai analysé l'image que vous avez partagée. Voici ce que j'en pense..."
    else:
        response = "Je comprends votre message. Comment puis-je vous aider davantage ?"
    
    # Store bot response
    if response:
        message_id = str(uuid.uuid4())
        session['chats'][chat_id]['messages'].append({
            'id': message_id,
            'content': response,
            'sender': 'bot',
            'timestamp': get_timestamp()
        })
        session.modified = True
    
    return jsonify({
        'response': response,
        'require_confirmation': require_confirmation
    })

@app.route('/chat_history', methods=['GET'])
def get_chat_history():
    """Retrieve the chat history for the current user."""
    # Initialize session storage if not already
    if 'chats' not in session:
        session['chats'] = {}
    
    chat_list = []
    # Convert session dict to list
    for chat_id, chat_data in session['chats'].items():
        chat_list.append({
            'id': chat_id,
            'name': chat_data.get('name', 'Nouveau chat'),
            'created_at': chat_data.get('created_at'),
            'ephemeral': chat_data.get('ephemeral', False)
        })
    
    # Sort by created_at (newest first)
    chat_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return jsonify(chat_list)

@app.route('/chat_messages', methods=['GET'])
def get_chat_messages():
    """Retrieve messages for a specific chat."""
    chat_id = request.args.get('chat_id')
    
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    
    # Initialize session storage if not already
    if 'chats' not in session:
        session['chats'] = {}
    
    # Update current chat ID in session
    session['current_chat_id'] = chat_id
    
    # Ensure chat exists
    if chat_id not in session['chats']:
        session['chats'][chat_id] = {
            'name': 'Nouveau chat',
            'created_at': get_timestamp(),
            'ephemeral': False,
            'messages': []
        }
        session.modified = True
    
    # Get chat info and messages
    chat_data = session['chats'][chat_id]
    message_list = chat_data.get('messages', [])
    
    return jsonify({
        'messages': message_list,
        'chat': {
            'id': chat_id,
            'name': chat_data.get('name', 'Nouveau chat'),
            'ephemeral': chat_data.get('ephemeral', False)
        }
    })

@app.route('/toggle_ephemeral', methods=['POST'])
def toggle_ephemeral():
    """Toggle ephemeral messages for a chat."""
    data = request.json
    chat_id = data.get('chat_id')
    
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    
    # Initialize session storage if not already
    if 'chats' not in session:
        session['chats'] = {}
    
    # Ensure chat exists
    if chat_id not in session['chats']:
        session['chats'][chat_id] = {
            'name': 'Nouveau chat',
            'created_at': get_timestamp(),
            'ephemeral': False,
            'messages': []
        }
    
    # Toggle status
    current_status = session['chats'][chat_id].get('ephemeral', False)
    session['chats'][chat_id]['ephemeral'] = not current_status
    session.modified = True
    
    return jsonify({
        'success': True,
        'ephemeral': not current_status
    })

@app.route('/rename_chat', methods=['POST'])
def rename_chat():
    """Rename a chat."""
    data = request.json
    chat_id = data.get('chat_id')
    new_name = data.get('name')
    
    if not chat_id or not new_name:
        return jsonify({'error': 'Missing chat ID or name'}), 400
    
    # Initialize session storage if not already
    if 'chats' not in session:
        session['chats'] = {}
    
    # Ensure chat exists
    if chat_id not in session['chats']:
        session['chats'][chat_id] = {
            'name': 'Nouveau chat',
            'created_at': get_timestamp(),
            'ephemeral': False,
            'messages': []
        }
    
    # Update chat name
    session['chats'][chat_id]['name'] = new_name
    session.modified = True
    
    return jsonify({
        'success': True,
        'name': new_name
    })

@app.route('/sandbox')
def sandbox():
    """Render the sandbox page."""
    return render_template('sandbox.html')

@app.route('/execute_code', methods=['POST'])
def sandbox_execute():
    """Execute code in the sandbox and return the result."""
    data = request.json
    code = data.get('code', '')
    
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    # Execute the code in the sandbox
    result = execute_code(code)
    
    # Store the code and result in session history
    if 'code_history' not in session:
        session['code_history'] = []
    
    # Add to history with a timestamp and ID
    code_entry = {
        'id': str(uuid.uuid4()),
        'code': code,
        'result': result,
        'timestamp': get_timestamp()
    }
    session['code_history'].append(code_entry)
    session.modified = True
    
    # Limit history to last 10 entries
    if len(session['code_history']) > 10:
        session['code_history'] = session['code_history'][-10:]
        session.modified = True
    
    # Add HTML formatted result
    result['html_result'] = format_result_as_html(result)
    
    return jsonify(result)

@app.route('/code_history', methods=['GET', 'DELETE'])
def code_history():
    """Get or clear the code execution history."""
    if 'code_history' not in session:
        session['code_history'] = []
    
    if request.method == 'DELETE':
        session['code_history'] = []
        session.modified = True
        return jsonify({'success': True})
    
    return jsonify(session['code_history'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
