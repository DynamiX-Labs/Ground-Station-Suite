/**
 * @license
 * Copyright (c) 2025 Efstratios Goudelis
 * Modifications and extensions Copyright (C) 2026 DynamiX-Labs
 */

import React from 'react';
import { Box, Typography, Divider } from '@mui/material';

function Row({ label, value }) {
  return (
    <Box sx={{
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      alignItems: 'center',
      py: 0.75,
      columnGap: 2,
    }}>
      <Typography variant="body2" color="text.secondary">{label}</Typography>
      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>{value}</Typography>
    </Box>
  );
}

export default function TelemetryValuesTab({ telemetry }) {
  const values = telemetry?.telemetry?.values || null;
  const rawFields = telemetry?.telemetry?.raw_fields || telemetry?.telemetry?.rawFields || null;

  if (!values) {
    return (
      <Typography variant="body2" color="text.secondary">
        No decoded telemetry available for this packet.
      </Typography>
    );
  }

  return (
    <Box>
      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>Engineering Values</Typography>
      <Divider sx={{ mb: 2 }} />
      <Box>
        {Object.entries(values).map(([k, v]) => (
          <Row
            key={k}
            label={k}
            value={typeof v === 'object' && v !== null ? JSON.stringify(v) : String(v)}
          />
        ))}
      </Box>

      {rawFields && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>Raw Fields</Typography>
          <Divider sx={{ mb: 2 }} />
          {Object.entries(rawFields).map(([k, v]) => (
            <Row key={k} label={k} value={String(v)} />
          ))}
        </Box>
      )}
    </Box>
  );
}
