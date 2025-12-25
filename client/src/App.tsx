import React, {useCallback, useEffect, useState, useMemo, memo} from 'react'
import './App.css'
import {CategoryScale, Chart as ChartJS, Legend, LinearScale, BarElement, Title, Tooltip as ChartTooltip} from 'chart.js'
import {Bar} from 'react-chartjs-2'
import {SlClose} from "react-icons/sl";
import {FaCalendar, FaClock, FaPlug} from "react-icons/fa6";
import {ImPower} from "react-icons/im";
import {MdEnergySavingsLeaf, MdPowerSettingsNew, MdAutoMode} from "react-icons/md";
import {FaRegChartBar} from "react-icons/fa";
import {LuHousePlug} from "react-icons/lu";
import {Modal} from "./Modal";
import {TimerSelector} from "./TimerSelector.tsx";
import {ScheduleSelector} from "./ScheduleSelector.tsx";
import {Tooltip} from "./Tooltip";

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    ChartTooltip,
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

interface ScheduledEvent {
    id: string
    plug_address: string
    plug_name: string
    target_datetime: string
    desired_state: boolean
    duration_seconds: number | null
    type?: string  // "automatic" or "manual"
    status: string
    created_at: string
}

interface Plug {
    enabled: boolean
    name: string
    address: string
    is_on: boolean | null
    timer_remaining: number | null
    schedules?: ScheduledEvent[]
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

const fmtDatetime = (isoString: string): string => {
    const date = new Date(isoString)
    const options: Intl.DateTimeFormatOptions = {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }
    return date.toLocaleDateString(undefined, options)
}

const fmtDuration = (seconds: number | null | undefined): string => {
    if (!seconds || seconds === 0) return ''
    const h = Math.floor(seconds / 3600)
    const m = Math.floor((seconds % 3600) / 60)
    if (h > 0 && m > 0) return `${h}h ${m}m`
    if (h > 0) return `${h}h`
    return `${m}m`
}

const ToastNotification = memo(({toast, onDismiss}: { toast: Toast, onDismiss: (id: string) => void }) => {
    return (
        <div className={`toast ${toast.type}`}>
            <div className="toast-message">{toast.message}</div>
            <button className="toast-close cursor-pointer" onClick={() => onDismiss(toast.id)}><SlClose/></button>
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
    const [scheduleModalPlug, setScheduleModalPlug] = useState<string | null>(null)

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

    const createSchedule = useCallback(async (address: string, targetDatetime: string, desiredState: boolean, durationMinutes?: number) => {
        const plug = plugs.find(p => p.address === address)
        const operationKey = `schedule-${address}`

        setPendingOperations(prev => ({...prev, [operationKey]: true}))
        setScheduleModalPlug(null)

        const response = await fetch(`${API}/plugs/${address}/schedule`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                target_datetime: targetDatetime,
                desired_state: desiredState,
                duration_minutes: durationMinutes
            })
        })

        if (response.ok) {
            await response.json()
            const timeStr = fmtDatetime(targetDatetime)
            const stateStr = desiredState ? 'ON' : 'OFF'
            let message = `${plug?.name}: Scheduled to turn ${stateStr} at ${timeStr}`
            if (durationMinutes && durationMinutes > 0) {
                const h = Math.floor(durationMinutes / 60)
                const m = durationMinutes % 60
                const durationStr = h > 0
                    ? `${h}h ${m > 0 ? m + 'm' : ''}`
                    : `${m}m`
                const oppositeState = desiredState ? 'OFF' : 'ON'
                message += ` (${oppositeState} after ${durationStr})`
            }
            showToast('success', message)
            await fetchPlugs()
        } else {
            showToast('error', `${plug?.name}: Failed to create schedule`)
        }

        setPendingOperations(prev => ({...prev, [operationKey]: false}))
    }, [plugs, showToast, fetchPlugs])

