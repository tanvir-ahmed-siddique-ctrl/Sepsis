"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type SlideId = "icu-board" | "bedside-chart" | "trustgate" | "handoff";

const SLIDES: Array<{
  id: SlideId;
  badge: string;
  title: string;
  caption: string;
  ctaHref: string;
  ctaLabel: string;
}> = [
  {
    id: "icu-board",
    badge: "01 · Live ICU Command Board",
    title: "Every adult ICU bed, sepsis risk trend & SLA timer in one view",
    caption: "Doctors and charge nurses see elevated 6-hour trajectories, vitals freshness, and bed ownership at a glance.",
    ctaHref: "/signin?next=/app/icu",
    ctaLabel: "Open Real ICU Board →",
  },
  {
    id: "bedside-chart",
    badge: "02 · Patient Trajectory & Drivers",
    title: "See why the risk rose — never an unexplained black-box number",
    caption: "Inspect serial MAP, heart rate, lactate slopes and Aurie AI guideline checklists right beside the trend.",
    ctaHref: "/signin?next=/app/chart",
    ctaLabel: "Open Bedside Charting →",
  },
  {
    id: "trustgate",
    badge: "03 · TrustGate Data Safety",
    title: "Automatically holds scores when labs are stale or units mismatch",
    caption: "Eliminates false alarm fatigue caused by delayed LIS draws or HL7 unit mismatches.",
    ctaHref: "/signin?next=/deploy",
    ctaLabel: "Open Deployment Console →",
  },
  {
    id: "handoff",
    badge: "04 · Alert SLA & Shift Handoff",
    title: "One-tap acknowledgement and clean nurse-to-doctor shift continuity",
    caption: "Watched beds, snoozed alerts, and unresolved escalations carry automatically into the incoming shift.",
    ctaHref: "/signin?next=/app/handoff",
    ctaLabel: "Open Shift Handoff →",
  },
];

const DEMO_BEDS = [
  {
    bed: "ICU-A · Bed 04",
    patient: "Encounter #4019 · 64y M",
    band: "High Risk",
    bandClass: "bg-[#FEF3F2] text-[#B42318] border-[#FECDCA]",
    score: "74%",
    scoreColor: "#B42318",
    freshness: "4 min ago",
    owner: "Dr. N. Rahman",
    alert: "Open alert · 6m left on SLA",
    spark: "M4 28 L22 26 L40 23 L58 18 L76 11 L94 6",
  },
  {
    bed: "ICU-A · Bed 07",
    patient: "Encounter #4022 · 51y F",
    band: "Watch",
    bandClass: "bg-[#FFFAEB] text-[#B54708] border-[#FEDF89]",
    score: "46%",
    scoreColor: "#DC6803",
    freshness: "7 min ago",
    owner: "Sr. F. Akter",
    alert: "Rising HR & RR trend",
    spark: "M4 27 L22 25 L40 24 L58 20 L76 17 L94 14",
  },
  {
    bed: "ICU-A · Bed 09",
    patient: "Encounter #4025 · 72y M",
    band: "TrustGate Hold",
    bandClass: "bg-[#F2F4F7] text-[#475467] border-[#E4E7EC]",
    score: "Abstain",
    scoreColor: "#667085",
    freshness: "Lactate >8h stale",
    owner: "Dr. N. Rahman",
    alert: "Awaiting fresh LIS chemistry",
    spark: "M4 22 L22 22 L40 21 L58 21 L76 21 L94 21",
  },
  {
    bed: "ICU-A · Bed 12",
    patient: "Encounter #4031 · 39y F",
    band: "Stable",
    bandClass: "bg-[#ECFDF3] text-[#027A48] border-[#ABEFC6]",
    score: "11%",
    scoreColor: "#1F7A4D",
    freshness: "2 min ago",
    owner: "Sr. F. Akter",
    alert: "Routine surveillance",
    spark: "M4 24 L22 25 L40 25 L58 26 L76 26 L94 27",
  },
];

