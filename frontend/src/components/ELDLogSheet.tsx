/**
 * ELDLogSheet — wraps ELDLogGrid in an authentic-looking FMCSA daily log
 * sheet card.  Includes a header with the date, the SVG grid (horizontally
 * scrollable on small screens), a per-row hours summary, and a remarks section.
 */

import {
  Card,
  CardContent,
  Typography,
  Box,
  Chip,
  Divider,
  Grid,
} from '@mui/material';
import EventNoteIcon from '@mui/icons-material/EventNote';
import ELDLogGrid from './ELDLogGrid';
import type { DailyLog, HosStatus } from '../types/api';

interface Props {
  log: DailyLog;
  dayNumber: number;
}

const STATUS_COLOR: Record<HosStatus, string> = {
  OFF: '#4caf50',
  SB:  '#9c27b0',
  D:   '#1565c0',
  ON:  '#f57c00',
};

function fmtDate(dateStr: string): string {
  return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function fmtHoursFull(h: number): string {
  const hrs  = Math.floor(h);
  const mins = Math.round((h - hrs) * 60);
  if (h === 0) return '0:00';
  return mins > 0 ? `${hrs}:${String(mins).padStart(2, '0')}` : `${hrs}:00`;
}

function totalDayHours(summary: DailyLog['summary']): number {
  return (
    summary.off_duty_hours +
    summary.sleeper_berth_hours +
    summary.driving_hours +
    summary.on_duty_hours
  );
}

export default function ELDLogSheet({ log, dayNumber }: Props) {
  const { date, entries, summary } = log;
  const totalHours = totalDayHours(summary);

  // Collect unique location remarks from entries (deduplicated, non-empty)
  const remarks = Array.from(
    new Set(entries.map((e) => e.location).filter((l) => l.trim()))
  ).slice(0, 6);

  const summaryRows: { code: HosStatus; label: string; value: number }[] = [
    { code: 'OFF', label: 'Off Duty',        value: summary.off_duty_hours },
    { code: 'SB',  label: 'Sleeper Berth',   value: summary.sleeper_berth_hours },
    { code: 'D',   label: 'Driving',         value: summary.driving_hours },
    { code: 'ON',  label: 'On Duty (N/D)',   value: summary.on_duty_hours },
  ];

  return (
    <Card
      sx={{
        // Print-friendly: each sheet gets a page break
        '@media print': { pageBreakBefore: dayNumber > 1 ? 'always' : 'auto' },
      }}
    >
      {/* ── Sheet header ─────────────────────────────────────────────────────── */}
      <Box
        sx={{
          px: 2.5,
          py: 1.5,
          background: 'linear-gradient(90deg, #1a237e 0%, #283593 100%)',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          flexWrap: 'wrap',
        }}
      >
        <EventNoteIcon sx={{ color: '#fff', fontSize: 20 }} />
        <Typography variant="subtitle1" sx={{ color: '#fff', fontWeight: 700 }}>
          Driver's Daily Log — Day {dayNumber}
        </Typography>
        <Chip
          label={fmtDate(date)}
          size="small"
          sx={{
            bgcolor: 'rgba(255,255,255,0.15)',
            color: '#e8eaf6',
            border: '1px solid rgba(255,255,255,0.2)',
            fontWeight: 500,
            fontSize: '0.75rem',
            ml: { xs: 0, sm: 'auto' },
          }}
        />
        <Chip
          label="24-Hour Period"
          size="small"
          sx={{
            bgcolor: 'rgba(255,255,255,0.08)',
            color: 'rgba(255,255,255,0.7)',
            border: '1px solid rgba(255,255,255,0.15)',
            fontSize: '0.7rem',
          }}
        />
      </Box>

      <CardContent sx={{ p: 2.5 }}>
        {/* ── FMCSA form attribution ────────────────────────────────────────── */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1.5, alignItems: 'baseline' }}>
          <Typography variant="caption" color="text.disabled" sx={{ fontFamily: 'monospace' }}>
            FMCSA Form 395.1 — Property-Carrying Driver — 70-Hr/8-Day Cycle
          </Typography>
          <Typography variant="caption" color="text.disabled" sx={{ fontFamily: 'monospace' }}>
            Total: {fmtHoursFull(totalHours)} / 24 hrs
          </Typography>
        </Box>

        {/* ── Log grid (scrollable on small screens) ───────────────────────── */}
        <Box
          sx={{
            overflowX: 'auto',
            overflowY: 'hidden',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            bgcolor: '#fff',
            '-webkit-overflow-scrolling': 'touch',
          }}
        >
          <Box sx={{ minWidth: 960, p: '12px 16px 8px' }}>
            <ELDLogGrid entries={entries} summary={summary} />
          </Box>
        </Box>

        {/* ── Hours summary table ───────────────────────────────────────────── */}
        <Box
          sx={{
            mt: 2,
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 1,
            overflow: 'hidden',
          }}
        >
          <Grid container>
            {summaryRows.map(({ code, label, value }, i) => (
              <Grid
                item
                xs={6}
                sm={3}
                key={code}
                sx={{
                  p: 1.5,
                  borderRight: i < 3 ? '1px solid' : 'none',
                  borderRightColor: 'divider',
                  borderBottom: { xs: i < 2 ? '1px solid' : 'none', sm: 'none' },
                  borderBottomColor: 'divider',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 0.25,
                  bgcolor: value > 0 ? `${STATUS_COLOR[code]}08` : 'transparent',
                }}
              >
                <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: STATUS_COLOR[code] }} />
                <Typography
                  variant="h6"
                  fontWeight={700}
                  sx={{ color: value > 0 ? STATUS_COLOR[code] : 'text.disabled', lineHeight: 1.2 }}
                >
                  {fmtHoursFull(value)}
                </Typography>
                <Typography variant="caption" color="text.secondary" textAlign="center">
                  {label}
                </Typography>
              </Grid>
            ))}
          </Grid>
        </Box>

        {/* ── Remarks / locations ───────────────────────────────────────────── */}
        {remarks.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              REMARKS / LOCATIONS
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
              {remarks.map((r, i) => (
                <Chip
                  key={i}
                  label={r}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: '0.72rem', maxWidth: 300 }}
                />
              ))}
            </Box>
          </>
        )}

        {/* ── Entry-level annotations ───────────────────────────────────────── */}
        {entries.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              DUTY STATUS CHANGES
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              {entries.filter(e => e.location).map((entry, i) => {
                const color = STATUS_COLOR[entry.status] ?? '#9e9e9e';
                const sh = Math.floor(entry.start_hour);
                const sm = Math.round((entry.start_hour - sh) * 60);
                const eh = Math.floor(entry.end_hour);
                const em = Math.round((entry.end_hour - eh) * 60);
                const startStr = `${sh.toString().padStart(2, '0')}:${sm.toString().padStart(2, '0')}`;
                const endStr   = `${eh.toString().padStart(2, '0')}:${em.toString().padStart(2, '0')}`;
                return (
                  <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box
                      sx={{
                        width: 32,
                        textAlign: 'center',
                        fontWeight: 700,
                        fontSize: '0.7rem',
                        color,
                        fontFamily: 'monospace',
                        bgcolor: `${color}15`,
                        borderRadius: 0.5,
                        px: 0.5,
                        py: 0.25,
                        flexShrink: 0,
                      }}
                    >
                      {entry.status}
                    </Box>
                    <Typography variant="caption" color="text.disabled" sx={{ fontFamily: 'monospace', flexShrink: 0 }}>
                      {startStr}–{endStr}
                    </Typography>
                    {entry.location && (
                      <Typography variant="caption" color="text.secondary" noWrap sx={{ overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {entry.location}
                      </Typography>
                    )}
                  </Box>
                );
              })}
            </Box>
          </>
        )}
      </CardContent>
    </Card>
  );
}