    const deleteSchedule = useCallback(async (address: string, scheduleId: string) => {
        const plug = plugs.find(p => p.address === address)
        const operationKey = `delete-schedule-${scheduleId}`

        setPendingOperations(prev => ({...prev, [operationKey]: true}))

        const response = await fetch(`${API}/plugs/${address}/schedules/${scheduleId}`, {
            method: 'DELETE'
        })

        if (response.ok) {
            showToast('success', `${plug?.name}: Schedule cancelled`)
            await fetchPlugs()
        } else {
            showToast('error', `${plug?.name}: Failed to cancel schedule`)
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
                        className="mb-4 border border-[#eee] rounded-lg bg-white"
                    >
                        <div className="flex flex-col md:flex-row items-center gap-2 p-[12px] cursor-pointer bg-[#f9f9f9] hover:bg-[#eef6ff]"
                             onClick={() => expand(p.address)}>
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

                            {/* Actions Container */}
                            <div className="flex items-center justify-center md:justify-start gap-2 w-full md:w-auto mt-2 md:mt-0" onClick={e => e.stopPropagation()}>
                                <Tooltip text={p.is_on ? "Turn Off" : "Turn On"}>
                                    <button
                                        aria-label={p.is_on ? "Turn Off" : "Turn On"}
                                        className={`w-10 h-10 flex items-center justify-center rounded transition-all cursor-pointer text-white shadow-sm hover:scale-105 active:scale-95 ${p.is_on ? 'bg-emerald-500 hover:bg-emerald-600' : 'bg-rose-500 hover:bg-rose-600'}`}
                                        disabled={pendingOperations[`toggle-${p.address}`]}
                                        onClick={() => togglePlug(p)}>
                                        {pendingOperations[`toggle-${p.address}`] ? <span className="spinner-small border-white border-t-transparent"></span> : <MdPowerSettingsNew className="size-5" />}
                                    </button>
                                </Tooltip>

                                <Tooltip text="Set Timer">
                                    <button
                                        aria-label="Set Timer"
                                        className="w-10 h-10 flex items-center justify-center bg-purple-100 text-purple-700 rounded hover:bg-purple-200 cursor-pointer shadow-sm hover:scale-105 active:scale-95 transition-all"
                                        onClick={() => setTimedModalPlug(p.address)}
                                        disabled={pendingOperations[`timed-${p.address}`]}>
                                        {pendingOperations[`timed-${p.address}`] ? <span className="spinner-small border-purple-400 border-t-purple-700"></span> : <FaClock className="size-5" />}
                                    </button>
                                </Tooltip>

                                <Tooltip text="Schedule">
                                    <button
                                        aria-label="Schedule"
                                        className="w-10 h-10 flex items-center justify-center bg-teal-100 text-teal-700 rounded hover:bg-teal-200 cursor-pointer shadow-sm hover:scale-105 active:scale-95 transition-all"
                                        onClick={() => setScheduleModalPlug(p.address)}
                                        disabled={pendingOperations[`schedule-${p.address}`]}>
                                        {pendingOperations[`schedule-${p.address}`] ? <span className="spinner-small border-teal-400 border-t-teal-700"></span> : <FaCalendar className="size-5" />}
                                    </button>
                                </Tooltip>

                                <Tooltip text={p.enabled ? "Switch to Manual" : "Switch to Automatic"}>
                                    <button
                                        aria-label={p.enabled ? "Switch to Manual" : "Switch to Automatic"}
                                        className={`w-10 h-10 flex items-center justify-center rounded transition-all cursor-pointer shadow-sm hover:scale-105 active:scale-95 ${p.enabled ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                                        disabled={pendingOperations[`enable-${p.address}`]}
                                        onClick={(e) => toggleEnable(p.address, e)}>
                                        {pendingOperations[`enable-${p.address}`] ? <span className="spinner-small border-blue-400 border-t-blue-700"></span> : <MdAutoMode className="size-5" />}
                                    </button>
                                </Tooltip>
                            </div>
                        </div>
                        {/* Display scheduled events */}
                        {p.schedules && p.schedules.length > 0 && (
                            <div className="p-[12px] bg-[#e8f5e9] border-t-1 border-t-[#d1e7dd] border-t-solid text-[0.9rem]">
                                <p className="font-semibold mb-2"><strong>Upcoming Schedules:</strong></p>
                                <ul className="list-none p-0 m-0 space-y-1">
                                    {p.schedules.map((schedule) => (
                                        <li key={schedule.id}
                                            className="flex items-center justify-between bg-white rounded p-2 border border-[#d1e7dd]">
                                            <div className="flex-1">
                                                <FaCalendar className="inline-block mr-2 text-teal-600"/>
                                                {schedule.type === 'automatic' ? (
                                                    <span className="inline-block px-2 py-0.5 mr-2 text-xs font-semibold text-blue-700 bg-blue-100 rounded">
                                                        Auto
                                                    </span>
                                                ) : (
                                                    <span className="inline-block px-2 py-0.5 mr-2 text-xs font-semibold text-purple-700 bg-purple-100 rounded">
                                                        Manual
                                                    </span>
                                                )}
                                                <span className={schedule.desired_state ? 'text-green-700 font-medium' : 'text-red-700 font-medium'}>
                                                    {schedule.desired_state ? 'ON' : 'OFF'}
                                                </span>
                                                <span className="ml-2">{fmtDatetime(schedule.target_datetime)}</span>
                                                {schedule.duration_seconds && (
                                                    <span className="ml-2 text-gray-600">
                                                        ({schedule.desired_state ? 'OFF' : 'ON'} after <FaClock
                                                        className="inline-block mx-1 text-teal-600"/>
                                                        {fmtDuration(schedule.duration_seconds)})
                                                    </span>
                                                )}
                                            </div>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    deleteSchedule(p.address, schedule.id)
                                                }}
                                                disabled={pendingOperations[`delete-schedule-${schedule.id}`]}
                                                className="ml-2 p-1 text-red-500 hover:text-red-700 hover:bg-red-50 rounded cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                {pendingOperations[`delete-schedule-${schedule.id}`] ? (
                                                    <span className="spinner-small"></span>
                                                ) : (
                                                    <SlClose/>
                                                )}
                                            </button>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {open === p.address && energyData[p.address] && (
                            <>
                                <div
                                    className="p-[12px] bg-[#fafafa] border-t-1 border-t-[#eee] border-t-solid border-b-1 border-b-[#eee] border-b-solid text-[0.9rem] ">
                                    <p><strong>Address:</strong> {p.address}</p>
                                    {p.periods.length > 0 && (
                                        <>
                                            <p><strong>Periods:</strong></p>
                                            <ul className="list-none p-0 m-0">
                                                {p.periods.map((period) => (
                                                    <li key={`${period.start_hour}-${period.end_hour}-${period.target_hour}`}
                                                        className="text-[0.9rem]">
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
            <Modal
                isOpen={scheduleModalPlug !== null}
                onClose={() => setScheduleModalPlug(null)}
                title="Schedule Plug"
            >
                <ScheduleSelector
                    onSelect={(targetDatetime, desiredState, durationMinutes) => scheduleModalPlug && createSchedule(scheduleModalPlug, targetDatetime, desiredState, durationMinutes)}
                    onCancel={() => setScheduleModalPlug(null)}
                />
            </Modal>
        </div>
    )
}

export default App