export function ProductShowcaseCarousel() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(() => {
      setIndex((cur) => (cur + 1) % SLIDES.length);
    }, 5500);
    return () => window.clearInterval(timer);
  }, [paused]);

  const current = SLIDES[index];

  function prev() {
    setPaused(true);
    setIndex((cur) => (cur - 1 + SLIDES.length) % SLIDES.length);
  }

  function next() {
    setPaused(true);
    setIndex((cur) => (cur + 1) % SLIDES.length);
  }

  return (
    <div
      className="rounded-3xl border border-border bg-white p-4 shadow-[0_24px_60px_-20px_rgba(15,31,38,0.10)] sm:p-7"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      {/* Top Carousel Pill Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Product views">
          {SLIDES.map((slide, idx) => {
            const active = idx === index;
            return (
              <button
                key={slide.id}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => {
                  setIndex(idx);
                  setPaused(true);
                }}
                className={`rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all ${
                  active
                    ? "bg-teal text-white shadow-sm"
                    : "bg-[#F4F7F6] text-muted hover:bg-[#E9EFEE] hover:text-ink"
                }`}
              >
                {slide.badge}
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={prev}
            aria-label="Previous slide"
            className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-white text-ink transition-colors hover:border-teal hover:text-teal"
          >
            ←
          </button>
          <button
            type="button"
            onClick={next}
            aria-label="Next slide"
            className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-white text-ink transition-colors hover:border-teal hover:text-teal"
          >
            →
          </button>
        </div>
      </div>

      {/* Active Slide Workspace Frame (Light, Authentic Medical UI) */}
      <div className="mt-5 overflow-hidden rounded-2xl border border-border bg-[#F8FAFA]">
        {/* Simulated Browser / App Topbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-white px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
            <span className="font-display text-xs font-semibold text-ink">
              Auralis Hospital Workspace · Adult ICU Unit A
            </span>
            <span className="hidden rounded-full bg-teal/10 px-2.5 py-0.5 text-[11px] font-medium text-teal sm:inline-block">
              Hospital-Local LAN · 0 Cloud PHI
            </span>
          </div>
          <span className="font-mono text-[11px] text-muted">Frozen Model Run-4 · Polling 3s</span>
        </div>

        {/* SLIDE 1: REALISTIC ICU COMMAND BOARD */}
        {current.id === "icu-board" && (
          <div className="p-4 sm:p-6">
            <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {[
                { label: "High Risk Alerts", val: "1", tone: "text-[#B42318]" },
                { label: "Watch Trajectory", val: "1", tone: "text-[#DC6803]" },
                { label: "TrustGate Hold", val: "1", tone: "text-muted" },
                { label: "Review SLA Target", val: "15 min", tone: "text-teal" },
              ].map((stat) => (
                <div key={stat.label} className="rounded-xl border border-border bg-white px-4 py-3">
                  <p className="text-[11px] font-medium text-muted">{stat.label}</p>
                  <p className={`mt-0.5 font-display text-xl font-bold ${stat.tone}`}>{stat.val}</p>
                </div>
              ))}
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              {DEMO_BEDS.map((b) => (
                <div key={b.bed} className="rounded-xl border border-border bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.02)]">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-display text-sm font-semibold text-ink">{b.bed}</p>
                      <p className="text-xs text-muted">{b.patient}</p>
                    </div>
                    <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${b.bandClass}`}>
                      {b.band}
                    </span>
                  </div>

                  <div className="mt-3 flex items-end justify-between">
                    <div>
                      <p className="text-[11px] text-muted">6h Sepsis Risk</p>
                      <p className="font-display text-2xl font-bold tabular-nums" style={{ color: b.scoreColor }}>
                        {b.score}
                      </p>
                    </div>
                    <svg viewBox="0 0 100 32" className="h-8 w-24">
                      <path d={b.spark} fill="none" stroke={b.scoreColor} strokeWidth="2.2" strokeLinecap="round" />
                    </svg>
                  </div>

                  <div className="mt-3 flex items-center justify-between border-t border-border/70 pt-2.5 text-[11px] text-muted">
                    <span>{b.alert}</span>
                    <span className="font-medium text-ink">{b.freshness}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SLIDE 2: BEDSIDE PATIENT TRAJECTORY & DRIVERS */}
        {current.id === "bedside-chart" && (
          <div className="grid gap-5 p-4 sm:p-6 lg:grid-cols-[1.25fr_0.75fr]">
            <div className="rounded-xl border border-border bg-white p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-display text-base font-semibold text-ink">ICU-A · Bed 04 · 6-Hour Risk Curve</p>
                  <p className="text-xs text-muted">Serial vitals + arterial lactate · TrustGate Verified</p>
                </div>
                <span className="rounded-full bg-[#FEF3F2] px-3 py-1 text-xs font-semibold text-[#B42318]">
                  Risk 74% (Watch ≥ 35%)
                </span>
              </div>

              <svg viewBox="0 0 420 130" className="mt-4 h-36 w-full">
                <defs>
                  <linearGradient id="cleanCurveFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#087E83" stopOpacity="0.22" />
                    <stop offset="100%" stopColor="#087E83" stopOpacity="0.0" />
                  </linearGradient>
                </defs>
                <line x1="12" y1="36" x2="408" y2="36" stroke="#FECDCA" strokeDasharray="4 4" />
                <line x1="12" y1="76" x2="408" y2="76" stroke="#E4EBEA" />
                <line x1="12" y1="112" x2="408" y2="112" stroke="#E4EBEA" />
                <path
                  d="M16 104 C 85 98, 150 86, 225 68 C 295 50, 350 32, 404 22 L 404 114 L 16 114 Z"
                  fill="url(#cleanCurveFill)"
                />
                <path
                  d="M16 104 C 85 98, 150 86, 225 68 C 295 50, 350 32, 404 22"
                  fill="none"
                  stroke="#087E83"
                  strokeWidth="3"
                  strokeLinecap="round"
                />
                {[
                  [16, 104],
                  [115, 92],
                  [225, 68],
                  [325, 41],
                  [404, 22],
                ].map(([cx, cy], idx) => (
                  <circle key={idx} cx={cx} cy={cy} r={idx === 4 ? 5 : 3.5} fill="#FFFFFF" stroke="#087E83" strokeWidth="2.5" />
                ))}
              </svg>

              <div className="mt-3 grid grid-cols-4 gap-2 text-center">
                {[
                  ["HR", "112 bpm", "+14"],
                  ["MAP", "63 mmHg", "-9"],
                  ["Lactate", "2.9 mmol/L", "+1.1"],
                  ["Resp", "26 /min", "+6"],
                ].map(([k, v, d]) => (
                  <div key={k} className="rounded-lg bg-[#F8FAFA] p-2">
                    <p className="text-[11px] font-medium text-muted">{k}</p>
                    <p className="font-display text-sm font-bold text-ink">{v}</p>
                    <p className="text-[10px] font-semibold text-teal">{d} (4h)</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-col justify-between rounded-xl border border-border bg-white p-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-teal">Top Physiological Drivers</p>
                <div className="mt-3 space-y-3">
                  {[
                    { name: "MAP downward slope (<65 mmHg)", pct: 86 },
                    { name: "Rising arterial lactate + shock index", pct: 74 },
                    { name: "Sustained tachypnea (26 /min)", pct: 58 },
                  ].map((d) => (
                    <div key={d.name}>
                      <div className="flex justify-between text-xs font-medium text-ink">
                        <span>{d.name}</span>
                        <span className="text-teal">High impact</span>
                      </div>
                      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-[#EEF3F2]">
                        <div className="h-full rounded-full bg-teal" style={{ width: `${d.pct}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4 rounded-xl border border-teal/20 bg-teal/[0.05] p-3.5 text-xs leading-5 text-ink">
                <strong className="text-teal">Aurie AI Context: </strong>
                 summarizes recent fluid balance and hospital Hour-1 bundle checklist without altering the 74% model output.
              </div>
            </div>
          </div>
        )}

        {/* SLIDE 3: TRUSTGATE DATA QUALITY & QUARANTINE */}
        {current.id === "trustgate" && (
          <div className="grid gap-4 p-4 sm:p-6 md:grid-cols-3">
            {[
              {
                status: "Verified Stream",
                badge: "bg-[#ECFDF3] text-[#027A48]",
                title: "Fresh Vitals & Matched Units",
                body: "HL7v2 monitor & LIS observations arrive within window with verified units. Model scores normally.",
              },
              {
                status: "TrustGate Abstain",
                badge: "bg-[#FFFAEB] text-[#B54708]",
                title: "Stale Lab Window (>8h)",
                body: "Instead of guessing or firing a noisy false alarm, Auralis shows 'Abstain · Missing fresh lactate' clearly.",
              },
              {
                status: "Quarantine Guard",
                badge: "bg-[#FEF3F2] text-[#B42318]",
                title: "Unit Conflict Intercepted",
                body: "Catches µmol/L vs mg/dL creatinine mismatches at the connector before they touch the patient chart.",
              },
            ].map((card) => (
              <div key={card.title} className="rounded-xl border border-border bg-white p-5">
                <span className={`inline-block rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${card.badge}`}>
                  {card.status}
                </span>
                <h4 className="mt-3 font-display text-base font-semibold text-ink">{card.title}</h4>
                <p className="mt-2 text-xs leading-5 text-muted">{card.body}</p>
              </div>
            ))}
          </div>
        )}

        {/* SLIDE 4: ALERT SLA & SHIFT HANDOFF */}
        {current.id === "handoff" && (
          <div className="grid gap-4 p-4 sm:p-6 lg:grid-cols-2">
            <div className="rounded-xl border border-border bg-white p-5">
              <div className="flex items-center justify-between">
                <span className="rounded-full bg-[#FEF3F2] px-2.5 py-0.5 text-xs font-semibold text-[#B42318]">
                  Active ICU Alert · SLA 09:14 remaining
                </span>
                <span className="text-xs text-muted">Bed 04</span>
              </div>
              <h4 className="mt-3 font-display text-lg font-semibold text-ink">
                Clinician review & one-tap bedside response
              </h4>
              <p className="mt-1.5 text-xs leading-5 text-muted">
                Doctors acknowledge, snooze during active bedside resuscitation, or record diagnostic feedback in one click.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <span className="rounded-lg bg-teal px-3 py-1.5 text-xs font-semibold text-white">✓ Acknowledge & Review</span>
                <span className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-ink">Quiet 1h (Treating at bedside)</span>
              </div>
            </div>

            <div className="rounded-xl border border-border bg-white p-5">
              <span className="rounded-full bg-teal/10 px-2.5 py-0.5 text-xs font-semibold text-teal">
                Incoming Shift Summary · 08:00 Handover
              </span>
              <h4 className="mt-3 font-display text-lg font-semibold text-ink">
                Structured nurse & consultant handoff
              </h4>
              <ul className="mt-2.5 space-y-2 text-xs text-muted">
                <li className="flex justify-between border-b border-border/60 pb-1.5">
                  <span className="font-medium text-ink">Bed 04 · High risk (74%)</span>
                  <span>Lactate repeat ordered · Dr. Rahman</span>
                </li>
                <li className="flex justify-between">
                  <span className="font-medium text-ink">Bed 09 · TrustGate hold</span>
                  <span>Morning chemistry panel pending</span>
                </li>
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Slide Caption & Direct Launch CTA */}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-4 px-1">
        <div className="max-w-2xl">
          <h3 className="font-display text-lg font-semibold text-ink">{current.title}</h3>
          <p className="mt-0.5 text-sm text-muted">{current.caption}</p>
        </div>
        <Link href={current.ctaHref} className="auralis-btn-primary shrink-0">
          {current.ctaLabel}
        </Link>
      </div>
    </div>
  );
}
