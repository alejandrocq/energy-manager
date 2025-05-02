import React, {useEffect, useState} from 'react'
import './App.css'
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
} from 'chart.js'
import {Line} from 'react-chartjs-2'

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    Title,
    Tooltip,
    Legend
)

interface Period {
    start_hour: number
    end_hour: number
    runtime_human: string
    target_hour: number | null
    target_price: number | null
}

interface Plug {
    name: string
    address: string
    is_on: boolean | null
    timer_remaining: number | null
    periods: Period[]
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

const App: React.FC = () => {
    const [plugs, setPlugs] = useState<Plug[]>([])
    const [open, setOpen] = useState<string | null>(null)
    const [energyData, setEnergyData] = useState<Record<string, DataPoint[]>>({})
    const [prices, setPrices] = useState<DataPoint[]>([])

    const fetchPlugs = async () => {
        const res = await fetch(`${API}/plugs`)
        setPlugs(await res.json())
    }

    const fetchEnergy = async (addr: string) => {
        const res = await fetch(`${API}/plugs/${addr}/energy`)
        const data = await res.json()
        setEnergyData(ed => ({...ed, [addr]: data}))
    }

    const fetchPrices = async () => {
        const res = await fetch(`${API}/prices`)
        setPrices(await res.json())
    }

    useEffect(() => {
        fetchPlugs()
        fetchPrices()
        const interval = setInterval(() => {
            fetchPlugs()
        }, 10000)
        return () => clearInterval(interval)
    }, [])

    const expand = (addr: string) => {
        if (open === addr) setOpen(null)
        else {
            setOpen(addr)
            fetchEnergy(addr)
        }
    }

    const togglePlug = async (plug: Plug) => {
        if (!plug.is_on) {
            await fetch(`${API}/plugs/${plug.address}/on`, {method: 'POST'})
        } else {
            await fetch(`${API}/plugs/${plug.address}/off`, {method: 'POST'})
        }
        await fetchPlugs()
        if (open === plug.address) {
            await fetchEnergy(plug.address)
        }
    }

    return (
        <div className="app-container">
            <h1>⚡️ Energy Manager</h1>
            <ul className="plug-list">
                {plugs.map(p => (
                    <li key={p.address} className="plug-item">
                        <div className="plug-header" onClick={() => expand(p.address)}>
                            <span className="plug-icon">🔌</span>
                            <span className="plug-name">{p.name}</span>
                            {p.timer_remaining != null && (
                                <span className="timer-label">⏳ {fmtTime(p.timer_remaining)}</span>
                            )}
                            <button className={`plug-toggle-btn ${p.is_on ? 'on' : 'off'}`}
                                    onClick={e => {
                                        e.stopPropagation()
                                        togglePlug(p)
                                    }}>
                                {p.is_on ? 'On' : 'Off'}
                            </button>
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
                                    <Line
                                        data={{
                                            labels: energyData[p.address].map(pt => pt.hour.toString()),
                                            datasets: [
                                                {
                                                    label: 'Energy (kWh)',
                                                    data: energyData[p.address].map(pt => pt.value),
                                                    borderColor: '#007acc',
                                                    backgroundColor: 'rgba(0,122,204,0.2)'
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
                <Line
                    data={{
                        labels: prices.map(pt => pt.hour.toString()),
                        datasets: [
                            {
                                label: 'Price (€/kWh)',
                                data: prices.map(pt => pt.value),
                                borderColor: '#e67e22',
                                backgroundColor: 'rgba(230,126,34,0.2)'
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
