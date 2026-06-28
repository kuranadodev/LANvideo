export function LogPanel({ logs }: { logs: string[] }) { return <section className="card logs"><h2>日志</h2>{logs.map((l,i)=><div key={i}>{l}</div>)}</section>; }
