/**
 * ELDLogGrid — draws an authentic FMCSA driver's daily log grid using SVG.
 *
 * Grid structure:
 *   - 4 status rows: OFF (Off Duty), SB (Sleeper Berth), D (Driving), ON (On Duty)
 *   - 24-hour X axis (midnight to midnight)
 *   - Quarter-hour tick marks
 *   - Hour labels: M, 1, 2 … 11, N, 1, 2 … 11, M
 *   - Status path: a continuous "step" line drawn using SVG <polyline>
 *     that moves horizontally for each period and vertically at transitions
 *   - Total hours displayed to the right of each row
 */

import type { ELDEntry, HosStatus, DaySummary } from '../types/api';

interface Props {
  entries: ELDEntry[];
  summary: DaySummary;
}

// ── Layout constants ───────────────────────────────────────────────────────────

const LEFT_W    = 52;   // width of row-label column
const RIGHT_W   = 64;   // width of row-total column
const GRID_W    = 840;  // width of the 24-hour drawing area
const ROW_H     = 44;   // height of each of the 4 status rows
const HEADER_H  = 28;   // height above grid for hour labels
const FOOTER_H  = 8;    // small bottom padding
const NUM_ROWS  = 4;

const TOTAL_W   = LEFT_W + GRID_W + RIGHT_W;
const GRID_H    = ROW_H * NUM_ROWS;
const TOTAL_H   = HEADER_H + GRID_H + FOOTER_H;
const PX_PER_HR = GRID_W / 24;          // ≈ 35 px per hour
const PX_PER_QH = PX_PER_HR / 4;        // quarter-hour tick spacing

// ── Status row mapping ─────────────────────────────────────────────────────────

const ROW_IDX: Record<HosStatus, number> = { OFF: 0, SB: 1, D: 2, ON: 3 };
const ROW_LABELS: { code: HosStatus; full: string }[] = [
  { code: 'OFF', full: 'Off Duty' },
  { code: 'SB',  full: 'Sleeper Berth' },
  { code: 'D',   full: 'Driving' },
  { code: 'ON',  full: 'On Duty' },
];

const STATUS_COLOR: Record<HosStatus, string> = {
  OFF: '#4caf50',  // green
  SB:  '#9c27b0',  // purple
  D:   '#1565c0',  // blue
  ON:  '#f57c00',  // orange
};

// ── Hour label helpers ─────────────────────────────────────────────────────────

function hourLabel(h: number): string {
  if (h === 0)  return 'M';
  if (h === 12) return 'N';
  if (h < 12)   return String(h);
  return String(h - 12);
}

function rowY(rowIdx: number): number {
  return HEADER_H + rowIdx * ROW_H + ROW_H / 2;
}

// ── Build the SVG polyline points for the status path ─────────────────────────

function buildPolylinePoints(entries: ELDEntry[]): string {
  if (entries.length === 0) return '';

  const pts: [number, number][] = [];

  entries.forEach((entry, i) => {
    const x1 = LEFT_W + entry.start_hour * PX_PER_HR;
    const x2 = LEFT_W + entry.end_hour   * PX_PER_HR;
    const y  = rowY(ROW_IDX[entry.status] ?? 0);

    if (i === 0) {
      // Start of path
      pts.push([x1, y]);
    } else {
      // The previous point is at [x1_prev_end, y_prev].
      // Adding [x1, y] here creates a vertical connector at x1.
      pts.push([x1, y]);
    }

    pts.push([x2, y]);
  });

  return pts.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(' ');
}

// ── Totals helpers ─────────────────────────────────────────────────────────────

function summaryForRow(code: HosStatus, summary: DaySummary): number {
  const map: Record<HosStatus, number> = {
    OFF: summary.off_duty_hours,
    SB:  summary.sleeper_berth_hours,
    D:   summary.driving_hours,
    ON:  summary.on_duty_hours,
  };
  return map[code] ?? 0;
}

function fmtHours(h: number): string {
  if (h === 0) return '—';
  const hrs  = Math.floor(h);
  const mins = Math.round((h - hrs) * 60);
  return mins > 0 ? `${hrs}:${String(mins).padStart(2, '0')}` : `${hrs}:00`;
}

// ── Component ──────────────────────────────────────────────────────────────────

