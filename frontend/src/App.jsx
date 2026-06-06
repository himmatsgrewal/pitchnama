import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000'

function formatDeliveries(n) {
  return (n / 1_000_000).toFixed(1) + 'M'
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

  const raw = (scoring + dismissal) / 2
  const needle = 100 * Math.tanh(raw / 100)

  const mag = Math.abs(needle)
  let verdict
  if (mag < 8) {
    verdict = 'Even contest'
  } else {
    const side = needle > 0 ? 'Batter edge' : 'Bowler edge'
    const strength = mag < 25 ? 'slight' : mag < 55 ? 'clear' : 'strong'
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

  return (
    <div className={`mx-auto mt-8 max-w-sm ${tilt.smallSample ? 'opacity-40' : ''}`}>
      <svg viewBox="0 0 300 175" className="w-full">
        <path d="M 30 150 A 120 120 0 0 1 150 30" fill="none" stroke="#2ecc71" strokeWidth="16" strokeLinecap="round" />
        <path d="M 150 30 A 120 120 0 0 1 270 150" fill="none" stroke="#e0a92e" strokeWidth="16" strokeLinecap="round" />
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

// Controlled searchable player picker (display text lives in the parent).
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

const LANDING_BG = {
  background:
    'radial-gradient(circle at 12% 18%, rgba(46,204,113,0.22), transparent 45%), ' +
    'radial-gradient(circle at 88% 22%, rgba(224,169,46,0.18), transparent 45%), ' +
    'radial-gradient(circle at 50% 105%, rgba(46,204,113,0.12), transparent 55%), ' +
    '#e9efec',
}

// A few example matchups for the quick-try chips (resolved by display label).
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
  const [analysing, setAnalysing] = useState(false)
  const [error, setError] = useState('')

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
      const [mRes, cRes] = await Promise.all([
        fetch(`${API_BASE}/matchup?${qs}`),
        fetch(`${API_BASE}/compare?${qs}`),
      ])
      if (!mRes.ok || !cRes.ok) throw new Error('HTTP error')
      setData(await mRes.json())
      setCompare(await cRes.json())
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
      {/* ---------- LANDING VIEW (light) ---------- */}
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

      {/* ---------- ANALYSIS VIEW (dark / floodlit) ---------- */}
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
                    {tab === 'charts' && (
                      <p className="text-center text-gray-500">Charts coming next.</p>
                    )}
                    {tab === 'report' && (
                      <p className="text-center text-gray-500">Report coming next.</p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <p className="mx-auto max-w-2xl text-center text-lg font-medium text-gray-400">
                No recorded deliveries between these two in this scope.
              </p>
            )}
          </main>
        </div>
      )}

      {/* Black overlay used for the floodlit fade between views. */}
      <div
        className={`pointer-events-none fixed inset-0 z-50 bg-floodlit transition-opacity duration-500 ${
          fading ? 'opacity-100' : 'opacity-0'
        }`}
      />
    </div>
  )
}

export default App