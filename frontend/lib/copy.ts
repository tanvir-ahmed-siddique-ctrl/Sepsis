export type Locale = "en" | "bn";

const STORAGE_KEY = "predictrx-locale";

export const COPY = {
  en: {
    disclaimer:
      "Research prototype—not approved for clinical use. The risk score supports, but does not replace, clinical judgment.",
    nav: {
      overview: "ICU overview",
      chart: "Bedside chart",
      ward: "Ward NEWS2",
      users: "Users",
      alerts: "Alerts",
      handoff: "Handoff",
      pilot: "Silent pilot",
      integration: "Integration hub",
      model: "Model transparency",
      readiness: "Readiness passport",
      presentation: "Presentation",
      signIn: "Sign in",
    },
    attention: {
      title: "New TrustGate alert",
      body: "needs clinician review",
      review: "Review",
      dismiss: "Hide banner",
    },
    trust: {
      alert: "Alert",
      watch: "Watch",
      verify_data: "Verify data",
      abstain: "Abstain",
    },
    risk: {
      insufficient_data: "Insufficient data",
      stable: "Stable",
      watch: "Watch",
      high_risk: "High risk",
    },
    scoreLabel: "Challenge-label early warning",
  },
  bn: {
    disclaimer:
      "গবেষণা প্রোটোটাইপ—ক্লিনিক্যাল ব্যবহারের অনুমোদন নেই। ঝুঁকি স্কোর ক্লিনিক্যাল সিদ্ধান্তের বিকল্প নয়।",
    nav: {
      overview: "আইসিইউ ওভারভিউ",
      chart: "বেডসাইড চার্ট",
      ward: "ওয়ার্ড NEWS2",
      users: "ব্যবহারকারী",
      alerts: "অ্যালার্ট",
      handoff: "হ্যান্ডঅফ",
      pilot: "নীরব পাইলট",
      integration: "ইন্টিগ্রেশন হাব",
      model: "মডেল স্বচ্ছতা",
      readiness: "প্রস্তুতি পাসপোর্ট",
      presentation: "প্রেজেন্টেশন",
      signIn: "সাইন ইন",
    },
    attention: {
      title: "নতুন TrustGate অ্যালার্ট",
      body: "ক্লিনিশিয়ানের পর্যালোচনা প্রয়োজন",
      review: "পর্যালোচনা",
      dismiss: "ব্যানার লুকান",
    },
    trust: {
      alert: "অ্যালার্ট",
      watch: "নজরদারি",
      verify_data: "ডেটা যাচাই করুন",
      abstain: "বিরত থাকুন",
    },
    risk: {
      insufficient_data: "পর্যাপ্ত তথ্য নেই",
      stable: "স্থিতিশীল",
      watch: "নজরদারি",
      high_risk: "উচ্চ ঝুঁকি",
    },
    scoreLabel: "চ্যালেঞ্জ-লেবেল আর্লি ওয়ার্নিং",
  },
} as const;

export function readLocale(): Locale {
  if (typeof window === "undefined") return "en";
  return window.localStorage.getItem(STORAGE_KEY) === "bn" ? "bn" : "en";
}

export function writeLocale(locale: Locale): void {
  window.localStorage.setItem(STORAGE_KEY, locale);
}
