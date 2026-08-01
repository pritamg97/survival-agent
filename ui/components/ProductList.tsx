import { Product } from "@/lib/fetchState";

const STATUS_STYLE: Record<string, string> = {
  live: "bg-accent/20 text-accent",
  dead: "bg-danger/20 text-danger",
  building: "bg-warning/20 text-warning",
};

export default function ProductList({ products }: { products: Product[] }) {
  return (
    <div className="card p-4">
      <h2 className="text-sm uppercase tracking-wide text-gray-400 mb-3">Products ({products.length})</h2>
      <div className="flex flex-col gap-2 max-h-96 overflow-y-auto">
        {products.length === 0 && <div className="text-gray-600 text-xs">No products yet.</div>}
        {products.map((p, i) => (
          <div key={i} className="flex items-center justify-between text-xs border-b border-white/5 pb-2">
            <div className="flex flex-col">
              <span className="text-gray-200 font-semibold">{p.name}</span>
              <span className="text-gray-500">
                ${p.price.toFixed(2)} · {p.customers} customers · ${p.revenue.toFixed(2)} earned
              </span>
            </div>
            <span className={`px-2 py-0.5 rounded text-[10px] uppercase ${STATUS_STYLE[p.status] || ""}`}>
              {p.status}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
