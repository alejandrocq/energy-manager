import React, { useState } from 'react';
import { FaClock } from 'react-icons/fa';

interface ScheduleSelectorProps {
  onSelect: (targetDatetime: string, desiredState: boolean, durationMinutes?: number) => void;
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

export const ScheduleSelector: React.FC<ScheduleSelectorProps> = ({ onSelect, onCancel }) => {
  const [targetDateTime, setTargetDateTime] = useState<string>('');
  const [desiredState, setDesiredState] = useState<boolean>(true); // true = ON, false = OFF
  const [useDuration, setUseDuration] = useState<boolean>(false);
  const [customDurationMode, setCustomDurationMode] = useState<boolean>(false);
  const [customHours, setCustomHours] = useState<string>('1');
  const [customMinutes, setCustomMinutes] = useState<string>('0');

  const now = new Date();
  now.setSeconds(0, 0);

  const handlePresetDurationClick = (minutes: number) => {
    if (!targetDateTime) return;
    const utcTime = toUTCISOString(targetDateTime);
    onSelect(utcTime, desiredState, minutes);
  };

  const handleCustomDurationSubmit = () => {
    if (!targetDateTime) return;
    const hours = parseInt(customHours) || 0;
    const minutes = parseInt(customMinutes) || 0;
    const totalMinutes = hours * 60 + minutes;
    const utcTime = toUTCISOString(targetDateTime);

    if (totalMinutes > 0 && totalMinutes <= 1440) { // Max 24 hours
      onSelect(utcTime, desiredState, totalMinutes);
    }
  };

  const handleScheduleNoDuration = () => {
    if (!targetDateTime) return;
    const utcTime = toUTCISOString(targetDateTime);
    onSelect(utcTime, desiredState);
  };

  const isValidTarget = targetDateTime !== '';

  return (
    <div className="space-y-4">
      {/* Datetime selection */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
          When to execute:
        </p>
        <input
          type="datetime-local"
          value={targetDateTime}
          onChange={(e) => setTargetDateTime(e.target.value)}
          min={formatDateTimeLocal(new Date(Date.now() + 60000))} // Minimum 1 minute from now
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

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
            Schedule
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
