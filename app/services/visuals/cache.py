"""Caching system for visual assets."""
import hashlib
import json
import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Base directory for caching
CACHE_DIR = Path(os.environ.get("CACHE_DIR", "data/visuals/cache"))

# Default TTL (1 day in seconds)
DEFAULT_TTL = 86400

# Maximum cache size (500 MB in bytes)
MAX_CACHE_SIZE = 500 * 1024 * 1024


class VisualCache:
    """Cache system for storing and retrieving visual assets."""

    def __init__(self, ttl: int = DEFAULT_TTL, max_size: int = MAX_CACHE_SIZE):
        """Initialize the visual cache.

        Args:
            ttl (int, optional): Time-to-live in seconds. Defaults to DEFAULT_TTL.
            max_size (int, optional): Maximum cache size in bytes. Defaults to MAX_CACHE_SIZE.
        """
        # Create cache directories
        self.cache_dir = CACHE_DIR
        self.metadata_dir = self.cache_dir / "metadata"
        self.assets_dir = self.cache_dir / "assets"
        
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.metadata_dir, exist_ok=True)
        os.makedirs(self.assets_dir, exist_ok=True)
        
        self.ttl = ttl
        self.max_size = max_size
        
        # Create cache stats file if it doesn't exist
        self.stats_path = self.cache_dir / "stats.json"
        if not self.stats_path.exists():
            self._write_stats({"hits": 0, "misses": 0, "size": 0})

    def get(self, key: str) -> Optional[str]:
        """Get an asset from the cache.

        Args:
            key (str): Cache key

        Returns:
            Optional[str]: Path to the cached asset if found, None otherwise
        """
        cache_key = self._hash_key(key)
        metadata_path = self.metadata_dir / f"{cache_key}.json"
        
        if not metadata_path.exists():
            self._update_stats("misses")
            return None
        
        try:
            # Read metadata
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            
            # Check if the asset has expired
            if time.time() > metadata.get("expires_at", 0):
                self._remove_asset(cache_key)
                self._update_stats("misses")
                return None
            
            # Check if the asset file exists
            asset_path = Path(metadata.get("asset_path", ""))
            if not asset_path.exists():
                self._remove_asset(cache_key)
                self._update_stats("misses")
                return None
            
            # Update last accessed time
            metadata["last_accessed"] = time.time()
            with open(metadata_path, "w") as f:
                json.dump(metadata, f)
            
            self._update_stats("hits")
            return str(asset_path)
            
        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.error("Error reading cache metadata: %s", e)
            self._update_stats("misses")
            return None

    def put(
        self, key: str, asset_path: str, metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Put an asset in the cache.

        Args:
            key (str): Cache key
            asset_path (str): Path to the asset to cache
            metadata (Optional[Dict[str, Any]], optional): Additional metadata. Defaults to None.

        Returns:
            str: Path to the cached asset

        Raises:
            FileNotFoundError: If the asset file doesn't exist
        """
        if not Path(asset_path).exists():
            raise FileNotFoundError(f"Asset file not found: {asset_path}")
        
        # Check if the cache is too large and clean if necessary
        self._check_cache_size()
        
        cache_key = self._hash_key(key)
        
        # Create new asset path in cache
        asset_extension = Path(asset_path).suffix
        cached_asset_path = self.assets_dir / f"{cache_key}{asset_extension}"
        
        # Copy the asset to the cache
        shutil.copy2(asset_path, cached_asset_path)
        
        # Update cache size
        asset_size = cached_asset_path.stat().st_size
        self._update_stats_value("size", lambda size: size + asset_size)
        
        # Create metadata
        metadata_dict = metadata or {}
        metadata_dict.update({
            "key": key,
            "cache_key": cache_key,
            "asset_path": str(cached_asset_path),
            "created_at": time.time(),
            "expires_at": time.time() + self.ttl,
            "last_accessed": time.time(),
            "size": asset_size,
        })
        
        # Save metadata
        metadata_path = self.metadata_dir / f"{cache_key}.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata_dict, f)
        
        return str(cached_asset_path)

    def invalidate(self, key: str) -> bool:
        """Invalidate a cached asset.

        Args:
            key (str): Cache key

        Returns:
            bool: True if the asset was found and removed, False otherwise
        """
        cache_key = self._hash_key(key)
        return self._remove_asset(cache_key)

    def clear(self) -> None:
        """Clear all cached assets."""
        # Remove all files in assets and metadata directories
        for file_path in self.assets_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
        
        for file_path in self.metadata_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
        
        # Reset stats
        self._write_stats({"hits": 0, "misses": 0, "size": 0})
        
        logger.info("Cache cleared")

    def _hash_key(self, key: str) -> str:
        """Create a hash of the cache key.

        Args:
            key (str): Cache key

        Returns:
            str: Hashed key
        """
        # Create a SHA-256 hash of the key
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _remove_asset(self, cache_key: str) -> bool:
        """Remove an asset from the cache.

        Args:
            cache_key (str): Hashed cache key

        Returns:
            bool: True if the asset was found and removed, False otherwise
        """
        metadata_path = self.metadata_dir / f"{cache_key}.json"
        
        if not metadata_path.exists():
            return False
        
        try:
            # Read metadata to get the asset path and size
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            
            asset_path = Path(metadata.get("asset_path", ""))
            asset_size = metadata.get("size", 0)
            
            # Remove the asset file if it exists
            if asset_path.exists():
                asset_path.unlink()
            
            # Remove the metadata file
            metadata_path.unlink()
            
            # Update cache size
            self._update_stats_value("size", lambda size: max(0, size - asset_size))
            
            return True
            
        except (json.JSONDecodeError, KeyError, IOError) as e:
            logger.error("Error removing cached asset: %s", e)
            return False

    def _check_cache_size(self) -> None:
        """Check if the cache is too large and clean if necessary."""
        stats = self._read_stats()
        current_size = stats.get("size", 0)
        
        if current_size > self.max_size:
            logger.info(
                "Cache size (%d bytes) exceeds maximum (%d bytes). Cleaning...",
                current_size, self.max_size
            )
            self._clean_cache()

    def _clean_cache(self) -> None:
        """Clean the cache by removing least recently used assets."""
        try:
            # Get all metadata files
            metadata_files = list(self.metadata_dir.glob("*.json"))
            
            if not metadata_files:
                return
            
            # Read metadata and sort by last accessed time
            asset_metadata = []
            for metadata_path in metadata_files:
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                    
                    asset_metadata.append(metadata)
                except (json.JSONDecodeError, IOError) as e:
                    logger.error("Error reading metadata file %s: %s", metadata_path, e)
            
            # Sort by last accessed time (oldest first)
            asset_metadata.sort(key=lambda x: x.get("last_accessed", 0))
            
            # Remove assets until the cache size is below the maximum
            stats = self._read_stats()
            current_size = stats.get("size", 0)
            target_size = self.max_size * 0.8  # Reduce to 80% of max
            
            for metadata in asset_metadata:
                if current_size <= target_size:
                    break
                
                cache_key = metadata.get("cache_key")
                if cache_key:
                    if self._remove_asset(cache_key):
                        current_size -= metadata.get("size", 0)
            
            logger.info("Cache cleaned. New size: %d bytes", current_size)
            
        except Exception as e:
            logger.error("Error cleaning cache: %s", e)

    def _read_stats(self) -> Dict[str, Any]:
        """Read cache stats.

        Returns:
            Dict[str, Any]: Cache stats
        """
        try:
            with open(self.stats_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If there's an error, reset stats
            default_stats = {"hits": 0, "misses": 0, "size": 0}
            self._write_stats(default_stats)
            return default_stats

    def _write_stats(self, stats: Dict[str, Any]) -> None:
        """Write cache stats.

        Args:
            stats (Dict[str, Any]): Cache stats
        """
        try:
            with open(self.stats_path, "w") as f:
                json.dump(stats, f)
        except IOError as e:
            logger.error("Error writing cache stats: %s", e)

    def _update_stats(self, stat_name: str) -> None:
        """Update a cache stat.

        Args:
            stat_name (str): Stat name to update
        """
        self._update_stats_value(stat_name, lambda x: x + 1)

    def _update_stats_value(self, stat_name: str, update_func) -> None:
        """Update a cache stat with a custom function.

        Args:
            stat_name (str): Stat name to update
            update_func: Function to apply to the current value
        """
        try:
            stats = self._read_stats()
            stats[stat_name] = update_func(stats.get(stat_name, 0))
            self._write_stats(stats)
        except Exception as e:
            logger.error("Error updating cache stats: %s", e)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache stats.

        Returns:
            Dict[str, Any]: Cache stats with additional calculated values
        """
        stats = self._read_stats()
        
        # Add additional stats
        total_requests = stats.get("hits", 0) + stats.get("misses", 0)
        if total_requests > 0:
            stats["hit_ratio"] = stats.get("hits", 0) / total_requests
        else:
            stats["hit_ratio"] = 0
        
        stats["size_mb"] = stats.get("size", 0) / (1024 * 1024)
        stats["max_size_mb"] = self.max_size / (1024 * 1024)
        stats["usage_percent"] = (stats.get("size", 0) / self.max_size) * 100 if self.max_size > 0 else 0
        
        return stats 