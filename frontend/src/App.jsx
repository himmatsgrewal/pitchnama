import { useState } from 'react'
import './App.css'

function App() {
  const [batter, setBatter] = useState('')
  const [bowler, setBowler] = useState('')
  const [format, setFormat] = useState('')
  const [result, setResult] = useState('')

  function handleAnalyse() {
    if (!batter || !bowler) {
      setResult('Please enter both a batter and a bowler.')
      return
    }
    const scope = format ? format : 'all formats'
    setResult(`Analysing ${batter} vs ${bowler} (${scope})...`)
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
          <input
            type="text"
            placeholder="Batter"
            value={batter}
            onChange={(e) => setBatter(e.target.value)}
            className="w-64 rounded-lg border-2 border-pitch-green px-4 py-3 text-lg focus:outline-none"
          />
          <span className="text-xl font-bold text-gray-400">vs</span>
          <input
            type="text"
            placeholder="Bowler"
            value={bowler}
            onChange={(e) => setBowler(e.target.value)}
            className="w-64 rounded-lg border-2 border-pitch-gold px-4 py-3 text-lg focus:outline-none"
          />
        </div>

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
            className="rounded-lg bg-pitch-green px-12 py-4 text-xl font-bold text-white hover:bg-green-600"
          >
            Analyse
          </button>
        </div>

        {result && (
          <p className="mt-8 text-lg font-medium text-gray-700">
            {result}
          </p>
        )}

        <p className="mt-12 text-sm text-gray-400">
          4.4M deliveries · 9,366 matches · 7 competitions
        </p>
      </main>
    </div>
  )
}

export default App