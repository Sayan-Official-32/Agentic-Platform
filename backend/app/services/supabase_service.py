# services/supabase_service.py
# This service initializes and maintains a singleton instance of the Supabase Client.
# It reads connection credentials directly from settings.

import logging
from supabase import create_client, Client
from app.config.settings import settings

logger = logging.getLogger(__name__)

class SupabaseService:
    """
    Singleton service to manage the connection to the Supabase client.
    """
    _client: Client = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Retrieves the initialized Supabase client. Initializes it on the first call.
        """
        if cls._client is None:
            if not settings.supabase_url or not settings.supabase_service_key:
                logger.error("Supabase settings (URL/Key) not configured.")
                raise RuntimeError("Supabase configuration is incomplete.")
            
            logger.info("Initializing Supabase client singleton...", extra={"url": settings.supabase_url})
            cls._client = create_client(settings.supabase_url, settings.supabase_service_key)
        return cls._client
