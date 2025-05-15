import os
import uuid
import logging
import datetime
from flask import Flask, render_template, request, jsonify, session
import firebase_admin
from firebase_admin import credentials, firestore

# Create fallback constants for when using the in-memory storage
class MockFirestore:
    SERVER_TIMESTAMP = datetime.datetime.now()
    
    class Query:
        DESCENDING = "DESCENDING"

# Use the real Firestore if available, otherwise use our mock
try:
    FIRESTORE = firestore
except NameError:
    FIRESTORE = MockFirestore

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Initialize Firestore DB
try:
    # Check if Firebase is already initialized to avoid re-initialization errors
    if not firebase_admin._apps:
        # Try to use application default credentials first
        try:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                'projectId': os.environ.get('FIRESTORE_PROJECT_ID', 'hamza-oc-chatbot'),
            })
        except Exception as credential_error:
            logging.warning(f"Could not use application default credentials: {credential_error}")
            # Fall back to using a local demo mode with a memory store for development
            firebase_admin.initialize_app()
    
    db = firestore.client()
    logging.info("Successfully connected to Firestore")
except Exception as e:
    logging.error(f"Error connecting to Firestore: {e}")
    # Set up an in-memory mock for development purposes
    class InMemoryDB:
        def __init__(self):
            self.data = {
                'chats': {},
                'messages': {}
            }
            logging.info("Initialized in-memory database")
        
        def collection(self, collection_name):
            return InMemoryCollection(self, collection_name)
    
    class InMemoryCollection:
        def __init__(self, db, collection_name):
            self.db = db
            self.collection_name = collection_name
        
        def document(self, doc_id):
            return InMemoryDocument(self.db, self.collection_name, doc_id)
        
        def order_by(self, field, direction=None):
            return self
        
        def stream(self):
            if self.collection_name == 'chats':
                docs = []
                for chat_id, chat_data in self.db.data['chats'].items():
                    docs.append(InMemoryDocSnapshot(chat_id, chat_data))
                return docs
            return []
    
    class InMemoryDocument:
        def __init__(self, db, collection_name, doc_id):
            self.db = db
            self.collection_name = collection_name
            self.id = doc_id
            
            # Initialize if not exists
            if collection_name not in self.db.data:
                self.db.data[collection_name] = {}
        
        def set(self, data):
            if self.collection_name == 'chats':
                self.db.data['chats'][self.id] = data
                # Initialize messages collection for this chat
                if self.id not in self.db.data['messages']:
                    self.db.data['messages'][self.id] = []
            else:
                # Handle message collections
                parent_id = self.collection_name.split('/')[1]  # Should be chat_id
                if parent_id not in self.db.data['messages']:
                    self.db.data['messages'][parent_id] = []
                
                # Add message with some default timestamp
                data['timestamp'] = datetime.datetime.now()
                self.db.data['messages'][parent_id].append({
                    'id': self.id,
                    **data
                })
        
        def get(self):
            # For chat document
            if self.collection_name == 'chats' and self.id in self.db.data['chats']:
                return InMemoryDocSnapshot(self.id, self.db.data['chats'][self.id])
            return InMemoryDocSnapshot(self.id, {})
        
        def update(self, data):
            if self.collection_name == 'chats' and self.id in self.db.data['chats']:
                self.db.data['chats'][self.id].update(data)
        
        def collection(self, subcollection_name):
            return InMemoryCollection(self.db, f"{self.collection_name}/{self.id}/{subcollection_name}")
    
    class InMemoryDocSnapshot:
        def __init__(self, doc_id, data):
            self.id = doc_id
            self._data = data
            self.exists = bool(data)
        
        def to_dict(self):
            return self._data
    
    # Create an instance of our in-memory database
    db = InMemoryDB()
    logging.warning("Using in-memory storage instead of Firestore")

