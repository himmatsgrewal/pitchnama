import { useState, useEffect } from 'react'
import './App.css'

// Where the API lives during development. (When we deploy for real,
// we'll swap this for the live address — noting it, not doing it now.)
const API_BASE = 'http://localhost:8000'

// 4400000 -> "4.4M" for the headline stat line.
function formatDeliveries(n) {
  return (n / 1_000_000).toFixed(1) + 'M'
}

// A small presentational card for one headline number.
function StatCard({ label, value }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white px-4 py-3 text-center">
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-gray-400">{label}</div>
    </div>
  )
}

// A reusable searchable player picker. We use it twice — once for the
// batter (green), once for the bowler (gold). It shows a text box; as you
// type, it filters the player list and shows matches; clicking a match
// selects that player and hands its scorecard name up to the parent.
function PlayerSelect({ placeholder, accentClass, players, loading, onSelect }) {
  const [query, setQuery] = useState('')   // what's typed in the box
  const [open, setOpen] = useState(false)  // is the suggestion list showing?

  const q = query.trim().toLowerCase()
  // Filter by the 'search' blob the API built, cap at 50 so the list stays snappy.
  const matches = q ? players.filter((p) => p.search.includes(q)).slice(0, 50) : []

  function choose(player) {
    setQuery(player.label)        // show the friendly name in the box
    setOpen(false)                // close the suggestion list
    onSelect(player.scorecard)    // send the scorecard name up (the API needs this)
  }

  function handleChange(e) {
    setQuery(e.target.value)
    setOpen(true)
    onSelect('')  // typing clears any earlier pick until they click a real match
  }

  return (
    <div className="relative w-64">
      <input
        type="text"
        placeholder={loading ? 'Loading players…' : placeholder}
        value={query}
        disabled={loading}
        onChange={handleChange}
        onFocus={() => setOpen(true)}
        // small delay so a click on a suggestion registers before the list closes
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        className={`w-full rounded-lg border-2 ${accentClass} px-4 py-3 text-lg focus:outline-none`}
      />

      {open && q && (
        <ul className="absolute z-10 mt-1 max-h-72 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white text-left shadow-lg">
          {matches.length === 0 ? (
            <li className="px-4 py-2 text-gray-400">No players found</li>
          ) : (
            matches.map((p) => (
              <li
                key={p.scorecard}
                // keep focus on the box so the click below actually registers
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

function App() {
  const [batter, setBatter] = useState('')   // holds a scorecard name, e.g. "RG Sharma"
  const [bowler, setBowler] = useState('')   // holds a scorecard name, e.g. "PJ Cummins"
  const [format, setFormat] = useState('')

  const [players, setPlayers] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [stats, setStats] = useState(null)   // live dataset totals for the stat line

  const [data, setData] = useState(null)        // the matchup result from /matchup
  const [analysing, setAnalysing] = useState(false)
  const [error, setError] = useState('')        // error from the Analyse action

  // Fetch the player list once, when the page first loads.
  useEffect(() => {
    async function loadPlayers() {
      try {
        const res = await fetch(`${API_BASE}/players`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setPlayers(data)
      } catch (err) {
        setLoadError('Could not load players. Is the API running on port 8000?')
      } finally {
        setLoading(false)
      }
    }
    loadPlayers()
  }, [])

  // Fetch the live dataset totals once, for the headline stat line.
  useEffect(() => {
    async function loadStats() {
      try {
        const res = await fetch(`${API_BASE}/stats`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        setStats(await res.json())
      } catch (err) {
        // leave stats null; the line below falls back gracefully
      }
    }
    loadStats()
  }, [])

  // Turn a scorecard name back into the friendly display name for titles.
  function labelFor(scorecard) {
    const p = players.find((x) => x.scorecard === scorecard)
    return p ? p.label : scorecard
  }

  async function handleAnalyse() {
    if (!batter || !bowler) {
      setError('Please select both a batter and a bowler from the dropdown.')
      setData(null)
      return
    }
    setError('')
    setData(null)
    setAnalysing(true)
    try {
      const params = new URLSearchParams({ batter, bowler })
      if (format) params.set('match_format', format)  // omit when "All formats"
      const res = await fetch(`${API_BASE}/matchup?${params.toString()}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setData(await res.json())
    } catch (err) {
      setError('Could not fetch the matchup. Is the API running on port 8000?')
    } finally {
      setAnalysing(false)
    }
  }

  return (
    <div>
      <header className="bg-pitch-green px-6 py-4">
        <h1 className="text-2xl font-bold text-white">
          Pitch<span className="text-pitch-gold-bright">Nama</span>
        </h1>
      </header>

      <main className="px-6 py-16 text-center">
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
            onSelect={setBatter}
          />
          <span className="text-xl font-bold text-gray-400">vs</span>
          <PlayerSelect
            placeholder="Bowler"
            accentClass="border-pitch-gold"
            players={players}
            loading={loading}
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
            className="rounded-lg border-2 border-gray-300 px-4 py-3 text-lg text-gray-700 focus:outline-none"
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

        {error && (
          <p className="mt-8 text-lg font-medium text-red-500">{error}</p>
        )}

        {data && !analysing && (
          data.total_balls > 0 ? (
            <div className="mx-auto mt-10 max-w-2xl">
              <h3 className="text-2xl font-bold">
                <span className="text-pitch-green">{labelFor(data.batter)}</span>
                <span className="mx-2 text-gray-400">vs</span>
                <span className="text-pitch-gold">{labelFor(data.bowler)}</span>
              </h3>
              <p className="mt-1 text-sm text-gray-400">
                {format || 'All formats'} · {data.matches_played} matches
              </p>
              <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
                <StatCard label="Balls" value={data.total_balls} />
                <StatCard label="Runs" value={data.total_runs} />
                <StatCard label="Average" value={data.avg != null ? data.avg.toFixed(2) : '—'} />
                <StatCard label="Strike rate" value={data.sr.toFixed(2)} />
                <StatCard label="Dismissals" value={data.dismissals} />
                <StatCard label="Matches" value={data.matches_played} />
              </div>
            </div>
          ) : (
            <p className="mt-8 text-lg font-medium text-gray-500">
              No recorded deliveries between these two in this scope.
            </p>
          )
        )}

        <p className="mt-12 text-sm text-gray-400">
          {stats
            ? `${formatDeliveries(stats.deliveries)} deliveries · ${stats.matches.toLocaleString()} matches · ${stats.competitions} competitions`
            : 'Loading dataset…'}
        </p>
      </main>
    </div>
  )
}

export default App