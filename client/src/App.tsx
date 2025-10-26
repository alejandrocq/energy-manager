import React, {useCallback, useEffect, useState, useMemo, memo} from 'react'
import './App.css'
import {CategoryScale, Chart as ChartJS, Legend, LinearScale, BarElement, Title, Tooltip} from 'chart.js'
import {Bar} from 'react-chartjs-2'
import {SlClose} from "react-icons/sl";
import {FaClock, FaPlug} from "react-icons/fa6";
import {ImPower} from "react-icons/im";
import {MdEnergySavingsLeaf} from "react-icons/md";
import {FaRegChartBar} from "react-icons/fa";
import {LuHousePlug} from "react-icons/lu";
import {Modal} from "./Modal";
import {TimerSelector} from "./TimerSelector.tsx";

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
            <button className="toast-close" onClick={() => onDismiss(toast.id)}><SlClose/></button>
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
    const [timedModalPlug, setTimedModalPlug] = useState<string | null>(null)

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

    const setTimer = useCallback(async (address: string, minutes: number, desiredState: boolean) => {
        const plug = plugs.find(p => p.address === address)
        const operationKey = `timed-${address}`

        setPendingOperations(prev => ({...prev, [operationKey]: true}))
        setTimedModalPlug(null)

        const response = await fetch(`${API}/plugs/${address}/timer`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({duration_minutes: minutes, desired_state: desiredState})
        })

        if (response.ok) {
            const hours = Math.floor(minutes / 60)
            const mins = minutes % 60
            const durationStr = hours > 0
                ? `${hours}h ${mins > 0 ? mins + 'm' : ''}`
                : `${mins}m`
            const stateStr = desiredState ? 'ON' : 'OFF'
            const currentStateStr = desiredState ? 'OFF' : 'ON'
            showToast('success', `${plug?.name}: Turned ${currentStateStr}, will turn ${stateStr} in ${durationStr}`)
            await fetchPlugs()
            if (open === address) await fetchEnergy(address)
        } else {
            showToast('error', `${plug?.name}: Failed to set timer`)
        }

        setPendingOperations(prev => ({...prev, [operationKey]: false}))
    }, [plugs, showToast, fetchPlugs, fetchEnergy, open])

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

            <div className="flex justify-center mb-5">
                <h1 className="flex items-center gap-1 text-3xl md:text-4xl font-bold">
                    <MdEnergySavingsLeaf className="inline-block align-middle size-18 text-green-700"/>
                    Energy Manager
                </h1>
            </div>
            <ul className="list-none p-0">
                <h2 className="flex items-center gap-1 text-2xl font-bold mb-4"><LuHousePlug/>Plugs</h2>
                {plugs.map(p => (
                    <li
                        key={p.address}
                        className={`
                            mb-4 border border-[#eee] rounded-lg overflow-hidden
                            ${p.enabled ? 'bg-white' : 'opacity-60 bg-[#f8f9fa] border-[#e9ecef]'}
                        `}
                    >
                        <div className="flex flex-col md:flex-row items-center gap-1 md:gap-2 p-[12px] cursor-pointer bg-[#f9f9f9] hover:bg-[#eef6ff]" onClick={() => expand(p.address)}>
                            <span className="text-5xl md:text-2xl"><FaPlug/></span>
                            <span className="flex-1">{p.name}</span>
                            {p.timer_remaining != null && (
                                <div className="flex items-center gap-1 text-green-800">
                                    <FaClock/> {fmtTime(p.timer_remaining)}
                                </div>
                            )}
                            {p.current_power != null && (
                                <div className="flex items-center gap-1 text-blue-500">
                                    <ImPower/> {p.current_power} W
                                </div>
                            )}
                            <button
                                className={`
                                    w-full md:w-[90px] h-[35px] mx-1 m-2 md:m-0 bg-gradient-to-r from-blue-600 to-blue-800 text-white rounded
                                    text-[0.9rem] shadow-md border-none cursor-pointer
                                    transition-shadow duration-300
                                    hover:from-blue-800 hover:to-blue-900 hover:shadow-lg
                                    disabled:opacity-50 disabled:cursor-not-allowed
                                `}
                                disabled={pendingOperations[`enable-${p.address}`]}
                                onClick={(e) => toggleEnable(p.address, e)}>
                                {pendingOperations[`enable-${p.address}`] ?
                                    <span className="spinner-small"></span> :
                                    p.enabled ? 'Disable' : 'Enable'}
                            </button>
                            {p.enabled && (
                                <>
                                    <button
                                        className={`
                                            w-full md:w-[90px] h-[35px] text-[0.9rem] rounded border-none cursor-pointer
                                            transition-shadow duration-200
                                            ${p.is_on
                                                ? 'bg-green-600 hover:bg-green-700 shadow-md border border-green-600'
                                                : 'bg-red-600 hover:bg-red-700 shadow-md border border-red-600'}
                                            text-white
                                            disabled:opacity-50 disabled:cursor-not-allowed
                                        `}
                                        disabled={pendingOperations[`toggle-${p.address}`]}
                                        onClick={e => {
                                            e.stopPropagation()
                                            togglePlug(p)
                                        }}>
                                        {pendingOperations[`toggle-${p.address}`] ?
                                            <span className="spinner-small"></span> :
                                            p.is_on ? 'On' : 'Off'}
                                    </button>
                                    <button
                                        className="w-full md:w-[110px] h-[35px] mx-1 m-2 md:m-0 bg-gradient-to-r from-purple-600 to-purple-800 text-white rounded text-[0.9rem] shadow-md border-none cursor-pointer transition-shadow duration-300 hover:from-purple-800 hover:to-purple-900 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1"
                                        onClick={e => {
                                            e.stopPropagation()
                                            setTimedModalPlug(p.address)
                                        }}
                                        disabled={pendingOperations[`timed-${p.address}`]}
                                    >
                                        {pendingOperations[`timed-${p.address}`] ? (
                                            <span className="spinner-small"></span>
                                        ) : (
                                            <>
                                                <FaClock className="w-3 h-3" />
                                                <span>Timer</span>
                                            </>
                                        )}
                                    </button>
                                </>
                            )}
                        </div>
                        {open === p.address && energyData[p.address] && (
                            <>
                                <div className="p-[12px] bg-[#fafafa] border-t-1 border-t-[#eee] border-t-solid border-b-1 border-b-[#eee] border-b-solid text-[0.9rem] ">
                                    <p><strong>Address:</strong> {p.address}</p>
                                    {p.periods.length > 0 && (
                                        <>
                                            <p><strong>Periods:</strong></p>
                                            <ul className="list-none p-0 m-0">
                                                {p.periods.map((period) => (
                                                    <li key={`${period.start_hour}-${period.end_hour}-${period.target_hour}`} className="text-[0.9rem]">
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
                                                    backgroundColor: '#6366f1'
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

            <h2 className="flex items-center gap-1 text-2xl font-bold"><FaRegChartBar/>Today's prices</h2>
            <div className="chart-container">
                <Bar
                    data={{
                        labels: prices.map(pt => pt.hour.toString()),
                        datasets: [
                            {
                                label: 'Price (€/kWh)',
                                data: prices.map(pt => pt.value),
                                backgroundColor: '#6366f1'
                            }
                        ]
                    }}
                    options={{
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {position: 'top'},
                        },
                        scales: {
                            y: {beginAtZero: true}
                        }
                    }}
                />
            </div>

            <Modal
                isOpen={timedModalPlug !== null}
                onClose={() => setTimedModalPlug(null)}
                title="Set Timer"
            >
                <TimerSelector
                    onSelect={(minutes, desiredState) => timedModalPlug && setTimer(timedModalPlug, minutes, desiredState)}
                    onCancel={() => setTimedModalPlug(null)}
                />
            </Modal>
        </div>
    )
}

export default App
