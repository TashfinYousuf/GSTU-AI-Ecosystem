from auth_manager import supabase

def get_user_sessions(user_id):
    """ইউজারের সব চ্যাট থ্রেড/সেশন ফেচ করবে (Sidebar-এ দেখানোর জন্য)"""
    try:
        response = supabase.table('chat_sessions').select('*').eq('user_id', user_id).order('last_active', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return []

def get_session_messages(session_id):
    """নির্দিষ্ট সেশনের সব মেসেজ ফেচ করবে (Chat UI-তে দেখানোর জন্য)"""
    try:
        response = supabase.table('chat_history').select('message_role, content').eq('session_id', session_id).order('created_at', desc=False).execute()
        # Streamlit-এর ফরম্যাটে ডেটা কনভার্ট করা
        return [{"role": msg['message_role'], "content": msg['content']} for msg in response.data]
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return []

def create_new_session(user_id, title, agent_type='gstu_ir'):
    """নতুন চ্যাট শুরু করলে ডাটাবেসে নতুন সেশন তৈরি করবে"""
    try:
        response = supabase.table('chat_sessions').insert({
            'user_id': user_id,
            'title': title,
            'agent_type': agent_type
        }).execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        print(f"Error creating session: {e}")
        return None

def save_message_to_cloud(session_id, role, content, metadata=None):
    """AI বা User-এর মেসেজ রিয়েল-টাইমে Supabase-এ সেভ করবে"""
    if not session_id:
        return
    try:
        supabase.table('chat_history').insert({
            'session_id': session_id,
            'message_role': role,
            'content': content,
            'metadata': metadata or {}
        }).execute()
        
        # সেশনের last_active টাইম আপডেট করা
        supabase.table('chat_sessions').update({'last_active': 'now()'}).eq('id', session_id).execute()
    except Exception as e:
        print(f"Error saving message: {e}")