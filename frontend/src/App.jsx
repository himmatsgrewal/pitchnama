import { useState, useEffect, useRef } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
  Legend, ResponsiveContainer,
} from 'recharts'
import { toPng } from 'html-to-image'
import './App.css'

const API_BASE = 'http://localhost:8000'

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
  // Tests: 50/50 — survival matters as much as scoring in long-form cricket.
  // T20 / ODI / All formats: 60/40 — limited-overs (and the overall picture,
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
          {/* Static, gentle glow — used on the losing side (and both sides when even). */}
          <filter id="glow-static" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          {/* Breathing glow — applied only to the winning side. */}
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

        {/* Halo behind each arc — pulses only on the winning side. */}
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
    ['Avg', (p) => (p.avg != null ? p.avg.toFixed(1) : '—')],
    ['SR', (p) => (p.sr != null ? p.sr.toFixed(1) : '—')],
    ['Wkts', (p) => p.wickets],
    ['Dot %', (p) => (p.dot_pct != null ? p.dot_pct.toFixed(0) : '—')],
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
            {entry.value != null ? entry.value.toFixed(1) : '—'}
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

// The shareable card — rendered in the viewport but hidden via `visibility`
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
          { label: 'Average', value: data.avg != null ? data.avg.toFixed(1) : '—' },
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
        placeholder={loading ? 'Loading players…' : placeholder}
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

const LANDING_BG = {
  background:
    'radial-gradient(circle at 12% 18%, rgba(46,204,113,0.22), transparent 45%), ' +
    'radial-gradient(circle at 88% 22%, rgba(224,169,46,0.18), transparent 45%), ' +
    'radial-gradient(circle at 50% 105%, rgba(46,204,113,0.12), transparent 55%), ' +
    '#e9efec',
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
        { label: 'Average', value: data.avg != null ? data.avg.toFixed(2) : '—' },
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
        <div className="flex min-h-screen flex-col" style={LANDING_BG}>
          <header className="bg-pitch-green px-6 py-4">
            <h1 className="text-2xl font-bold text-white">
              Pitch<span className="text-pitch-gold-bright">Nama</span>
            </h1>
          </header>

          <main className="flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
            <h2 className="text-5xl font-bold text-gray-900">
              Every matchup, decoded.
            </h2>
            <p className="mt-4 text-lg text-gray-500">
              The chronicle of every contest
            </p>

            <div className="mt-12 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
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

            <div className="mt-8 flex justify-center">
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

            <div className="mt-8 flex justify-center">
              <button
                type="button"
                onClick={handleAnalyse}
                disabled={analysing}
                className="rounded-lg bg-pitch-green px-12 py-4 text-xl font-bold text-white hover:bg-green-600 disabled:opacity-60"
              >
                {analysing ? 'Analysing…' : 'Analyse'}
              </button>
            </div>

            <div className="mt-8 flex flex-wrap items-center justify-center gap-2">
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

            <p className="mt-12 text-sm text-gray-400">
              {stats
                ? `${formatDeliveries(stats.deliveries)} deliveries · ${stats.matches.toLocaleString()} matches · ${stats.competitions} competitions`
                : 'Loading dataset…'}
            </p>
          </main>
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
                    {generatingCard ? 'Generating…' : 'Generate Card'}
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