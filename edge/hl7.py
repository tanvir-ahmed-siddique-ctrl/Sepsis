"""Minimal HL7 v2 MLLP framing, validation, and acknowledgement helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

VT = b"\x0b"
FS = b"\x1c"
CR = b"\x0d"
MLLP_END = FS + CR


class HL7Error(ValueError):
    """Raised when a message cannot be safely accepted."""


class MLLPFramer:
    """Incrementally extract MLLP frames from an arbitrary TCP byte stream."""

    def __init__(self, max_message_bytes: int = 2 * 1024 * 1024) -> None:
        self.buffer = bytearray()
        self.max_message_bytes = max_message_bytes

    def feed(self, data: bytes) -> list[bytes]:
        self.buffer.extend(data)
        frames: list[bytes] = []
        while True:
            start = self.buffer.find(VT)
            if start < 0:
                if len(self.buffer) > self.max_message_bytes:
                    self.buffer.clear()
                    raise HL7Error("MLLP start byte not found before size limit")
                return frames
            if start:
                del self.buffer[:start]
            end = self.buffer.find(MLLP_END, 1)
            if end < 0:
                if len(self.buffer) > self.max_message_bytes:
                    self.buffer.clear()
                    raise HL7Error("MLLP frame exceeds size limit")
                return frames
            frames.append(bytes(self.buffer[1:end]))
            del self.buffer[: end + len(MLLP_END)]


@dataclass(frozen=True)
class MessageHeader:
    field_separator: str
    encoding_chars: str
    sending_application: str
    sending_facility: str
    receiving_application: str
    receiving_facility: str
    message_type: str
    trigger_event: str
    control_id: str
    processing_id: str
    version: str


def parse_header(message: bytes | str, *, require_oru: bool = True) -> MessageHeader:
    try:
        text = message.decode("utf-8") if isinstance(message, bytes) else message
    except UnicodeDecodeError as exc:
        raise HL7Error("HL7 message must be UTF-8") from exc
    first = text.replace("\r\n", "\r").replace("\n", "\r").split("\r", 1)[0]
    if len(first) < 4 or not first.startswith("MSH"):
        raise HL7Error("HL7 message must begin with MSH")
    separator = first[3]
    fields = first.split(separator)
    if len(fields) < 12:
        raise HL7Error("MSH segment is incomplete")
    encoding = fields[1]
    component = encoding[0] if encoding else "^"
    message_parts = fields[8].split(component)
    message_type = message_parts[0] if message_parts else ""
    trigger = message_parts[1] if len(message_parts) > 1 else ""
    if require_oru and (message_type, trigger) != ("ORU", "R01"):
        raise HL7Error(f"unsupported message type {fields[8]!r}; expected ORU^R01")
    if not fields[9]:
        raise HL7Error("MSH-10 message control ID is required")
    return MessageHeader(
        field_separator=separator,
        encoding_chars=encoding or "^~\\&",
        sending_application=fields[2],
        sending_facility=fields[3],
        receiving_application=fields[4],
        receiving_facility=fields[5],
        message_type=message_type,
        trigger_event=trigger,
        control_id=fields[9],
        processing_id=fields[10] or "P",
        version=fields[11] or "2.5.1",
    )


def build_ack(
    header: MessageHeader | None,
    code: str,
    text: str = "",
    *,
    fallback_control_id: str = "UNKNOWN",
) -> bytes:
    """Build an MLLP-wrapped HL7 ACK. ``code`` must be AA, AE, or AR."""
    if code not in {"AA", "AE", "AR"}:
        raise ValueError("ACK code must be AA, AE, or AR")
    h = header or MessageHeader("|", "^~\\&", "", "", "PREDICTRX-EDGE", "", "ORU", "R01",
                                fallback_control_id, "P", "2.5.1")
    sep = h.field_separator
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S+0000")
    ack_id = f"ACK-{h.control_id}"[:199]
    msh = sep.join([
        "MSH", h.encoding_chars, h.receiving_application or "PREDICTRX-EDGE",
        h.receiving_facility, h.sending_application, h.sending_facility, stamp, "",
        "ACK^R01", ack_id, h.processing_id, h.version,
    ])
    safe_text = text.replace("\r", " ").replace("\n", " ").replace(sep, " ")[:200]
    msa = sep.join(["MSA", code, h.control_id or fallback_control_id, safe_text])
    return VT + (msh + "\r" + msa + "\r").encode("utf-8") + MLLP_END

