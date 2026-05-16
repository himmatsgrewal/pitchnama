"""
scout_report.py — Bilingual scout report generation for PitchNama.

Takes the structured output of compare_matchup_to_baseline() and produces
a clean, coach-readable narrative paragraph in either English or Hindi.

Sample-size honesty is built in: anywhere the data is thin, the report
says so explicitly. Phase narrative is included only when the scope is
T20 (where our phase definitions apply); for ODIs, Tests, and all-formats
scopes, the phase sentence is omitted rather than shown with wrong numbers.

Usage:
    from pitchnama.matchup import compare_matchup_to_baseline
    from pitchnama.scout_report import generate_report

    data = compare_matchup_to_baseline('RG Sharma', 'PJ Cummins', format='T20')
    print(generate_report(data, language='en'))
    print(generate_report(data, language='hi'))
"""

from .players import display_name, load_display_names


# Thresholds for sample-size honesty
SMALL_SAMPLE_THRESHOLD = 30          # below this, flag the overall sample as modest
PHASE_MIN_BALLS = 3
PHASE_DIVERGENCE_THRESHOLD = 0.2     # SR or avg must diverge from baseline by ≥30% to be worth mentioning

# T20 competitions where our phase definitions apply
T20_COMPETITIONS = {'ipl', 't20i', 'bbl', 'psl', 'cpl'}


# ---------- Helpers ----------

def _fmt(value: Optional[float], spec: str = '.1f', dash: str = '—') -> str:
    """Format a number, returning a dash if value is None."""
    if value is None:
        return dash
    return format(value, spec)


def _format_scope_en(format: Optional[str], competition: Optional[str]) -> str:
    """Render the analysis scope in English."""
    if competition:
        labels = {
            'ipl': 'the IPL', 't20i': "men's T20Is", 'odi': "men's ODIs",
            'test': "men's Tests", 'bbl': 'the BBL', 'psl': 'the PSL',
            'cpl': 'the CPL',
        }
        return labels.get(competition, competition)
    if format:
        return {'T20': 'T20 cricket', 'ODI': 'ODI cricket',
                'Test': 'Test cricket'}.get(format, format)
    return 'all formats'


def _format_scope_hi(format: Optional[str], competition: Optional[str]) -> str:
    """Render the analysis scope in Hindi."""
    if competition:
        labels = {
            'ipl': 'आईपीएल', 't20i': 'पुरुष T20I', 'odi': 'पुरुष वनडे',
            'test': 'पुरुष टेस्ट', 'bbl': 'बिग बैश लीग', 'psl': 'पीएसएल',
            'cpl': 'सीपीएल',
        }
        return labels.get(competition, competition)
    if format:
        return {'T20': 'T20 क्रिकेट', 'ODI': 'वनडे क्रिकेट',
                'Test': 'टेस्ट क्रिकेट'}.get(format, format)
    return 'सभी फॉर्मैट'


def _is_t20_scope(format: Optional[str], competition: Optional[str]) -> bool:
    """
    Decide whether T20-style phase narrative is appropriate.
    True only when scope is unambiguously T20 (a single T20 competition,
    or format='T20' explicitly).
    """
    if competition is not None:
        return competition in T20_COMPETITIONS
    if format == 'T20':
        return True
    return False  # ODI, Test, all-formats — skip phase narrative


