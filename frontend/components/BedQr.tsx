"use client";

import QRCode from "qrcode";
import { useEffect, useState } from "react";

export function BedQr({ encounterKey, bed }: { encounterKey: string; bed: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    const url = `${window.location.origin}/chart?bed=${encodeURIComponent(encounterKey)}`;
    void QRCode.toDataURL(url, { width: 180, margin: 1, errorCorrectionLevel: "M" }).then(setSrc);
  }, [encounterKey]);
  if (!src) return null;
  return (
    <div className="print:block">
      {/* The QR contains only an encounter key and local URL, never a name or risk score. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={`QR code for bed ${bed}`} width={180} height={180} />
      <p className="mt-1 text-center text-xs font-medium">PredictRx · Bed {bed}</p>
      <button type="button" className="mt-2 w-full border border-ink/20 px-2 py-1 text-xs print:hidden" onClick={() => window.print()}>
        Print bed label
      </button>
    </div>
  );
}
