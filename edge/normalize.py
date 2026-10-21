"""Site-edge normalization for common IEEE 11073 MDC symbolic observation codes.

Monitor vendors differ. This small, explicit map covers common vital signs and
must be verified against the site's central-station interface specification.
Unknown codes are left unchanged so the API quarantines them visibly.
"""

from __future__ import annotations

MDC_TO_LOINC = {
    "MDC_PULS_OXIM_PULS_RATE": "8867-4",
    "MDC_ECG_HEART_RATE": "8867-4",
    "MDC_PULS_OXIM_SAT_O2": "59408-5",
    "MDC_PRESS_BLD_NONINV_SYS": "8480-6",
    "MDC_PRESS_BLD_NONINV_DIA": "8462-4",
    "MDC_PRESS_BLD_NONINV_MEAN": "8478-0",
    "MDC_RESP_RATE": "9279-1",
    "MDC_TEMP": "8310-5",
}


def normalize_mdc(message: bytes) -> bytes:
    text = message.decode("utf-8")
    segments = text.replace("\r\n", "\r").replace("\n", "\r").split("\r")
    normalized: list[str] = []
    for segment in segments:
        if not segment.startswith("OBX|"):
            normalized.append(segment)
            continue
        fields = segment.split("|")
        if len(fields) <= 3:
            normalized.append(segment)
            continue
        parts = fields[3].split("^")
        code = parts[0].strip()
        system = parts[2].strip().upper() if len(parts) > 2 else ""
        if system in {"MDC", "IEEE11073", "IEEE 11073"} and code in MDC_TO_LOINC:
            while len(parts) < 3:
                parts.append("")
            parts[0] = MDC_TO_LOINC[code]
            parts[2] = "LN"
            fields[3] = "^".join(parts)
            segment = "|".join(fields)
        normalized.append(segment)
    return "\r".join(normalized).encode("utf-8")
