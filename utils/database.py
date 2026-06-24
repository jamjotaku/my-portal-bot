import os
import asyncio
import logging
from config import settings
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        self.client: Client = None
        self.app_user_id = None
        self._authenticate()

    def _authenticate(self):
        if not self.supabase_url or not self.supabase_key:
            logger.error("Supabase credentials not found in settings.")
            return

        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Successfully connected to Supabase.")
            
            try:
                users_response = self.client.auth.admin.list_users()
                users = getattr(users_response, 'users', users_response)
                if users and len(users) > 0:
                    self.app_user_id = users[0].id
                    logger.info(f"Supabase bound to user: {self.app_user_id}")
                else:
                    logger.error("No users found in Supabase Auth.")
            except Exception as e:
                logger.warning(f"Could not list admin users: {e}")
                
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")

    async def add_memo(self, content, tags):
        if not self.client or not self.app_user_id:
            return
        
        def _add():
            try:
                data = {
                    "user_id": self.app_user_id,
                    "content": content,
                    "tags": tags
                }
                self.client.table('memos').insert(data).execute()
            except Exception as e:
                logger.error(f"Error adding memo: {e}")
        await asyncio.to_thread(_add)

    async def add_bookmark(self, original_url, content, title, description, image_url, tags):
        if not self.client or not self.app_user_id:
            return
            
        def _add():
            try:
                data = {
                    "user_id": self.app_user_id,
                    "original_url": original_url,
                    "content": content,
                    "title": title,
                    "description": description,
                    "image_url": image_url,
                    "tags": tags
                }
                self.client.table('bookmarks').insert(data).execute()
            except Exception as e:
                logger.error(f"Error adding bookmark: {e}")
        await asyncio.to_thread(_add)
        
    async def update_discord_status(self, status, activity, vc_channel_name):
        if not self.client or not self.app_user_id:
            return
            
        def _update():
            try:
                data = {
                    "user_id": self.app_user_id,
                    "status": status,
                    "activity": activity,
                    "vc_channel_name": vc_channel_name
                }
                self.client.table('discord_status').upsert(data).execute()
            except Exception as e:
                logger.error(f"Error updating discord status: {e}")
        await asyncio.to_thread(_update)

    async def get_recent_memos(self, limit=5):
        if not self.client or not self.app_user_id:
            return []
        def _get():
            try:
                response = self.client.table('memos').select('*').eq('user_id', self.app_user_id).order('created_at', desc=True).limit(limit).execute()
                return response.data
            except Exception as e:
                logger.error(f"Error fetching memos: {e}")
                return []
        return await asyncio.to_thread(_get)

    async def get_recent_bookmarks(self, limit=5):
        if not self.client or not self.app_user_id:
            return []
        def _get():
            try:
                response = self.client.table('bookmarks').select('*').eq('user_id', self.app_user_id).order('created_at', desc=True).limit(limit).execute()
                return response.data
            except Exception as e:
                logger.error(f"Error fetching bookmarks: {e}")
                return []
        return await asyncio.to_thread(_get)

    async def add_mental_log(self, level: int):
        if not self.client or not self.app_user_id:
            return
            
        def _add():
            try:
                data = {
                    "user_id": self.app_user_id,
                    "level": level
                }
                self.client.table('mental_logs').insert(data).execute()
            except Exception as e:
                logger.error(f"Error adding mental log: {e}")
        await asyncio.to_thread(_add)

db = Database()
