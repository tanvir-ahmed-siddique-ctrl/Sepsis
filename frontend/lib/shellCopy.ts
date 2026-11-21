import type { Locale } from "@/lib/copy";

/** Chrome labels for hospital / IT / admin / vendor shells (Bangla when locale=bn). */
const BN: Record<string, string> = {
  // Surfaces
  "Hospital clinical": "হাসপাতাল ক্লিনিক্যাল",
  "Hospital administration": "হাসপাতাল প্রশাসন",
  Deployment: "ডিপ্লয়মেন্ট",
  "Vendor Control Plane": "ভেন্ডর কন্ট্রোল প্লেন",
  "Fleet Operator Console": "ফ্লিট অপারেটর কনসোল",
  "Customer Portal": "কাস্টমার পোর্টাল",
  "Evaluation Environment": "ইভ্যালুয়েশন এনভায়রনমেন্ট",
  "Platform operations": "প্ল্যাটফর্ম অপারেশনস",
  "Deployment console": "ডিপ্লয়মেন্ট কনসোল",
  "Hospital Deployment Console": "হাসপাতাল ডিপ্লয়মেন্ট কনসোল",
  "Hospital Workspace": "হাসপাতাল ওয়ার্কস্পেস",
  "Clinical IT": "ক্লিনিক্যাল আইটি",
  // Groups
  Monitor: "মনিটর",
  Care: "কেয়ার",
  Team: "টিম",
  Administration: "প্রশাসন",
  Governance: "গভর্ন্যান্স",
  Clinical: "ক্লিনিক্যাল",
  Technical: "টেকনিক্যাল",
  Account: "অ্যাকাউন্ট",
  Overview: "ওভারভিউ",
  Interfaces: "ইন্টারফেস",
  Operations: "অপারেশনস",
  Customers: "কাস্টমার",
  Fleet: "ফ্লিট",
  // Clinical
  "ICU board": "আইসিইউ বোর্ড",
  "Ward / NEWS2": "ওয়ার্ড / NEWS2",
  Alerts: "অ্যালার্ট",
  Charting: "চার্টিং",
  Handoff: "হ্যান্ডঅফ",
  Staff: "স্টাফ",
  Profile: "প্রোফাইল",
  "ICU (read-only)": "আইসিইউ (রিড-অনলি)",
  // Admin / IT
  "Hospital overview": "হাসপাতাল ওভারভিউ",
  "Staff & access": "স্টাফ ও অ্যাক্সেস",
  "Unit settings": "ইউনিট সেটিংস",
  "Shift roster": "শিফট রোস্টার",
  "Silent evaluation": "নীরব ইভ্যালুয়েশন",
  "Staff directory": "স্টাফ ডিরেক্টরি",
  Integrations: "ইন্টিগ্রেশন",
  Connectivity: "কানেকটিভিটি",
  "Readiness gates": "রেডিনেস গেটস",
  "Ops & backup": "অপস ও ব্যাকআপ",
  "Site licence": "সাইট লাইসেন্স",
  "Deployment home": "ডিপ্লয়মেন্ট হোম",
  "Site setup": "সাইট সেটআপ",
  "HIS / interfaces": "HIS / ইন্টারফেস",
  Licence: "লাইসেন্স",
  "Fleet overview": "ফ্লিট ওভারভিউ",
  "Site diagnostics": "সাইট ডায়াগনস্টিকস",
  // Vendor
  "Control plane home": "কন্ট্রোল প্লেন হোম",
  "Organizations & sites": "অর্গানাইজেশন ও সাইট",
  Commercial: "কমার্শিয়াল",
  "Partnership / FDE": "পার্টনারশিপ / FDE",
  "Support & service": "সাপোর্ট ও সার্ভিস",
  Documents: "ডকুমেন্টস",
  "Fleet site diagnostics": "ফ্লিট সাইট ডায়াগনস্টিকস",
  "Readiness overview": "রেডিনেস ওভারভিউ",
  "Operator desk": "অপারেটর ডেস্ক",
  // Chrome
  "Sign out": "সাইন আউট",
  Minimize: "ছোট করুন",
  Language: "ভাষা",
  "Profile and security": "প্রোফাইল ও নিরাপত্তা",
  "Install app": "অ্যাপ ইনস্টল",
};

export function shellText(label: string, locale: Locale): string {
  if (locale !== "bn") return label;
  return BN[label] ?? label;
}
