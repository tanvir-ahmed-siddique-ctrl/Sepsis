"use client";

import { ApiError, Panel, Pill } from "@/components/ui";
import { api, type Provenance, type SignalMatrix } from "@/lib/api";
import { humanize } from "@/lib/pilot";
import { usePoll } from "@/lib/usePoll";

export function ProvenancePanel({ patientId }: { patientId: string }) {
  const id = encodeURIComponent(patientId);
  const provenance = usePoll(
    () => api<{ source_mode: string; unit_id: string; observations: Provenance[]; note: string }>(`/v1/patients/${id}/provenance`),
    15000,
    [id],
  );
  const matrix = usePoll(() => api<SignalMatrix>(`/v1/patients/${id}/signals?hours=24`), 15000, [id]);

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Panel title="Data provenance">
        {provenance.error && <ApiError error={provenance.error} />}
        {provenance.data && (
          <>
            <p className="-mt-2 mb-2 text-xs text-ink/55">{provenance.data.note}</p>
            <div className="max-h-80 overflow-auto">
              <table className="w-full text-left text-xs">
                <thead className="sticky top-0 bg-white text-ink/50">
                  <tr>
                    <th className="py-1 font-medium">Signal</th>
                    <th className="py-1 font-medium">Latest</th>
                    <th className="py-1 font-medium">Source time</th>
                    <th className="py-1 font-medium">Feed</th>
                  </tr>
                </thead>
                <tbody>
                  {provenance.data.observations.map((row) => (
                    <tr key={row.code} className="border-t border-ink/5">
                      <td className="py-1">
                        {row.code} {row.required && <span className="text-ink/40">(required)</span>}
                      </td>
                      <td className="py-1 tabular-nums">
                        {Number(row.value.toFixed(2))} {row.unit}
                        {row.validation_warning && <Pill tone="warning">{humanize(row.validation_warning)}</Pill>}
                      </td>
                      <td className="py-1 tabular-nums">{row.source_time.replace("T", " ").slice(0, 16)}</td>
                      <td className="py-1">{row.connector} · {row.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Panel>
      <Panel title="Missing-signal matrix (last 24 h)">
        {matrix.error && <ApiError error={matrix.error} />}
        {matrix.data && (
          <>
            <p className="-mt-2 mb-2 text-xs text-ink/55">
              Filled = observed that hour. Empty cells are real gaps (not model “guesses”). The scorer may
              forward-fill within clinical limits; TrustGate still blocks interrupts when required vitals are too old.
            </p>
            <div className="overflow-x-auto">
              <table className="text-[10px]" aria-label="Observed signals by hour">
                <tbody>
                  {matrix.data.signals.map((signal) => (
                    <tr key={signal.code}>
                      <th scope="row" className={`pr-2 text-left font-medium ${signal.required ? "text-ink" : "text-ink/55"}`}>
                        {signal.code}
                      </th>
                      {signal.observed.map((seen, index) => (
                        <td key={index} className="p-[1px]">
                          <span
                            className={`block h-3 w-3 ${seen ? (signal.required ? "bg-accent" : "bg-ink/50") : signal.required ? "border border-risk-high/50" : "border border-ink/10"}`}
                            title={`${signal.code} hour ${matrix.data?.hours[index]}: ${seen ? "observed" : "missing"}`}
                          />
                        </td>
                      ))}
                      <td className="pl-2 tabular-nums text-ink/55">{signal.observed_hours}/{matrix.data?.window_hours}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {(() => {
              const gaps = matrix.data.signals.filter((s) => s.required && s.observed_hours < (matrix.data?.window_hours ?? 24));
              if (!gaps.length) {
                return <p className="mt-3 text-xs text-ink/55">Required vitals look complete for this window — no action.</p>;
              }
              return (
                <div className="mt-3 space-y-2 border-t border-ink/10 pt-3 text-sm">
                  <p className="font-medium">What to do next</p>
                  <ol className="list-decimal space-y-1 pl-5 text-ink/75">
                    <li>
                      <strong>Bedside now:</strong> chart the missing required signals (
                      {gaps.map((g) => g.code).join(", ")}) in{" "}
                      <a className="text-accent underline" href="/chart">
                        Chart
                      </a>{" "}
                      or confirm the monitor/LIS is sending them.
                    </li>
                    <li>
                      <strong>What the system does:</strong> TrustGate stays on Verify data / Abstain — no interruptive
                      alert until freshness recovers. The probability may still show for research.
                    </li>
                    <li>
                      <strong>IT / Integration Hub:</strong> if the same codes gap across many beds, open{" "}
                      <a className="text-accent underline" href="/integration">
                        Integration Hub
                      </a>{" "}
                      → quarantine / feed health → map codes or fix the connector (this is a paid data-quality service
                      line in the commercial plan).
                    </li>
                  </ol>
                </div>
              );
            })()}
          </>
        )}
      </Panel>
    </div>
  );
}
