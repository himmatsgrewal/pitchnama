import { useState, useEffect, useRef } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
  Legend, ResponsiveContainer,
} from 'recharts'
import { toPng } from 'html-to-image'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function formatDeliveries(n) {
  return (n / 1_000_000).toFixed(1) + 'M'
}

const COMPETITION_LABELS = {
  ipl: 'IPL', t20i: 'T20I', odi: 'ODI', test: 'Test',
  bbl: 'BBL', psl: 'PSL', cpl: 'CPL',
}

// ---- DRAFT tilt formula (uncalibrated; we tighten the dial in a later pass) ----
function computeTilt(c) {
  const m = c.overall_matchup
  const b = c.overall_baseline

  const scoring = (m.sr / b.sr - 1) * 100

  const baselineBpd = b.balls / b.wickets
  let dismissal
  if (m.wickets === 0) {
    dismissal = 100
  } else {
    const matchupBpd = m.balls / m.wickets
    dismissal = (matchupBpd / baselineBpd - 1) * 100
  }

  // Weight scoring vs survival by format.
  // Tests: 50/50 - survival matters as much as scoring in long-form cricket.
  // T20 / ODI / All formats: 60/40 - limited-overs (and the overall picture,
  // since most deliveries are limited-overs) values scoring more.
  const scoringWeight = c.format === 'Test' ? 0.5 : 0.6
  const dismissalWeight = 1 - scoringWeight
  const raw = scoring * scoringWeight + dismissal * dismissalWeight
  const needle = 100 * Math.tanh(raw / 50)

  const mag = Math.abs(needle)
  let verdict
  if (mag < 6) {
    verdict = 'Even contest'
  } else {
    const side = needle > 0 ? 'Batter edge' : 'Bowler edge'
    const strength = mag < 18 ? 'slight' : mag < 45 ? 'clear' : 'strong'
    verdict = `${side} · ${strength}`
  }

  const srPct = Math.round((m.sr / b.sr - 1) * 100)
  const srPart = srPct >= 0 ? `strike rate up ${srPct}%` : `strike rate down ${Math.abs(srPct)}%`
  let outPart
  if (m.wickets === 0) {
    outPart = `not dismissed in ${m.balls} balls`
  } else {
    outPart = `dismissed every ${Math.round(m.balls / m.wickets)} balls vs his usual ${Math.round(baselineBpd)}`
  }

  return { needle, verdict, why: `${srPart}, ${outPart}`, smallSample: c.sample_size < 30 }
}

function TiltMeter({ tilt, shown }) {
  const rotation = -tilt.needle * 0.9
  // Even contests (verdict starts with "Even") get no winner; nobody breathes.
  const winner = tilt.verdict.startsWith('Even')
    ? null
    : tilt.needle > 0 ? 'batter' : 'bowler'

  return (
    <div className={`mx-auto mt-8 max-w-sm ${tilt.smallSample ? 'opacity-40' : ''}`}>
      <svg viewBox="0 0 300 175" className="w-full">
        <defs>
          {/* Static, gentle glow - used on the losing side (and both sides when even). */}
          <filter id="glow-static" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Breathing glow - applied only to the winning side. */}
          <filter id="glow-pulse" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="blur">
              <animate
                attributeName="stdDeviation"
                values="2.5;8;2.5"
                dur="2.6s"
                repeatCount="indefinite"
                calcMode="spline"
                keyTimes="0;0.5;1"
                keySplines="0.4 0 0.6 1;0.4 0 0.6 1"
              />
            </feGaussianBlur>
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Halo behind each arc - pulses only on the winning side. */}
        <path
          d="M 30 150 A 120 120 0 0 1 150 30"
          fill="none" stroke="#2ecc71" strokeWidth="16" strokeLinecap="round"
          opacity={winner === 'batter' ? 0.6 : 0.25}
          filter={winner === 'batter' ? 'url(#glow-pulse)' : 'url(#glow-static)'}
        />
        <path
          d="M 150 30 A 120 120 0 0 1 270 150"
          fill="none" stroke="#e0a92e" strokeWidth="16" strokeLinecap="round"
          opacity={winner === 'bowler' ? 0.6 : 0.25}
          filter={winner === 'bowler' ? 'url(#glow-pulse)' : 'url(#glow-static)'}
        />

        {/* Crisp top arcs (always solid) */}
        <path d="M 30 150 A 120 120 0 0 1 150 30" fill="none" stroke="#2ecc71" strokeWidth="16" strokeLinecap="round" />
        <path d="M 150 30 A 120 120 0 0 1 270 150" fill="none" stroke="#e0a92e" strokeWidth="16" strokeLinecap="round" />

        {/* Needle */}
        <g
          style={{
            transformOrigin: '150px 150px',
            transformBox: 'view-box',
            transform: `rotate(${shown ? rotation : 0}deg)`,
            transition: 'transform 1100ms cubic-bezier(0.34, 1.55, 0.5, 1)',
          }}
        >
          <line x1="150" y1="150" x2="150" y2="48" stroke="white" strokeWidth="5" strokeLinecap="round" />
        </g>
        <circle cx="150" cy="150" r="9" fill="white" />
        <text x="30" y="171" textAnchor="middle" fontSize="13" fontWeight="bold" fill="#2ecc71">Batter</text>
        <text x="270" y="171" textAnchor="middle" fontSize="13" fontWeight="bold" fill="#e0a92e">Bowler</text>
      </svg>

      <p className="mt-2 text-center text-lg font-bold text-white">{tilt.verdict}</p>
      <p className="mt-1 text-center text-sm text-gray-400">{tilt.why}</p>
      {tilt.smallSample && (
        <p className="mt-1 text-center text-xs uppercase tracking-wide text-gray-500">small sample</p>
      )}
    </div>
  )
}

