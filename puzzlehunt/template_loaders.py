import redis
from django.template.loaders.cached import Loader as CachedLoader
from django.template.exceptions import TemplateDoesNotExist
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class RedisVersionedLoader(CachedLoader):
    """
    A template loader that extends Django's cached template loader but stores
    template versions in Redis to allow for template cache invalidation.
    
    This loader adds a version number from Redis to the cache key, so that
    when the version is incremented, all cached templates will be reloaded.
    """
    
    def __init__(self, engine, loaders):
        """
        Initialize the loader with the given engine and loaders.
        
        Args:
            engine: The template engine instance
            loaders: A list of template loaders to use
        """
        super().__init__(engine, loaders)
        self.version_prefix = getattr(settings, 'TEMPLATE_VERSION_PREFIX', 'template_version:')
        
        # Initialize Redis client
        try:
            redis_url = settings.CACHES['default']['LOCATION']
            self.redis_client = redis.from_url(redis_url)
            logger.debug(f"RedisVersionedLoader initialized with Redis URL: {redis_url}")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis client for template versioning: {e}")
            self.redis_client = None
    
    def cache_key(self, template_name, skip=None):
        """
        Generate a cache key for the template name and skip.
        Includes the template version in the key to support cache invalidation.
        """
        # Get the base cache key from the parent class
        base_key = super().cache_key(template_name, skip)
        
        # Get version from Redis
        version = 1
        if self.redis_client:
            try:
                key = f"{self.version_prefix}{template_name}"
                stored_version = self.redis_client.get(key)
                if stored_version:
                    version = int(stored_version)
                else:
                    # Initialize the version in Redis if it doesn't exist
                    self.redis_client.set(key, version)
                    logger.debug(f"Created initial version for '{template_name}': {version}")
            except Exception as e:
                logger.warning(f"Error getting template version: {e}")
        
        # Return key with version
        return f"{base_key}-v{version}"
    
    def increment_template_version(self, template_name):
        """
        Increment the version for a specific template.
        This invalidates the cache for that template.
        
        Args:
            template_name: The name of the template to invalidate
        """
        if not self.redis_client:
            logger.warning("Redis client not available, cannot invalidate template cache")
            return
        
        try:
            key = f"{self.version_prefix}{template_name}"
            new_version = self.redis_client.incr(key)
            logger.debug(f"Invalidated template '{template_name}', new version: {new_version}")
        except Exception as e:
            logger.warning(f"Error incrementing template version: {e}")

    