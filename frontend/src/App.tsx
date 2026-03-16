import { useState } from 'react';
import { Box, Container, Grid, Alert, Collapse } from '@mui/material';
import Header from './components/Header';
import TripForm from './components/TripForm';
import RouteMap from './components/RouteMap';
import TripSummary from './components/TripSummary';
import ELDLogSheet from './components/ELDLogSheet';
import StopDetails from './components/StopDetails';
import LoadingSkeleton from './components/LoadingSkeleton';
import { calculateTrip, parseApiError } from './services/tripApi';
import type { TripRequest, TripResponse } from './types/api';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TripResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleCalculate = async (req: TripRequest) => {
    setLoading(true);
    setErrorMsg(null);
    setResult(null);

    try {
      const data = await calculateTrip(req);
      setResult(data);
      // Scroll to results on mobile
      setTimeout(() => {
        document.getElementById('results-section')?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (err) {
      const { message } = parseApiError(err);
      setErrorMsg(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <Header />

      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Grid container spacing={3} alignItems="flex-start">
          {/* ── Left column: form ───────────────────────────────────── */}
          <Grid item xs={12} md={4} lg={3}>
            <Box sx={{ position: { md: 'sticky' }, top: { md: 80 } }}>
              <TripForm onSubmit={handleCalculate} loading={loading} />
            </Box>
          </Grid>

          {/* ── Right column: results ────────────────────────────────── */}
          <Grid item xs={12} md={8} lg={9} id="results-section">
            <Collapse in={!!errorMsg}>
              <Alert
                severity="error"
                onClose={() => setErrorMsg(null)}
                sx={{ mb: 2, borderRadius: 2 }}
              >
                {errorMsg}
              </Alert>
            </Collapse>

            {loading && <LoadingSkeleton />}

            {result && !loading && (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {/* Map */}
                <RouteMap result={result} />

                {/* Trip summary */}
                <TripSummary result={result} />

                {result.total_trip_days > 5 && (
                  <Alert severity="info" sx={{ borderRadius: 2 }}>
                    This trip spans <strong>{result.total_trip_days} days</strong> due to mandatory
                    HOS rest periods. Scroll down to view all daily log sheets.
                  </Alert>
                )}

                {/* ELD daily log sheets */}
                {result.daily_logs.map((log, i) => (
                  <ELDLogSheet key={log.date} log={log} dayNumber={i + 1} />
                ))}

                {/* Stop details timeline */}
                <StopDetails stops={result.stops} />
              </Box>
            )}

            {!loading && !result && !errorMsg && (
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: 300,
                  color: 'text.secondary',
                  flexDirection: 'column',
                  gap: 1,
                }}
              >
                <Box sx={{ fontSize: 64, opacity: 0.2 }}>🚛</Box>
                <Box sx={{ typography: 'body1', opacity: 0.5 }}>
                  Enter trip details to generate your ELD log
                </Box>
              </Box>
            )}
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}
