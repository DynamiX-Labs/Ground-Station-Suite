import { useSelector } from 'react-redux';

export const useUserTimeSettings = () => {
    const preferences = useSelector((state) => state.preferences?.preferences || []);

    const timezone = preferences.find((pref) => pref.name === 'timezone')?.value || 'UTC';
    const localePref = preferences.find((pref) => pref.name === 'locale')?.value || 'browser';
    const locale = localePref === 'browser' ? undefined : localePref;

    return { timezone, locale, localePref };
};
