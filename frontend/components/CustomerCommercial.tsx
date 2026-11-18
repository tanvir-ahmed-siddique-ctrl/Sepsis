"use client";

import { useEffect, useState } from "react";
import { accountApi } from "@/lib/account-api";

type Quote = { id: string; site_id: string; currency: string; status: string; current_version: number; current: { total_minor: number; valid_until: string } };
type Contract = { id: string; site_id: string; scope: string; status: string; starts_on: string; ends_on: string; document_ref: string };
type Licence = { id: string; site_id: string; modules: string[]; unit_limit: number; bed_limit: number; support_tier: string; status: string; expires_on: string };
type Invoice = { id: string; invoice_number: string; currency: string; status: string; due_on: string; total_minor: number; verified_minor: number; balance_minor: number };
type Payment = { id: string; invoice_id: string; amount_minor: number; status: string; reference: string; evidence_ref: string };
type Credit = { id: string; invoice_id: string; amount_minor: number; reason: string; document_ref: string; status: string };
type Renewal = { id: string; contract_id: string; request_type: string; status: string };
type Contact = { id: string; channel: string; contact_role: string; summary: string; next_action: string | null; created_at: string };
type Assessment = { id: string; site_id: string; maturity: string; decision: string; findings: string };

function money(minor: number, currency: string) { return `${currency} ${(minor / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; }

export function CustomerCommercial() {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [licences, setLicences] = useState<Licence[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [credits, setCredits] = useState<Credit[]>([]);
  const [renewals, setRenewals] = useState<Renewal[]>([]);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [payment, setPayment] = useState({ invoice_id: "", amount: "", paid_on: "", channel: "bank_transfer", reference: "", evidence_ref: "" });
  const [renewal, setRenewal] = useState({ contract_id: "", request_type: "renew", note: "" });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    try {
      const [q, c, l, i, p, r, h, a, n] = await Promise.all([
        accountApi<{ quotes: Quote[] }>("/v1/quotes"), accountApi<{ contracts: Contract[] }>("/v1/contracts"),
        accountApi<{ licences: Licence[] }>("/v1/licences"), accountApi<{ invoices: Invoice[] }>("/v1/invoices"),
        accountApi<{ payments: Payment[] }>("/v1/payments"), accountApi<{ renewals: Renewal[] }>("/v1/renewals"),
        accountApi<{ contacts: Contact[] }>("/v1/contacts"), accountApi<{ assessments: Assessment[] }>("/v1/assessments"),
        accountApi<{ credits: Credit[] }>("/v1/credits"),
      ]);
      setQuotes(q.quotes); setContracts(c.contracts); setLicences(l.licences); setInvoices(i.invoices); setPayments(p.payments); setRenewals(r.renewals); setContacts(h.contacts); setAssessments(a.assessments); setCredits(n.credits);
      setError(null);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Account records unavailable"); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);

  async function submitPayment(event: React.FormEvent) {
    event.preventDefault(); setNotice(null);
    const amount_minor = Math.round(Number(payment.amount) * 100);
    if (!Number.isSafeInteger(amount_minor) || amount_minor <= 0) { setError("Enter a valid positive amount"); return; }
    try {
      await accountApi("/v1/payments", { method: "POST", body: JSON.stringify({ ...payment, amount_minor }) });
      setPayment({ invoice_id: "", amount: "", paid_on: "", channel: "bank_transfer", reference: "", evidence_ref: "" });
      setNotice("Evidence submitted for verification. Invoice balance is unchanged until finance verifies receipt.");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Submission failed"); }
  }
  async function submitRenewal(event: React.FormEvent) {
    event.preventDefault(); setNotice(null);
    try { await accountApi("/v1/renewals", { method: "POST", body: JSON.stringify(renewal) }); setRenewal({ contract_id: "", request_type: "renew", note: "" }); setNotice("Request recorded for account review."); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Request failed"); }
  }

  async function downloadLicence(id: string) {
    try {
      const result = await accountApi<{ package: object }>(`/v1/licences/${encodeURIComponent(id)}/package`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(result.package, null, 2)], { type: "application/json" }));
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = `auralis-licence-${id}.json`; anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Licence package unavailable"); }
  }

  if (loading) return <p role="status" className="py-8 text-sm text-slate">Loading commercial records…</p>;
  if (error && !contracts.length && !invoices.length && !quotes.length) return <p role="alert" className="border-l-2 border-risk-watch bg-warm p-5 text-sm">{error}</p>;
  return <div className="space-y-10">
    <header className="border-b border-[#D6DCD8] pb-6"><p className="text-xs font-semibold uppercase tracking-widest text-forest">Auralis / customer account</p><h1 className="mt-3 font-display text-4xl">Contracts & finance</h1><p className="mt-3 text-sm text-slate">Records for your organization only. Payment evidence is reviewed manually; no card checkout is connected.</p></header>
    {error && <p role="alert" className="border-l-2 border-risk-watch p-4 text-sm">{error}</p>}{notice && <p role="status" className="border-l-2 border-forest p-4 text-sm">{notice}</p>}
    <section><h2 className="text-xl font-semibold">Issued proposals</h2><div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-[#D6DCD8] text-xs uppercase tracking-wider text-slate"><th className="py-3">Site</th><th>Version</th><th>Status</th><th>Valid until</th><th>Value</th></tr></thead><tbody>{quotes.map((q) => <tr key={q.id} className="border-b border-[#D6DCD8]"><td className="py-3 font-mono">{q.site_id}</td><td><a className="text-forest underline" href={`/api/account/v1/quotes/${encodeURIComponent(q.id)}/versions/${q.current_version}/pdf`}>Version {q.current_version} PDF</a></td><td>{q.status.replaceAll("_", " ")}</td><td>{q.current.valid_until}</td><td>{money(q.current.total_minor, q.currency)}</td></tr>)}</tbody></table>{!quotes.length && <p className="py-4 text-sm text-slate">No issued proposal.</p>}</div></section>
    <section className="grid gap-8 lg:grid-cols-2"><div><h2 className="text-xl font-semibold">Contracts</h2><div className="mt-3 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{contracts.map((c) => <div key={c.id} className="py-4 text-sm"><p className="font-semibold">{c.scope}</p><p className="mt-1 text-slate">{c.site_id} · {c.status} · {c.starts_on} to {c.ends_on}</p><p className="mt-1 font-mono text-xs text-slate">Document reference: {c.document_ref}</p></div>)}{!contracts.length && <p className="py-4 text-sm text-slate">No signed contract.</p>}</div></div><div><h2 className="text-xl font-semibold">Recorded licence scope</h2><div className="mt-3 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{licences.map((l) => <div key={l.id} className="py-4 text-sm"><p className="font-semibold">{l.site_id} · {l.status.replaceAll("_", " ")}</p><p className="mt-1 text-slate">Modules: {l.modules.join(", ")} · {l.unit_limit} unit(s) · {l.bed_limit} bed band</p><p className="mt-1 text-slate">Support: {l.support_tier} · expires {l.expires_on}</p>{l.status === "issued_for_site_review" && <button type="button" onClick={() => void downloadLicence(l.id)} className="mt-2 text-forest underline">Download signed site package</button>}</div>)}{!licences.length && <p className="py-4 text-sm text-slate">No licence record. Clinical activation requires separate hospital governance.</p>}</div></div></section>
    <section><h2 className="text-xl font-semibold">Invoices & balances</h2><div className="mt-3 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-[#D6DCD8] text-xs uppercase tracking-wider text-slate"><th className="py-3">Invoice</th><th>Due</th><th>Status</th><th>Total</th><th>Verified</th><th>Outstanding</th></tr></thead><tbody>{invoices.map((i) => <tr key={i.id} className="border-b border-[#D6DCD8]"><td className="py-3 font-mono"><a href={`/api/account/v1/invoices/${encodeURIComponent(i.id)}/pdf`} className="text-forest underline underline-offset-2">{i.invoice_number} ↓</a></td><td>{i.due_on}</td><td>{i.status.replaceAll("_", " ")}</td><td>{money(i.total_minor, i.currency)}</td><td>{money(i.verified_minor, i.currency)}</td><td className="font-semibold">{money(i.balance_minor, i.currency)}</td></tr>)}</tbody></table>{!invoices.length && <p className="py-4 text-sm text-slate">No issued invoice.</p>}</div></section>
    <section className="grid gap-8 lg:grid-cols-[1fr_1.2fr]"><form onSubmit={(event) => void submitPayment(event)} className="grid content-start gap-3 text-sm"><h2 className="text-xl font-semibold">Submit payment evidence</h2><label>Invoice<select required value={payment.invoice_id} onChange={(event) => setPayment({ ...payment, invoice_id: event.target.value })} className="mt-1 block w-full border bg-white p-2"><option value="">Select invoice</option>{invoices.filter((i) => i.balance_minor > 0).map((i) => <option key={i.id} value={i.id}>{i.invoice_number} · {money(i.balance_minor, i.currency)} outstanding</option>)}</select></label><label>Amount in invoice currency<input required type="number" min="0.01" step="0.01" value={payment.amount} onChange={(event) => setPayment({ ...payment, amount: event.target.value })} className="mt-1 block w-full border p-2" /></label><label>Payment date<input required type="date" value={payment.paid_on} onChange={(event) => setPayment({ ...payment, paid_on: event.target.value })} className="mt-1 block w-full border p-2" /></label><label>Channel<select value={payment.channel} onChange={(event) => setPayment({ ...payment, channel: event.target.value })} className="mt-1 block w-full border bg-white p-2"><option value="bank_transfer">Bank transfer</option><option value="cheque">Cheque</option><option value="other_approved">Other approved</option></select></label><label>Transaction reference<input required minLength={3} value={payment.reference} onChange={(event) => setPayment({ ...payment, reference: event.target.value })} className="mt-1 block w-full border p-2" /></label><label>Evidence document reference<input required minLength={3} value={payment.evidence_ref} onChange={(event) => setPayment({ ...payment, evidence_ref: event.target.value })} className="mt-1 block w-full border p-2" /></label><button disabled={!invoices.some((i) => i.balance_minor > 0)} className="justify-self-start bg-forest px-4 py-2 font-semibold text-white disabled:opacity-50">Submit for verification</button></form><div><h2 className="text-xl font-semibold">Payment review</h2><div className="mt-3 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{payments.map((p) => <p key={p.id} className="py-3 text-sm">{p.reference} · {p.status.replaceAll("_", " ")}{p.status === "verified" && <a href={`/api/account/v1/payments/${encodeURIComponent(p.id)}/receipt.pdf`} className="ml-3 text-forest underline underline-offset-2">Receipt ↓</a>}<small className="block text-slate">Evidence {p.evidence_ref} · {p.amount_minor / 100} in invoice currency</small></p>)}{!payments.length && <p className="py-4 text-sm text-slate">No payment evidence submitted.</p>}</div></div></section>
    <section className="grid gap-8 border-t border-[#D6DCD8] pt-7 lg:grid-cols-2"><form onSubmit={(event) => void submitRenewal(event)} className="grid content-start gap-3 text-sm"><h2 className="text-xl font-semibold">Request a contract change</h2><label>Contract<select required value={renewal.contract_id} onChange={(event) => setRenewal({ ...renewal, contract_id: event.target.value })} className="mt-1 block w-full border bg-white p-2"><option value="">Select contract</option>{contracts.map((c) => <option key={c.id} value={c.id}>{c.site_id} · ends {c.ends_on}</option>)}</select></label><label>Request<select value={renewal.request_type} onChange={(event) => setRenewal({ ...renewal, request_type: event.target.value })} className="mt-1 block w-full border bg-white p-2"><option value="renew">Renew</option><option value="expand">Expand</option><option value="downgrade">Downgrade</option><option value="cancel">Cancel</option></select></label><label>Details<textarea required minLength={3} maxLength={500} value={renewal.note} onChange={(event) => setRenewal({ ...renewal, note: event.target.value })} className="mt-1 block w-full border p-2" /></label><button disabled={!contracts.length} className="justify-self-start bg-forest px-4 py-2 font-semibold text-white disabled:opacity-50">Record request</button></form><div><h2 className="text-xl font-semibold">Requests & account timeline</h2><div className="mt-3 space-y-3 text-sm">{renewals.map((r) => <p key={r.id} className="border-b border-[#D6DCD8] pb-2">{r.request_type} · {r.status} <small className="block font-mono text-slate">{r.contract_id}</small></p>)}{contacts.map((c) => <p key={c.id} className="border-b border-[#D6DCD8] pb-2">{c.channel} · {c.summary}<small className="block text-slate">{c.contact_role} · {c.created_at.slice(0, 10)}{c.next_action ? ` · next: ${c.next_action}` : ""}</small></p>)}{!renewals.length && !contacts.length && <p className="text-slate">No account activity recorded.</p>}</div></div></section>
    <section className="border-t border-[#D6DCD8] pt-7"><h2 className="text-xl font-semibold">Site readiness assessments</h2><div className="mt-3 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{assessments.map((a) => <p key={a.id} className="py-3 text-sm">{a.site_id} · {a.maturity} · {a.decision.replaceAll("_", " ")}<small className="block text-slate">{a.findings}</small></p>)}{!assessments.length && <p className="py-4 text-sm text-slate">No assessment record.</p>}</div></section>
    <section className="border-t border-[#D6DCD8] pt-7"><h2 className="text-xl font-semibold">Issued credit notes</h2><div className="mt-3 divide-y divide-[#D6DCD8] border-y border-[#D6DCD8]">{credits.map((credit) => <p key={credit.id} className="py-3 text-sm">{credit.amount_minor / 100} in invoice currency · {credit.reason}<small className="block font-mono text-slate">Document {credit.document_ref}</small></p>)}{!credits.length && <p className="py-4 text-sm text-slate">No issued credit note.</p>}</div></section>
  </div>;
}
