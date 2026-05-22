import {
    Alert,
    Box,
    Button,
    Container,
    Divider,
    Paper,
    Stack,
    Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import HomeIcon from '@mui/icons-material/Home';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

const NotFoundPage = () => {
    const navigate = useNavigate();

    return (
        <Container
            maxWidth="md"
            sx={{
                minHeight: '100vh',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                py: 4,
            }}
        >
            <Paper elevation={4} sx={{ width: '100%', p: { xs: 2.5, sm: 4 }, borderRadius: 2 }}>
                <Stack spacing={2.5}>
                    <Stack direction="row" spacing={1.5} alignItems="center">
                        <ErrorOutlineIcon color="error" sx={{ fontSize: 30 }} />
                        <Box>
                            <Typography variant="h5" sx={{ fontWeight: 700 }}>
                                Page Not Found
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                                Error code: 404
                            </Typography>
                        </Box>
                    </Stack>

                    <Divider />

                    <Alert severity="error" variant="outlined">
                        The page you requested does not exist or may have been moved.
                    </Alert>

                    <Typography variant="body1" color="text.secondary">
                        Check the URL or continue using one of the actions below.
                    </Typography>

                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                        <Button
                            variant="contained"
                            startIcon={<HomeIcon />}
                            onClick={() => navigate('/')}
                        >
                            Back to Home
                        </Button>
                        <Button
                            variant="outlined"
                            startIcon={<ArrowBackIcon />}
                            onClick={() => navigate(-1)}
                        >
                            Go Back
                        </Button>
                    </Stack>
                </Stack>
            </Paper>
        </Container>
    );
};

export default NotFoundPage;
