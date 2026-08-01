"use client";

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Transaction } from "@/lib/fetchState";

interface TransactionChartProps {
  transactions: Transaction[];
  startBalance: number;
}

export default function TransactionChart({ transactions, startBalance }: TransactionChartProps) {
  let running = startBalance;
  const data = transactions.map((tx) => {
    running += tx.type === "revenue" ? tx.amount : -tx.amount;
    return {
      time: new Date(tx.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      balance: Number(running.toFixed(2)),
    };
  });

  return (
    <div className="card p-4">
      <h2 className="text-sm uppercase tracking-wide text-gray-400 mb-3">Balance History</h2>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="balanceFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#00ff88" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#00ff88" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f1f2b" />
            <XAxis dataKey="time" stroke="#666" fontSize={10} />
            <YAxis stroke="#666" fontSize={10} />
            <Tooltip
              contentStyle={{ background: "#12121a", border: "1px solid #1f1f2b", fontSize: 12 }}
              labelStyle={{ color: "#999" }}
            />
            <Area type="monotone" dataKey="balance" stroke="#00ff88" fill="url(#balanceFill)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
