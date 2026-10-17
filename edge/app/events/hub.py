"""In-memory SSE hub — ring buffer + per-connection queues."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field

from beacon_contract import new_id
from beacon_contract.enums import SseEvent
from beacon_contract.events import SseMessage

RING_SIZE = 200
PING_INTERVAL_S = 15.0


@dataclass
class _ChannelState:
    ring: deque[SseMessage] = field(default_factory=lambda: deque(maxlen=RING_SIZE))
    subscribers: list[asyncio.Queue[SseMessage | None]] = field(default_factory=list)


class EventHub:
    def __init__(self) -> None:
        self._channels: dict[str, _ChannelState] = defaultdict(_ChannelState)

    def publish(self, channels: list[str], message: SseMessage) -> None:
        for name in channels:
            state = self._channels[name]
            state.ring.append(message)
            dead: list[asyncio.Queue[SseMessage | None]] = []
            for q in state.subscribers:
                try:
                    q.put_nowait(message)
                except asyncio.QueueFull:
                    dead.append(q)
            for q in dead:
                try:
                    state.subscribers.remove(q)
                except ValueError:
                    pass

    def publish_event(
        self, channels: list[str], event: SseEvent, data: dict
    ) -> SseMessage:
        msg = SseMessage(id=new_id(), event=event, data=data)
        self.publish(channels, msg)
        return msg

    def replay_since(self, channels: list[str], last_event_id: str | None) -> list[SseMessage]:
        """Replay buffered messages after last_event_id (ring insertion order)."""
        ordered: list[SseMessage] = []
        seen: set[str] = set()
        for name in channels:
            for msg in self._channels[name].ring:
                if msg.id in seen:
                    continue
                seen.add(msg.id)
                ordered.append(msg)
        if last_event_id is None:
            return ordered
        for i, msg in enumerate(ordered):
            if msg.id == last_event_id:
                return ordered[i + 1 :]
        # Unknown id — fall back to uuid7 watermark.
        return [m for m in ordered if m.id > last_event_id]

    def subscribe(self, channels: list[str]) -> asyncio.Queue[SseMessage | None]:
        q: asyncio.Queue[SseMessage | None] = asyncio.Queue(maxsize=256)
        for name in channels:
            self._channels[name].subscribers.append(q)
        return q

    def unsubscribe(self, channels: list[str], q: asyncio.Queue[SseMessage | None]) -> None:
        for name in channels:
            subs = self._channels[name].subscribers
            try:
                subs.remove(q)
            except ValueError:
                pass
        # Wake the listener so the stream generator can exit promptly.
        try:
            q.put_nowait(None)
        except asyncio.QueueFull:
            pass

    def reset(self) -> None:
        """Test helper."""
        self._channels.clear()


_hub = EventHub()


def get_hub() -> EventHub:
    return _hub
