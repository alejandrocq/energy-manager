import React, { useEffect, useState } from 'react';
import './App.css';

interface Plug {
    name: string;
    address: string;
    is_on: boolean | null;
    timer_remaining: number | null;
}

const API_BASE = '/api';

const fmtTime = (sec: number): string => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    return `${h.toString().padStart(2, '0')}:${m
        .toString()
        .padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
};

const App: React.FC = () => {
    const [plugs, setPlugs] = useState<Plug[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchPlugs = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/plugs`);
            const data = (await res.json()) as Plug[];
            setPlugs(data);
        } catch (err) {
            console.error('Failed to fetch plugs', err);
        }
        setLoading(false);
    };

    useEffect(() => {
        fetchPlugs();
        const interval = setInterval(fetchPlugs, 10_000);
        return () => clearInterval(interval);
    }, []);

    const toggle = async (plug: Plug) => {
        const action = plug.is_on ? 'off' : 'on';
        try {
            await fetch(`${API_BASE}/plugs/${plug.address}/${action}`, {
                method: 'POST',
            });
            fetchPlugs();
        } catch (err) {
            console.error(err);
        }
    };

    return (
        <div className="app-container">
            <h1>🔌 Energy Manager</h1>
            {loading ? (
                <p>Loading…</p>
            ) : (
                <>
                    <ul className="plug-list">
                        {plugs.map((p) => (
                            <li key={p.address}>
                                <div className="plug-info">
                                    <span className="plug-icon">🔌</span>
                                    <span className="plug-name">{p.name}</span>
                                    {p.is_on != null && (
                                        <span className="status-label">
                      {p.is_on ? '🟢 On' : '🔴 Off'}
                    </span>
                                    )}
                                    {p.timer_remaining != null && (
                                        <span className="timer-label">
                      ⏳ {fmtTime(p.timer_remaining)}
                    </span>
                                    )}
                                </div>
                                <button
                                    className={`toggle-btn ${p.is_on ? 'on' : 'off'}`}
                                    onClick={() => toggle(p)}
                                >
                  <span className="btn-icon">
                    {p.is_on ? '🔴' : '🟢'}
                  </span>
                                    {p.is_on ? 'Turn Off' : 'Turn On'}
                                </button>
                            </li>
                        ))}
                    </ul>

                    <h2>📈 Today’s Price Curve</h2>
                    <img
                        src="/api/static/prices_chart.png"
                        alt="Prices chart"
                        className="price-chart"
                    />
                </>
            )}
        </div>
    );
};

export default App;
