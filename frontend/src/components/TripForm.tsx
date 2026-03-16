import { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Box,
  InputAdornment,
  Divider,
  Tooltip,
  Slider,
  CircularProgress,
} from '@mui/material';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import LocalShippingIcon from '@mui/icons-material/LocalShipping';
import FlagIcon from '@mui/icons-material/Flag';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import RouteIcon from '@mui/icons-material/Route';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import type { TripRequest, FormValues, FormErrors } from '../types/api';

interface Props {
  onSubmit: (req: TripRequest) => void;
  loading: boolean;
}

const INITIAL: FormValues = {
  current_location: '',
  pickup_location: '',
  dropoff_location: '',
  current_cycle_used: '0',
};

function validate(v: FormValues): FormErrors {
  const errors: FormErrors = {};
  if (!v.current_location.trim()) errors.current_location = 'Required';
  if (!v.pickup_location.trim()) errors.pickup_location = 'Required';
  if (!v.dropoff_location.trim()) errors.dropoff_location = 'Required';

  const hours = parseFloat(v.current_cycle_used);
  if (isNaN(hours) || hours < 0 || hours > 70) {
    errors.current_cycle_used = 'Must be between 0 and 70 hours';
  }
  return errors;
}

export default function TripForm({ onSubmit, loading }: Props) {
  const [values, setValues] = useState<FormValues>(INITIAL);
  const [errors, setErrors] = useState<FormErrors>({});
  const [touched, setTouched] = useState<Partial<Record<keyof FormValues, boolean>>>({});

  const set = (field: keyof FormValues) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setValues((v) => ({ ...v, [field]: e.target.value }));
    if (touched[field]) {
      setErrors((prev) => ({ ...prev, ...validate({ ...values, [field]: e.target.value }) }));
    }
  };

  const blur = (field: keyof FormValues) => () => {
    setTouched((t) => ({ ...t, [field]: true }));
    setErrors((prev) => ({ ...prev, ...validate(values) }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const allTouched = { current_location: true, pickup_location: true, dropoff_location: true, current_cycle_used: true };
    setTouched(allTouched);
    const errs = validate(values);
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;

    onSubmit({
      current_location: values.current_location.trim(),
      pickup_location: values.pickup_location.trim(),
      dropoff_location: values.dropoff_location.trim(),
      current_cycle_used: parseFloat(values.current_cycle_used),
    });
  };

  const cycleHours = parseFloat(values.current_cycle_used) || 0;
  const cyclePercent = Math.min((cycleHours / 70) * 100, 100);

  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2.5 }}>
          <RouteIcon sx={{ color: 'primary.main' }} />
          <Typography variant="h6">Plan Your Trip</Typography>
        </Box>

        <Box component="form" onSubmit={handleSubmit} noValidate sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Current location */}
          <TextField
            label="Current Location"
            placeholder="e.g. Austin, TX"
            value={values.current_location}
            onChange={set('current_location')}
            onBlur={blur('current_location')}
            error={!!errors.current_location && !!touched.current_location}
            helperText={touched.current_location && errors.current_location}
            fullWidth
            disabled={loading}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <LocationOnIcon sx={{ color: '#4caf50', fontSize: 20 }} />
                </InputAdornment>
              ),
            }}
          />

          {/* Pickup */}
          <TextField
            label="Pickup Location"
            placeholder="e.g. Dallas, TX"
            value={values.pickup_location}
            onChange={set('pickup_location')}
            onBlur={blur('pickup_location')}
            error={!!errors.pickup_location && !!touched.pickup_location}
            helperText={touched.pickup_location && errors.pickup_location}
            fullWidth
            disabled={loading}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <LocalShippingIcon sx={{ color: 'primary.main', fontSize: 20 }} />
                </InputAdornment>
              ),
            }}
          />

          {/* Dropoff */}
          <TextField
            label="Dropoff Location"
            placeholder="e.g. Los Angeles, CA"
            value={values.dropoff_location}
            onChange={set('dropoff_location')}
            onBlur={blur('dropoff_location')}
            error={!!errors.dropoff_location && !!touched.dropoff_location}
            helperText={touched.dropoff_location && errors.dropoff_location}
            fullWidth
            disabled={loading}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <FlagIcon sx={{ color: '#e53935', fontSize: 20 }} />
                </InputAdornment>
              ),
            }}
          />

          <Divider sx={{ my: 0.5 }} />

          {/* Cycle hours */}
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1 }}>
              <AccessTimeIcon sx={{ color: 'text.secondary', fontSize: 18 }} />
              <Typography variant="body2" fontWeight={600} color="text.secondary">
                Current Cycle Used (hrs)
              </Typography>
              <Tooltip
                title="Hours already used in your 70-hour/8-day on-duty cycle. The FMCSA limits drivers to 70 on-duty hours in any 8 consecutive days."
                arrow
                placement="right"
              >
                <InfoOutlinedIcon sx={{ fontSize: 16, color: 'text.disabled', cursor: 'help', ml: 'auto' }} />
              </Tooltip>
            </Box>

            <TextField
              value={values.current_cycle_used}
              onChange={set('current_cycle_used')}
              onBlur={blur('current_cycle_used')}
              error={!!errors.current_cycle_used && !!touched.current_cycle_used}
              helperText={
                (touched.current_cycle_used && errors.current_cycle_used) ||
                `${Math.max(0, 70 - cycleHours).toFixed(1)} hours remaining in cycle`
              }
              type="number"
              inputProps={{ min: 0, max: 70, step: 0.5 }}
              fullWidth
              disabled={loading}
              size="small"
            />

            <Slider
              value={cycleHours}
              onChange={(_, val) => {
                const v = (val as number).toString();
                setValues((prev) => ({ ...prev, current_cycle_used: v }));
              }}
              min={0}
              max={70}
              step={0.5}
              disabled={loading}
              sx={{
                mt: 1,
                color: cyclePercent > 80 ? 'error.main' : cyclePercent > 60 ? 'warning.main' : 'primary.main',
                '& .MuiSlider-thumb': { width: 14, height: 14 },
              }}
            />

            {/* Cycle bar */}
            <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5 }}>
              <Box
                sx={{
                  height: 6,
                  borderRadius: 3,
                  flex: cyclePercent,
                  bgcolor: cyclePercent > 80 ? 'error.main' : cyclePercent > 60 ? 'warning.main' : 'primary.main',
                  transition: 'flex 0.2s, background-color 0.2s',
                  minWidth: 0,
                }}
              />
              <Box
                sx={{
                  height: 6,
                  borderRadius: 3,
                  flex: 100 - cyclePercent,
                  bgcolor: 'grey.200',
                  minWidth: 0,
                }}
              />
            </Box>
          </Box>

          {/* Submit */}
          <Button
            type="submit"
            variant="contained"
            fullWidth
            disabled={loading}
            size="large"
            sx={{ mt: 1 }}
            startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <RouteIcon />}
          >
            {loading ? 'Calculating Route…' : 'Calculate Trip'}
          </Button>

          {loading && (
            <Typography variant="caption" color="text.secondary" textAlign="center">
              Geocoding locations and computing HOS schedule…
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
}
