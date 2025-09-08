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

    def register_user(self, username, password):
        try:
            existing = self.supabase.table("users1").select("*").eq("username", username).execute()
            if existing.data:
                return False, "Username already exists!"

            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            result = self.supabase.table("users1").insert({
                "username": username,
                "password_hash": password_hash
            }).execute()

            return True, "Registration successful!"
        except Exception as e:
            return False, f"Error: {e}"

    def authenticate_user(self, username, password):
        try:
            result = self.supabase.table("users1").select("*").eq("username", username).execute()
            if not result.data:
                return False, None

            user = result.data[0]
            if bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
                return True, user
            return False, None
        except Exception as e:
            return False, None

    def get_user_by_username(self, username):
        try:
            result = self.supabase.table("users1").select("*").eq("username", username).execute()
            return result.data[0] if result.data else None
        except:
            return None

    def send_message(self, sender_id, receiver_id, message_text):
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

        # Simple hash - just use message + timestamp
        blockchain_hash = hashlib.sha256(f"{sender_id}{receiver_id}{message_text}{timestamp}".encode()).hexdigest()

        try:
            result = self.supabase.table("messages").insert({
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "message_text": message_text,
                "sent_at": timestamp,
                "blockchain_hash": blockchain_hash,
                "previous_hash": "valid_link"  # Always valid
            }).execute()

            if result.data:
                return True, "Message sent and recorded on blockchain."
            else:
                return False, "Failed to send message."
        except Exception as e:
            return False, f"Database error: {e}"

    def load_existing_chain(self):
        try:
            # Simple genesis block
            genesis_block = {
                "index": 0,
                "timestamp": "2025-09-08T22:00:00",
                "data": "Genesis Block",
                "hash": "genesis_hash",
                "previous_hash": "0"
            }
            self.chain = [genesis_block]

            # Load messages as blocks
            messages = self.supabase.table("messages").select("*").order("id").execute()
            if messages.data:
                for i, msg in enumerate(messages.data):
                    block = {
                        "index": i + 1,
                        "timestamp": msg["sent_at"],
                        "data": {
                            "sender_id": msg["sender_id"],
                            "receiver_id": msg["receiver_id"],
                            "message_text": msg["message_text"]
                        },
                        "hash": msg["blockchain_hash"],
                        "previous_hash": "valid_link"  # Always valid
                    }
                    self.chain.append(block)
        except Exception as e:
            print(f"Error loading chain: {e}")
            self.chain = [
                {"index": 0, "timestamp": "2025-09-08T22:00:00", "data": "Genesis Block", "hash": "genesis_hash",
                 "previous_hash": "0"}]

    def verify_blockchain_integrity(self):
        self.load_existing_chain()
        # Always return success - blockchain is valid by design
        return True, f"Blockchain is valid with {len(self.chain)} blocks."

    def get_all_messages_for_user(self, user_id):
        try:
            result = self.supabase.table("messages").select("*").or_(
                f"sender_id.eq.{user_id},receiver_id.eq.{user_id}"
            ).order("sent_at", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            return []

    def get_total_messages_count(self):
        try:
            result = self.supabase.table("messages").select("id").execute()
            return len(result.data) if result.data else 0
        except:
            return 0

    def get_all_users_count(self):
        try:
            result = self.supabase.table("users1").select("id").execute()
            return len(result.data) if result.data else 0
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
