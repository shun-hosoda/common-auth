"""JWKS (JSON Web Key Set) service for fetching and caching public keys."""

import logging
from typing import Protocol
from datetime import datetime, timedelta
import httpx
from cachetools import TTLCache
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import jwt
from jwt.algorithms import RSAAlgorithm

from common_auth.config import AuthConfig
from common_auth.exceptions import JWKSError

logger = logging.getLogger(__name__)


class JWKSService(Protocol):
    """Protocol for JWKS service implementations."""

    async def get_public_key(self, kid: str) -> RSAPublicKey:
        """
        Get public key for given key ID.
        
        Args:
            kid: Key ID from JWT header
            
        Returns:
            RSA public key
            
        Raises:
            JWKSError: If key cannot be retrieved
        """
        ...

    async def fetch_jwks(self) -> dict:
        """
        Fetch JWKS from remote endpoint.
        
        Returns:
            JWKS response dictionary
            
        Raises:
            JWKSError: If fetch fails
        """
        ...


class RemoteJWKSService:
    """
    JWKS service that fetches keys from Keycloak and caches them.
    
    Features:
    - TTL-based caching (default 24 hours)
    - Automatic refresh on unknown kid
    - Graceful degradation (uses cache when fetch fails)
    """

    def __init__(self, config: AuthConfig) -> None:
        """
        Initialize JWKS service.
        
        Args:
            config: Authentication configuration
        """
        self.config = config
        self.jwks_url = config.jwks_url
        self.cache_ttl = config.jwks_cache_ttl
        
        # Cache for JWKS response
        self._jwks_cache: TTLCache = TTLCache(maxsize=1, ttl=self.cache_ttl)
        self._cache_key = "jwks"
        
        # Cache for parsed public keys
        self._key_cache: dict[str, RSAPublicKey] = {}
        
        logger.info(f"Initialized JWKS service with URL: {self.jwks_url}, TTL: {self.cache_ttl}s")

    async def fetch_jwks(self) -> dict:
        """
        Fetch JWKS from Keycloak.
        
        Returns:
            JWKS response dictionary
            
        Raises:
            JWKSError: If fetch fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.jwks_url,
                    timeout=10.0
                )
                response.raise_for_status()
                jwks = response.json()
                
                # Cache the JWKS response
                self._jwks_cache[self._cache_key] = jwks
                logger.info(f"Fetched JWKS with {len(jwks.get('keys', []))} keys")
                
                return jwks
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching JWKS: {e}")
            
            # Try to use cached JWKS (graceful degradation)
            if self._cache_key in self._jwks_cache:
                logger.warning("Using cached JWKS due to fetch failure")
                return self._jwks_cache[self._cache_key]
            
            raise JWKSError(f"Failed to fetch JWKS and no cache available: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching JWKS: {e}")
            
            # Try to use cached JWKS
            if self._cache_key in self._jwks_cache:
                logger.warning("Using cached JWKS due to unexpected error")
                return self._jwks_cache[self._cache_key]
            
            raise JWKSError(f"Failed to fetch JWKS: {e}") from e

    async def get_public_key(self, kid: str) -> RSAPublicKey:
        """
        Get public key for given key ID.
        
        Strategy:
        1. Check key cache
        2. Check JWKS cache
        3. Fetch fresh JWKS if cache miss or kid not found
        
        Args:
            kid: Key ID from JWT header
            
        Returns:
            RSA public key
            
        Raises:
            JWKSError: If key cannot be retrieved
        """
        # Check key cache
        if kid in self._key_cache:
            logger.debug(f"Key cache hit for kid: {kid}")
            return self._key_cache[kid]
        
        # Get JWKS (from cache or fetch)
        jwks = await self._get_jwks(kid)
        
        # Find key in JWKS
        key_data = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                key_data = key
                break
        
        if not key_data:
            # Key not found, try refreshing JWKS once
            logger.warning(f"Key {kid} not found in cached JWKS, refreshing...")
            jwks = await self.fetch_jwks()
            
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    key_data = key
                    break
        
        if not key_data:
            raise JWKSError(f"Key with kid '{kid}' not found in JWKS")
        
        # Parse public key
        try:
            public_key = RSAAlgorithm.from_jwk(key_data)
            self._key_cache[kid] = public_key
            logger.info(f"Parsed and cached public key for kid: {kid}")
            return public_key
        except Exception as e:
            raise JWKSError(f"Failed to parse public key for kid '{kid}': {e}") from e

    async def _get_jwks(self, kid: str | None = None) -> dict:
        """
        Get JWKS from cache or fetch if expired.
        
        Args:
            kid: Optional key ID (for logging)
            
        Returns:
            JWKS dictionary
        """
        if self._cache_key in self._jwks_cache:
            logger.debug("JWKS cache hit")
            return self._jwks_cache[self._cache_key]
        
        logger.info("JWKS cache miss, fetching...")
        return await self.fetch_jwks()

    def clear_cache(self) -> None:
        """Clear all caches (for testing)."""
        self._jwks_cache.clear()
        self._key_cache.clear()
        logger.info("Cleared JWKS caches")
