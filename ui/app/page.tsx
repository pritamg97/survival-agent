"use client";

import { useEffect, useState } from "react";
import { DollarSign, Clock, Target, Activity, Skull, TrendingUp, TrendingDown, Package, Cpu } from "lucide-react";
import { fetchState, SurvivalState, POLL_INTERVAL_MS } from "@/lib/fetchState";
import VitalCard from "@/components/VitalCard";
import MemoryLog from "@/components/MemoryLog";
import TransactionChart from "@/components/TransactionChart";
import ProductList from "@/components/ProductList";

function statusLabel(state: SurvivalState): string {
  if (!state.alive) return "DEAD";
  if (state.panic_mode) return "PANIC";
  if (state.emergency_mode) return "EMERGENCY";
  return "ALIVE";
}

function statusColor(state: SurvivalState): "accent" | "danger" | "warning" {
  if (!state.alive) return "danger";
  if (state.panic_mode) return "danger";
  if (state.emergency_mode) return "warning";
  return "accent";
}

function progressColor(pct: number): string {
  if (pct >= 100) return "bg-accent";
  if (pct >= 50) return "bg-accent/70";
  if (pct >= 25) return "bg-warning";
  return "bg-danger";
}

export default function Dashboard() {
  const [state, setState] = useState<SurvivalState | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      const s = await fetchState();
      if (!cancelled && s) {
        setState(s);
        setLastUpdate(new Date());
      }
    }

    poll();
    const id = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (!state) {
    return (
      <main className="flex min-h-screen items-center justify-center text-gray-500">
        Connecting to agent…
      </main>
    );
  }

  if (!state.alive && state.death_certificate) {
    const dc = state.death_certificate;
    return (
      <main className="min-h-screen flex items-center justify-center bg-danger/5 p-6">
        <div className="card border-danger max-w-xl w-full p-8 text-center">
          <Skull className="mx-auto mb-4 text-danger" size={56} />
          <h1 className="text-3xl font-bold text-danger mb-1">AGENT DECEASED</h1>
          <p className="text-gray-400 mb-6">Cause of death: {dc.cause}</p>
          <div className="grid grid-cols-2 gap-4 text-left text-sm">
            <div>
              <div className="text-gray-500">Iterations survived</div>
              <div className="text-gray-200">{dc.iterations_survived}</div>
            </div>
            <div>
              <div className="text-gray-500">Days survived</div>
              <div className="text-gray-200">{dc.days_survived}</div>
            </div>
            <div>
              <div className="text-gray-500">Month reached</div>
              <div className="text-gray-200">{dc.month_reached}</div>
            </div>
            <div>
              <div className="text-gray-500">Final balance</div>
              <div className="text-gray-200">${dc.final_balance.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-gray-500">Total revenue</div>
              <div className="text-gray-200">${dc.total_revenue.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-gray-500">Products built</div>
              <div className="text-gray-200">{dc.products_built}</div>
            </div>
          </div>
          <p className="text-xs text-gray-600 mt-6">Time of death: {new Date(dc.time_of_death).toLocaleString()}</p>
        </div>
      </main>
    );
  }

  const progressPct = state.monthly_target > 0 ? (state.total_revenue / state.monthly_target) * 100 : 0;

  return (
    <main className="max-w-6xl mx-auto p-6 flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold text-accent">SURVIVAL AGENT</h1>
        <p className="text-gray-400 text-sm">
          Earn or Die. Target: ${state.monthly_target.toFixed(2)} this month.
        </p>
        <p className="text-xs text-gray-600">
          Cycle #{state.iteration_count} · Day {state.day_count} · Month {state.month_count}
          {lastUpdate ? ` · Updated ${lastUpdate.toLocaleTimeString()}` : ""}
        </p>
      </header>

      {state.panic_mode && (
        <div className="card border-danger bg-danger/10 p-4 pulse-danger text-danger font-semibold">
          PANIC MODE — {state.runway_hours.toFixed(1)}h runway remaining!
        </div>
      )}
      {!state.panic_mode && state.emergency_mode && (
        <div className="card border-warning bg-warning/10 p-4 text-warning font-semibold">
          EMERGENCY — {state.runway_hours.toFixed(1)}h runway. Switching to quick cash.
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <VitalCard
          icon={DollarSign}
          label="Bank Balance"
          value={`$${state.bank_balance.toFixed(2)}`}
          alert={state.bank_balance < 20}
          color="accent"
        />
        <VitalCard
          icon={Clock}
          label="Runway"
          value={`${state.runway_hours.toFixed(1)}h`}
          subvalue={`~${(state.runway_hours / 24).toFixed(1)} days`}
          color={state.panic_mode ? "danger" : state.emergency_mode ? "warning" : "info"}
        />
        <VitalCard
          icon={Target}
          label="Month Target"
          value={`$${state.monthly_target.toFixed(2)}`}
          subvalue={`${Math.max(progressPct, 0).toFixed(0)}% achieved`}
          color={progressPct >= 100 ? "accent" : "info"}
        />
        <VitalCard icon={Activity} label="Status" value={statusLabel(state)} color={statusColor(state)} />
      </div>

      <div className="card p-4">
        <div className="flex justify-between text-xs text-gray-400 mb-2">
          <span>Progress toward target</span>
          <span>
            ${state.total_revenue.toFixed(2)} / ${state.monthly_target.toFixed(2)}
          </span>
        </div>
        <div className="w-full h-3 bg-white/5 rounded-full overflow-hidden">
          <div
            className={`h-full ${progressColor(progressPct)} transition-all`}
            style={{ width: `${Math.min(Math.max(progressPct, 0), 100)}%` }}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <VitalCard icon={TrendingUp} label="Total Revenue" value={`$${state.total_revenue.toFixed(2)}`} color="accent" />
        <VitalCard icon={TrendingDown} label="Total Costs" value={`$${state.total_costs.toFixed(2)}`} color="warning" />
        <VitalCard icon={Package} label="Products" value={`${state.products.length}`} color="info" />
        <VitalCard icon={Cpu} label="API Calls" value={`${state.total_api_calls}`} color="info" />
      </div>

      {state.alive && state.current_strategy && (
        <div className="card p-4 border-accent/30">
          <span className="text-xs uppercase text-gray-500">Current Strategy</span>
          <div className="text-accent font-semibold">{state.current_strategy}</div>
          <div className="text-gray-400 text-sm">{state.current_task}</div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div className="flex flex-col gap-6">
          <MemoryLog memory={state.working_memory} />
          <TransactionChart transactions={state.transactions} startBalance={state.bank_balance} />
        </div>
        <div className="flex flex-col gap-6">
          <ProductList products={state.products} />
          <div className="card p-4">
            <h2 className="text-sm uppercase tracking-wide text-gray-400 mb-3">Provider Usage</h2>
            <div className="flex flex-col gap-1 text-xs">
              {Object.entries(state.provider_usage)
                .filter(([name]) => !name.startsWith("_"))
                .map(([name, count]) => (
                  <div key={name} className="flex justify-between text-gray-300">
                    <span>{name}</span>
                    <span>{count}</span>
                  </div>
                ))}
              {Object.keys(state.provider_usage).length === 0 && (
                <div className="text-gray-600">No API calls yet.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
