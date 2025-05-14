# This file is not actively used in this application as we're using Firestore
# It's included to maintain compatibility with the Flask app structure

class Chat:
    def __init__(self, id, name, created_at, ephemeral=False):
        self.id = id
        self.name = name
        self.created_at = created_at
        self.ephemeral = ephemeral
        
class Message:
    def __init__(self, id, chat_id, content, sender, timestamp, has_image=False):
        self.id = id
        self.chat_id = chat_id
        self.content = content
        self.sender = sender  # 'user' or 'bot'
        self.timestamp = timestamp
        self.has_image = has_image
