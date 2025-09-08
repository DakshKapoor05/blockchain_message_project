import streamlit as st
from supabase import create_client
import bcrypt
import hashlib
import json
import datetime

class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.compute_hash()
    
    def compute_hash(self):
        block_string = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}"
        return hashlib.sha256(block_string.encode()).hexdigest()

class BlockchainMessengerDB:
    def __init__(self):
        url = st.secrets['connections']['supabase']['url']
        key = st.secrets['connections']['supabase']['key']
        self.supabase = create_client(url, key)
        self.chain = []
        self.load_existing_chain()
    
    def create_genesis_block(self):
        return Block(0, datetime.datetime.now().isoformat(), "Genesis Block", "0")
    
    def get_latest_block(self):
        if len(self.chain) == 0:
            return self.create_genesis_block()
        return self.chain[-1]
    
    def add_block_to_chain(self, data):
        previous_block = self.get_latest_block()
        new_block = Block(
            previous_block.index + 1,
            datetime.datetime.now().isoformat(),
            data,
            previous_block.hash
        )
        self.chain.append(new_block)
        return new_block
    
    def load_existing_chain(self):
        # Start with fresh genesis block
        genesis = self.create_genesis_block()
        self.chain = [genesis]
    
    def verify_blockchain_integrity(self):
        if len(self.chain) <= 1:
            return True, "Blockchain has 1 block(s). Genesis only or empty."
        
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Check if current block's hash is valid
            if current_block.hash != current_block.compute_hash():
                return False, f"Invalid hash at block {i}. Data inconsistency detected."
            
            # Check if previous hash is correct
            if current_block.previous_hash != previous_block.hash:
                return False, f"Invalid previous hash at block {i}."
        
        return True, "Blockchain integrity verified successfully!"
    
    def debug_blockchain(self):
        st.write(f"Chain length: {len(self.chain)}")
        for i, block in enumerate(self.chain):
            st.write(f"Block {i}: hash={block.hash[:16]}..., prev={block.previous_hash[:16]}...")
    
    # User methods
    def register_user(self, username, password):
        try:
            existing = self.supabase.table('users1').select('*').eq('username', username).execute()
            if existing.data:
                return False, 'Username already exists!'
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            res = self.supabase.table('users1').insert({
                'username': username,
                'password_hash': hashed.decode()
            }).execute()
            return True, 'User registered successfully'
        except Exception as e:
            return False, f'Registration failed: {e}'
    
    def authenticate_user(self, username, password):
        try:
            res = self.supabase.table('users1').select('*').eq('username', username).execute()
            if not res.data:
                return False, None
            user = res.data[0]
            if bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
                return True, user
            return False, None
        except:
            return False, None
    
    def get_user_by_username(self, username):
        try:
            res = self.supabase.table('users1').select('*').eq('username', username).execute()
            return res.data[0] if res.data else None
        except:
            return None
    
    def send_message(self, sender_id, receiver_id, message_text):
        try:
            message_data = f"From {sender_id} to {receiver_id}: {message_text}"
            new_block = self.add_block_to_chain(message_data)
            
            res = self.supabase.table('messages').insert({
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'message_text': message_text,
                'blockchain_hash': new_block.hash
            }).execute()
            
            return True, 'Message sent and added to blockchain'
        except Exception as e:
            return False, str(e)
    
    def get_all_messages_for_user(self, user_id):
        try:
            res = self.supabase.table('messages').select('*').or_(
                f'sender_id.eq.{user_id},receiver_id.eq.{user_id}'
            ).order('sent_at', desc=True).execute()
            return res.data if res.data else []
        except:
            return []
    
    def get_total_messages_count(self):
        try:
            res = self.supabase.table('messages').select('id', count='exact').execute()
            return res.count if res.count else 0
        except:
            return 0
    
    def get_all_users_count(self):
        try:
            res = self.supabase.table('users1').select('id', count='exact').execute()
            return res.count if res.count else 0
        except:
            return 0
