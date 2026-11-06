"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useSession } from "@/lib/session";
import type { UserRole } from "@/lib/api";

const personas: {name:string; role:UserRole; route:string; scope:string}[] = [
  {name:"Platform operator",role:"operator",route:"/super-admin",scope:"Fleet health and commercial control plane. Patient charts remain hospital-local."},
  {name:"Hospital director",role:"admin",route:"/hospital-admin",scope:"Site setup, users, integration and silent-pilot governance."},
  {name:"ICU consultant",role:"clinician",route:"/icu",scope:"ICU risk review, explainability, alert ownership and bedside context."},
  {name:"Bedside nurse",role:"nurse",route:"/chart",scope:"Admission, vitals, ward observations and shift handoff."},
  {name:"Clinical IT engineer",role:"admin",route:"/integration",scope:"Hospital-admin view of FHIR/HL7 feeds, mapping and quarantine."},
];
export default function EvaluatorPage(){
  const {signInDemo}=useSession();const router=useRouter();const [busy,setBusy]=useState<string|null>(null);const [error,setError]=useState<string|null>(null);
  async function enter(item:typeof personas[number]){setBusy(item.name);try{await signInDemo("judge-"+item.role,item.role);router.push(item.route)}catch(cause){setError(cause instanceof Error?cause.message:String(cause));setBusy(null)}}
  return <div className="mx-auto max-w-6xl space-y-7 bg-[#080C14] px-5 py-8 text-slate-50 sm:px-8"><header><p className="text-xs font-semibold uppercase tracking-widest text-cyan-400">Congress evaluator gateway</p><h1 className="mt-2 font-display text-4xl">Choose a workflow</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">These roles are simulated for judging. Hospital accounts are issued by each site. Every API still checks its assigned role.</p></header>
    {error&&<p role="alert" className="bg-risk-high/10 p-3 text-risk-high">{error}</p>}
    <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">{personas.map(item=><button key={item.name} disabled={busy!==null} onClick={()=>void enter(item)} className="min-h-48 bg-[#0F172A] p-6 text-left transition duration-150 hover:-translate-y-0.5 hover:bg-slate-800 disabled:opacity-50"><span className="text-xs uppercase tracking-wider text-cyan-400">{item.role}</span><h2 className="mt-3 font-display text-2xl">{item.name}</h2><p className="mt-3 text-sm leading-6 text-slate-300">{item.scope}</p><span className="mt-5 inline-block text-sm font-semibold text-cyan-400">{busy===item.name?"Opening…":"Enter workspace →"}</span></button>)}</div>
    <details className="bg-[#0F172A] p-5"><summary className="cursor-pointer font-semibold">Official 100-point rubric · show evidence route</summary><div className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">{[
      ["Innovation","20","/connection","Connection ladder and guarded transfer"],
      ["Technical execution","20","/docs","Model, ingest, reliability and explainability"],
      ["Business & global readiness","20","/business","Buyer path and pricing hypotheses"],
      ["Impact & ethical AI","20","/evidence","Measured evidence and safeguards"],
      ["Scalability & collaboration","10","/operations","Local operations and fleet boundaries"],
      ["Presentation","10","/presentation","Three-minute walkthrough"],
    ].map(([name,points,href,detail])=><Link key={name} href={href} className="bg-slate-800 p-4"><span className="font-mono text-cyan-400">{points} points</span><strong className="mt-2 block">{name}</strong><span className="mt-1 block text-slate-300">{detail}</span></Link>)}</div></details>
    <p className="text-xs text-slate-400">Clinical IT uses the hospital administrator role in the current authorization model. The vendor fleet console has separate authentication.</p><Link href="/" className="text-sm text-cyan-400 underline">Back to portal</Link>
  </div>;
}
