import React, { useState } from 'react';
import { Box, CardMedia } from '@mui/material';
import FolderIcon from '@mui/icons-material/Folder';

export default function DecodedFolderThumbnail({ image, alt }) {
    const [hasError, setHasError] = useState(false);

    if (!image || hasError) {
        return (
            <Box
                data-testid="decoded-folder-thumbnail-fallback"
                sx={{
                    height: 200,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: 'linear-gradient(180deg, #111827 0%, #0b1220 100%)',
                }}
            >
                <FolderIcon sx={{ color: 'warning.main', fontSize: 56 }} />
            </Box>
        );
    }

    return (
        <CardMedia
            data-testid="decoded-folder-thumbnail-image"
            component="img"
            height="200"
            image={image}
            alt={alt}
            onError={() => setHasError(true)}
            sx={{
                objectFit: 'contain',
                background: 'linear-gradient(180deg, #111827 0%, #0b1220 100%)',
            }}
        />
    );
}
