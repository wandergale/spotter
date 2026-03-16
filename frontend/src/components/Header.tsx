import { AppBar, Toolbar, Typography, Box, Chip } from '@mui/material';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import VerifiedIcon from '@mui/icons-material/Verified';

export default function Header() {
  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        background: 'linear-gradient(135deg, #0d47a1 0%, #1565c0 60%, #1976d2 100%)',
        borderBottom: '1px solid rgba(255,255,255,0.12)',
      }}
    >
      <Toolbar sx={{ gap: 1.5 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 36,
            height: 36,
            bgcolor: 'rgba(255,255,255,0.15)',
            borderRadius: 2,
            backdropFilter: 'blur(4px)',
          }}
        >
          <LocalShippingIcon sx={{ fontSize: 22, color: '#fff' }} />
        </Box>

        <Box sx={{ flexGrow: 1 }}>
          <Typography
            variant="h6"
            sx={{ fontWeight: 700, letterSpacing: 0.3, lineHeight: 1.2 }}
          >
            ELD Trip Planner
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.75, letterSpacing: 0.5 }}>
            FMCSA Hours of Service Compliance
          </Typography>
        </Box>

        <Chip
          icon={<VerifiedIcon sx={{ fontSize: '14px !important', color: '#a5d6a7 !important' }} />}
          label="70-Hour / 8-Day Cycle"
          size="small"
          sx={{
            bgcolor: 'rgba(255,255,255,0.1)',
            color: '#e3f2fd',
            border: '1px solid rgba(255,255,255,0.2)',
            fontWeight: 500,
            fontSize: '0.7rem',
            display: { xs: 'none', sm: 'flex' },
          }}
        />
      </Toolbar>
    </AppBar>
  );
}
