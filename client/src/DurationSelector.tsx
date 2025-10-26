import React, { useState } from 'react';
import { FaClock } from 'react-icons/fa';

interface DurationSelectorProps {
  onSelect: (minutes: number) => void;
  onCancel: () => void;
}

const PRESET_DURATIONS = [
  { label: '30 minutes', minutes: 30 },
  { label: '1 hour', minutes: 60 },
  { label: '2 hours', minutes: 120 },
  { label: '4 hours', minutes: 240 },
  { label: '8 hours', minutes: 480 },
];

export const DurationSelector: React.FC<DurationSelectorProps> = ({ onSelect, onCancel }) => {
  const [customMode, setCustomMode] = useState(false);
  const [customHours, setCustomHours] = useState('1');
  const [customMinutes, setCustomMinutes] = useState('0');

  const handlePresetClick = (minutes: number) => {
    onSelect(minutes);
  };

  const handleCustomSubmit = () => {
    const hours = parseInt(customHours) || 0;
    const minutes = parseInt(customMinutes) || 0;
    const totalMinutes = hours * 60 + minutes;

    if (totalMinutes > 0 && totalMinutes <= 1440) { // Max 24 hours
      onSelect(totalMinutes);
    }
  };

  return (
    <div className="space-y-4">
      {!customMode ? (
        <>
          {/* Preset durations */}
          <div className="grid grid-cols-2 gap-2">
            {PRESET_DURATIONS.map((duration) => (
              <button
                key={duration.minutes}
                onClick={() => handlePresetClick(duration.minutes)}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg font-medium transition-all transform hover:scale-105 active:scale-95"
              >
                <FaClock className="w-4 h-4" />
                {duration.label}
              </button>
            ))}
          </div>

          {/* Custom duration button */}
          <button
            onClick={() => setCustomMode(true)}
            className="w-full px-4 py-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors"
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
                onClick={() => setCustomMode(false)}
                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleCustomSubmit}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg font-medium transition-all"
              >
                Confirm
              </button>
            </div>
          </div>
        </>
      )}

      {/* Cancel button */}
      <button
        onClick={onCancel}
        className="w-full px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
      >
        Cancel
      </button>
    </div>
  );
};
