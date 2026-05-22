import { useEffect, useRef, useCallback, useState } from 'react';

const useWakeLock = (isActive = false) => {
    const wakeLockRef = useRef(null);
    const isSupported = useRef('wakeLock' in navigator);
    const [wakeLockActive, setWakeLockActive] = useState(false);

    const acquire = useCallback(async () => {
        if (!isSupported.current) {
            console.warn('Screen Wake Lock API not supported');
            return false;
        }

        try {
            if (wakeLockRef.current) {
                return true; // Already have a wake lock
            }

            wakeLockRef.current = await navigator.wakeLock.request('screen');
            setWakeLockActive(true);

            wakeLockRef.current.addEventListener('release', () => {
                console.log('Wake lock released');
                wakeLockRef.current = null;
                setWakeLockActive(false);
            });

            console.log('Wake lock acquired');
            return true;
        } catch (err) {
            console.error('Failed to acquire wake lock:', err);
            return false;
        }
    }, []);

    const release = useCallback(() => {
        if (wakeLockRef.current) {
            wakeLockRef.current.release();
            wakeLockRef.current = null;
            setWakeLockActive(false);
        }
    }, []);

    const handleVisibilityChange = useCallback(() => {
        if (document.visibilityState === 'visible' && isActive && !wakeLockRef.current) {
            acquire();
        }
    }, [acquire, isActive]);

    useEffect(() => {
        if (isActive) {
            acquire();
        } else {
            release();
        }
    }, [isActive, acquire, release]);

    useEffect(() => {
        document.addEventListener('visibilitychange', handleVisibilityChange);

        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
            release();
        };
    }, [handleVisibilityChange, release]);

    return {
        isSupported: isSupported.current,
        isActive: wakeLockActive,
        acquire,
        release
    };
};

export default useWakeLock;