def _find_notable_phase(phases: dict, language: str) -> Optional[str]:
    """
    Look through phase data and return a narrative sentence describing
    the most divergent phase, if any. Returns None if nothing worth saying.

    Rules:
      - Only phases with >= PHASE_MIN_BALLS deliveries are eligible
      - Phase must show meaningful divergence from baseline SR
      - Pick the phase with the largest divergence
    """
    candidates = []
    for phase_name, p in phases.items():
        n = p.get('matchup_balls', 0)
        if n < PHASE_MIN_BALLS:
            continue
        m_sr = p.get('matchup_sr')
        b_sr = p.get('baseline_sr')
        if m_sr is None or b_sr is None or b_sr == 0:
            continue
        divergence = abs(m_sr - b_sr) / b_sr
        if divergence < PHASE_DIVERGENCE_THRESHOLD:
            continue
        candidates.append((phase_name, p, divergence))

    if not candidates:
        return None

    # Pick the phase with the largest divergence
    candidates.sort(key=lambda x: x[2], reverse=True)
    phase_name, p, _ = candidates[0]

    m_sr = p['matchup_sr']
    b_sr = p['baseline_sr']
    n = p['matchup_balls']
    direction_en = "drops to" if m_sr < b_sr else "rises to"
    direction_hi = "गिरकर" if m_sr < b_sr else "बढ़कर"

    phase_label_en = {'Powerplay': 'the powerplay',
                      'Middle': 'the middle overs',
                      'Death': 'the death overs'}.get(phase_name, phase_name)

    phase_label_hi = {'Powerplay': 'पावरप्ले',
                      'Middle': 'मिडल ओवर्स',
                      'Death': 'डेथ ओवर्स'}.get(phase_name, phase_name)

    if language == 'en':
        caveat = ""
        if n < PHASE_MIN_BALLS * 2:
            caveat = f" — though the sample is small ({n} balls)"
        return (f"In {phase_label_en}, the batter's career strike rate "
                f"of {b_sr:.1f} {direction_en} {m_sr:.1f} against this bowler{caveat}.")
    else:  # hi
        caveat = ""
        if n < PHASE_MIN_BALLS * 2:
            caveat = f" — हालाँकि नमूना सीमित है ({n} गेंदें)"
        return (f"{phase_label_hi} में, बल्लेबाज़ का करियर स्ट्राइक रेट "
                f"{b_sr:.1f} इस गेंदबाज़ के सामने {direction_hi} {m_sr:.1f} हो जाता है{caveat}।")


# ---------- English report ----------

def _report_en(data: dict) -> str:
    """Generate the English scout report from compare_matchup_to_baseline output."""
    if 'message' in data:
        return data['message']

    overrides = load_display_names()
    batter = display_name(data['batter'], overrides)
    bowler = display_name(data['bowler'], overrides)
    scope = _format_scope_en(data.get('format'), data.get('competition'))
    n_balls = data['sample_size']
    n_matches = data['matches_played']

    matchup = data['overall_matchup']
    baseline = data['overall_baseline']

    m_avg = matchup['avg']
    m_sr = matchup['sr']
    b_avg = baseline['avg']
    b_sr = baseline['sr']

    # Sentence 1: headline finding
    if m_avg is not None and b_avg is not None:
        if m_avg < b_avg * 0.8:
            edge = f"{bowler} has a clear edge in this matchup"
        elif m_avg > b_avg * 1.2:
            edge = f"{batter} has handled {bowler} better than most"
        else:
            edge = f"this matchup has been broadly even"
    else:
        edge = f"the matchup between {batter} and {bowler} is finely poised"

    headline = (
        f"Across {n_balls} deliveries in {n_matches} matches in {scope}, "
        f"{edge}."
    )

    # Sentence 2: matchup vs baseline
    matchup_line = (
        f" {batter} averages {_fmt(m_avg, '.1f')} against {bowler} "
        f"(career baseline: {_fmt(b_avg, '.1f')}), "
        f"scoring at a strike rate of {_fmt(m_sr, '.1f')} "
        f"(career: {_fmt(b_sr, '.1f')})."
    )

    # Sentence 3: phase narrative — only for T20 scopes
    phase_line = ""
    if _is_t20_scope(data.get('format'), data.get('competition')):
        notable = _find_notable_phase(data.get('phases', {}), language='en')
        if notable:
            phase_line = " " + notable

    # Sentence 4: format breakdown if multi-format
    breakdown = data.get('competition_breakdown', {})
    nonzero = {c: s for c, s in breakdown.items() if s.get('balls', 0) > 0}
    breakdown_line = ""
    if len(nonzero) >= 2:
        parts = []
        for comp, s in sorted(nonzero.items(),
                              key=lambda kv: kv[1]['balls'], reverse=True):
            avg_str = _fmt(s.get('avg'), '.1f')
            parts.append(f"{comp.upper()} ({s['balls']} balls, avg {avg_str})")
        breakdown_line = " The matchup is split across " + ", ".join(parts) + "."

    # Sentence 5: sample caveat
    caveat = ""
    if n_balls < SMALL_SAMPLE_THRESHOLD:
        caveat = (f" Sample size is modest ({n_balls} balls); "
                  f"the pattern is suggestive rather than conclusive.")

    return headline + matchup_line + phase_line + breakdown_line + caveat


