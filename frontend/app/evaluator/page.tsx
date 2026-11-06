"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useSession } from "@/lib/session";
import type { UserRole } from "@/lib/api";

const personas: {name:string; role:UserRole; route:string; scope:string}[] = [
  {name:"Platform operator",role:"operator",route:"/super-admin",scope:"Fleet health and commercial control plane. Patient charts remain hospital-local."},
  {name:"Hospital director",role:"admin",route:"/hospital-admin",scope:"Site setup, users, integration and silent-pilot governance."},
  {name:"ICU consultant",role:"clinician",route:"/dashboard",scope:"ICU risk review, explainability, alert ownership and bedside context."},
  {name:"Bedside nurse",role:"nurse",route:"/chart",scope:"Admission, vitals, ward observations and shift handoff."},
  {name:"Clinical IT engineer",role:"admin",route:"/integration",scope:"Hospital-admin view of FHIR/HL7 feeds, mapping and quarantine."},
];
export default function EvaluatorPage(){
  const {signInDemo}=useSession();const router=useRouter();const [busy,setBusy]=useState<string|null>(null);const [error,setError]=useState<string|null>(null);
  async function enter(item:typeof personas[number]){setBusy(item.name);try{await signInDemo("judge-"+item.role,item.role);router.push(item.route)}catch(cause){setError(cause instanceof Error?cause.message:String(cause));setBusy(null)}}
  return <div className="mx-auto max-w-6xl space-y-7 py-8"><header><p className="text-xs font-semibold uppercase tracking-widest text-accent">Congress evaluator gateway</p><h1 className="mt-2 font-display text-4xl">Choose a workflow</h1><p className="mt-3 max-w-2xl text-sm leading-6 text-ink/65">These roles are simulated for judging. Hospital accounts are issued by each site. Every API still checks its assigned role.</p></header>
    {error&&<p role="alert" className="bg-risk-high/10 p-3 text-risk-high">{error}</p>}
    <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">{personas.map(item=><button key={item.name} disabled={busy!==null} onClick={()=>void enter(item)} className="min-h-48 bg-white p-6 text-left transition duration-150 hover:-translate-y-0.5 hover:shadow-md disabled:opacity-50"><span className="text-xs uppercase tracking-wider text-accent">{item.role}</span><h2 className="mt-3 font-display text-2xl">{item.name}</h2><p className="mt-3 text-sm leading-6 text-ink/65">{item.scope}</p><span className="mt-5 inline-block text-sm font-semibold text-accent">{busy===item.name?"Opening…":"Enter workspace →"}</span></button>)}</div>
    <p className="text-xs text-ink/55">Clinical IT uses the hospital administrator role in the current authorization model. The vendor fleet console has separate authentication.</p><Link href="/home" className="text-sm text-accent underline">Back to portal</Link>
  </div>;
}