export default function ELDLogGrid({ entries, summary }: Props) {
  const polylinePoints = buildPolylinePoints(entries);

  return (
    <svg
      viewBox={`0 0 ${TOTAL_W} ${TOTAL_H}`}
      width={TOTAL_W}
      height={TOTAL_H}
      style={{ display: 'block', fontFamily: 'monospace, sans-serif' }}
      aria-label="ELD daily log grid"
    >
      {/* ── Background ─────────────────────────────────────────────────────── */}
      <rect x={0} y={0} width={TOTAL_W} height={TOTAL_H} fill="#fff" />

      {/* ── Alternating row bands ────────────────────────────────────────────── */}
      {ROW_LABELS.map(({ code }, i) => (
        <rect
          key={code}
          x={LEFT_W}
          y={HEADER_H + i * ROW_H}
          width={GRID_W}
          height={ROW_H}
          fill={i % 2 === 0 ? '#fafafa' : '#f3f4f6'}
        />
      ))}

      {/* ── Quarter-hour vertical tick marks ─────────────────────────────────── */}
      {Array.from({ length: 24 * 4 + 1 }, (_, q) => {
        const x = LEFT_W + q * PX_PER_QH;
        const isHour    = q % 4 === 0;
        const isHalfHr  = q % 2 === 0 && !isHour;
        const tickH     = isHour ? GRID_H : isHalfHr ? ROW_H * 0.5 : ROW_H * 0.25;
        return (
          <line
            key={q}
            x1={x} y1={HEADER_H}
            x2={x} y2={isHour ? HEADER_H + GRID_H : HEADER_H + tickH}
            stroke={isHour ? '#9e9e9e' : isHalfHr ? '#d0d0d0' : '#e8e8e8'}
            strokeWidth={isHour ? (q % 12 === 0 ? 1.5 : 1) : 0.5}
          />
        );
      })}

      {/* ── Horizontal row separator lines ───────────────────────────────────── */}
      {Array.from({ length: NUM_ROWS + 1 }, (_, i) => (
        <line
          key={i}
          x1={LEFT_W} y1={HEADER_H + i * ROW_H}
          x2={LEFT_W + GRID_W} y2={HEADER_H + i * ROW_H}
          stroke={i === 0 || i === NUM_ROWS ? '#757575' : '#bdbdbd'}
          strokeWidth={i === 0 || i === NUM_ROWS ? 1.5 : 1}
        />
      ))}

      {/* ── Grid border (left + right) ────────────────────────────────────────── */}
      <line x1={LEFT_W} y1={HEADER_H} x2={LEFT_W} y2={HEADER_H + GRID_H} stroke="#757575" strokeWidth={1.5} />
      <line x1={LEFT_W + GRID_W} y1={HEADER_H} x2={LEFT_W + GRID_W} y2={HEADER_H + GRID_H} stroke="#757575" strokeWidth={1.5} />

      {/* ── Hour labels (top) ────────────────────────────────────────────────── */}
      {Array.from({ length: 25 }, (_, h) => (
        <text
          key={h}
          x={LEFT_W + h * PX_PER_HR}
          y={HEADER_H - 6}
          textAnchor="middle"
          fontSize={h === 0 || h === 12 || h === 24 ? 9 : 8.5}
          fontWeight={h === 0 || h === 12 || h === 24 ? 700 : 400}
          fill={h === 0 || h === 12 || h === 24 ? '#424242' : '#616161'}
          fontFamily="monospace, sans-serif"
        >
          {hourLabel(h === 24 ? 0 : h)}
        </text>
      ))}

      {/* ── Row labels (left) ────────────────────────────────────────────────── */}
      {ROW_LABELS.map(({ code, full }, i) => (
        <g key={code}>
          {/* Short code */}
          <text
            x={LEFT_W - 6}
            y={HEADER_H + i * ROW_H + ROW_H / 2 - 5}
            textAnchor="end"
            fontSize={11}
            fontWeight={700}
            fill="#1a1a1a"
            fontFamily="monospace, sans-serif"
          >
            {code}
          </text>
          {/* Long label */}
          <text
            x={LEFT_W - 6}
            y={HEADER_H + i * ROW_H + ROW_H / 2 + 7}
            textAnchor="end"
            fontSize={7.5}
            fill="#757575"
            fontFamily="sans-serif"
          >
            {full}
          </text>
        </g>
      ))}

      {/* ── Row total labels (right) ─────────────────────────────────────────── */}
      {ROW_LABELS.map(({ code }, i) => {
        const hours = summaryForRow(code, summary);
        return (
          <g key={`tot-${code}`}>
            <text
              x={LEFT_W + GRID_W + RIGHT_W / 2}
              y={HEADER_H + i * ROW_H + ROW_H / 2 - 4}
              textAnchor="middle"
              fontSize={11}
              fontWeight={700}
              fill={hours > 0 ? STATUS_COLOR[code] : '#bdbdbd'}
              fontFamily="monospace, sans-serif"
            >
              {fmtHours(hours)}
            </text>
            <text
              x={LEFT_W + GRID_W + RIGHT_W / 2}
              y={HEADER_H + i * ROW_H + ROW_H / 2 + 8}
              textAnchor="middle"
              fontSize={7}
              fill="#9e9e9e"
              fontFamily="sans-serif"
            >
              hrs
            </text>
          </g>
        );
      })}

      {/* ── Right column border ───────────────────────────────────────────────── */}
      <line
        x1={LEFT_W + GRID_W + 1} y1={HEADER_H}
        x2={LEFT_W + GRID_W + 1} y2={HEADER_H + GRID_H}
        stroke="#bdbdbd" strokeWidth={1}
      />

      {/* ── Status path (the "ELD line") ──────────────────────────────────────── */}
      {polylinePoints && (
        <polyline
          points={polylinePoints}
          fill="none"
          stroke="#1a237e"
          strokeWidth={2.5}
          strokeLinecap="square"
          strokeLinejoin="miter"
        />
      )}

      {/* ── Entry start/end dots ─────────────────────────────────────────────── */}
      {entries.map((entry, i) => {
        const color = STATUS_COLOR[entry.status] ?? '#1565c0';
        const cx = LEFT_W + entry.start_hour * PX_PER_HR;
        const cy = rowY(ROW_IDX[entry.status] ?? 0);
        return (
          <circle key={i} cx={cx} cy={cy} r={3} fill={color} stroke="#fff" strokeWidth={1.5} />
        );
      })}
    </svg>
  );
}
