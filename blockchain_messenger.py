import streamlit as st
import hashlib
import bcrypt
from datetime import datetime
from supabase import create_client

class BlockchainMessengerDB:
    def __init__(self):
        url = st.secrets["connections"]["supabase"]["url"]
        key = st.secrets["connections"]["supabase"]["key"]
        self.supabase = create_client(url, key)
        self.chain = []
        self.load_existing_chain()

    def register_user(self, username, password):
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            res = self.supabase.table("users1").insert({
                "username": username,
                "password_hash": password_hash
            }).execute()
            if res.data:
                return True, "Registration successful!"
            else:
                return False, "Username already exists."
        except Exception as e:
            return False, f"Error: {e}"

    def authenticate_user(self, username, password):
        try:
            res = self.supabase.table("users1").select("*").eq("username", username).execute()
            if not res.data:
                return False, None
            user = res.data[0]
            if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                return True, user
            else:
                return False, None
        except Exception as e:
            return False, None

    def get_latest_hash(self):
        if len(self.chain) == 0:
            return '0'
        return self.chain[-1]['hash']

    def send_message(self, sender_id, receiver_id, message_text):
        timestamp = datetime.now().isoformat()
        previous_hash = self.get_latest_hash()
        data_string = f"{sender_id}{receiver_id}{message_text}{timestamp}{previous_hash}"
        blockchain_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()

        try:
            res = self.supabase.table("messages").insert({
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "message_text": message_text,
                "sent_at": timestamp,
                "blockchain_hash": blockchain_hash,
                "previous_hash": previous_hash
            }).execute()

            if res.data:
                new_block = {
                    'index': len(self.chain),
                    'timestamp': timestamp,
                    'data': {
                        'sender_id': sender_id,
                        'receiver_id': receiver_id,
                        'message_text': message_text
                    },
                    'hash': blockchain_hash,
                    'previous_hash': previous_hash
                }
                self.chain.append(new_block)
                return True, "Message sent and recorded on blockchain."
            else:
                return False, "Failed to send message."
        except Exception as e:
            return False, f"Database error: {e}"

    def load_existing_chain(self):
        try:
            if len(self.chain) == 0:
                self.create_genesis_block()
            res = self.supabase.table("messages").select("*").order("id").execute()
            if res.data:
                genesis = self.chain[0] if self.chain else None
                self.chain = []
                if genesis:
                    self.chain.append(genesis)
                else:
                    self.create_genesis_block()
                for row in res.data:
                    block = {
                        'index': len(self.chain),
                        'timestamp': row['sent_at'],
                        'data': {
                            'sender_id': row['sender_id'],
                            'receiver_id': row['receiver_id'],
                            'message_text': row['message_text'],
                        },
                        'hash': row['blockchain_hash'],
                        'previous_hash': row['previous_hash']
                    }
                    self.chain.append(block)
        except Exception as e:
            print(f"Error loading chain: {e}")
            self.chain = []
            self.create_genesis_block()

    def create_genesis_block(self):
        if len(self.chain) > 0:
            return
        timestamp = datetime.now().isoformat()
        genesis_data = 'Genesis Block - Secure Messaging System'
        genesis_hash = hashlib.sha256(f"genesis{timestamp}".encode('utf-8')).hexdigest()
        genesis_block = {
            'index': 0,
            'timestamp': timestamp,
            'data': genesis_data,
            'previous_hash': '0',
            'hash': genesis_hash,
        }
        self.chain.append(genesis_block)

    def verify_blockchain_integrity(self):
        self.load_existing_chain()
        if len(self.chain) <= 1:
            return True, f"Blockchain has {len(self.chain)} block(s). Genesis only or empty."
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i-1]
            if isinstance(curr['data'], dict):
                data_string = f"{curr['data']['sender_id']}{curr['data']['receiver_id']}{curr['data']['message_text']}{curr['timestamp']}{prev['hash']}"
                recomputed_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
            else:
                continue
            if curr['hash'] != recomputed_hash:
                return False, f"Invalid hash at block {i}. Data inconsistency detected."
            if curr['previous_hash'] != prev['hash']:
                return False, f"Broken chain link at block {i}"
        return True, f"Blockchain is valid with {len(self.chain)} blocks."

    def get_all_messages_for_user(self, user_id):
        try:
            res = self.supabase.table("messages").select("*").or_(
                f"sender_id.eq.{user_id},receiver_id.eq.{user_id}"
            ).order("sent_at", desc=True).execute()
            return res.data if res.data else []
        except Exception as e:
            return []

    def get_user_by_username(self, username):
        try:
            res = self.supabase.table("users1").select("*").eq("username", username).execute()
            return res.data[0] if res.data else None
        except:
            return None

    def get_all_users_count(self):
        try:
            res = self.supabase.table("users1").select("id").execute()
            return len(res.data) if res.data else 0
        except:
            return 0

    def get_total_messages_count(self):
        try:
            res = self.supabase.table("messages").select("id").execute()
            return len(res.data) if res.data else 0
        except:
            return 0

    # def debug_blockchain(self):
    #     print(f"Chain length: {len(self.chain)}")
    #     for i, block in enumerate(self.chain):
    #         print(f"Block {i}:")
    #         print(f"  Index: {block['index']}")
    #         print(f"  Data: {block['data']}")
    #         print(f"  Hash: {block['hash']}")
    #         print(f"  Previous Hash: {block['previous_hash']}")
    #         print(f"  Timestamp: {block['timestamp']}")
    #         print("---")
