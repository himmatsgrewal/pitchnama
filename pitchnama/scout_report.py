"""
scout_report.py — Bilingual scout report generation for PitchNama.

Takes the structured output of compare_matchup_to_baseline() and produces
a clean, coach-readable narrative paragraph in either English or Hindi.

The English version uses analyst-grade language. The Hindi version uses
the register of Star Sports Hindi commentary — accessible to coaches, fans,
and selectors who prefer Hindi, without being either Sanskritized or
colloquial.

Sample-size honesty is built in: anywhere the data is thin, the report
says so explicitly. We never overclaim from small samples.

Usage:
    from pitchnama.matchup import compare_matchup_to_baseline
    from pitchnama.scout_report import generate_report

    data = compare_matchup_to_baseline('RG Sharma', 'PJ Cummins', format='Test')
    print(generate_report(data, language='en'))
    print(generate_report(data, language='hi'))
"""

from typing import Optional


# Threshold below which a sample is flagged as "small" in the report.
SMALL_SAMPLE_THRESHOLD = 30


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


# ---------- English report ----------

def _report_en(data: dict) -> str:
    """Generate the English scout report from compare_matchup_to_baseline output."""
    if 'message' in data:
        return data['message']

    batter = data['batter']
    bowler = data['bowler']
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
        f"{batter} averages {_fmt(m_avg, '.1f')} against {bowler} "
        f"(career baseline: {_fmt(b_avg, '.1f')}), "
        f"scoring at a strike rate of {_fmt(m_sr, '.1f')} "
        f"(career: {_fmt(b_sr, '.1f')})."
    )

    # Sentence 3: format breakdown if multi-format
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

    # Sentence 4: sample caveat
    caveat = ""
    if n_balls < SMALL_SAMPLE_THRESHOLD:
        caveat = (f" Sample size is modest ({n_balls} balls); "
                  f"the pattern is suggestive rather than conclusive.")

    return headline + " " + matchup_line + breakdown_line + caveat


# ---------- Hindi report ----------

def _report_hi(data: dict) -> str:
    """Generate the Hindi scout report (Star Sports Hindi register)."""
    if 'message' in data:
        return data['message']

    batter = data['batter']
    bowler = data['bowler']
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
        f"{batter} का {bowler} के सामने औसत {_fmt(m_avg, '.1f')} है "
        f"(करियर औसत: {_fmt(b_avg, '.1f')}), "
        f"और स्ट्राइक रेट {_fmt(m_sr, '.1f')} है "
        f"(करियर: {_fmt(b_sr, '.1f')})।"
    )

    # Sentence 3: format breakdown
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

    # Sentence 4: sample caveat
    caveat = ""
    if n_balls < SMALL_SAMPLE_THRESHOLD:
        caveat = (f" नमूना सीमित है ({n_balls} गेंदें); "
                  f"पैटर्न संकेत देता है, निष्कर्ष नहीं।")

    return headline + " " + matchup_line + breakdown_line + caveat


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