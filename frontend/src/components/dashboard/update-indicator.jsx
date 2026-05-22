import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Box, Chip, Tooltip } from '@mui/material';
import NewReleasesIcon from '@mui/icons-material/NewReleases';
import { fetchUpdateCheck } from './update-slice.jsx';
import { useTranslation } from 'react-i18next';

const CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000; // 6 hours

function UpdateIndicator({ compact = true }) {
    const dispatch = useDispatch();
    const { t } = useTranslation('dashboard');
    const { data } = useSelector((state) => state.updateCheck || {});

    useEffect(() => {
        dispatch(fetchUpdateCheck());
        const interval = setInterval(() => {
            dispatch(fetchUpdateCheck());
        }, CHECK_INTERVAL_MS);
        return () => clearInterval(interval);
    }, [dispatch]);

    if (!data?.isUpdateAvailable) {
        return null;
    }

    const latestLabel = data?.latestTag || data?.latestVersion || 'latest';
    const publishedAt = data?.publishedAt
        ? new Date(data.publishedAt).toLocaleDateString()
        : t('version_update.unknown_date', 'Unknown date');

    const tooltip = (
        <Box sx={{ fontSize: '0.75rem', lineHeight: 1.4 }}>
            <Box>
                {t('version_update.latest', 'Latest')}: {latestLabel}
            </Box>
            <Box>
                {t('version_update.published', 'Published')}: {publishedAt}
            </Box>
            <Box>
                {t('version_update.click_to_open', 'Click to open release')}
            </Box>
        </Box>
    );

    return (
        <Tooltip title={tooltip} placement="bottom-start">
            <Chip
                icon={<NewReleasesIcon />}
                label={compact ? t('version_update.available', 'Update') : t('version_update.available_full', 'Update available')}
                size="small"
                color="warning"
                onClick={() => {
                    if (data?.latestUrl) {
                        window.open(data.latestUrl, '_blank', 'noopener,noreferrer');
                    }
                }}
                sx={{
                    height: 20,
                    fontSize: '0.65rem',
                    fontWeight: 600,
                    cursor: data?.latestUrl ? 'pointer' : 'default',
                }}
            />
        </Tooltip>
    );
}

export default React.memo(UpdateIndicator);
