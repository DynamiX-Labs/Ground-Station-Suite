import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions, Button, Typography } from '@mui/material';
import ErrorIcon from '@mui/icons-material/Error';
import { useTranslation } from 'react-i18next';

const WaterfallErrorDialog = ({ open, message, onClose }) => {
    const { t } = useTranslation('waterfall');

    return (
        <Dialog open={open} onClose={onClose} aria-labelledby="error-dialog-title" aria-describedby="error-dialog-description">
            <DialogTitle id="error-dialog-title" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <ErrorIcon color="error" />
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>{t('error_dialog.title')}</Typography>
            </DialogTitle>
            <DialogContent>
                <DialogContentText id="error-dialog-description" sx={{ whiteSpace: 'pre-wrap' }}>
                    {message}
                </DialogContentText>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose} variant="contained" color="error" autoFocus>
                    {t('error_dialog.close')}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default WaterfallErrorDialog;
