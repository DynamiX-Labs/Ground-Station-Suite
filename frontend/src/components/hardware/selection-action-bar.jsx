import React from 'react';
import {Box, Button, Chip, Stack, Typography} from '@mui/material';

export default function SelectionActionBar({
    selectedCount,
    onClearSelection,
    primaryActions,
    secondaryActions,
}) {
    return (
        <Stack
            direction={{xs: 'column', md: 'row'}}
            spacing={1.5}
            sx={{
                mt: 1.5,
                mb: 1,
                alignItems: {xs: 'stretch', md: 'center'},
                justifyContent: 'space-between',
                gap: 1.5,
            }}
        >
            <Stack direction="row" spacing={1} sx={{alignItems: 'center', minHeight: 32}}>
                <Typography variant="body2" color="text.secondary">
                    Selection
                </Typography>
                <Chip size="small" color={selectedCount > 0 ? 'primary' : 'default'} label={`${selectedCount} selected`} />
                {selectedCount > 0 && (
                    <Button size="small" variant="text" onClick={onClearSelection}>
                        Clear
                    </Button>
                )}
            </Stack>
            <Stack direction={{xs: 'column', sm: 'row'}} spacing={1} sx={{flexWrap: 'wrap'}}>
                {primaryActions}
            </Stack>
            {secondaryActions ? (
                <Box sx={{display: 'flex', justifyContent: {xs: 'flex-start', md: 'flex-end'}}}>
                    {secondaryActions}
                </Box>
            ) : null}
        </Stack>
    );
}
