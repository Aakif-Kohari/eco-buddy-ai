"""
Local Message Broker and Telemetry Engine.
Simulates a high-frequency IoT Pub/Sub architecture (like MQTT) using asyncio,
allowing devices to broadcast their state and the optimizer to subscribe and react.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable, List, DefaultDict
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

class MessageBroker:
    """
    An asynchronous, in-memory Pub/Sub message broker mimicking an MQTT server.
    Handles high-throughput telemetry streams from smart devices.
    """
    def __init__(self):
        # Maps topic strings to lists of callback functions
        self.subscribers: DefaultDict[str, List[Callable[[str, Dict[str, Any]], None]]] = defaultdict(list)
        self.message_history: List[Dict[str, Any]] = []
        self.max_history_len = 50000
        self.is_running = False
        self._lock = asyncio.Lock()
        
    async def subscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]):
        """
        Registers a callback to receive messages published to a specific topic.
        Supports wildcard subscriptions (e.g., 'home/telemetry/#').
        """
        async with self._lock:
            self.subscribers[topic].append(callback)
            logger.debug(f"Subscribed to topic: {topic}")

    async def unsubscribe(self, topic: str, callback: Callable[[str, Dict[str, Any]], None]):
        """Removes a callback from a topic."""
        async with self._lock:
            if topic in self.subscribers and callback in self.subscribers[topic]:
                self.subscribers[topic].remove(callback)
                logger.debug(f"Unsubscribed from topic: {topic}")

    def _matches_topic(self, subscription_topic: str, message_topic: str) -> bool:
        """
        Evaluates MQTT-style wildcard matching.
        '#' matches everything from that level down.
        '+' matches exactly one level.
        """
        if subscription_topic == message_topic:
            return True
            
        sub_parts = subscription_topic.split('/')
        msg_parts = message_topic.split('/')
        
        for i, sub_part in enumerate(sub_parts):
            if sub_part == '#':
                return True
            if i >= len(msg_parts):
                return False
            if sub_part != '+' and sub_part != msg_parts[i]:
                return False
                
        return len(sub_parts) == len(msg_parts)

    async def publish(self, topic: str, payload: Dict[str, Any], retain: bool = False):
        """
        Broadcasts a message to all matching subscribers asynchronously.
        """
        message = {
            "topic": topic,
            "payload": payload,
            "timestamp": time.time(),
            "retained": retain
        }
        
        async with self._lock:
            self.message_history.append(message)
            if len(self.message_history) > self.max_history_len:
                self.message_history.pop(0)
                
            # Find all matching subscriptions
            matched_callbacks = []
            for sub_topic, callbacks in self.subscribers.items():
                if self._matches_topic(sub_topic, topic):
                    matched_callbacks.extend(callbacks)
                    
        # Execute callbacks concurrently without blocking the broker thread
        if matched_callbacks:
            # In a true asyncio environment, we would use create_task
            for cb in matched_callbacks:
                try:
                    # Handle both sync and async callbacks
                    if asyncio.iscoroutinefunction(cb):
                        asyncio.create_task(cb(topic, payload))
                    else:
                        cb(topic, payload)
                except Exception as e:
                    logger.error(f"Error in subscriber callback for topic {topic}: {e}")

    def get_latest_retained(self, topic: str) -> Optional[Dict[str, Any]]:
        """Retrieves the most recent retained message for a given topic."""
        for msg in reversed(self.message_history):
            if msg["retained"] and self._matches_topic(topic, msg["topic"]):
                return msg["payload"]
        return None


class TelemetryEngine:
    """
    Manages the polling and broadcasting loop for a collection of IoTDevices.
    """
    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self.devices = []
        self._loop_task = None
        self.poll_interval_seconds = 1.0

    def register_device(self, device: Any):
        self.devices.append(device)
        logger.info(f"TelemetryEngine registered device: {device.name}")

    async def start(self):
        """Starts the continuous telemetry polling loop."""
        self.broker.is_running = True
        logger.info("TelemetryEngine started.")
        self._loop_task = asyncio.create_task(self._telemetry_loop())

    async def stop(self):
        """Stops the telemetry loop gracefully."""
        self.broker.is_running = False
        if self._loop_task:
            self._loop_task.cancel()
        logger.info("TelemetryEngine stopped.")

    async def _telemetry_loop(self):
        while self.broker.is_running:
            for device in self.devices:
                try:
                    payload = device.get_telemetry()
                    topic = f"home/devices/{device.device_type.lower()}/{device.id}/state"
                    
                    # Fire and forget publish
                    await self.broker.publish(topic, payload, retain=True)
                except Exception as e:
                    logger.error(f"Failed to extract telemetry from {device.name}: {e}")
                    
            await asyncio.sleep(self.poll_interval_seconds)
