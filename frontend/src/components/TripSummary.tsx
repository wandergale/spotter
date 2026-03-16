import {
  Card,
  CardContent,
  Typography,
  Box,
  Grid,
  Divider,
} from '@mui/material';
import RouteIcon from '@mui/icons-material/Route';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import HotelIcon from '@mui/icons-material/Hotel';
import LocalGasStationIcon from '@mui/icons-material/LocalGasStation';
import DirectionsCarIcon from '@mui/icons-material/DirectionsCar';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import type { TripResponse } from '../types/api';

interface Props { result: TripResponse }

function fmtDur(h: number): string {
  const hrs = Math.floor(h);
  const mins = Math.round((h - hrs) * 60);
  return mins > 0 ? `${hrs}h ${mins}m` : `${hrs}h`;
}

interface StatProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  color?: string;
}

function Stat({ icon, label, value, sub, color = 'primary.main' }: StatProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        p: 2,
        borderRadius: 2,
        bgcolor: 'background.default',
        border: '1px solid',
        borderColor: 'divider',
        gap: 0.5,
        minWidth: 110,
        flex: 1,
      }}
    >
      <Box sx={{ color, display: 'flex', alignItems: 'center', mb: 0.5 }}>{icon}</Box>
      <Typography variant="h6" fontWeight={700} lineHeight={1}>
        {value}
      </Typography>
      {sub && (
        <Typography variant="caption" color="text.secondary" lineHeight={1}>
          {sub}
        </Typography>
      )}
      <Typography variant="caption" color="text.secondary" fontWeight={500}>
        {label}
      </Typography>
    </Box>
  );
}

export default function TripSummary({ result }: Props) {
  const { route, stops, daily_logs, total_driving_hours, total_trip_days } = result;

  const restStops   = stops.filter((s) => s.type === 'rest').length;
  const fuelStops   = stops.filter((s) => s.type === 'fuel').length;
  const breakStops  = stops.filter((s) => s.type === 'break').length;

  // Total trip elapsed time = last departure time from the last log entry's time range
  const totalRestHours = daily_logs.reduce(
    (acc, d) => acc + d.summary.off_duty_hours + d.summary.sleeper_berth_hours,
    0
  );
  const totalOnDutyHours = daily_logs.reduce((acc, d) => acc + d.summary.on_duty_hours, 0);

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
        <DirectionsCarIcon sx={{ color: '#fff', fontSize: 20 }} />
        <Typography variant="subtitle1" sx={{ color: '#fff', fontWeight: 600 }}>
          Trip Summary
        </Typography>
      </Box>

      <CardContent sx={{ p: 2.5 }}>
        {/* Main stats row */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1.5, mb: 2.5 }}>
          <Stat
            icon={<RouteIcon />}
            label="Total Distance"
            value={`${route.total_distance_miles.toFixed(0)}`}
            sub="miles"
          />
          <Stat
            icon={<AccessTimeIcon />}
            label="Driving Time"
            value={fmtDur(total_driving_hours)}
            color="success.main"
          />
          <Stat
            icon={<AccessTimeIcon />}
            label="Total Trip Time"
            value={fmtDur(total_driving_hours + totalRestHours + totalOnDutyHours)}
            color="secondary.main"
          />
          <Stat
            icon={<CalendarTodayIcon />}
            label="Trip Days"
            value={`${total_trip_days}`}
            sub={total_trip_days === 1 ? 'day' : 'days'}
          />
        </Box>

        <Divider sx={{ mb: 2 }} />

        {/* Stop breakdown */}
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          STOP BREAKDOWN
        </Typography>
        <Grid container spacing={1}>
          {[
            { label: 'Rest Stops (10hr)', value: restStops, icon: <HotelIcon sx={{ fontSize: 16 }} />, color: '#6a1b9a' },
            { label: '30-min Breaks', value: breakStops, icon: <AccessTimeIcon sx={{ fontSize: 16 }} />, color: '#f57c00' },
            { label: 'Fuel Stops', value: fuelStops, icon: <LocalGasStationIcon sx={{ fontSize: 16 }} />, color: '#00838f' },
          ].map(({ label, value, icon, color }) => (
            <Grid item xs={4} key={label}>
              <Box
                sx={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center',
                  p: 1.5, borderRadius: 2, bgcolor: 'background.default',
                  border: '1px solid', borderColor: 'divider',
                }}
              >
                <Box sx={{ color, mb: 0.5 }}>{icon}</Box>
                <Typography variant="h6" fontWeight={700} lineHeight={1}>
                  {value}
                </Typography>
                <Typography variant="caption" color="text.secondary" textAlign="center">
                  {label}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>

        <Divider sx={{ my: 2 }} />

        {/* HOS hours breakdown */}
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          TOTAL HOS HOURS
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {[
            { label: 'Driving', value: total_driving_hours, color: '#1565c0' },
            { label: 'On Duty', value: totalOnDutyHours, color: '#f57c00' },
            { label: 'Off Duty', value: totalRestHours, color: '#4caf50' },
          ].map(({ label, value, color }) => (
            <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, flex: '1 1 auto', minWidth: 100 }}>
              <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: color, flexShrink: 0 }} />
              <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>{label}</Typography>
              <Typography variant="body2" fontWeight={700}>{fmtDur(value)}</Typography>
            </Box>
          ))}
        </Box>
      </CardContent>
    </Card>
  );
}
