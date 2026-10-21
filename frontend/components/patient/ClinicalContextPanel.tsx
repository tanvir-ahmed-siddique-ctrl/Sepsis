"use client";

import { useState } from "react";
import { ApiError, Panel, Pill } from "@/components/ui";
import { api } from "@/lib/api";
import { useSession } from "@/lib/session";
import { usePoll } from "@/lib/usePoll";

const INPUT = "w-full border border-ink/20 bg-white px-2 py-1.5 text-sm outline-none focus:border-accent";

type ConditionInfo = { code: string; label: string; effect: string; note?: string };

type ContextView = {
  context: {
    documented: boolean;
    policy_version: string;
    alert_policy: "standard" | "shadow_only";
    alert_policy_reason: string | null;
    cautions: string[];
    driver_annotations: { feature: string; condition: string; effect: string }[];
    goals_of_care?: string;
    goals_label?: string;
    conditions?: ConditionInfo[];
    other_note?: string | null;
    reason?: string;
    recorded_by?: string;
    recorded_at?: string;
    review_due?: string;
    review_overdue?: boolean;
  };
  catalogue: {
    goals_of_care: { code: string; label: string }[];
    conditions: ConditionInfo[];
  };
};

const EFFECT_LABEL: Record<string, string> = {
  baseline: "may be chronic baseline",
  underestimate: "model may under-call",
  out_of_scope: "outside validated population",
  unmodelled: "not in model inputs",
};