@app.route('/')
def index():
    """Render the main page with a new chat ID."""
    # Generate a new chat ID if none exists
    if 'current_chat_id' not in session:
        session['current_chat_id'] = str(uuid.uuid4())
    
    return render_template('index.html', chat_id=session['current_chat_id'])

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages, create new chats, and process special modes."""
    data = request.json
    
    # Handle new chat creation
    if data.get('new_chat'):
        new_chat_id = str(uuid.uuid4())
        session['current_chat_id'] = new_chat_id
        
        # Create a new chat in Firestore
        if db:
            try:
                db.collection('chats').document(new_chat_id).set({
                    'name': 'Nouveau chat',
                    'created_at': FIRESTORE.SERVER_TIMESTAMP,
                    'ephemeral': False
                })
                logging.debug(f"Created new chat with ID: {new_chat_id}")
            except Exception as e:
                logging.error(f"Error creating new chat: {e}")
        
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
    
    # Store user message in Firestore
    if db and (message or has_image):
        try:
            message_ref = db.collection('chats').document(chat_id).collection('messages').document()
            message_ref.set({
                'content': message,
                'sender': 'user',
                'has_image': has_image,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            logging.error(f"Error storing user message: {e}")
    
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
    
    # Store bot response in Firestore
    if db and response:
        try:
            message_ref = db.collection('chats').document(chat_id).collection('messages').document()
            message_ref.set({
                'content': response,
                'sender': 'bot',
                'timestamp': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            logging.error(f"Error storing bot response: {e}")
    
    return jsonify({
        'response': response,
        'require_confirmation': require_confirmation
    })

@app.route('/chat_history', methods=['GET'])
def get_chat_history():
    """Retrieve the chat history for the current user."""
    if not db:
        return jsonify([])
    
    try:
        # Fetch chats from Firestore
        chats_ref = db.collection('chats')
        chats = chats_ref.order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        
        chat_list = []
        for chat in chats:
            chat_data = chat.to_dict()
            chat_list.append({
                'id': chat.id,
                'name': chat_data.get('name', 'Nouveau chat'),
                'created_at': chat_data.get('created_at'),
                'ephemeral': chat_data.get('ephemeral', False)
            })
        
        return jsonify(chat_list)
    except Exception as e:
        logging.error(f"Error fetching chat history: {e}")
        return jsonify([])

@app.route('/chat_messages', methods=['GET'])
def get_chat_messages():
    """Retrieve messages for a specific chat."""
    chat_id = request.args.get('chat_id')
    
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    
    if not db:
        return jsonify([])
    
    try:
        # Update current chat ID in session
        session['current_chat_id'] = chat_id
        
        # Fetch messages from Firestore
        messages_ref = db.collection('chats').document(chat_id).collection('messages')
        messages = messages_ref.order_by('timestamp').stream()
        
        message_list = []
        for message in messages:
            msg_data = message.to_dict()
            message_list.append({
                'id': message.id,
                'content': msg_data.get('content', ''),
                'sender': msg_data.get('sender', 'user'),
                'has_image': msg_data.get('has_image', False),
                'timestamp': msg_data.get('timestamp')
            })
        
        # Get chat info
        chat_ref = db.collection('chats').document(chat_id)
        chat = chat_ref.get()
        chat_data = chat.to_dict() if chat.exists else {}
        
        return jsonify({
            'messages': message_list,
            'chat': {
                'id': chat_id,
                'name': chat_data.get('name', 'Nouveau chat'),
                'ephemeral': chat_data.get('ephemeral', False)
            }
        })
    except Exception as e:
        logging.error(f"Error fetching chat messages: {e}")
        return jsonify({'messages': [], 'chat': {'id': chat_id, 'name': 'Nouveau chat', 'ephemeral': False}})

@app.route('/toggle_ephemeral', methods=['POST'])
def toggle_ephemeral():
    """Toggle ephemeral messages for a chat."""
    data = request.json
    chat_id = data.get('chat_id')
    
    if not chat_id:
        return jsonify({'error': 'No chat ID provided'}), 400
    
    if not db:
        return jsonify({'success': False})
    
    try:
        # Get current ephemeral status
        chat_ref = db.collection('chats').document(chat_id)
        chat = chat_ref.get()
        
        if chat.exists:
            chat_data = chat.to_dict()
            current_status = chat_data.get('ephemeral', False)
            
            # Toggle status
            chat_ref.update({
                'ephemeral': not current_status
            })
            
            return jsonify({
                'success': True,
                'ephemeral': not current_status
            })
        else:
            return jsonify({'error': 'Chat not found'}), 404
    except Exception as e:
        logging.error(f"Error toggling ephemeral status: {e}")
        return jsonify({'success': False})

@app.route('/rename_chat', methods=['POST'])
def rename_chat():
    """Rename a chat."""
    data = request.json
    chat_id = data.get('chat_id')
    new_name = data.get('name')
    
    if not chat_id or not new_name:
        return jsonify({'error': 'Missing chat ID or name'}), 400
    
    if not db:
        return jsonify({'success': False})
    
    try:
        # Update chat name in Firestore
        chat_ref = db.collection('chats').document(chat_id)
        chat_ref.update({
            'name': new_name
        })
        
        return jsonify({
            'success': True,
            'name': new_name
        })
    except Exception as e:
        logging.error(f"Error renaming chat: {e}")
        return jsonify({'success': False})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
