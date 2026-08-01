export interface Product {
  name: string;
  description: string;
  price: number;
  status: "live" | "dead" | "building";
  url: string;
  customers: number;
  revenue: number;
  created_at: string;
  age_cycles?: number;
}

export interface Transaction {
  type: "cost" | "revenue" | "burn";
  amount: number;
  description: string;
  timestamp: string;
}

export interface DeathCertificate {
  cause: string;
  time_of_death: string;
  iterations_survived: number;
  days_survived: number;
  month_reached: number;
  total_revenue: number;
  total_costs: number;
  total_burn: number;
  final_balance: number;
  products_built: number;
}

export interface SurvivalState {
  alive: boolean;
  bank_balance: number;
  burn_rate_per_hour: number;
  runway_hours: number;
  iteration_count: number;
  day_count: number;
  month_count: number;
  monthly_target: number;
  current_strategy: string | null;
  current_task: string | null;
  emergency_mode: boolean;
  panic_mode: boolean;
  naive_mode: boolean;
  products: Product[];
  transactions: Transaction[];
  total_revenue: number;
  total_costs: number;
  total_burn: number;
  working_memory: string[];
  reason_of_death: string | null;
  death_certificate: DeathCertificate | null;
  provider_usage: Record<string, number>;
  total_api_calls: number;
  total_tokens_used: number;
}

const GITHUB_USER = process.env.NEXT_PUBLIC_GITHUB_USER || "";
const GITHUB_REPO = process.env.NEXT_PUBLIC_GITHUB_REPO || "";
const GITHUB_BRANCH = process.env.NEXT_PUBLIC_GITHUB_BRANCH || "main";

export function getRawStateUrl(): string {
  return `https://raw.githubusercontent.com/${GITHUB_USER}/${GITHUB_REPO}/${GITHUB_BRANCH}/state/state.json`;
}

export async function fetchState(): Promise<SurvivalState | null> {
  const url = `${getRawStateUrl()}?t=${Date.now()}`;
  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as SurvivalState;
  } catch {
    return null;
  }
}

export const POLL_INTERVAL_MS = 30_000;
