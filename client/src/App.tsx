import React, {useCallback, useEffect, useState, useMemo, memo} from 'react'
import './App.css'
import {CategoryScale, Chart as ChartJS, Legend, LinearScale, BarElement, Title, Tooltip} from 'chart.js'
import {Bar} from 'react-chartjs-2'

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend
)

type ToastType = 'success' | 'error'

interface Toast {
    id: string;
    type: ToastType;
    message: string;
    duration?: number;
}

interface Period {
    start_hour: number
    end_hour: number
    runtime_human: string
    target_hour: number | null
    target_price: number | null
}

interface Plug {
    enabled: boolean
    name: string
    address: string
    is_on: boolean | null
    timer_remaining: number | null
    periods: Period[]
    current_power?: number | null
}

interface DataPoint {
    hour: number
    value: number
}

const API = '/api'

const fmtTime = (sec: number): string => {
    const h = Math.floor(sec / 3600)
    const m = Math.floor((sec % 3600) / 60)
    const s = sec % 60
    return `${h.toString().padStart(2, '0')}:${m
        .toString()
        .padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const ToastNotification = memo(({toast, onDismiss}: { toast: Toast, onDismiss: (id: string) => void }) => {
    return (
        <div className={`toast ${toast.type}`}>
            <div className="toast-message">{toast.message}</div>
            <button className="toast-close" onClick={() => onDismiss(toast.id)}>✕</button>
        </div>
    );
});

const useToasts = () => {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const dismissToast = useCallback((id: string) => {
        setToasts(prevToasts => prevToasts.filter(toast => toast.id !== id));
    }, []);

    const showToast = useCallback((type: ToastType, message: string, duration = 3000) => {
        const id = 'toast-' + Date.now();
        const toast: Toast = {id, type, message, duration};

        setToasts(prevToasts => [...prevToasts, toast]);

        if (duration > 0) {
            setTimeout(() => {
                dismissToast(id);
            }, duration);
        }

        return id;
    }, [dismissToast]);

    const ToastContainer = useMemo(() => {
        return (
            <div className="toast-container">
                {toasts.map(toast => (
                    <ToastNotification
                        key={toast.id}
                        toast={toast}
                        onDismiss={dismissToast}
                    />
                ))}
            </div>
        );
    }, [toasts, dismissToast]);

    return {showToast, ToastContainer};
};

const App: React.FC = () => {
    const [plugs, setPlugs] = useState<Plug[]>([])
    const [open, setOpen] = useState<string | null>(null)
    const [energyData, setEnergyData] = useState<Record<string, DataPoint[]>>({})
    const [prices, setPrices] = useState<DataPoint[]>([])
    const [loading, setLoading] = useState<boolean>(false)
    const [pendingOperations, setPendingOperations] = useState<Record<string, boolean>>({})

    const {showToast, ToastContainer} = useToasts();

    const fetchPlugs = useCallback(async () => {
        const res = await fetch(`${API}/plugs`)
        if (!res.ok) showToast('error', 'Failed to fetch plugs')
        else setPlugs(await res.json())
    }, [showToast])

    const fetchEnergy = useCallback(async (addr: string) => {
        const res = await fetch(`${API}/plugs/${addr}/energy`)
        if (!res.ok) showToast('error', `Failed to fetch energy data for ${addr}`)
        else {
            const data = await res.json()
            setEnergyData(ed => ({...ed, [addr]: data}))
        }
    }, [showToast])

    const fetchPrices = useCallback(async () => {
        const res = await fetch(`${API}/prices`)
        if (!res.ok) showToast('error', 'Failed to fetch prices data')
        else setPrices(await res.json())
    }, [showToast])

    useEffect(() => {
        setLoading(true)
        Promise.all([fetchPlugs(), fetchPrices()])
            .finally(() => setLoading(false))

        const interval = setInterval(() => {
            fetchPlugs()
        }, 10000)
        return () => clearInterval(interval)
    }, [fetchPlugs, fetchPrices])

    const expand = useCallback((addr: string) => {
        if (open === addr) setOpen(null)
        else {
            setOpen(addr)
            fetchEnergy(addr)
        }
    }, [open, fetchEnergy])

    const togglePlug = useCallback(async (plug: Plug) => {
        const operationKey = `toggle-${plug.address}`
        setPendingOperations(prev => ({...prev, [operationKey]: true}))

        let response;
        if (!plug.is_on) {
            response = await fetch(`${API}/plugs/${plug.address}/on`, {method: 'POST'})
        } else {
            response = await fetch(`${API}/plugs/${plug.address}/off`, {method: 'POST'})
        }

        const action = plug.is_on ? 'OFF' : 'ON'

        if (response.ok) {
            showToast('success', `${plug.name}: Turned ${action} successfully`)
            await fetchPlugs()
            if (open === plug.address) await fetchEnergy(plug.address)
        } else {
            showToast('error', `${plug.name}: Failed to turn ${action}`)
        }

        setPendingOperations(prev => ({...prev, [operationKey]: false}))
    }, [showToast, fetchPlugs, fetchEnergy, open])

    const toggleEnable = useCallback(async (address: string, e: React.MouseEvent) => {
        e.stopPropagation()
        const operationKey = `enable-${address}`
        const plug = plugs.find(p => p.address === address)

        setPendingOperations(prev => ({...prev, [operationKey]: true}))

        const action = plug?.enabled ? 'disabled' : 'enabled'
        const response = await fetch(`${API}/plugs/${address}/toggle_enable`, {method: 'POST'})

        if (response.ok) {
            showToast('success', `${plug?.name}: ${action} successfully`)
            await fetchPlugs()
        } else {
            showToast('error', `${plug?.name}: Could not be ${action}`)
        }

        setPendingOperations(prev => ({...prev, [operationKey]: false}))
    }, [plugs, showToast, fetchPlugs])

    if (loading) {
        return (
            <div className="app-container loading-container">
                <div className="spinner"></div>
                <p>Loading...</p>
            </div>
        )
    }

    return (
        <div className="app-container">
            {ToastContainer}

            <h1>⚡️ Energy Manager</h1>
            <ul className="plug-list">
                {plugs.map(p => (
                    <li key={p.address} className={`plug-item ${p.enabled ? '' : 'disabled'}`}>
                        <div className="plug-header" onClick={() => expand(p.address)}>
                            <span className="plug-icon">🔌</span>
                            <span className="plug-name">{p.name}</span>
                            {p.timer_remaining != null && (
                                <span className="timer-label">
                                    ⏳ {fmtTime(p.timer_remaining)}
                                </span>
                            )}
                            {p.current_power != null && (
                                <span className="power_label">
                                    ⚡ {p.current_power} W
                                </span>
                            )}
                            <button
                                className={`enable-disable-btn`}
                                disabled={pendingOperations[`enable-${p.address}`]}
                                onClick={(e) => toggleEnable(p.address, e)}>
                                {pendingOperations[`enable-${p.address}`] ?
                                    <span className="spinner-small"></span> :
                                    p.enabled ? 'Disable' : 'Enable'}
                            </button>
                            {p.enabled && (
                                <button
                                    className={`plug-toggle-btn ${p.is_on ? 'on' : 'off'}`}
                                    disabled={pendingOperations[`toggle-${p.address}`]}
                                    onClick={e => {
                                        e.stopPropagation()
                                        togglePlug(p)
                                    }}>
                                    {pendingOperations[`toggle-${p.address}`] ?
                                        <span className="spinner-small"></span> :
                                        p.is_on ? 'On' : 'Off'}
                                </button>
                            )}
                        </div>
                        {open === p.address && energyData[p.address] && (
                            <>
                                <div className="plug-details">
                                    <p><strong>Address:</strong> {p.address}</p>
                                    {p.periods.length > 0 && (
                                        <>
                                            <p><strong>Periods:</strong></p>
                                            <ul className="period-list">
                                                {p.periods.map((period, idx) => (
                                                    <li key={idx} className="period-item">
                                                        {period.start_hour}:00 - {period.end_hour}:00 | Runtime {period.runtime_human} |
                                                        Target {period.target_hour}:00 ({period.target_price} €/kWh)
                                                    </li>
                                                ))
                                                }
                                            </ul>
                                        </>
                                    )}
                                </div>
                                <div className="chart-container">
                                    <Bar
                                        data={{
                                            labels: energyData[p.address].map(pt => pt.hour.toString()),
                                            datasets: [
                                                {
                                                    label: 'Energy (kWh)',
                                                    data: energyData[p.address].map(pt => pt.value),
                                                    borderColor: '#007acc',
                                                    backgroundColor: '#007acc'
                                                }
                                            ]
                                        }}
                                        options={{
                                            responsive: true,
                                            maintainAspectRatio: false,
                                            plugins: {
                                                legend: {position: 'top'},
                                                title: {display: true, text: 'Hourly Energy Usage'}
                                            }
                                        }}
                                    />
                                </div>
                            </>
                        )}
                    </li>
                ))}
            </ul>

            <h2>📈 Today’s Price Curve</h2>
            <div className="chart-container">
                <Bar
                    data={{
                        labels: prices.map(pt => pt.hour.toString()),
                        datasets: [
                            {
                                label: 'Price (€/kWh)',
                                data: prices.map(pt => pt.value),
                                borderColor: '#007acc',
                                backgroundColor: '#007acc'
                            }
                        ]
                    }}
                    options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {position: 'top'},
                            title: {display: true, text: 'Electricity Prices Today'}
                        },
                        scales: {
                            y: {beginAtZero: true}
                        }
                    }}
                />
            </div>
        </div>
    )
}

export default App
