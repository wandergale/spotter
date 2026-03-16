import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1565c0',     // deep blue — professional logistics look
      light: '#5e92f3',
      dark: '#003c8f',
      contrastText: '#fff',
    },
    secondary: {
      main: '#f57c00',     // amber — accent for highlights
      light: '#ffad42',
      dark: '#bb4d00',
    },
    background: {
      default: '#f0f4f8',
      paper: '#ffffff',
    },
    text: {
      primary: '#1a2027',
      secondary: '#546e7a',
    },
    error: { main: '#c62828' },
    success: { main: '#2e7d32' },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica Neue", Arial, sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 700 },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 500 },
    subtitle2: { fontWeight: 600, fontSize: '0.8rem', letterSpacing: 0.5 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          border: '1px solid #e0e7ef',
          boxShadow: '0 2px 8px rgba(21,101,192,0.06)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 8,
          padding: '10px 24px',
        },
        containedPrimary: {
          boxShadow: '0 2px 8px rgba(21,101,192,0.3)',
          '&:hover': { boxShadow: '0 4px 12px rgba(21,101,192,0.4)' },
        },
      },
    },
    MuiTextField: {
      defaultProps: { size: 'small' },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 600 } },
    },
  },
});

export default theme;
