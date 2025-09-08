import streamlit as st
from supabase import create_client
import bcrypt
import hashlib
import json
import datetime
import sqlite3
import os

class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.compute_hash()
    
    def compute_hash(self):
        block_string = json.dumps({
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def to_dict(self):
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'data': self.data,
            'previous_hash': self.previous_hash,
            'hash': self.hash
        }

class BlockchainMessengerDB:
    def __init__(self):
        # Initialize Supabase connection
        url = st.secrets['connections']['supabase']['url']
        key = st.secrets['connections']['supabase']['key']
        self.supabase = create_client(url, key)
        
        # Initialize blockchain
        self.chain = []
        self.blockchain_file = 'blockchain_data.db'
        self.init_local_blockchain()
        self.load_existing_chain()
    
    def init_local_blockchain(self):
        # Initialize local SQLite database for blockchain storage
        conn = sqlite3.connect(self.blockchain_file)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blockchain_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_index INTEGER,
                timestamp TEXT,
                data TEXT,
                previous_hash TEXT,
                hash TEXT,
                UNIQUE(block_index)
            )
        ''')
        conn.commit()
        conn.close()
    
    def create_genesis_block(self):
        # Create the first block in the blockchain
        genesis_block = Block(0, datetime.datetime.now().isoformat(), 'Genesis Block', '0')
        return genesis_block
    
    def get_latest_block(self):
        # Get the most recent block in the chain
        if len(self.chain) == 0:
            return self.create_genesis_block()
        return self.chain[-1]
    
    def add_block_to_chain(self, data):
        # Add a new block to the blockchain
        previous_block = self.get_latest_block()
        new_index = previous_block.index + 1
        new_timestamp = datetime.datetime.now().isoformat()
        new_block = Block(new_index, new_timestamp, data, previous_block.hash)
        
        # Add to memory chain
        self.chain.append(new_block)
        
        # Store in local database
        conn = sqlite3.connect(self.blockchain_file)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO blockchain_log (block_index, timestamp, data, previous_hash, hash) VALUES (?, ?, ?, ?, ?)
            ''', (new_block.index, new_block.timestamp, new_block.data, new_block.previous_hash, new_block.hash))
            conn.commit()
        except Exception as e:
            st.error(f"Error storing block: {e}")
        finally:
            conn.close()
        
        return new_block
    
    def load_existing_chain(self):
        # Load blockchain from local database
        conn = sqlite3.connect(self.blockchain_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM blockchain_log ORDER BY block_index')
        rows = cursor.fetchall()
        conn.close()
        
        self.chain = []
        if not rows:
            # No existing chain, create genesis block
            genesis = self.create_genesis_block()
            self.chain.append(genesis)
            self.save_block_to_db(genesis)
        else:
            # Load existing blocks
            for row in rows:
                block = Block(row[1], row[2], row[3], row[4])
                block.hash = row[5]  # Use stored hash
                self.chain.append(block)
    
    def save_block_to_db(self, block):
        # Save a single block to database
        conn = sqlite3.connect(self.blockchain_file)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO blockchain_log (block_index, timestamp, data, previous_hash, hash) VALUES (?, ?, ?, ?, ?)
            ''', (block.index, block.timestamp, block.data, block.previous_hash, block.hash))
            conn.commit()
        except Exception as e:
            st.error(f"Error saving block: {e}")
        finally:
            conn.close()
    
    def verify_blockchain_integrity(self):
        # Verify the integrity of the entire blockchain
        if len(self.chain) <= 1:
            return True, "Blockchain has 1 block(s). Genesis only or empty."
        
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Verify current block's hash
            if current_block.hash != current_block.compute_hash():
                return False, f"Invalid hash at block {i}. Data inconsistency detected."
            
            # Verify link to previous block
            if current_block.previous_hash != previous_block.hash:
                return False, f"Invalid hash chain at block {i}. Link broken."
        
        return True, "Blockchain integrity verified successfully!"
    
    def debug_blockchain(self):
        # Debug blockchain information
        st.write(f"Chain length: {len(self.chain)}")
        for block in self.chain:
            st.json(block.to_dict())
    
    # User-related methods (registration, authentication, user queries)
    def register_user(self, username, password):
        try:
            existing = self.supabase.table('users1').select('*').eq('username', username).execute()
            if existing.data:
                return False, 'Username already exists!'
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            user_data = {
                'username': username,
                'password_hash': hashed.decode()
            }
            res = self.supabase.table('users1').insert(user_data).execute()
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
            else:
                return False, None
        except Exception as e:
            return False, None
    
    def get_user_by_username(self, username):
        try:
            res = self.supabase.table('users1').select('*').eq('username', username).execute()
            return res.data[0] if res.data else None
        except:
            return None
    
    # Messaging methods
    def send_message(self, sender_id, receiver_id, message_text):
        try:
            message_data = {
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'message_text': message_text,
                'sent_at': datetime.datetime.utcnow().isoformat()
            }
            message_json = json.dumps(message_data)
            new_block = self.add_block_to_chain(message_json)
            res = self.supabase.table('messages').insert({
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'message_text': message_text,
                'sent_at': message_data['sent_at'],
                'blockchain_hash': new_block.hash
            }).execute()
            if res.error:
                return False, res.error.message
            return True, 'Message sent and added to blockchain'
        except Exception as e:
            return False, str(e)
    
    def get_all_messages_for_user(self, user_id):
        try:
            res = self.supabase.table('messages').select('*').or_(
                f'sender_id.eq.{user_id},receiver_id.eq.{user_id}'
            ).order('sent_at', desc=True).execute()
            if res.error:
                return []
            return res.data
        except Exception:
            return []
    
    # Statistics methods
    def get_total_messages_count(self):
        try:
            res = self.supabase.table('messages').select('id', count='exact').execute()
            if res.error:
                return 0
            return res.count
        except Exception:
            return 0
    
    def get_all_users_count(self):
        try:
            res = self.supabase.table('users1').select('id', count='exact').execute()
            if res.error:
                return 0
            return res.count
        except Exception:
            return 0