export function ClinicalContextPanel({ patientId, onSaved }: { patientId: string; onSaved?: () => void }) {
  const id = encodeURIComponent(patientId);
  const { me } = useSession();
  const canEdit = Boolean(me?.roles.some((role) => role === "clinician" || role === "admin"));
  const { data, error, refresh } = usePoll(() => api<ContextView>(`/v1/patients/${id}/context`), 15000, [id]);
  const [editing, setEditing] = useState(false);
  const [goals, setGoals] = useState("full_treatment");
  const [conditions, setConditions] = useState<string[]>([]);
  const [otherNote, setOtherNote] = useState("");
  const [reason, setReason] = useState("");
  const [reviewHours, setReviewHours] = useState(72);
  const [status, setStatus] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (error) return <ApiError error={error} />;
  if (!data) return null;
  const { context, catalogue } = data;

  function startEditing() {
    setGoals(context.goals_of_care ?? "full_treatment");
    setConditions(context.conditions?.map((item) => item.code) ?? []);
    setOtherNote(context.other_note ?? "");
    setReason("");
    setEditing(true);
  }

  async function save() {
    try {
      await api(`/v1/patients/${id}/context`, {
        method: "PUT",
        body: JSON.stringify({
          goals_of_care: goals,
          conditions,
          other_note: otherNote.trim() || null,
          reason: reason.trim(),
          review_hours: reviewHours,
        }),
      });
      setStatus("Context saved and audited. The model score is unchanged.");
      setSaveError(null);
      setEditing(false);
      await refresh();
      onSaved?.();
    } catch (cause) {
      setSaveError(cause instanceof Error ? cause.message : String(cause));
    }
  }

  return (
    <Panel title="Patient context the model cannot see">
      <p className="-mt-2 mb-3 text-xs text-ink/55">
        The frozen model learned population patterns. A doctor documents chronic, terminal or unusual conditions here;
        PredictRx annotates the score and adjusts alert routing by a fixed policy ({context.policy_version}). It never edits
        the probability.
      </p>

      {!context.documented ? (
        <p className="text-sm text-ink/60">No context documented. Standard alert policy applies.</p>
      ) : (
        <div className="space-y-2 text-sm">
          <div className="flex flex-wrap gap-2">
            <Pill>{context.goals_label}</Pill>
            <Pill>{context.alert_policy === "shadow_only" ? "Alerts shadow-only" : "Standard alerting"}</Pill>
            {context.review_overdue && <Pill>Review overdue</Pill>}
          </div>
          {context.conditions && context.conditions.length > 0 && (
            <ul className="space-y-1">
              {context.conditions.map((item) => (
                <li key={item.code}>
                  {item.label} <span className="text-xs text-ink/50">· {EFFECT_LABEL[item.effect] ?? item.effect}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="text-xs text-ink/55">
            Recorded by {context.recorded_by} · {context.recorded_at && new Date(context.recorded_at).toLocaleString()} · review
            due {context.review_due && new Date(context.review_due).toLocaleString()} · reason: {context.reason}
          </p>
        </div>
      )}

      {context.cautions.length > 0 && (
        <ul className="mt-3 space-y-1 border-l-2 border-accent/50 pl-3 text-sm">
          {context.cautions.map((caution) => (
            <li key={caution}>{caution}</li>
          ))}
        </ul>
      )}
      {context.driver_annotations.length > 0 && (
        <p className="mt-2 text-xs text-ink/60">
          Drivers that may reflect the documented baseline:{" "}
          {context.driver_annotations.map((item) => `${item.feature} (${item.condition.replaceAll("_", " ")})`).join(", ")}
        </p>
      )}

      {canEdit && !editing && (
        <button type="button" className="mt-3 border border-ink/20 px-2 py-1 text-xs" onClick={startEditing}>
          {context.documented ? "Update context" : "Document context"}
        </button>
      )}
      {!canEdit && <p className="mt-3 text-xs text-ink/50">Context is documented by a doctor or hospital admin.</p>}

      {editing && (
        <form
          className="mt-3 grid gap-3 lg:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <div className="space-y-2">
            <label className="block text-xs text-ink/60">
              Goals of care
              <select value={goals} onChange={(e) => setGoals(e.target.value)} className={INPUT}>
                {catalogue.goals_of_care.map((item) => (
                  <option key={item.code} value={item.code}>{item.label}</option>
                ))}
              </select>
            </label>
            <fieldset className="space-y-1">
              <legend className="text-xs text-ink/60">Known conditions</legend>
              {catalogue.conditions.map((item) => (
                <label key={item.code} className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={conditions.includes(item.code)}
                    onChange={(e) =>
                      setConditions((current) => (e.target.checked ? [...current, item.code] : current.filter((c) => c !== item.code)))
                    }
                  />
                  <span>
                    {item.label}
                    <span className="block text-xs text-ink/50">{item.note}</span>
                  </span>
                </label>
              ))}
            </fieldset>
          </div>
          <div className="space-y-2">
            {conditions.includes("other_unmodelled") && (
              <label className="block text-xs text-ink/60">
                Other condition (short clinical term, no identifiers)
                <input value={otherNote} onChange={(e) => setOtherNote(e.target.value)} maxLength={160} required className={INPUT} />
              </label>
            )}
            <label className="block text-xs text-ink/60">
              Reason / source (e.g. ward round, family meeting)
              <input value={reason} onChange={(e) => setReason(e.target.value)} minLength={3} maxLength={300} required className={INPUT} />
            </label>
            <label className="block text-xs text-ink/60">
              Review within (hours) — suppression lapses after this
              <input
                type="number"
                min={1}
                max={168}
                value={reviewHours}
                onChange={(e) => setReviewHours(Number(e.target.value))}
                className={INPUT}
              />
            </label>
            <div className="flex gap-2">
              <button type="submit" className="border border-accent bg-accent px-3 py-1 text-xs text-white">Save context</button>
              <button type="button" className="border border-ink/20 px-3 py-1 text-xs" onClick={() => setEditing(false)}>Cancel</button>
            </div>
          </div>
        </form>
      )}
      {status && <p className="mt-3 text-sm text-accent">{status}</p>}
      {saveError && <p role="alert" className="mt-3 text-sm text-risk-high">{saveError}</p>}
    </Panel>
  );
}
