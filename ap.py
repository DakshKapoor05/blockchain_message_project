import streamlit as st
from blockchain_messenger import BlockchainMessengerDB
import time

st.set_page_config(
    page_title="🔐 Blockchain Messenger",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def init_db():
    return BlockchainMessengerDB()

def login(db):
    st.subheader("🔑 Login to Your Account")
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("👤 Username", placeholder="Enter your username", key="login_username")
        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_password")
        submitted = st.form_submit_button("🚀 Login", use_container_width=True)
        if submitted:
            if username and password:
                ok, user = db.authenticate_user(username, password)
                if ok:
                    st.session_state["logged_in"] = True
                    st.session_state["user"] = user
                    st.success(f"✅ Welcome back, {username}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password!")
            else:
                st.warning("⚠️ Please enter both username and password")
    with st.expander("🎮 Demo Credentials", expanded=False):
        st.markdown("""
        **Demo Account 1:**
        - Username: `user1`  
        - Password: `pass123`
        **Demo Account 2:**
        - Username: `user2`
        - Password: `pass456`
        *Use these to test the blockchain messaging system!*
        """)

def register(db):
    st.subheader("📝 Create New Account")
    st.markdown("💡 **Tip:** You can also use the demo accounts `user1` and `user2` with password `pass123` and `pass456`")
    with st.form("register_form", clear_on_submit=False):
        username = st.text_input("👤 Choose Username", placeholder="Enter a unique username", key="register_username")
        password1 = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="register_password1")
        password2 = st.text_input("🔒 Confirm Password", type="password", placeholder="Re-enter your password", key="register_password2")
        submitted = st.form_submit_button("📝 Register", use_container_width=True)
        if submitted:
            if not username or not password1 or not password2:
                st.warning("⚠️ All fields are required!")
            elif password1 != password2:
                st.error("❌ Passwords do not match!")
            elif len(password1) < 4:
                st.error("❌ Password must be at least 4 characters long!")
            else:
                ok, msg = db.register_user(username, password1)
                if ok:
                    st.success(f"✅ {msg}")
                    st.markdown("🎉 You can now login with your credentials!")
                else:
                    st.error(f"❌ {msg}")

