import streamlit as st
from supabase import create_client
import bcrypt
import hashlib
import json
import datetime
import sqlite3

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
        url = st.secrets['connections']['supabase']['url']
        key = st.secrets['connections']['supabase']['key']
        self.supabase = create_client(url, key)
        self.chain = []
        self.blockchain_file = 'blockchain_data.db'
        self.init_local_blockchain()
        self.load_existing_chain()

    def init_local_blockchain(self):
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
        genesis_block = Block(0, datetime.datetime.now().isoformat(), 'Genesis Block', '0')
        return genesis_block

    def get_latest_block(self):
        if len(self.chain) == 0:
            return self.create_genesis_block()
        return self.chain[-1]

    def add_block_to_chain(self, data):
        previous_block = self.get_latest_block()
        new_index = previous_block.index + 1
        new_timestamp = datetime.datetime.now().isoformat()
        new_block = Block(new_index, new_timestamp, data, previous_block.hash)
        self.chain.append(new_block)
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
        conn = sqlite3.connect(self.blockchain_file)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM blockchain_log ORDER BY block_index')
        rows = cursor.fetchall()
        conn.close()
        self.chain = []
        if not rows:
            genesis = self.create_genesis_block()
            self.chain.append(genesis)
            self.save_block_to_db(genesis)
        else:
            for row in rows:
                block = Block(row[1], row[2], row[3], row[4])
                block.hash = row[5]
                self.chain.append(block)

    def save_block_to_db(self, block):
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
        if len(self.chain) <= 1:
            return True, "Blockchain has 1 block(s). Genesis only or empty."
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            if current_block.hash != current_block.compute_hash():
                return False, f"Invalid hash at block {i}. Data inconsistency detected."
            if current_block.previous_hash != previous_block.hash:
                return False, f"Invalid hash chain at block {i}. Link broken."
        return True, "Blockchain integrity verified successfully!"

    def debug_blockchain(self):
        st.write(f"Chain length: {len(self.chain)}")
        for block in self.chain:
            st.json(block.to_dict())

    def register_user(self, username, password):
        try:
            existing = self.supabase.table('users1').select('*').eq('username', username).execute()
            if existing.data:
                return False, 'Username already exists!'
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            user_data = {'username': username, 'password_hash': hashed.decode()}
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
        except Exception:
            return False, None

    def get_user_by_username(self, username):
        try:
            res = self.supabase.table('users1').select('*').eq('username', username).execute()
            return res.data[0] if res.data else None
        except:
            return None

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
                'blockchain_hash': new_block.hash,
                'previous_hash': new_block.previous_hash
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
        if hasattr(res, 'count') and res.count is not None:
            return res.count
        if hasattr(res, 'data') and res.data:
            return len(res.data)
        return 0
    except Exception as e:
        st.error(f"Error fetching total messages count: {e}")
        return 0


    def get_all_users_count(self):
    try:
        res = self.supabase.table('users1').select('id', count='exact').execute()
        if hasattr(res, 'count') and res.count is not None:
            return res.count
        if hasattr(res, 'data') and res.data:
            return len(res.data)
        return 0
    except Exception as e:
        st.error(f"Error fetching total users count: {e}")
        return 0

