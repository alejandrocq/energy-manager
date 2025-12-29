export type FrequencyType = 'daily' | 'weekly' | 'monthly' | 'custom';

export interface RecurrenceConfig {
    frequency: FrequencyType;
    interval: number;
    days_of_week?: number[];  // 0=Monday, 6=Sunday
    days_of_month?: number[]; // 1-31
    time: string;             // HH:MM format
    end_date?: string;        // ISO format date
}

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DAY_NAMES_FULL = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

export function formatRecurrencePattern(recurrence: RecurrenceConfig): string {
    const parts: string[] = [];

    if (recurrence.frequency === 'daily') {
        if (recurrence.interval === 1) {
            parts.push('Daily');
        } else {
            parts.push(`Every ${recurrence.interval} days`);
        }
    } else if (recurrence.frequency === 'weekly') {
        if (recurrence.interval === 1) {
            parts.push('Weekly');
        } else {
            parts.push(`Every ${recurrence.interval} weeks`);
        }
        if (recurrence.days_of_week && recurrence.days_of_week.length > 0) {
            const dayNames = recurrence.days_of_week
                .sort((a, b) => a - b)
                .map(d => DAY_NAMES[d]);
            parts.push(`on ${dayNames.join(', ')}`);
        }
    } else if (recurrence.frequency === 'monthly') {
        if (recurrence.interval === 1) {
            parts.push('Monthly');
        } else {
            parts.push(`Every ${recurrence.interval} months`);
        }
        if (recurrence.days_of_month && recurrence.days_of_month.length > 0) {
            const days = recurrence.days_of_month.sort((a, b) => a - b);
            parts.push(`on day ${days.join(', ')}`);
        }
    } else if (recurrence.frequency === 'custom') {
        parts.push('Custom');
        if (recurrence.days_of_week && recurrence.days_of_week.length > 0) {
            const dayNames = recurrence.days_of_week
                .sort((a, b) => a - b)
                .map(d => DAY_NAMES[d]);
            parts.push(`on ${dayNames.join(', ')}`);
        }
        if (recurrence.days_of_month && recurrence.days_of_month.length > 0) {
            const days = recurrence.days_of_month.sort((a, b) => a - b);
            parts.push(`on day ${days.join(', ')}`);
        }
    }

    parts.push(`at ${recurrence.time}`);

    if (recurrence.end_date) {
        const endDate = new Date(recurrence.end_date);
        const options: Intl.DateTimeFormatOptions = {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        };
        parts.push(`until ${endDate.toLocaleDateString(undefined, options)}`);
    }

    return parts.join(' ');
}

export function validateRecurrence(recurrence: RecurrenceConfig): { valid: boolean; error?: string } {
    // Validate frequency
    if (!['daily', 'weekly', 'monthly', 'custom'].includes(recurrence.frequency)) {
        return { valid: false, error: 'Invalid frequency' };
    }

    // Validate interval
    if (recurrence.interval < 1) {
        return { valid: false, error: 'Interval must be at least 1' };
    }

    // Validate time
    const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
    if (!timeRegex.test(recurrence.time)) {
        return { valid: false, error: 'Invalid time format (use HH:MM)' };
    }

    // Validate days_of_week
    if (recurrence.days_of_week) {
        for (const d of recurrence.days_of_week) {
            if (d < 0 || d > 6) {
                return { valid: false, error: 'Day of week must be 0-6' };
            }
        }
    }

    // Validate days_of_month
    if (recurrence.days_of_month) {
        for (const d of recurrence.days_of_month) {
            if (d < 1 || d > 31) {
                return { valid: false, error: 'Day of month must be 1-31' };
            }
        }
    }

    // Frequency-specific validation
    if (recurrence.frequency === 'weekly' && (!recurrence.days_of_week || recurrence.days_of_week.length === 0)) {
        return { valid: false, error: 'Weekly frequency requires at least one day' };
    }

    if (recurrence.frequency === 'monthly' && (!recurrence.days_of_month || recurrence.days_of_month.length === 0)) {
        return { valid: false, error: 'Monthly frequency requires at least one day' };
    }

    if (recurrence.frequency === 'custom') {
        const hasDaysOfWeek = recurrence.days_of_week && recurrence.days_of_week.length > 0;
        const hasDaysOfMonth = recurrence.days_of_month && recurrence.days_of_month.length > 0;
        if (!hasDaysOfWeek && !hasDaysOfMonth) {
            return { valid: false, error: 'Custom frequency requires days of week or days of month' };
        }
    }

    // Validate end_date if provided
    if (recurrence.end_date) {
        const endDate = new Date(recurrence.end_date);
        if (isNaN(endDate.getTime())) {
            return { valid: false, error: 'Invalid end date' };
        }
        if (endDate < new Date()) {
            return { valid: false, error: 'End date cannot be in the past' };
        }
    }

    return { valid: true };
}

export function getDayName(dayIndex: number, full: boolean = false): string {
    return full ? DAY_NAMES_FULL[dayIndex] : DAY_NAMES[dayIndex];
}

export function getDefaultRecurrence(frequency: FrequencyType): RecurrenceConfig {
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    switch (frequency) {
        case 'daily':
            return { frequency: 'daily', interval: 1, time };
        case 'weekly':
            return { frequency: 'weekly', interval: 1, days_of_week: [now.getDay() === 0 ? 6 : now.getDay() - 1], time };
        case 'monthly':
            return { frequency: 'monthly', interval: 1, days_of_month: [now.getDate()], time };
        case 'custom':
            return { frequency: 'custom', interval: 1, days_of_week: [], days_of_month: [], time };
    }
}
