import React, { useState } from 'react';
import { FaClock, FaRepeat } from 'react-icons/fa6';
import { RecurrenceConfig, FrequencyType, validateRecurrence } from './recurrenceUtils';

interface ScheduleSelectorProps {
  onSelect: (targetDatetime: string, desiredState: boolean, durationMinutes?: number, recurrence?: RecurrenceConfig) => void;
  onCancel: () => void;
}

const formatDateTimeLocal = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
};

const formatDateLocal = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

// Convert local datetime string (YYYY-MM-DDTHH:MM) to UTC ISO format
const toUTCISOString = (localDateTime: string): string => {
  return new Date(localDateTime).toISOString();
};

const PRESET_DURATIONS = [
  { label: '30 minutes', minutes: 30 },
  { label: '1 hour', minutes: 60 },
  { label: '2 hours', minutes: 120 },
  { label: '4 hours', minutes: 240 },
  { label: '8 hours', minutes: 480 },
];

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export const ScheduleSelector: React.FC<ScheduleSelectorProps> = ({ onSelect, onCancel }) => {
  // One-time schedule state
  const [targetDateTime, setTargetDateTime] = useState<string>('');

  // Common state
  const [desiredState, setDesiredState] = useState<boolean>(true);
  const [useDuration, setUseDuration] = useState<boolean>(false);
  const [customDurationMode, setCustomDurationMode] = useState<boolean>(false);
  const [customHours, setCustomHours] = useState<string>('1');
  const [customMinutes, setCustomMinutes] = useState<string>('0');

  // Repeating schedule state
  const [isRepeating, setIsRepeating] = useState<boolean>(false);
  const [frequency, setFrequency] = useState<FrequencyType>('daily');
  const [interval, setInterval] = useState<number>(1);
  const [daysOfWeek, setDaysOfWeek] = useState<number[]>([]);
  const [daysOfMonth, setDaysOfMonth] = useState<number[]>([]);
  const [time, setTime] = useState<string>(() => {
    const now = new Date();
    return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
  });
  const [endDate, setEndDate] = useState<string>('');
  const [validationError, setValidationError] = useState<string>('');

  const now = new Date();
  now.setSeconds(0, 0);

  const toggleDayOfWeek = (day: number) => {
    setDaysOfWeek(prev =>
      prev.includes(day) ? prev.filter(d => d !== day) : [...prev, day].sort()
    );
    setValidationError('');
  };

  const toggleDayOfMonth = (day: number) => {
    setDaysOfMonth(prev =>
      prev.includes(day) ? prev.filter(d => d !== day) : [...prev, day].sort((a, b) => a - b)
    );
    setValidationError('');
  };

  const handleFrequencyChange = (newFrequency: FrequencyType) => {
    setFrequency(newFrequency);
    setValidationError('');
    // Reset days when switching frequency
    if (newFrequency === 'daily') {
      setDaysOfWeek([]);
      setDaysOfMonth([]);
    } else if (newFrequency === 'weekly') {
      setDaysOfMonth([]);
      if (daysOfWeek.length === 0) {
        // Default to current day
        const currentDay = now.getDay() === 0 ? 6 : now.getDay() - 1;
        setDaysOfWeek([currentDay]);
      }
    } else if (newFrequency === 'monthly') {
      setDaysOfWeek([]);
      if (daysOfMonth.length === 0) {
        // Default to current day of month
        setDaysOfMonth([now.getDate()]);
      }
    }
  };

  const buildRecurrence = (): RecurrenceConfig => {
    return {
      frequency,
      interval,
      days_of_week: frequency === 'weekly' || frequency === 'custom' ? daysOfWeek : undefined,
      days_of_month: frequency === 'monthly' || frequency === 'custom' ? daysOfMonth : undefined,
      time,
      end_date: endDate || undefined
    };
  };

  const handlePresetDurationClick = (minutes: number) => {
    if (isRepeating) {
      const recurrence = buildRecurrence();
      const validation = validateRecurrence(recurrence);
      if (!validation.valid) {
        setValidationError(validation.error || 'Invalid configuration');
        return;
      }
      onSelect('', desiredState, minutes, recurrence);
    } else {
      if (!targetDateTime) return;
      const utcTime = toUTCISOString(targetDateTime);
      onSelect(utcTime, desiredState, minutes);
    }
  };

  const handleCustomDurationSubmit = () => {
    const hours = parseInt(customHours) || 0;
    const mins = parseInt(customMinutes) || 0;
    const totalMinutes = hours * 60 + mins;

    if (totalMinutes <= 0 || totalMinutes > 1440) return;

    if (isRepeating) {
      const recurrence = buildRecurrence();
      const validation = validateRecurrence(recurrence);
      if (!validation.valid) {
        setValidationError(validation.error || 'Invalid configuration');
        return;
      }
      onSelect('', desiredState, totalMinutes, recurrence);
    } else {
      if (!targetDateTime) return;
      const utcTime = toUTCISOString(targetDateTime);
      onSelect(utcTime, desiredState, totalMinutes);
    }
  };

  const handleScheduleNoDuration = () => {
    if (isRepeating) {
      const recurrence = buildRecurrence();
      const validation = validateRecurrence(recurrence);
      if (!validation.valid) {
        setValidationError(validation.error || 'Invalid configuration');
        return;
      }
      onSelect('', desiredState, undefined, recurrence);
    } else {
      if (!targetDateTime) return;
      const utcTime = toUTCISOString(targetDateTime);
      onSelect(utcTime, desiredState);
    }
  };

  const isValidTarget = isRepeating ? time !== '' : targetDateTime !== '';

  return (
    <div className="space-y-4">
      {/* Repeat toggle */}
      <div className="flex items-center gap-2 p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
        <input
          type="checkbox"
          id="isRepeating"
          checked={isRepeating}
          onChange={(e) => {
            setIsRepeating(e.target.checked);
            setValidationError('');
          }}
          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
        />
        <label htmlFor="isRepeating" className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 cursor-pointer">
          <FaRepeat className="w-4 h-4" />
          Repeat schedule
        </label>
      </div>

      {!isRepeating ? (
        /* One-time schedule: Datetime selection */
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            When to execute:
          </p>
          <input
            type="datetime-local"
            value={targetDateTime}
            onChange={(e) => setTargetDateTime(e.target.value)}
            min={formatDateTimeLocal(new Date(Date.now() + 60000))}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      ) : (
        /* Repeating schedule configuration */
        <div className="space-y-4">
          {/* Frequency selector */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Frequency:
            </p>
            <div className="grid grid-cols-2 gap-2">
              {(['daily', 'weekly', 'monthly', 'custom'] as FrequencyType[]).map((freq) => (
                <button
                  key={freq}
                  onClick={() => handleFrequencyChange(freq)}
                  className={`px-3 py-2 rounded-lg font-medium transition-all cursor-pointer text-sm ${
                    frequency === freq
                      ? 'bg-blue-500 text-white shadow-md'
                      : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                  }`}
                >
                  {freq.charAt(0).toUpperCase() + freq.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Interval */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Every:
            </p>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="1"
                max="30"
                value={interval}
                onChange={(e) => setInterval(Math.max(1, parseInt(e.target.value) || 1))}
                className="w-20 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {frequency === 'daily' ? (interval === 1 ? 'day' : 'days') :
                 frequency === 'weekly' ? (interval === 1 ? 'week' : 'weeks') :
                 frequency === 'monthly' ? (interval === 1 ? 'month' : 'months') :
                 (interval === 1 ? 'occurrence' : 'occurrences')}
              </span>
            </div>
          </div>

          {/* Days of week (for weekly and custom) */}
          {(frequency === 'weekly' || frequency === 'custom') && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Days of week:
              </p>
              <div className="flex flex-wrap gap-2">
                {DAY_NAMES.map((day, idx) => (
                  <button
                    key={idx}
                    onClick={() => toggleDayOfWeek(idx)}
                    className={`px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer text-sm ${
                      daysOfWeek.includes(idx)
                        ? 'bg-blue-500 text-white shadow-md'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    {day}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Days of month (for monthly and custom) */}
          {(frequency === 'monthly' || frequency === 'custom') && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Days of month:
              </p>
              <div className="grid grid-cols-7 gap-1 max-h-32 overflow-y-auto">
                {Array.from({ length: 31 }, (_, i) => i + 1).map((day) => (
                  <button
                    key={day}
                    onClick={() => toggleDayOfMonth(day)}
                    className={`px-2 py-1 rounded font-medium transition-all cursor-pointer text-xs ${
                      daysOfMonth.includes(day)
                        ? 'bg-blue-500 text-white shadow-md'
                        : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
                    }`}
                  >
                    {day}
                  </button>
                ))}
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Days that don't exist in a month will be skipped
              </p>
            </div>
          )}

          {/* Time */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Time:
            </p>
            <input
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* End date (optional) */}
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
              End date (optional):
            </p>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              min={formatDateLocal(new Date(Date.now() + 86400000))}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            {endDate && (
              <button
                onClick={() => setEndDate('')}
                className="text-xs text-blue-500 hover:text-blue-700 cursor-pointer"
              >
                Clear end date (repeat indefinitely)
              </button>
            )}
          </div>

          {/* Validation error */}
          {validationError && (
            <div className="p-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-sm rounded-lg">
              {validationError}
            </div>
          )}
        </div>
      )}

      {/* Desired state selection */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Desired state at scheduled time:
        </p>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => setDesiredState(false)}
            className={`px-4 py-2 rounded-lg font-medium transition-all cursor-pointer ${
              !desiredState
                ? 'bg-red-500 text-white shadow-md'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
            }`}
          >
            Turn OFF
          </button>
          <button
            onClick={() => setDesiredState(true)}
            className={`px-4 py-2 rounded-lg font-medium transition-all cursor-pointer ${
              desiredState
                ? 'bg-green-500 text-white shadow-md'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600'
            }`}
          >
            Turn ON
          </button>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {desiredState
            ? 'Plug will turn ON at the scheduled time'
            : 'Plug will turn OFF at the scheduled time'}
        </p>
      </div>

      {/* Optional duration toggle */}
      <div className="space-y-3 pt-3 border-t border-gray-300 dark:border-gray-600">
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="useDuration"
            checked={useDuration}
            onChange={(e) => setUseDuration(e.target.checked)}
            className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
          />
          <label htmlFor="useDuration" className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Auto {desiredState ? 'turn OFF' : 'turn ON'} after duration
          </label>
        </div>

        {useDuration && (
          <>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {desiredState
                ? 'Select how long to keep the plug ON before automatically turning it OFF:'
                : 'Select how long to keep the plug OFF before automatically turning it ON:'}
            </p>

            {!customDurationMode ? (
              <>
                {/* Preset durations */}
                <div className="grid grid-cols-2 gap-2">
                  {PRESET_DURATIONS.map((duration) => (
                    <button
                      key={duration.minutes}
                      onClick={() => handlePresetDurationClick(duration.minutes)}
                      disabled={!isValidTarget}
                      className="flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg font-medium transition-all transform hover:scale-105 active:scale-95 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <FaClock className="w-4 h-4" />
                      {duration.label}
                    </button>
                  ))}
                </div>

                {/* Custom duration button */}
                <button
                  onClick={() => setCustomDurationMode(true)}
                  className="w-full px-4 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors cursor-pointer"
                >
                  Custom duration
                </button>
              </>
            ) : (
              <>
                {/* Custom duration input */}
                <div className="space-y-3">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Set a custom duration (max 24 hours):
                  </p>

                  <div className="flex gap-3 items-center">
                    <div className="flex-1">
                      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                        Hours
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="24"
                        value={customHours}
                        onChange={(e) => setCustomHours(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>

                    <div className="flex-1">
                      <label className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                        Minutes
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="59"
                        value={customMinutes}
                        onChange={(e) => setCustomMinutes(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => setCustomDurationMode(false)}
                      className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors cursor-pointer"
                    >
                      Back
                    </button>
                    <button
                      onClick={handleCustomDurationSubmit}
                      disabled={!isValidTarget}
                      className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Schedule
                    </button>
                  </div>
                </div>
              </>
            )}
          </>
        )}

        {/* Schedule button (no duration) */}
        {!useDuration && (
          <button
            onClick={handleScheduleNoDuration}
            disabled={!isValidTarget}
            className="w-full px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg font-medium transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRepeating ? 'Create Repeating Schedule' : 'Schedule'}
          </button>
        )}
      </div>

      {/* Cancel button */}
      <button
        onClick={onCancel}
        className="w-full px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors cursor-pointer"
      >
        Cancel
      </button>
    </div>
  );
};
