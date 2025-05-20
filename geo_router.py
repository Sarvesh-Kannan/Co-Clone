"""
Geographic Routing Simulation

This module simulates DNS-based geographic routing to select
the closest proxy instance for code completion requests.
Inspired by GitHub Copilot's architecture.
"""

import json
import logging
import os
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import httpx
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("geo-router")

# Simulated regions
REGIONS = {
    "us-west": {"host": "localhost", "port": 8000, "latency": 0.010, "weight": 10},
    "us-east": {"host": "localhost", "port": 8001, "latency": 0.050, "weight": 5},
    "eu-west": {"host": "localhost", "port": 8002, "latency": 0.100, "weight": 3},
    "ap-east": {"host": "localhost", "port": 8003, "latency": 0.150, "weight": 2},
}

# Current state
health_status: Dict[str, bool] = {region: True for region in REGIONS}
last_health_check: Dict[str, float] = {region: 0 for region in REGIONS}

@dataclass
class Region:
    name: str
    host: str
    port: int
    latency: float
    weight: int
    healthy: bool = True
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    def __str__(self) -> str:
        status = "HEALTHY" if self.healthy else "UNHEALTHY"
        return f"{self.name} ({self.url}) - {status}, latency: {self.latency:.3f}s"

class GeoRouter:
    """Simulates DNS-based geographical routing for selecting the closest proxy instance."""
    
    def __init__(self, update_interval: int = 60):
        self.regions: Dict[str, Region] = {}
        self.update_interval = update_interval
        self.last_update = 0
        self._initialize_regions()
        
    def _initialize_regions(self) -> None:
        """Initialize the regions from the configuration."""
        for name, config in REGIONS.items():
            self.regions[name] = Region(
                name=name,
                host=config["host"],
                port=config["port"],
                latency=config["latency"],
                weight=config["weight"],
                healthy=True
            )
        logger.info(f"Initialized {len(self.regions)} regions")
    
    async def check_health(self, client: httpx.AsyncClient, region_name: str) -> bool:
        """Check if a region is healthy by making a health check request."""
        region = self.regions[region_name]
        url = f"{region.url}/health"
        
        try:
            response = await client.get(url, timeout=2.0)
            if response.status_code == 200:
                data = response.json()
                return data.get("status") == "healthy"
            return False
        except Exception as e:
            logger.warning(f"Health check failed for {region_name}: {str(e)}")
            return False
    
    async def update_health_status(self) -> None:
        """Update the health status of all regions."""
        # Only update every update_interval seconds
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return
        
        self.last_update = current_time
        logger.info("Updating health status for all regions")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for region_name in self.regions:
                self.regions[region_name].healthy = await self.check_health(client, region_name)
        
        logger.info("Health status updated")
        for region in self.regions.values():
            logger.info(str(region))
    
    def get_region(self, user_location: Optional[str] = None) -> Tuple[str, Region]:
        """
        Get the best region for a user based on their location.
        
        Args:
            user_location: Optional location string (e.g., 'us', 'eu', 'ap')
            
        Returns:
            Tuple of (token URL, region object)
        """
        # Filter for healthy regions
        healthy_regions = {name: region for name, region in self.regions.items() if region.healthy}
        
        if not healthy_regions:
            # If no healthy regions, try any region
            logger.warning("No healthy regions available, using any region")
            healthy_regions = self.regions
        
        # Select region based on user location or random with weighting
        selected_region = None
        
        if user_location:
            # Try to match by location prefix
            matching_regions = {
                name: region for name, region in healthy_regions.items() 
                if name.startswith(user_location.lower())
            }
            
            if matching_regions:
                # Choose a random matching region weighted by their weights
                weights = [region.weight for region in matching_regions.values()]
                selected_name = random.choices(
                    list(matching_regions.keys()), 
                    weights=weights, 
                    k=1
                )[0]
                selected_region = matching_regions[selected_name]
        
        if not selected_region:
            # Fallback: choose a random healthy region weighted by their weights
            weights = [region.weight for region in healthy_regions.values()]
            selected_name = random.choices(
                list(healthy_regions.keys()), 
                weights=weights, 
                k=1
            )[0]
            selected_region = healthy_regions[selected_name]
        
        token_url = f"{selected_region.url}/token"
        return token_url, selected_region

# Singleton instance
router = GeoRouter()

def get_proxy_for_location(location: Optional[str] = None) -> Dict:
    """
    Get a proxy for the user's location.
    
    Args:
        location: User's location (e.g., 'us', 'eu', 'ap')
        
    Returns:
        Dict with token URL and region information
    """
    token_url, region = router.get_region(location)
    
    # Simulate network latency
    time.sleep(region.latency)
    
    return {
        "token_url": token_url,
        "region": region.name,
        "latency": region.latency,
        "url": region.url
    }

if __name__ == "__main__":
    import asyncio
    
    async def main():
        """Test the geo-routing functionality."""
        r = GeoRouter()
        await r.update_health_status()
        
        locations = [None, "us", "eu", "ap"]
        for location in locations:
            token_url, region = r.get_region(location)
            print(f"Location: {location or 'default'} -> {region.name} ({token_url})")
    
    asyncio.run(main()) 