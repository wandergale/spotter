import {
  Card,
  CardContent,
  Typography,
  Box,
  Divider,
  Chip,
} from '@mui/material';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import FlagIcon from '@mui/icons-material/Flag';
import HotelIcon from '@mui/icons-material/Hotel';
import LocalGasStationIcon from '@mui/icons-material/LocalGasStation';
import FreeBreakfastIcon from '@mui/icons-material/FreeBreakfast';
import ListAltIcon from '@mui/icons-material/ListAlt';
import type { Stop, StopType } from '../types/api';

interface Props { stops: Stop[] }

const STOP_CONFIG: Record<StopType, { label: string; icon: React.ReactNode; color: string; bg: string }> = {
  pickup:  { label: 'Pickup',           icon: <LocalShippingIcon sx={{ fontSize: 18 }} />, color: '#1565c0', bg: '#e3f2fd' },
  dropoff: { label: 'Dropoff',          icon: <FlagIcon sx={{ fontSize: 18 }} />,           color: '#c62828', bg: '#ffebee' },
  rest:    { label: '10-Hr Rest',       icon: <HotelIcon sx={{ fontSize: 18 }} />,          color: '#6a1b9a', bg: '#f3e5f5' },
  fuel:    { label: 'Fuel Stop',        icon: <LocalGasStationIcon sx={{ fontSize: 18 }} />, color: '#00838f', bg: '#e0f7fa' },
  break:   { label: '30-Min Break',     icon: <FreeBreakfastIcon sx={{ fontSize: 18 }} />,  color: '#e65100', bg: '#fff3e0' },
};

function fmt(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit', hour12: true,
  });
}

function fmtDur(h: number): string {
  const hrs  = Math.floor(h);
  const mins = Math.round((h - hrs) * 60);
  return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
}

export default function StopDetails({ stops }: Props) {
  if (stops.length === 0) return null;

  return (
    <Card>
      {/* Header */}
      <Box
        sx={{
          px: 2.5, py: 1.5,
          background: 'linear-gradient(90deg, #1565c0 0%, #1976d2 100%)',
          display: 'flex', alignItems: 'center', gap: 1,
        }}
      >
        <ListAltIcon sx={{ color: '#fff', fontSize: 20 }} />
        <Typography variant="subtitle1" sx={{ color: '#fff', fontWeight: 600 }}>
          Stop Details
        </Typography>
        <Chip
          label={`${stops.length} stops`}
          size="small"
          sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: '#fff', fontSize: '0.7rem', ml: 'auto' }}
        />
      </Box>

      <CardContent sx={{ p: 0 }}>
        {stops.map((stop, i) => {
          const cfg = STOP_CONFIG[stop.type] ?? STOP_CONFIG.rest;
          const isLast = i === stops.length - 1;

          return (
            <Box key={i}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 0,
                  px: 2.5,
                  py: 2,
                  transition: 'background 0.15s',
                  '&:hover': { bgcolor: 'action.hover' },
                }}
              >
                {/* Timeline connector */}
                <Box
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    mr: 2,
                    flexShrink: 0,
                  }}
                >
                  {/* Icon badge */}
                  <Box
                    sx={{
                      width: 36,
                      height: 36,
                      borderRadius: '50%',
                      bgcolor: cfg.bg,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: cfg.color,
                      border: `2px solid ${cfg.color}40`,
                      flexShrink: 0,
                    }}
                  >
                    {cfg.icon}
                  </Box>
                  {/* Connector line */}
                  {!isLast && (
                    <Box
                      sx={{
                        width: 2,
                        flex: 1,
                        minHeight: 24,
                        bgcolor: 'divider',
                        mt: 0.5,
                        borderRadius: 1,
                      }}
                    />
                  )}
                </Box>

                {/* Content */}
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap', mb: 0.5 }}>
                    <Chip
                      label={cfg.label}
                      size="small"
                      sx={{
                        bgcolor: cfg.bg,
                        color: cfg.color,
                        fontWeight: 700,
                        fontSize: '0.72rem',
                        height: 22,
                      }}
                    />
                    <Chip
                      label={fmtDur(stop.duration_hours)}
                      size="small"
                      variant="outlined"
                      sx={{ fontSize: '0.7rem', height: 22 }}
                    />
                    <Typography
                      variant="caption"
                      color="text.disabled"
                      sx={{ ml: 'auto', fontFamily: 'monospace', flexShrink: 0 }}
                    >
                      Stop {i + 1}
                    </Typography>
                  </Box>

                  <Typography
                    variant="body2"
                    fontWeight={600}
                    noWrap
                    sx={{ mb: 0.25, maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}
                  >
                    {stop.location.name || 'En route'}
                  </Typography>

                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Box>
                      <Typography variant="caption" color="text.disabled">Arrival</Typography>
                      <Typography variant="caption" display="block" fontWeight={500}>
                        {fmt(stop.arrival_time)}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.disabled">Departure</Typography>
                      <Typography variant="caption" display="block" fontWeight={500}>
                        {fmt(stop.departure_time)}
                      </Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.disabled">Coords</Typography>
                      <Typography variant="caption" display="block" sx={{ fontFamily: 'monospace', fontSize: '0.68rem' }}>
                        {stop.location.lat.toFixed(3)}, {stop.location.lng.toFixed(3)}
                      </Typography>
                    </Box>
                  </Box>
                </Box>
              </Box>

              {!isLast && <Divider sx={{ ml: 7 }} />}
            </Box>
          );
        })}
      </CardContent>
    </Card>
  );
}
