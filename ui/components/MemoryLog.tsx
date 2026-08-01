interface MemoryLogProps {
  memory: string[];
}

export default function MemoryLog({ memory }: MemoryLogProps) {
  const entries = [...memory].reverse().slice(0, 30);

  return (
    <div className="card p-4">
      <h2 className="text-sm uppercase tracking-wide text-gray-400 mb-3">Memory Log</h2>
      <div className="max-h-96 overflow-y-auto flex flex-col gap-2 text-xs">
        {entries.length === 0 && <div className="text-gray-600">No memory entries yet.</div>}
        {entries.map((entry, i) => (
          <div key={i} className="border-l-2 border-accent/40 pl-2 py-0.5 text-gray-300">
            {entry}
          </div>
        ))}
      </div>
    </div>
  );
}
