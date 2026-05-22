import React from 'react';
import { useSelector } from 'react-redux';
import NotFoundPage from '../common/not-found-page.jsx';
import CelestialMainLayout from './main-layout.jsx';

const CelestialRouteGuard = () => {
    const preferences = useSelector((state) => state.preferences?.preferences || []);
    const celestialEnabledPreference = preferences.find((pref) => pref.name === 'celestial_enabled');
    const celestialEnabled = String(celestialEnabledPreference?.value ?? 'false').toLowerCase() === 'true';

    if (!celestialEnabled) {
        return <NotFoundPage />;
    }

    return <CelestialMainLayout />;
};

export default CelestialRouteGuard;