# ---------- Hindi report ----------

def _report_hi(data: dict) -> str:
    """Generate the Hindi scout report (Star Sports Hindi register)."""
    if 'message' in data:
        return data['message']

    overrides = load_display_names()
    batter = display_name(data['batter'], overrides)
    bowler = display_name(data['bowler'], overrides)
    scope = _format_scope_hi(data.get('format'), data.get('competition'))
    n_balls = data['sample_size']
    n_matches = data['matches_played']

    matchup = data['overall_matchup']
    baseline = data['overall_baseline']

    m_avg = matchup['avg']
    m_sr = matchup['sr']
    b_avg = baseline['avg']
    b_sr = baseline['sr']

    # Sentence 1: headline finding
    if m_avg is not None and b_avg is not None:
        if m_avg < b_avg * 0.8:
            edge = f"इस सामना में {bowler} को स्पष्ट बढ़त मिली है"
        elif m_avg > b_avg * 1.2:
            edge = f"{batter} ने {bowler} को सामान्य से बेहतर खेला है"
        else:
            edge = f"यह सामना मोटे तौर पर बराबरी का रहा है"
    else:
        edge = f"{batter} और {bowler} के बीच का सामना संतुलित है"

    headline = (
        f"{scope} में {n_matches} मैचों की {n_balls} गेंदों में, "
        f"{edge}।"
    )

    # Sentence 2: matchup vs baseline
    matchup_line = (
        f" {batter} का {bowler} के सामने औसत {_fmt(m_avg, '.1f')} है "
        f"(करियर औसत: {_fmt(b_avg, '.1f')}), "
        f"और स्ट्राइक रेट {_fmt(m_sr, '.1f')} है "
        f"(करियर: {_fmt(b_sr, '.1f')})।"
    )

    # Sentence 3: phase narrative — only for T20 scopes
    phase_line = ""
    if _is_t20_scope(data.get('format'), data.get('competition')):
        notable = _find_notable_phase(data.get('phases', {}), language='hi')
        if notable:
            phase_line = " " + notable

    # Sentence 4: format breakdown
    breakdown = data.get('competition_breakdown', {})
    nonzero = {c: s for c, s in breakdown.items() if s.get('balls', 0) > 0}
    breakdown_line = ""
    if len(nonzero) >= 2:
        comp_labels_hi = {
            'ipl': 'आईपीएल', 't20i': 'T20I', 'odi': 'वनडे',
            'test': 'टेस्ट', 'bbl': 'बीबीएल', 'psl': 'पीएसएल', 'cpl': 'सीपीएल',
        }
        parts = []
        for comp, s in sorted(nonzero.items(),
                              key=lambda kv: kv[1]['balls'], reverse=True):
            label = comp_labels_hi.get(comp, comp)
            avg_str = _fmt(s.get('avg'), '.1f')
            parts.append(f"{label} ({s['balls']} गेंदें, औसत {avg_str})")
        breakdown_line = " यह सामना फैला है " + ", ".join(parts) + " में।"

    # Sentence 5: sample caveat
    caveat = ""
    if n_balls < SMALL_SAMPLE_THRESHOLD:
        caveat = (f" नमूना सीमित है ({n_balls} गेंदें); "
                  f"पैटर्न संकेत देता है, निष्कर्ष नहीं।")

    return headline + matchup_line + phase_line + breakdown_line + caveat


# ---------- Public API ----------

def generate_report(data: dict, language: str = 'en') -> str:
    """
    Generate a scout report paragraph from compare_matchup_to_baseline output.

    Args:
        data: The dict returned by compare_matchup_to_baseline().
        language: 'en' for English (default), 'hi' for Hindi.

    Returns:
        A clean prose paragraph suitable for embedding in scout reports,
        coach briefings, social posts, or web app output.
    """
    if language == 'hi':
        return _report_hi(data)
    elif language == 'en':
        return _report_en(data)
    else:
        raise ValueError(f"Unsupported language: {language}. Use 'en' or 'hi'.")