/** Path → product surface helpers for shell selection. */

export type ProductSurface =
  | "public"
  | "auth"
  | "hospital"
  | "deployment"
  | "vendor"
  | "customer"
  | "evaluation"
  | "presentation";

const AUTH = new Set(["/signin", "/login", "/activate"]);
const EVAL = new Set(["/system-check", "/evaluator", "/judge", "/judge-guide"]);
const PRESENTATION = new Set(["/presentation"]);

const PUBLIC_PREFIXES = [
  "/",
  "/home",
  "/product",
  "/aurie",
  "/solutions",
  "/for-hospitals",
  "/deployment-integration",
  "/security",
  "/resources",
  "/about",
  "/contact",
  "/services",
  "/docs",
  "/evidence",
  "/model",
  "/business",
  "/workflows",
  "/api-reference",
];

/** Integration / commissioning surfaces — not general hospital-admin pages. */
const DEPLOY_PREFIXES = [
  "/deploy",
  "/app/admin/integrations",
  "/app/admin/connections",
  "/app/admin/readiness",
  "/app/admin/operations",
  "/app/admin/pilot",
  "/app/admin/licence",
  "/hospital-admin",
  "/admin/setup",
  "/integration",
  "/connection",
  "/pilot",
  "/readiness",
  "/operations",
];

/** Hospital-admin product pages stay in the hospital shell. */
const HOSPITAL_ADMIN_PREFIXES = [
  "/app/admin/overview",
  "/app/admin/users",
  "/app/admin/setup",
  "/admin/users",
];

export function resolveSurface(pathname: string): ProductSurface {
  if (PRESENTATION.has(pathname)) return "presentation";
  if (AUTH.has(pathname)) return "auth";
  if (EVAL.has(pathname) || pathname.startsWith("/evaluator")) return "evaluation";
  if (pathname.startsWith("/platform") || pathname.startsWith("/super-admin")) return "vendor";
  if (pathname.startsWith("/portal")) return "customer";
  if (HOSPITAL_ADMIN_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(prefix + "/"))) return "hospital";
  if (DEPLOY_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(prefix + "/"))) return "deployment";
  if (
    pathname.startsWith("/app") ||
    pathname.startsWith("/icu") ||
    pathname.startsWith("/ward") ||
    pathname.startsWith("/chart") ||
    pathname.startsWith("/alerts") ||
    pathname.startsWith("/handoff") ||
    pathname.startsWith("/staff") ||
    pathname.startsWith("/profile") ||
    pathname.startsWith("/patient") ||
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/admin")
  ) {
    return "hospital";
  }
  if (PUBLIC_PREFIXES.some((prefix) => pathname === prefix || (prefix !== "/" && pathname.startsWith(prefix + "/")))) {
    return "public";
  }
  if (pathname === "/") return "public";
  return "public";
}

export function isFullBleedSurface(surface: ProductSurface): boolean {
  return surface === "public" || surface === "auth" || surface === "presentation";
}
