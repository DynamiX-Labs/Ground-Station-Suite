import {styled} from '@mui/material/styles';
import MuiAccordion from '@mui/material/Accordion';
import MuiAccordionSummary, {accordionSummaryClasses} from '@mui/material/AccordionSummary';
import ArrowForwardIosSharpIcon from '@mui/icons-material/ArrowForwardIosSharp';
import MuiAccordionDetails from '@mui/material/AccordionDetails';
import React from 'react';
import {Box, CircularProgress} from "@mui/material";

export const Accordion = styled((props) => (
    <MuiAccordion disableGutters elevation={0} square {...props} />
))(({theme}) => ({
    border: `1px solid ${theme.palette.divider}`,
    '&:not(:last-child)': {
        borderBottom: 0,
    },
    '&::before': {
        display: 'none',
    },
}));

export const AccordionSummary = styled((props) => (
    <MuiAccordionSummary
        expandIcon={<ArrowForwardIosSharpIcon sx={{fontSize: '0.9rem'}}/>}
        {...props}
    />
))(({theme}) => ({
    backgroundColor: theme.palette.mode === 'dark' ? theme.palette.overlay.light : theme.palette.overlay.light,
    flexDirection: 'row-reverse',
    minHeight: 34,
    height: 34,
    fontSize: '0.7rem',
    [`& .${accordionSummaryClasses.expandIconWrapper}.${accordionSummaryClasses.expanded}`]:
        {
            transform: 'rotate(90deg)',
        },
    [`& .${accordionSummaryClasses.content}`]: {
        marginLeft: theme.spacing(1),
    },
}));

export const AccordionDetails = styled(MuiAccordionDetails)(({theme}) => ({
    padding: theme.spacing(2),
    borderTop: `1px solid ${theme.palette.border.dark}`,
}));

export const LoadingOverlay = ({loading, children}) => {
    return (
        <Box sx={{position: 'relative'}}>
            {children}

            {loading && (
                <Box
                    sx={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        display: 'flex',
                        justifyContent: 'center',
                        alignItems: 'center',
                        zIndex: 1000,
                    }}
                >
                    <CircularProgress/>
                </Box>
            )}
        </Box>
    );
};