def messaging(db):
    user = st.session_state["user"]
    st.sidebar.title("Navigation")
    st.sidebar.write(f"**👤 Logged in as:** {user['username']}")
    if st.sidebar.button("🚪 Logout", use_container_width=True, key="logout_button"):
        for key in ["logged_in", "user", "page"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    st.title(f"💬 Welcome, {user['username']}!")
    tab1, tab2, tab3 = st.tabs(["📤 Send Message", "📥 Inbox", "⛓️ Blockchain Stats"])
    
    with tab1:
        st.subheader("📤 Send New Message")
        with st.form("send_message_form", clear_on_submit=True):
            receiver = st.text_input("📮 Send to (username)", placeholder="Enter recipient's username", key="msg_receiver")
            message = st.text_area("💬 Your Message", placeholder="Type your message here...", height=150, key="msg_content")
            sent = st.form_submit_button("📨 Send Message", use_container_width=True)
            if sent:
                if not receiver or not message:
                    st.warning("⚠️ Please enter both recipient and message!")
                else:
                    receiver_user = db.get_user_by_username(receiver)
                    if not receiver_user:
                        st.error("❌ Recipient user not found!")
                    elif receiver_user["id"] == user["id"]:
                        st.error("❌ You cannot send a message to yourself!")
                    else:
                        ok, msg = db.send_message(user["id"], receiver_user["id"], message)
                        if ok:
                            st.success(f"✅ {msg}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
    
    with tab2:
        st.subheader("📥 Your Messages")
        messages = db.get_all_messages_for_user(user["id"])
        if messages:
            for m in messages:
                sender_user = db.supabase.table("users1").select("username").eq("id", m["sender_id"]).execute()
                receiver_user = db.supabase.table("users1").select("username").eq("id", m["receiver_id"]).execute()
                sender_name = sender_user.data[0]["username"] if sender_user.data else "Unknown"
                receiver_name = receiver_user.data[0]["username"] if receiver_user.data else "Unknown"
                if m["sender_id"] == user["id"]:
                    direction = f"📤 **You** → {receiver_name}"
                    st.markdown(f'<div style="background-color: #f1f5f9; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 3px solid #0ea5e9;">', unsafe_allow_html=True)
                else:
                    direction = f"📥 **{sender_name}** → You"
                    st.markdown(f'<div style="background-color: #f0fdf4; padding: 15px; border-radius: 8px; margin: 10px 0; border-left: 3px solid #22c55e;">', unsafe_allow_html=True)
                st.markdown(f"**{direction}**")
                st.write(f"💬 {m['message_text']}")
                st.caption(f"🕒 {m['sent_at'][:19]} | 🔗 Hash: {m['blockchain_hash'][:16]}...")
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.markdown("📭 No messages found. Start a conversation!")
    
    with tab3:
        st.subheader("⛓️ Blockchain Statistics")
        db.load_existing_chain()
        col1, col2, col3 = st.columns(3)
        with col1:
            total_messages = db.get_total_messages_count()
            st.metric("📨 Total Messages", total_messages)
        with col2:
            st.metric("⛓️ Blockchain Blocks", len(db.chain))
        with col3:
            total_users = db.get_all_users_count()
            st.metric("👥 Total Users", total_users)
        
        col4, col5 = st.columns([1, 1])
        with col4:
            verify_clicked = st.button("🔍 Verify Blockchain Integrity", key="verify_blockchain_btn", use_container_width=True)
            if verify_clicked:
                with st.spinner("Verifying blockchain..."):
                    db.load_existing_chain()
                    is_valid, message = db.verify_blockchain_integrity()
                    if is_valid:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
        
        if len(db.chain) > 0:
            st.subheader("🔗 Recent Blockchain Blocks")
            recent_blocks = db.chain[-3:] if len(db.chain) > 3 else db.chain
            for block in reversed(recent_blocks):
                with st.expander(f"Block #{block['index']} - {block['timestamp'][:19]}"):
                    st.json({
                        "Index": block['index'],
                        "Timestamp": block['timestamp'],
                        "Data": block['data'],
                        "Hash": block['hash'],
                        "Previous Hash": block['previous_hash']
                    })

def main():
    st.markdown("""
    <style>
    body {
        font-family: "Segoe UI", sans-serif;
        background-color: #fafbfc;
    }
    .stButton > button {
        background-color: #1f2937 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        transition: background-color 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #374151 !important;
    }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 1px solid #d1d5db !important;
        border-radius: 6px !important;
        padding: 0.75rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #1f2937 !important;
        outline: none !important;
    }
    [data-testid="metric-container"] {
        background: white !important;
        border: 1px solid #e5e7eb !important;
        border-radius: 8px !important;
        padding: 1rem !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1) !important;
    }
    div[data-testid="stHorizontalBlock"] > div {
        gap: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    db = init_db()
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "page" not in st.session_state:
        st.session_state["page"] = "login"
    if not st.session_state["logged_in"]:
        st.title("🔐 Secure Blockchain Messaging")
        st.markdown("### Send encrypted messages with blockchain verification")
        st.markdown("---")
        col1, col2, col3 = st.columns([1.2, 1.2, 5.6])
        with col1:
            if st.button("Login", type="primary" if st.session_state["page"] == "login" else "secondary", key="main_login_btn"):
                st.session_state["page"] = "login"
                st.rerun()
        with col2:
            if st.button("Register", type="primary" if st.session_state["page"] == "register" else "secondary", key="main_register_btn"):
                st.session_state["page"] = "register"
                st.rerun()
        st.markdown("---")
        if st.session_state["page"] == "login":
            login(db)
        else:
            register(db)
    else:
        messaging(db)

if __name__ == "__main__":
    main()
