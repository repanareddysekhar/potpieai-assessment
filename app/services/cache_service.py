"""
Cache service for storing and retrieving API results.
"""
import json
import hashlib
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

import redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheService:
    """Service for caching API results using Redis."""
    
    def __init__(self):
        """Initialize the cache service."""
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        self.default_ttl = 3600  # 1 hour default TTL
        
    def _generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate a cache key from parameters."""
        # Create a consistent string from the parameters
        param_string = json.dumps(kwargs, sort_keys=True)
        # Hash it to create a consistent key
        param_hash = hashlib.md5(param_string.encode()).hexdigest()
        return f"{prefix}:{param_hash}"
    
    def get_pr_analysis_cache_key(self, repo_url: str, pr_number: int) -> str:
        """Generate cache key for PR analysis results."""
        return self._generate_cache_key("pr_analysis", repo_url=repo_url, pr_number=pr_number)
    
    def get_pr_data_cache_key(self, repo_url: str, pr_number: int) -> str:
        """Generate cache key for PR data."""
        return self._generate_cache_key("pr_data", repo_url=repo_url, pr_number=pr_number)
    
    def get_file_analysis_cache_key(self, repo_url: str, pr_number: int, file_path: str, file_sha: str) -> str:
        """Generate cache key for individual file analysis."""
        return self._generate_cache_key(
            "file_analysis", 
            repo_url=repo_url, 
            pr_number=pr_number, 
            file_path=file_path,
            file_sha=file_sha
        )
    
    def set_cache(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set a value in cache with optional TTL."""
        try:
            ttl = ttl or self.default_ttl
            serialized_value = json.dumps(value, default=str)
            
            result = self.redis_client.setex(key, ttl, serialized_value)
            
            logger.info("Cache set successfully",
                       cache_key=key,
                       ttl_seconds=ttl,
                       value_size=len(serialized_value))
            
            return result
            
        except Exception as e:
            logger.error("Failed to set cache",
                        cache_key=key,
                        error=str(e))
            return False
    
    def get_cache(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        try:
            cached_value = self.redis_client.get(key)
            
            if cached_value is None:
                logger.info("Cache miss", cache_key=key)
                return None
            
            deserialized_value = json.loads(cached_value)
            
            logger.info("Cache hit", cache_key=key)
            return deserialized_value
            
        except Exception as e:
            logger.error("Failed to get cache",
                        cache_key=key,
                        error=str(e))
            return None
    
    def delete_cache(self, key: str) -> bool:
        """Delete a value from cache."""
        try:
            result = self.redis_client.delete(key)
            
            logger.info("Cache deleted",
                       cache_key=key,
                       existed=bool(result))
            
            return bool(result)
            
        except Exception as e:
            logger.error("Failed to delete cache",
                        cache_key=key,
                        error=str(e))
            return False
    
    def get_cache_ttl(self, key: str) -> Optional[int]:
        """Get the TTL of a cached value."""
        try:
            ttl = self.redis_client.ttl(key)
            
            if ttl == -2:  # Key doesn't exist
                return None
            elif ttl == -1:  # Key exists but has no TTL
                return -1
            else:
                return ttl
                
        except Exception as e:
            logger.error("Failed to get cache TTL",
                        cache_key=key,
                        error=str(e))
            return None
    
    def cache_pr_analysis_result(self, repo_url: str, pr_number: int, result: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache PR analysis result."""
        cache_key = self.get_pr_analysis_cache_key(repo_url, pr_number)
        
        # Add cache metadata
        cached_result = {
            "result": result,
            "cached_at": datetime.utcnow().isoformat(),
            "repo_url": repo_url,
            "pr_number": pr_number
        }
        
        return self.set_cache(cache_key, cached_result, ttl)
    
    def get_cached_pr_analysis_result(self, repo_url: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """Get cached PR analysis result."""
        cache_key = self.get_pr_analysis_cache_key(repo_url, pr_number)
        cached_data = self.get_cache(cache_key)
        
        if cached_data:
            logger.info("Retrieved cached PR analysis",
                       repo_url=repo_url,
                       pr_number=pr_number,
                       cached_at=cached_data.get("cached_at"))
            return cached_data.get("result")
        
        return None
    
    def cache_pr_data(self, repo_url: str, pr_number: int, pr_data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache PR data (metadata, files, etc.)."""
        cache_key = self.get_pr_data_cache_key(repo_url, pr_number)
        
        # Add cache metadata
        cached_data = {
            "pr_data": pr_data,
            "cached_at": datetime.utcnow().isoformat(),
            "repo_url": repo_url,
            "pr_number": pr_number
        }
        
        return self.set_cache(cache_key, cached_data, ttl or 1800)  # 30 minutes for PR data
    
    def get_cached_pr_data(self, repo_url: str, pr_number: int) -> Optional[Dict[str, Any]]:
        """Get cached PR data."""
        cache_key = self.get_pr_data_cache_key(repo_url, pr_number)
        cached_data = self.get_cache(cache_key)
        
        if cached_data:
            logger.info("Retrieved cached PR data",
                       repo_url=repo_url,
                       pr_number=pr_number,
                       cached_at=cached_data.get("cached_at"))
            return cached_data.get("pr_data")
        
        return None
    
    def invalidate_pr_cache(self, repo_url: str, pr_number: int) -> bool:
        """Invalidate all cache entries for a specific PR."""
        try:
            analysis_key = self.get_pr_analysis_cache_key(repo_url, pr_number)
            data_key = self.get_pr_data_cache_key(repo_url, pr_number)
            
            analysis_deleted = self.delete_cache(analysis_key)
            data_deleted = self.delete_cache(data_key)
            
            logger.info("PR cache invalidated",
                       repo_url=repo_url,
                       pr_number=pr_number,
                       analysis_deleted=analysis_deleted,
                       data_deleted=data_deleted)
            
            return analysis_deleted or data_deleted
            
        except Exception as e:
            logger.error("Failed to invalidate PR cache",
                        repo_url=repo_url,
                        pr_number=pr_number,
                        error=str(e))
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            info = self.redis_client.info()
            
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "0B"),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) / 
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100, 
                    2
                )
            }
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {}
