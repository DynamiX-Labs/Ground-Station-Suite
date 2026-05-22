import { Box, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';
import { Y_AXIS_WIDTH, X_AXIS_HEIGHT, Y_AXIS_TOP_MARGIN } from './timeline-constants.jsx';

export const TimelineContainer = styled(Box)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  backgroundColor: theme.palette.background.paper,
  overflow: 'hidden',
}));

export const TimelineContent = styled(Box)(({ theme }) => ({
  flex: 1,
  overflow: 'auto',
  display: 'flex',
  flexDirection: 'column',
}));

export const TimelineCanvas = styled(Box)(({ theme }) => ({
  position: 'relative',
  flex: 1,
  backgroundColor: theme.palette.mode === 'dark' ? '#1a1a1a' : '#f5f5f5',
  borderRadius: theme.shape.borderRadius,
  overflow: 'hidden',
  padding: '0 4px',
}));

export const TimelineAxis = styled(Box)(({ theme }) => ({
  position: 'absolute',
  bottom: 0,
  left: 0,
  right: 0,
  height: `${X_AXIS_HEIGHT}px`,
  display: 'flex',
  alignItems: 'center',
  borderTop: `1px solid ${theme.palette.divider}`,
  backgroundColor: theme.palette.background.default,
  overflow: 'hidden',
}));

export const ElevationAxis = styled(Box)(({ theme }) => ({
  position: 'absolute',
  left: 0,
  top: `${Y_AXIS_TOP_MARGIN}px`,
  bottom: `${X_AXIS_HEIGHT}px`,
  width: `${Y_AXIS_WIDTH}px`,
  borderRight: `1px solid ${theme.palette.divider}`,
  borderBottom: 'none',
  backgroundColor: theme.palette.background.default,
}));

export const ElevationLabel = styled(Typography)(({ theme }) => ({
  position: 'absolute',
  fontSize: '0.65rem',
  color: theme.palette.text.secondary,
  userSelect: 'none',
  textAlign: 'right',
  paddingRight: '4px',
  width: '100%',
  transform: 'translateY(-50%)', // Center the label on its position
  zIndex: 2, // Ensure labels appear above corner boxes
}));

export const TimeLabel = styled(Typography)(({ theme }) => ({
  position: 'absolute',
  fontSize: '0.7rem',
  color: theme.palette.text.secondary,
  userSelect: 'none',
  transform: 'translateX(-50%)',
  whiteSpace: 'nowrap',
}));