function StatCard({ label, value, shown, delay }) {
  return (
    <div
      className={`rounded-lg bg-surface px-4 py-4 text-center transition-all duration-500 ease-out ${
        shown ? 'translate-y-0 opacity-100' : 'translate-y-3 opacity-0'
      }`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <div className="text-3xl font-bold text-white">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-gray-400">{label}</div>
    </div>
  )
}

function PhaseTable({ phases }) {
  const cols = [
    ['Balls', (p) => p.balls],
    ['Runs', (p) => p.runs],
    ['Avg', (p) => (p.avg != null ? p.avg.toFixed(1) : '-')],
    ['SR', (p) => (p.sr != null ? p.sr.toFixed(1) : '-')],
    ['Wkts', (p) => p.wickets],
    ['Dot %', (p) => (p.dot_pct != null ? p.dot_pct.toFixed(0) : '-')],
  ]
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-gray-400">
            <th className="py-2 pr-3 text-left font-medium">Phase</th>
            {cols.map(([h]) => (
              <th key={h} className="px-3 py-2 text-right font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(phases).map(([name, p]) => (
            <tr key={name} className="border-t border-white/10">
              <td className="py-2 pr-3 text-left text-gray-200">{name}</td>
              {cols.map(([h, get]) => (
                <td key={h} className="px-3 py-2 text-right text-white">{get(p)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PhasesPanel({ data }) {
  const formats = Object.entries(data.phase_splits_by_format || {})
  if (formats.length === 0) {
    return <p className="text-center text-gray-500">No phase data for this scope.</p>
  }
  return (
    <div className="space-y-8">
      {formats.map(([fmt, phases]) => (
        <div key={fmt}>
          <h4 className="mb-2 text-sm font-bold uppercase tracking-wide text-pitch-green">{fmt}</h4>
          <PhaseTable phases={phases} />
        </div>
      ))}
    </div>
  )
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null
  return (
    <div className="rounded-lg border border-white/10 bg-surface px-3 py-2 text-sm shadow-lg">
      <p className="font-bold text-white">{label}</p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="mt-0.5 text-gray-300">
          <span style={{ color: entry.color }}>●</span>{' '}
          <span className="text-gray-400">{entry.name}:</span>{' '}
          <span className="font-medium text-white">
            {entry.value != null ? entry.value.toFixed(1) : '-'}
          </span>
          {entry.payload?.balls != null && entry.dataKey === 'sr' && (
            <span className="text-gray-500"> ({entry.payload.balls} balls)</span>
          )}
        </p>
      ))}
    </div>
  )
}

function ChartHeader({ title, subtitle }) {
  return (
    <div className="mb-3">
      <h4 className="text-sm font-bold uppercase tracking-wide text-pitch-green">{title}</h4>
      {subtitle && <p className="mt-1 text-xs text-gray-500">{subtitle}</p>}
    </div>
  )
}

function PressureMetric({ label, baseline, matchup, delta, batterFriendlyHigh }) {
  const batterDoingBetter = batterFriendlyHigh ? delta > 0 : delta < 0
  const arrow = delta > 0 ? '▲' : delta < 0 ? '▼' : '·'
  const arrowColor = batterDoingBetter ? '#2ecc71' : '#e0a92e'
  return (
    <div className="rounded-lg bg-surface p-4 text-center">
      <p className="text-xs uppercase tracking-wide text-gray-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-white">
        {matchup.toFixed(0)}<span className="text-sm text-gray-500">%</span>
      </p>
      <p className="mt-1 text-xs text-gray-500">
        usual {baseline.toFixed(0)}%
      </p>
      <p className="mt-2 text-sm font-medium" style={{ color: arrowColor }}>
        {arrow} {Math.abs(delta).toFixed(0)}%
      </p>
    </div>
  )
}

// The shareable card - rendered in the viewport but hidden via `visibility`
// (everything still paints, the browser just doesn't show it).
// Briefly shown during capture so html-to-image gets accurate styles.
function ShareCard({ data, compare, tilt, cardRef, scopeLabel, batterLabel, bowlerLabel, visible }) {
  if (!data || !compare || !tilt) return null

  const rotation = -tilt.needle * 0.9

  return (
    <div
      ref={cardRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '1080px',
        height: '1080px',
        pointerEvents: 'none',
        zIndex: 9999,
        visibility: visible ? 'visible' : 'hidden',
        background:
          'radial-gradient(circle at 15% 15%, rgba(46,204,113,0.18), transparent 50%), ' +
          'radial-gradient(circle at 85% 20%, rgba(224,169,46,0.16), transparent 50%), ' +
          'radial-gradient(circle at 50% 110%, rgba(46,204,113,0.10), transparent 60%), ' +
          '#0d1117',
        color: '#ffffff',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        padding: '60px 70px',
        boxSizing: 'border-box',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{ fontSize: '32px', fontWeight: 700, letterSpacing: '0.5px' }}>
        Pitch<span style={{ color: '#e0a92e' }}>Nama</span>
      </div>

      <div style={{ marginTop: '60px', textAlign: 'center' }}>
        <div style={{ fontSize: '64px', fontWeight: 800, lineHeight: 1.1 }}>
          <span style={{ color: '#2ecc71' }}>{batterLabel}</span>
          <span style={{ color: '#6b7280', margin: '0 18px', fontWeight: 600 }}>vs</span>
          <span style={{ color: '#e0a92e' }}>{bowlerLabel}</span>
        </div>
        <div style={{ marginTop: '14px', fontSize: '22px', color: '#9ca3af' }}>
          {scopeLabel} · {data.matches_played} matches · {data.total_balls} balls
        </div>
      </div>

      <div style={{ marginTop: '48px', display: 'flex', justifyContent: 'center' }}>
        <svg viewBox="0 0 300 175" width="520" height="304">
          <path d="M 30 150 A 120 120 0 0 1 150 30" fill="none" stroke="#2ecc71" strokeWidth="16" strokeLinecap="round" />
          <path d="M 150 30 A 120 120 0 0 1 270 150" fill="none" stroke="#e0a92e" strokeWidth="16" strokeLinecap="round" />
          <g style={{ transformOrigin: '150px 150px', transformBox: 'view-box', transform: `rotate(${rotation}deg)` }}>
            <line x1="150" y1="150" x2="150" y2="48" stroke="white" strokeWidth="5" strokeLinecap="round" />
          </g>
          <circle cx="150" cy="150" r="9" fill="white" />
          <text x="30" y="171" textAnchor="middle" fontSize="13" fontWeight="bold" fill="#2ecc71">Batter</text>
          <text x="270" y="171" textAnchor="middle" fontSize="13" fontWeight="bold" fill="#e0a92e">Bowler</text>
        </svg>
      </div>

      <div style={{ marginTop: '8px', textAlign: 'center' }}>
        <div style={{ fontSize: '36px', fontWeight: 700, color: '#ffffff' }}>{tilt.verdict}</div>
        <div style={{ marginTop: '8px', fontSize: '20px', color: '#9ca3af' }}>{tilt.why}</div>
      </div>

      <div
        style={{
          marginTop: '40px',
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '14px',
        }}
      >
        {[
          { label: 'Balls', value: data.total_balls },
          { label: 'Runs', value: data.total_runs },
          { label: 'Average', value: data.avg != null ? data.avg.toFixed(1) : '-' },
          { label: 'Strike rate', value: data.sr.toFixed(1) },
          { label: 'Dismissals', value: data.dismissals },
          { label: 'Matches', value: data.matches_played },
        ].map((c) => (
          <div
            key={c.label}
            style={{
              background: '#141b24',
              borderRadius: '12px',
              padding: '16px 12px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '38px', fontWeight: 800, color: '#ffffff' }}>{c.value}</div>
            <div style={{ marginTop: '4px', fontSize: '14px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '1px' }}>
              {c.label}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 'auto', textAlign: 'center', fontSize: '18px', color: '#9ca3af' }}>
        pitchnama.com · the chronicle of every contest
      </div>
    </div>
  )
}

function ChartsPanel({ data, compare }) {
  if (!compare || !data) {
    return <p className="text-center text-gray-500">No chart data available.</p>
  }

  const m = compare.overall_matchup
  const b = compare.overall_baseline

  const headlineData = [
    { metric: 'Strike rate', baseline: b.sr, matchup: m.sr },
    ...(m.avg != null && b.avg != null
      ? [{ metric: 'Average', baseline: b.avg, matchup: m.avg }]
      : []),
  ]

  const phaseChartsData = Object.entries(compare.phases_by_format || {}).map(
    ([fmt, phases]) => ({
      fmt,
      rows: Object.entries(phases)
        .filter(([, p]) => p.matchup_balls >= 5 && p.matchup_sr != null && p.baseline_sr != null)
        .map(([phase, p]) => ({
          phase,
          baseline: p.baseline_sr,
          matchup: p.matchup_sr,
          balls: p.matchup_balls,
        })),
    })
  ).filter((g) => g.rows.length > 0)

  const hasPressure = m.dot_pct != null && b.dot_pct != null
    && m.boundary_pct != null && b.boundary_pct != null
  const pressure = hasPressure ? {
    dotDelta: m.dot_pct - b.dot_pct,
    boundaryDelta: m.boundary_pct - b.boundary_pct,
  } : null

  const competitionData = Object.entries(data.competition_breakdown || {})
    .filter(([, s]) => s.balls > 0 && s.sr != null)
    .map(([code, s]) => ({
      competition: COMPETITION_LABELS[code] || code.toUpperCase(),
      sr: s.sr,
      balls: s.balls,
    }))

  return (
    <div className="space-y-12">
      <div>
        <ChartHeader
          title="Career baseline vs this matchup"
          subtitle="Green = his usual numbers. Gold = under this bowler's pressure."
        />
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={headlineData} margin={{ top: 20, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="metric" stroke="#9ca3af" tick={{ fontSize: 13 }} axisLine={false} tickLine={false} />
            <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
            <Legend
              wrapperStyle={{ paddingTop: 12, fontSize: 13 }}
              iconType="circle"
              formatter={(v) => <span className="text-gray-300">{v}</span>}
            />
            <Bar dataKey="baseline" name="Career baseline" fill="#2ecc71" radius={[6, 6, 0, 0]} />
            <Bar dataKey="matchup" name="Vs this bowler" fill="#e0a92e" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {phaseChartsData.length > 0 && (
        <div>
          <ChartHeader
            title="Phase strike rate"
            subtitle="Where in the innings does the matchup tip? Each chart compares his usual phase SR (green) to the matchup (gold)."
          />
          <div className="space-y-6">
            {phaseChartsData.map(({ fmt, rows }) => (
              <div key={fmt}>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-300">{fmt}</p>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={rows} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="phase" stroke="#9ca3af" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                    <Bar dataKey="baseline" name="His usual" fill="#2ecc71" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="matchup" name="Vs this bowler" fill="#e0a92e" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ))}
          </div>
        </div>
      )}

      {pressure && (
        <div>
          <ChartHeader
            title="How the bowler does it"
            subtitle="Dot balls and boundaries against this bowler vs his usual rate. Gold = bowler ahead, green = batter ahead."
          />
          <div className="grid grid-cols-2 gap-3">
            <PressureMetric
              label="Dot balls"
              baseline={b.dot_pct}
              matchup={m.dot_pct}
              delta={pressure.dotDelta}
              batterFriendlyHigh={false}
            />
            <PressureMetric
              label="Boundaries"
              baseline={b.boundary_pct}
              matchup={m.boundary_pct}
              delta={pressure.boundaryDelta}
              batterFriendlyHigh={true}
            />
          </div>
        </div>
      )}

      {competitionData.length >= 2 && (
        <div>
          <ChartHeader
            title="Strike rate by competition"
            subtitle={`Each bar = strike rate against this bowler in that competition. Dashed green line = his overall career strike rate (${b.sr.toFixed(0)}) for reference.`}
          />
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={competitionData} margin={{ top: 20, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="competition" stroke="#9ca3af" tick={{ fontSize: 13 }} axisLine={false} tickLine={false} />
              <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
              <ReferenceLine
                y={b.sr}
                stroke="#2ecc71"
                strokeDasharray="4 4"
                strokeWidth={1.5}
              />
              <Bar dataKey="sr" name="Strike rate" fill="#e0a92e" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

function PlayerSelect({ placeholder, accentClass, players, loading, value, onChange, onSelect }) {
  const [open, setOpen] = useState(false)

  const q = value.trim().toLowerCase()
  const matches = q ? players.filter((p) => p.search.includes(q)).slice(0, 50) : []

  function choose(player) {
    onChange(player.label)
    setOpen(false)
    onSelect(player.scorecard)
  }

  function handleChange(e) {
    onChange(e.target.value)
    setOpen(true)
    onSelect('')
  }

  return (
    <div className="relative w-64">
      <input
        type="text"
        placeholder={loading ? 'Loading players...' : placeholder}
        value={value}
        disabled={loading}
        onChange={handleChange}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        className={`w-full rounded-lg border-2 ${accentClass} bg-white px-4 py-3 text-lg focus:outline-none`}
      />

      {open && q && (
        <ul className="absolute z-10 mt-1 max-h-72 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white text-left shadow-lg">
          {matches.length === 0 ? (
            <li className="px-4 py-2 text-gray-400">No players found</li>
          ) : (
            matches.map((p) => (
              <li
                key={p.scorecard}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => choose(p)}
                className="cursor-pointer px-4 py-2 hover:bg-gray-100"
              >
                {p.label}
                {p.country && <span className="text-gray-400"> · {p.country}</span>}
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}

function ReportPanel({ report }) {
  if (!report) {
    return <p className="text-center text-gray-500">No report available.</p>
  }
  return (
    <div className="space-y-8 text-left">
      <div>
        <h4 className="mb-2 text-sm font-bold uppercase tracking-wide text-pitch-green">English</h4>
        <p className="leading-relaxed text-gray-200">{report.english}</p>
      </div>
      <div>
        <h4 className="mb-2 text-sm font-bold uppercase tracking-wide text-pitch-green">हिन्दी</h4>
        <p className="leading-relaxed text-gray-200">{report.hindi}</p>
      </div>
    </div>
  )
}

// ---- Landing-page broadcast styles + content (below and around the hero) ----

const LANDING_CSS = `
.pn-wrap { max-width: 1000px; margin: 0 auto; padding: 0 28px; }
.pn-eyebrow {
  font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 600;
  letter-spacing: 2.5px; text-transform: uppercase; display: inline-flex;
  align-items: center; gap: 9px;
}
.pn-eyebrow::before { content: ""; width: 22px; height: 2px; background: currentColor; display: inline-block; }
.pn-eyebrow.grn { color: #1a9e58; }
.pn-eyebrow.gld { color: #b8860b; }

/* ABOUT */
.pn-about { padding: 60px 0 20px; border-top: 1px solid rgba(13,17,23,0.10); }
.pn-about h2 {
  font-family: 'Oswald', sans-serif; font-weight: 600; font-size: 40px; line-height: 1.05;
  letter-spacing: -0.3px; margin: 18px 0 0; max-width: 640px; text-transform: uppercase; color: #0d1117;
}
.pn-lead { margin-top: 18px; max-width: 620px; font-size: 16.5px; line-height: 1.65; color: #384049; }
.pn-lead b.grn { color: #1a9e58; font-weight: 600; }
.pn-lead b.gld { color: #b8860b; font-weight: 600; }

.pn-features { margin-top: 40px; border-top: 2px solid #0d1117; }
@media (min-width: 720px) { .pn-features { display: grid; grid-template-columns: 1fr 1fr; column-gap: 40px; } }
.pn-feat { display: grid; grid-template-columns: 44px 1fr; gap: 18px; padding: 22px 4px;
  border-bottom: 1px solid rgba(13,17,23,0.10); align-items: start; }
.pn-feat .ic { width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; color: #0d1117; }
.pn-feat .ic svg { width: 30px; height: 30px; }
.pn-feat h3 { font-family: 'Oswald', sans-serif; font-weight: 500; font-size: 19px;
  letter-spacing: 0.2px; text-transform: uppercase; margin-bottom: 4px; color: #0d1117; }
.pn-feat p { font-size: 14px; line-height: 1.55; color: #5c6570; max-width: 560px; }

.pn-coverage { margin-top: 26px; display: flex; flex-wrap: wrap; gap: 6px 20px;
  justify-content: space-between; align-items: center; font-family: 'IBM Plex Mono', monospace;
  font-size: 12px; letter-spacing: 0.5px; color: #5c6570; padding: 14px 0 0; border-top: 1px solid rgba(13,17,23,0.10); }
.pn-coverage b { color: #0d1117; }
.pn-coverage a { color: #5c6570; }

/* WHAT'S NEXT */
.pn-next { padding: 56px 0 20px; border-top: 1px solid rgba(13,17,23,0.10); }
.pn-next-grid { margin-top: 26px; display: grid; grid-template-columns: 1fr; gap: 0; }
@media (min-width: 720px) { .pn-next-grid { grid-template-columns: 1fr 1fr; column-gap: 40px; } }
.pn-next-item { padding: 22px 0; border-top: 1px solid rgba(13,17,23,0.10);
  display: grid; grid-template-columns: 1fr auto; align-items: start; gap: 12px; }
.pn-next-item h3 { font-family: 'Oswald', sans-serif; font-weight: 500; font-size: 22px;
  text-transform: uppercase; letter-spacing: 0.2px; color: #0d1117; }
.pn-next-item p { grid-column: 1 / -1; font-size: 14px; line-height: 1.55; color: #5c6570; margin-top: 6px; max-width: 440px; }
.pn-pill { font-family: 'IBM Plex Mono', monospace; font-size: 10px; font-weight: 600;
  letter-spacing: 1.5px; text-transform: uppercase; color: #b8860b;
  border: 1px solid rgba(184,134,11,0.4); padding: 4px 8px; border-radius: 2px; white-space: nowrap; }

/* WHY + VOICES */
.pn-why { padding: 60px 0 30px; border-top: 1px solid rgba(13,17,23,0.10); }
.pn-why-grid { display: grid; grid-template-columns: 1fr; gap: 40px; }
@media (min-width: 900px) { .pn-why-grid { grid-template-columns: 1.35fr 1fr; gap: 56px; align-items: start; } }
.pn-why-inner { max-width: 680px; }
.pn-why-body { margin-top: 20px; }
.pn-why-body p { font-size: 16px; line-height: 1.58; color: #33393f; margin-bottom: 11px; font-style: italic; }
.pn-why-body p.lede { font-family: 'Oswald', sans-serif; font-weight: 400; font-size: 22px;
  line-height: 1.28; text-transform: none; color: #0d1117; letter-spacing: 0; font-style: italic; margin-bottom: 13px; }
.pn-why-body .grn { color: #1a9e58; font-weight: 600; }
.pn-why-body .gld { color: #b8860b; font-weight: 600; }
.pn-why-sign { font-family: 'Oswald', sans-serif; font-weight: 600; font-size: 20px;
  text-transform: uppercase; letter-spacing: 1px; margin-top: 20px; color: #0d1117;
  display: inline-flex; align-items: center; gap: 12px; }
.pn-why-sign::before { content: ""; width: 34px; height: 2px; background: linear-gradient(90deg, #2ecc71, #e0a92e); }

.pn-voices { padding-top: 46px; }
.pn-vhead { font-family: 'Oswald', sans-serif; text-transform: uppercase; letter-spacing: 0.5px;
  font-size: 15px; color: #5c6570; margin: 14px 0 22px; font-weight: 500; }
.pn-quote { padding: 26px 0; border-top: 1px solid rgba(13,17,23,0.10); }
.pn-quote:first-of-type { border-top: 2px solid #0d1117; padding-top: 24px; }
.pn-quote:last-of-type { padding-bottom: 4px; }
.pn-quote p { font-style: italic; font-size: 15.5px; line-height: 1.65; color: #2b3138; margin-bottom: 13px; }
.pn-quote .who { font-family: 'Oswald', sans-serif; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.4px; font-size: 14px; color: #0d1117; }
.pn-quote .role { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #5c6570;
  display: block; margin-top: 2px; letter-spacing: 0.3px; text-transform: none; }

/* FOOTER */
.pn-foot { border-top: 2px solid #0d1117; margin-top: 30px; padding: 26px 0 60px; text-align: center; }
.pn-foot .built { font-family: 'Oswald', sans-serif; text-transform: uppercase; letter-spacing: 0.5px; font-size: 15px; color: #0d1117; }
.pn-foot .built b { font-weight: 600; }
.pn-foot .links { margin-top: 14px; display: flex; gap: 10px; justify-content: center; }
.pn-foot .links a { font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 1px;
  text-transform: uppercase; text-decoration: none; color: #0d1117; border: 1px solid #0d1117;
  padding: 7px 16px; border-radius: 2px; transition: all 0.15s; }
.pn-foot .links a:hover { background: #0d1117; color: #fff; }
.pn-foot .brand { margin-top: 20px; font-family: 'IBM Plex Mono', monospace; font-size: 11px;
  letter-spacing: 1px; color: #9aa3ad; text-transform: uppercase; }
.pn-foot .brand b { color: #b8860b; }

/* HERO broadcast type */
.pn-hero-head { font-family: 'Oswald', sans-serif; font-weight: 700; letter-spacing: -0.5px;
  text-transform: uppercase; line-height: 1.0; display: flex; flex-direction: column; align-items: center; gap: 2px; }
.pn-hero-head .l2 { display: inline-flex; align-items: baseline; }
.pn-ballO { display: inline-block; height: 0.78em; width: 0.78em; margin: 0 0.02em; transform: translateY(0.03em); }
.pn-ballO svg { height: 100%; width: 100%; }
.pn-logo { font-family: 'Oswald', sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
`

// cricket line icons for the feature list
const FEAT_ICONS = {
  tilt: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 15a9 9 0 0 1 18 0" /><line x1="12" y1="15" x2="16" y2="9" /><circle cx="12" cy="15" r="1.4" fill="currentColor" stroke="none" /></svg>
  ),
  charts: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><line x1="4" y1="20" x2="4" y2="12" /><line x1="10" y1="20" x2="10" y2="6" /><line x1="16" y1="20" x2="16" y2="14" /><line x1="22" y1="20" x2="22" y2="9" /></svg>
  ),
  report: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M6 3h9l4 4v14H6z" /><path d="M15 3v4h4" /><line x1="9" y1="12" x2="16" y2="12" /><line x1="9" y1="16" x2="16" y2="16" /></svg>
  ),
  format: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4" /><circle cx="12" cy="12" r="0.5" fill="currentColor" stroke="none" /></svg>
  ),
  cards: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="5" width="18" height="14" rx="1.5" /><path d="M3 15l5-4 4 3 3-2 6 4" /><circle cx="8" cy="9.5" r="1.3" /></svg>
  ),
  comps: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v13" /><path d="M7 5l10 0" /><path d="M9 21h6" /><path d="M12 16c-3 0-5-2-5-5" /><path d="M12 16c3 0 5-2 5-5" /></svg>
  ),
}

const FEATURES = [
  { icon: 'tilt', title: 'The tilt meter', body: 'One needle for who holds the edge, with the reasoning underneath. No false precision.' },
  { icon: 'charts', title: 'Phase & matchup charts', body: "How the contest shifts by phase and format, measured against the batter's own baseline." },
  { icon: 'report', title: 'Bilingual scout report', body: 'A pundit-style read of the matchup in English and Hindi. The numbers, told as a story.' },
  { icon: 'format', title: 'Format-aware analysis', body: 'Powerplay, middle, death. Phases that adapt to T20, ODI and Test, never mixed together.' },
  { icon: 'cards', title: 'Shareable cards', body: 'Turn any matchup into a clean, branded image ready for Instagram or WhatsApp.' },
  { icon: 'comps', title: 'Seven competitions', body: 'IPL, T20Is, ODIs, Tests, BBL, PSL and CPL. Millions of deliveries in one place.' },
]

function AboutSection({ stats }) {
  const yearRange = stats && stats.year_start && stats.year_end
    ? `${stats.year_start}-${stats.year_end}`
    : '2001-2026'
  const deliveries = stats ? `${formatDeliveries(stats.deliveries)}+ deliveries` : '4.4M+ deliveries'
  const matches = stats ? `${stats.matches.toLocaleString()} matches` : '9,475 matches'

  return (
    <section className="pn-about">
      <div className="pn-wrap">
        <span className="pn-eyebrow grn">About PitchNama</span>
        <h2>Every batter versus every bowler, read through the numbers.</h2>
        <p className="pn-lead">
          Pick any <b className="grn">batter</b> and any <b className="gld">bowler</b>. PitchNama
          breaks down the contest between them, head-to-head record, phase splits that respect the
          format, a tilt meter for who holds the edge, and a scout report in English and Hindi. Built
          for people who watch the duels inside the game, not just the scoreline.
        </p>

        <div className="pn-features">
          {FEATURES.map((f) => (
            <div className="pn-feat" key={f.title}>
              <div className="ic">{FEAT_ICONS[f.icon]}</div>
              <div>
                <h3>{f.title}</h3>
                <p>{f.body}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="pn-coverage">
          <span>Coverage <b>{yearRange}</b> &nbsp;/&nbsp; {deliveries} &nbsp;/&nbsp; {matches}</span>
          <span>Data <a href="https://cricsheet.org" target="_blank" rel="noopener noreferrer">Cricsheet</a> (CC BY-SA 4.0)</span>
        </div>
      </div>
    </section>
  )
}

const ROADMAP = [
  { title: "Women's cricket", body: "The same matchup depth applied to women's data, WT20Is, WODIs, WBBL and WPL. A part of the game analytics tools have long overlooked." },
  { title: 'Venue analysis', body: "How each ground behaves, batting or bowling friendly, phase by phase, so a matchup can be read in the context of where it's played." },
]

function RoadmapSection() {
  return (
    <section className="pn-next">
      <div className="pn-wrap">
        <span className="pn-eyebrow gld">What's next</span>
        <div className="pn-next-grid">
          {ROADMAP.map((r) => (
            <div className="pn-next-item" key={r.title}>
              <h3>{r.title}</h3>
              <span className="pn-pill">Coming soon</span>
              <p>{r.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

const VOICES = [
  { quote: 'Those analytics and data given helps me on the field to make my decisions.', who: 'Rohit Sharma', role: 'Former India captain' },
  { quote: 'Data has made players sit up and take notice of it.', who: 'Rahul Dravid', role: 'Former India captain & head coach' },
  { quote: 'Analysis is easy. The trick is turning it into info players can use.', who: 'Nathan Leamon', role: 'Analyst, CricViz co-founder' },
]

function WhyAndVoices() {
  return (
    <section className="pn-why">
      <div className="pn-wrap">
        <div className="pn-why-grid">
          <div className="pn-why-inner">
            <span className="pn-eyebrow grn">Why I built this</span>
            <div className="pn-why-body">
              <p className="lede">I fell in love with cricket as a kid, and it became the best part of my childhood.</p>
              <p>I love every format for its own reasons. The ODIs, the T20s, and leagues like the IPL, BBL and more that have carried this game to new fans all over the world. Test cricket will always be closest to my heart, but the truth is I just love all of it.</p>
              <p>A big part of that love came from the modern day legends I grew up watching. <span className="grn">Rohit Sharma</span> pulling with all the time in the world, <span className="grn">Virat Kohli</span> driving through the covers, <span className="gld">Jasprit Bumrah</span> nailing his yorkers. Moments like those, and the hard work, dedication, and fight these players bring for their team, pulled me deeper into this game than anything else.</p>
              <p>Like most kids who grow up loving the game, I wanted to play it. That didn't work out, but the love never faded. I still needed to be part of this beautiful game somehow, so I decided to serve it a different way, through the numbers, as an analyst.</p>
              <p>PitchNama is where that begins. It focuses on matchups because that's where cricket's drama really lives, not just in the scoreboard, but in the duels within it. One batter, one bowler, and the story of who holds the edge. This is a start, and only a start. I want to keep building, keep learning, and help this game grow in every way I can.</p>
              <p>Because I believe cricket should be the biggest game on the planet, and I'd love to spend my life helping it get there.</p>
              <p>Cricket isn't just a sport to me. It's a religion, and I'm one of its most devoted followers.</p>
              <div className="pn-why-sign">Himmat</div>
            </div>
          </div>

          <aside className="pn-voices">
            <span className="pn-eyebrow gld">Voices from the game</span>
            <p className="pn-vhead">On data in cricket</p>
            {VOICES.map((v) => (
              <div className="pn-quote" key={v.who}>
                <p>"{v.quote}"</p>
                <span className="who">{v.who}<span className="role">{v.role}</span></span>
              </div>
            ))}
          </aside>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="pn-foot">
      <div className="pn-wrap">
        <p className="built">Built by <b>Himmat Singh Grewal</b></p>
        <div className="links">
          <a href="https://github.com/himmatsgrewal" target="_blank" rel="noopener noreferrer">GitHub</a>
          <a href="https://www.linkedin.com/in/himmatsinghgrewal/" target="_blank" rel="noopener noreferrer">LinkedIn</a>
        </div>
        <p className="brand">Pitch<b>Nama</b> / the chronicle of every contest</p>
      </div>
    </footer>
  )
}

// cricket ball glyph used as the O in DECODED
function BallO() {
  return (
    <span className="pn-ballO">
      <svg viewBox="0 0 72 72" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <radialGradient id="pn-lea" cx="36%" cy="30%" r="78%">
            <stop offset="0%" stopColor="#b4241f" />
            <stop offset="50%" stopColor="#8f1714" />
            <stop offset="100%" stopColor="#520c0a" />
          </radialGradient>
        </defs>
        <circle cx="36" cy="36" r="34" fill="url(#pn-lea)" />
        <ellipse cx="25" cy="22" rx="13" ry="8" fill="#fff" opacity="0.12" />
        <g stroke="#e9cfa6" strokeWidth="1.7" strokeLinecap="round">
          <g><line x1="6" y1="28.5" x2="9" y2="28.5" /><line x1="12" y1="28.5" x2="15" y2="28.5" /><line x1="18" y1="28.5" x2="21" y2="28.5" /><line x1="24" y1="28.5" x2="27" y2="28.5" /><line x1="30" y1="28.5" x2="33" y2="28.5" /><line x1="36" y1="28.5" x2="39" y2="28.5" /><line x1="42" y1="28.5" x2="45" y2="28.5" /><line x1="48" y1="28.5" x2="51" y2="28.5" /><line x1="54" y1="28.5" x2="57" y2="28.5" /><line x1="60" y1="28.5" x2="63" y2="28.5" /></g>
          <g><line x1="9" y1="31.4" x2="12" y2="31.4" /><line x1="15" y1="31.4" x2="18" y2="31.4" /><line x1="21" y1="31.4" x2="24" y2="31.4" /><line x1="27" y1="31.4" x2="30" y2="31.4" /><line x1="33" y1="31.4" x2="36" y2="31.4" /><line x1="39" y1="31.4" x2="42" y2="31.4" /><line x1="45" y1="31.4" x2="48" y2="31.4" /><line x1="51" y1="31.4" x2="54" y2="31.4" /><line x1="57" y1="31.4" x2="60" y2="31.4" /></g>
          <g><line x1="6" y1="34.3" x2="9" y2="34.3" /><line x1="12" y1="34.3" x2="15" y2="34.3" /><line x1="18" y1="34.3" x2="21" y2="34.3" /><line x1="24" y1="34.3" x2="27" y2="34.3" /><line x1="30" y1="34.3" x2="33" y2="34.3" /><line x1="36" y1="34.3" x2="39" y2="34.3" /><line x1="42" y1="34.3" x2="45" y2="34.3" /><line x1="48" y1="34.3" x2="51" y2="34.3" /><line x1="54" y1="34.3" x2="57" y2="34.3" /><line x1="60" y1="34.3" x2="63" y2="34.3" /></g>
          <line x1="4" y1="37" x2="68" y2="37" strokeWidth="0.8" opacity="0.6" />
          <g><line x1="6" y1="39.7" x2="9" y2="39.7" /><line x1="12" y1="39.7" x2="15" y2="39.7" /><line x1="18" y1="39.7" x2="21" y2="39.7" /><line x1="24" y1="39.7" x2="27" y2="39.7" /><line x1="30" y1="39.7" x2="33" y2="39.7" /><line x1="36" y1="39.7" x2="39" y2="39.7" /><line x1="42" y1="39.7" x2="45" y2="39.7" /><line x1="48" y1="39.7" x2="51" y2="39.7" /><line x1="54" y1="39.7" x2="57" y2="39.7" /><line x1="60" y1="39.7" x2="63" y2="39.7" /></g>
          <g><line x1="9" y1="42.6" x2="12" y2="42.6" /><line x1="15" y1="42.6" x2="18" y2="42.6" /><line x1="21" y1="42.6" x2="24" y2="42.6" /><line x1="27" y1="42.6" x2="30" y2="42.6" /><line x1="33" y1="42.6" x2="36" y2="42.6" /><line x1="39" y1="42.6" x2="42" y2="42.6" /><line x1="45" y1="42.6" x2="48" y2="42.6" /><line x1="51" y1="42.6" x2="54" y2="42.6" /><line x1="57" y1="42.6" x2="60" y2="42.6" /></g>
          <g><line x1="6" y1="45.5" x2="9" y2="45.5" /><line x1="12" y1="45.5" x2="15" y2="45.5" /><line x1="18" y1="45.5" x2="21" y2="45.5" /><line x1="24" y1="45.5" x2="27" y2="45.5" /><line x1="30" y1="45.5" x2="33" y2="45.5" /><line x1="36" y1="45.5" x2="39" y2="45.5" /><line x1="42" y1="45.5" x2="45" y2="45.5" /><line x1="48" y1="45.5" x2="51" y2="45.5" /><line x1="54" y1="45.5" x2="57" y2="45.5" /><line x1="60" y1="45.5" x2="63" y2="45.5" /></g>
        </g>
      </svg>
    </span>
  )
}

const LANDING_HERO_BG = {
  background:
    'radial-gradient(circle at 12% 18%, rgba(46,204,113,0.20), transparent 45%), ' +
    'radial-gradient(circle at 88% 22%, rgba(224,169,46,0.16), transparent 45%), ' +
    '#ffffff',
}

const EXAMPLES = [
  ['Rohit Sharma', 'Pat Cummins'],
  ['Virat Kohli', 'Kagiso Rabada'],
  ['David Warner', 'Stuart Broad'],
]

function App() {
  const [view, setView] = useState('landing')
  const [fading, setFading] = useState(false)
  const [shown, setShown] = useState(false)
  const [tab, setTab] = useState('phases')

  const [batterText, setBatterText] = useState('')
  const [bowlerText, setBowlerText] = useState('')
  const [batter, setBatter] = useState('')
  const [bowler, setBowler] = useState('')
  const [format, setFormat] = useState('')

  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [stats, setStats] = useState(null)

  const [data, setData] = useState(null)
  const [compare, setCompare] = useState(null)
  const [report, setReport] = useState(null)
  const [analysing, setAnalysing] = useState(false)
  const [error, setError] = useState('')

  const cardRef = useRef(null)
  const [cardVisible, setCardVisible] = useState(false)
  const [generatingCard, setGeneratingCard] = useState(false)

  useEffect(() => {
    async function loadPlayers() {
      try {
        const res = await fetch(`${API_BASE}/players`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        setPlayers(await res.json())
      } catch (err) {
        setLoadError('Could not load players. Is the API running on port 8000?')
      } finally {
        setLoading(false)
      }
    }
    loadPlayers()
  }, [])

  useEffect(() => {
    async function loadStats() {
      try {
        const res = await fetch(`${API_BASE}/stats`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        setStats(await res.json())
      } catch (err) {
        // leave null
      }
    }
    loadStats()
  }, [])

  useEffect(() => {
    if (view === 'analysis') {
      setShown(false)
      const t = setTimeout(() => setShown(true), 50)
      return () => clearTimeout(t)
    }
    setShown(false)
  }, [view])

  function labelFor(scorecard) {
    const p = players.find((x) => x.scorecard === scorecard)
    return p ? p.label : scorecard
  }

  function scorecardForLabel(label) {
    const p = players.find((x) => x.label.toLowerCase() === label.toLowerCase())
    return p ? p.scorecard : null
  }

  function goTo(nextView) {
    setFading(true)
    setTimeout(() => {
      setView(nextView)
      setFading(false)
    }, 500)
  }

  async function runAnalysis(batterName, bowlerName) {
    if (!batterName || !bowlerName) {
      setError('Please select both a batter and a bowler from the dropdown.')
      return
    }
    setError('')
    setAnalysing(true)
    try {
      const params = new URLSearchParams({ batter: batterName, bowler: bowlerName })
      if (format) params.set('match_format', format)
      const qs = params.toString()
      const [mRes, cRes, rRes] = await Promise.all([
        fetch(`${API_BASE}/matchup?${qs}`),
        fetch(`${API_BASE}/compare?${qs}`),
        fetch(`${API_BASE}/report?${qs}`),
      ])
      if (!mRes.ok || !cRes.ok || !rRes.ok) throw new Error('HTTP error')
      setData(await mRes.json())
      setCompare(await cRes.json())
      setReport(await rRes.json())
      setTab('phases')
      goTo('analysis')
    } catch (err) {
      setError('Could not fetch the matchup. Is the API running on port 8000?')
    } finally {
      setAnalysing(false)
    }
  }

  function handleAnalyse() {
    runAnalysis(batter, bowler)
  }

  function tryExample(bLabel, bwLabel) {
    const bScore = scorecardForLabel(bLabel)
    const bwScore = scorecardForLabel(bwLabel)
    if (!bScore || !bwScore) {
      setError(`Couldn't find ${!bScore ? bLabel : bwLabel} in the player list.`)
      return
    }
    setBatterText(bLabel)
    setBatter(bScore)
    setBowlerText(bwLabel)
    setBowler(bwScore)
    runAnalysis(bScore, bwScore)
  }

  async function handleGenerateCard() {
    setGeneratingCard(true)
    setCardVisible(true)
    // Wait two animation frames so the card actually paints before capture.
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
    try {
      if (!cardRef.current) throw new Error('Card not ready')
      const png = await toPng(cardRef.current, {
        cacheBust: true,
        pixelRatio: 1,
        width: 1080,
        height: 1080,
      })
      const link = document.createElement('a')
      const safeBatter = (data?.batter || 'batter').replace(/\s+/g, '_')
      const safeBowler = (data?.bowler || 'bowler').replace(/\s+/g, '_')
      link.download = `pitchnama-${safeBatter}-vs-${safeBowler}.png`
      link.href = png
      link.click()
    } catch (err) {
      console.error('Card generation failed:', err)
    } finally {
      setCardVisible(false)
      setGeneratingCard(false)
    }
  }

  const entrance = `transition-all duration-500 ease-out ${
    shown ? 'translate-y-0 opacity-100' : 'translate-y-3 opacity-0'
  }`

  const cards = data
    ? [
        { label: 'Balls', value: data.total_balls },
        { label: 'Runs', value: data.total_runs },
        { label: 'Average', value: data.avg != null ? data.avg.toFixed(2) : '-' },
        { label: 'Strike rate', value: data.sr.toFixed(2) },
        { label: 'Dismissals', value: data.dismissals },
        { label: 'Matches', value: data.matches_played },
      ]
    : []

  const tilt = compare && data && data.total_balls > 0 ? computeTilt(compare) : null
  const tabs = ['charts', 'phases', 'report']

  return (
    <div>
      {view === 'landing' && (
        <div className="flex min-h-screen flex-col">
          <style>{LANDING_CSS}</style>
          <header className="bg-pitch-green px-6 py-4">
            <h1 className="pn-logo text-2xl text-white">
              Pitch<span className="text-pitch-gold-bright">Nama</span>
            </h1>
          </header>

          <div style={LANDING_HERO_BG}>
          <main className="flex flex-col items-center justify-center px-6 pt-16 pb-20 text-center">
            <h1 className="pn-hero-head text-6xl text-gray-900">
              <span>Every matchup,</span>
              <span className="l2">dec<BallO />ded.</span>
            </h1>
            <p className="mt-4 text-lg text-gray-500">
              The chronicle of every contest
            </p>

            <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <PlayerSelect
                placeholder="Batter"
                accentClass="border-pitch-green"
                players={players}
                loading={loading}
                value={batterText}
                onChange={setBatterText}
                onSelect={setBatter}
              />
              <span className="text-xl font-bold text-gray-400">vs</span>
              <PlayerSelect
                placeholder="Bowler"
                accentClass="border-pitch-gold"
                players={players}
                loading={loading}
                value={bowlerText}
                onChange={setBowlerText}
                onSelect={setBowler}
              />
            </div>

            {loadError && (
              <p className="mt-4 text-sm font-medium text-red-500">{loadError}</p>
            )}

            <div className="mt-6 flex justify-center">
              <select
                value={format}
                onChange={(e) => setFormat(e.target.value)}
                className="rounded-lg border-2 border-gray-300 bg-white px-4 py-3 text-lg text-gray-700 focus:outline-none"
              >
                <option value="">All formats</option>
                <option value="T20">T20</option>
                <option value="ODI">ODI</option>
                <option value="Test">Test</option>
              </select>
            </div>

            <div className="mt-6 flex justify-center">
              <button
                type="button"
                onClick={handleAnalyse}
                disabled={analysing}
                className="pn-logo rounded-lg bg-pitch-green px-14 py-3.5 text-xl tracking-wide text-white hover:bg-green-600 disabled:opacity-60"
              >
                {analysing ? 'Analysing...' : 'Analyse'}
              </button>
            </div>

            <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
              <span className="text-sm text-gray-400">Or try:</span>
              {EXAMPLES.map(([b, bw]) => (
                <button
                  key={`${b}-${bw}`}
                  type="button"
                  onClick={() => tryExample(b, bw)}
                  className="rounded-full border border-gray-300 px-3 py-1 text-sm text-gray-600 transition-colors hover:border-pitch-green hover:text-pitch-green"
                >
                  {b} vs {bw}
                </button>
              ))}
            </div>

            {error && (
              <p className="mt-6 text-lg font-medium text-red-500">{error}</p>
            )}

            <p className="mt-10 text-xs uppercase tracking-widest text-gray-400" style={{ fontFamily: "'IBM Plex Mono', monospace" }}>
              {stats
                ? `${formatDeliveries(stats.deliveries)} deliveries / ${stats.matches.toLocaleString()} matches / ${stats.competitions} competitions${
                    stats.year_start && stats.year_end ? ` / ${stats.year_start}-${stats.year_end}` : ''
                  }`
                : 'Loading dataset...'}
            </p>
          </main>
          </div>

          {/* Below-the-hero content */}
          <AboutSection stats={stats} />
          <RoadmapSection />
          <WhyAndVoices />
          <Footer />
        </div>
      )}

      {view === 'analysis' && data && (
        <div className="min-h-screen bg-floodlit text-white">
          <div className="flex items-center justify-between px-6 py-4">
            <button
              type="button"
              onClick={() => goTo('landing')}
              className="text-sm font-medium text-gray-400 hover:text-white"
            >
              ← Back
            </button>
            <span className="text-xl font-bold text-white">
              Pitch<span className="text-pitch-gold">Nama</span>
            </span>
          </div>

          <main className="px-6 py-10">
            {data.total_balls > 0 ? (
              <div className="mx-auto max-w-3xl">
                <div className="text-center">
                  <h3 className={`text-3xl font-bold ${entrance}`}>
                    <span className="text-pitch-green">{labelFor(data.batter)}</span>
                    <span className="mx-2 text-gray-500">vs</span>
                    <span className="text-pitch-gold">{labelFor(data.bowler)}</span>
                  </h3>
                  <p
                    className={`mt-2 text-sm text-gray-400 ${entrance}`}
                    style={{ transitionDelay: '80ms' }}
                  >
                    {format || 'All formats'} · {data.matches_played} matches
                  </p>

                  {tilt && <TiltMeter tilt={tilt} shown={shown} />}

                  <div className="mt-8 grid grid-cols-2 gap-3 sm:grid-cols-3">
                    {cards.map((c, i) => (
                      <StatCard
                        key={c.label}
                        label={c.label}
                        value={c.value}
                        shown={shown}
                        delay={150 + i * 70}
                      />
                    ))}
                  </div>
                </div>

                <div className="mt-12">
                  <div className="flex justify-center gap-1 border-b border-white/10">
                    {tabs.map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setTab(t)}
                        className={`px-4 py-2 text-sm font-medium capitalize ${
                          tab === t
                            ? 'border-b-2 border-pitch-green text-white'
                            : 'text-gray-400 hover:text-white'
                        }`}
                      >
                        {t}
                      </button>
                    ))}
                  </div>

                  <div className="mt-6">
                    {tab === 'phases' && <PhasesPanel data={data} />}
                    {tab === 'charts' && <ChartsPanel data={data} compare={compare} />}
                    {tab === 'report' && <ReportPanel report={report} />}
                  </div>
                </div>

                <div className="mt-10 flex justify-center">
                  <button
                    type="button"
                    onClick={handleGenerateCard}
                    disabled={generatingCard}
                    className="rounded-lg bg-pitch-gold px-8 py-3 text-sm font-bold uppercase tracking-wide text-floodlit hover:opacity-90 disabled:opacity-60"
                  >
                    {generatingCard ? 'Generating...' : 'Generate Card'}
                  </button>
                </div>

                <ShareCard
                  data={data}
                  compare={compare}
                  tilt={tilt}
                  cardRef={cardRef}
                  visible={cardVisible}
                  scopeLabel={format || 'All formats'}
                  batterLabel={labelFor(data.batter)}
                  bowlerLabel={labelFor(data.bowler)}
                />
              </div>
            ) : (
              <p className="mx-auto max-w-2xl text-center text-lg font-medium text-gray-400">
                No recorded deliveries between these two in this scope.
              </p>
            )}
          </main>
        </div>
      )}

      <div
        className={`pointer-events-none fixed inset-0 z-50 bg-floodlit transition-opacity duration-500 ${
          fading ? 'opacity-100' : 'opacity-0'
        }`}
      />
    </div>
  )
}

export default App
