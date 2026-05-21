"""
scout_report.py — Bilingual scout report generation for PitchNama.

Takes compare_matchup_to_baseline() output and produces a coach-readable
narrative in English or Hindi. Format-aware: phase narrative uses the
correct phases for the format, and for 'all formats' scope it highlights
the single most striking phase finding across all formats.
"""

from typing import Optional


SMALL_SAMPLE_THRESHOLD = 30
PHASE_MIN_BALLS = 3
PHASE_DIVERGENCE_THRESHOLD = 0.2


# ---------- Helpers ----------

def _fmt(value: Optional[float], spec: str = '.1f', dash: str = '—') -> str:
    if value is None:
        return dash
    return format(value, spec)


def _scope_en(format: Optional[str], competition: Optional[str]) -> str:
    if competition:
        labels = {'ipl': 'the IPL', 't20i': "men's T20Is", 'odi': "men's ODIs",
                  'test': "men's Tests", 'bbl': 'the BBL', 'psl': 'the PSL', 'cpl': 'the CPL'}
        return labels.get(competition, competition)
    if format:
        return {'T20': 'T20 cricket', 'ODI': 'ODI cricket', 'Test': 'Test cricket'}.get(format, format)
    return 'all formats'


def _scope_hi(format: Optional[str], competition: Optional[str]) -> str:
    if competition:
        labels = {'ipl': 'आईपीएल', 't20i': 'पुरुष T20I', 'odi': 'पुरुष वनडे',
                  'test': 'पुरुष टेस्ट', 'bbl': 'बिग बैश लीग', 'psl': 'पीएसएल', 'cpl': 'सीपीएल'}
        return labels.get(competition, competition)
    if format:
        return {'T20': 'T20 क्रिकेट', 'ODI': 'वनडे क्रिकेट', 'Test': 'टेस्ट क्रिकेट'}.get(format, format)
    return 'सभी फॉर्मैट'


# Phase label translations for Hindi
PHASE_HI = {
    'Powerplay': 'पावरप्ले',
    'Middle': 'मिडल ओवर्स',
    'Death': 'डेथ ओवर्स',
    'First 30 overs': 'पहले 30 ओवर',
    'Overs 30-80': '30 से 80 ओवर',
    'Overs 80+': '80+ ओवर',
}

PHASE_EN = {
    'Powerplay': 'the powerplay',
    'Middle': 'the middle overs',
    'Death': 'the death overs',
    'First 30 overs': 'the first 30 overs',
    'Overs 30-80': 'overs 30 to 80',
    'Overs 80+': 'overs 80 and beyond',
}

FORMAT_HI = {'T20': 'T20', 'ODI': 'वनडे', 'Test': 'टेस्ट'}


def _find_sharpest_phase(phases_by_format: dict):
    """
    Across all formats, find the single phase with the largest meaningful
    divergence from baseline SR. Returns (format, phase, phase_stats) or None.
    """
    best = None
    best_div = PHASE_DIVERGENCE_THRESHOLD
    for fmt, phases in phases_by_format.items():
        for phase, p in phases.items():
            n = p.get('matchup_balls', 0)
            if n < PHASE_MIN_BALLS:
                continue
            m_sr, b_sr = p.get('matchup_sr'), p.get('baseline_sr')
            if m_sr is None or b_sr is None or b_sr == 0:
                continue
            div = abs(m_sr - b_sr) / b_sr
            if div >= best_div:
                best_div = div
                best = (fmt, phase, p)
    return best


def _phase_sentence_en(fmt: str, phase: str, p: dict, multi_format: bool) -> str:
    m_sr, b_sr, n = p['matchup_sr'], p['baseline_sr'], p['matchup_balls']
    direction = "drops to" if m_sr < b_sr else "rises to"
    phase_label = PHASE_EN.get(phase, phase)
    fmt_prefix = f"In {fmt} cricket, in {phase_label}" if multi_format else f"In {phase_label}"
    caveat = f" — though the sample is small ({n} balls)" if n < PHASE_MIN_BALLS * 2 else ""
    return (f"{fmt_prefix}, the batter's career strike rate of {b_sr:.1f} "
            f"{direction} {m_sr:.1f} against this bowler{caveat}.")


def _phase_sentence_hi(fmt: str, phase: str, p: dict, multi_format: bool) -> str:
    m_sr, b_sr, n = p['matchup_sr'], p['baseline_sr'], p['matchup_balls']
    direction = "गिरकर" if m_sr < b_sr else "बढ़कर"
    phase_label = PHASE_HI.get(phase, phase)
    fmt_prefix = f"{FORMAT_HI.get(fmt, fmt)} में {phase_label} में" if multi_format else f"{phase_label} में"
    caveat = f" — हालाँकि नमूना सीमित है ({n} गेंदें)" if n < PHASE_MIN_BALLS * 2 else ""
    return (f"{fmt_prefix}, बल्लेबाज़ का करियर स्ट्राइक रेट {b_sr:.1f} "
            f"इस गेंदबाज़ के सामने {direction} {m_sr:.1f} हो जाता है{caveat}।")


# ---------- Reports ----------

def _report_en(data: dict) -> str:
    if 'message' in data:
        return data['message']

    from .players import display_name, load_display_names
    overrides = load_display_names()
    batter = display_name(data['batter'], overrides)
    bowler = display_name(data['bowler'], overrides)
    scope = _scope_en(data.get('format'), data.get('competition'))
    n_balls = data['sample_size']
    n_matches = data['matches_played']

    m, b = data['overall_matchup'], data['overall_baseline']
    m_avg, m_sr, b_avg, b_sr = m['avg'], m['sr'], b['avg'], b['sr']

    if m_avg is not None and b_avg is not None:
        if m_avg < b_avg * 0.8:
            edge = f"{bowler} has a clear edge in this matchup"
        elif m_avg > b_avg * 1.2:
            edge = f"{batter} has handled {bowler} better than most"
        else:
            edge = "this matchup has been broadly even"
    else:
        edge = f"the matchup between {batter} and {bowler} is finely poised"

    out = f"Across {n_balls} deliveries in {n_matches} matches in {scope}, {edge}."
    out += (f" {batter} averages {_fmt(m_avg)} against {bowler} "
            f"(career baseline: {_fmt(b_avg)}), scoring at a strike rate of "
            f"{_fmt(m_sr)} (career: {_fmt(b_sr)}).")

    # Phase sentence — sharpest finding across whatever formats are present
    phases_by_format = data.get('phases_by_format', {})
    multi = data.get('format') is None and data.get('competition') is None
    sharp = _find_sharpest_phase(phases_by_format)
    if sharp:
        fmt, phase, p = sharp
        out += " " + _phase_sentence_en(fmt, phase, p, multi)

    # Per-competition breakdown if multi-format
    breakdown = data.get('competition_breakdown', {})
    nonzero = {c: s for c, s in breakdown.items() if s.get('balls', 0) > 0}
    if len(nonzero) >= 2:
        parts = [f"{c.upper()} ({s['balls']} balls, avg {_fmt(s.get('avg'))})"
                 for c, s in sorted(nonzero.items(), key=lambda kv: kv[1]['balls'], reverse=True)]
        out += " The matchup is split across " + ", ".join(parts) + "."

    if n_balls < SMALL_SAMPLE_THRESHOLD:
        out += (f" Sample size is modest ({n_balls} balls); "
                f"the pattern is suggestive rather than conclusive.")
    return out


def _report_hi(data: dict) -> str:
    if 'message' in data:
        return data['message']

    from .players import display_name, load_display_names
    overrides = load_display_names()
    batter = display_name(data['batter'], overrides)
    bowler = display_name(data['bowler'], overrides)
    scope = _scope_hi(data.get('format'), data.get('competition'))
    n_balls = data['sample_size']
    n_matches = data['matches_played']

    m, b = data['overall_matchup'], data['overall_baseline']
    m_avg, m_sr, b_avg, b_sr = m['avg'], m['sr'], b['avg'], b['sr']

    if m_avg is not None and b_avg is not None:
        if m_avg < b_avg * 0.8:
            edge = f"इस सामना में {bowler} को स्पष्ट बढ़त मिली है"
        elif m_avg > b_avg * 1.2:
            edge = f"{batter} ने {bowler} को सामान्य से बेहतर खेला है"
        else:
            edge = "यह सामना मोटे तौर पर बराबरी का रहा है"
    else:
        edge = f"{batter} और {bowler} के बीच का सामना संतुलित है"

    out = f"{scope} में {n_matches} मैचों की {n_balls} गेंदों में, {edge}।"
    out += (f" {batter} का {bowler} के सामने औसत {_fmt(m_avg)} है "
            f"(करियर औसत: {_fmt(b_avg)}), और स्ट्राइक रेट {_fmt(m_sr)} है "
            f"(करियर: {_fmt(b_sr)})।")

    phases_by_format = data.get('phases_by_format', {})
    multi = data.get('format') is None and data.get('competition') is None
    sharp = _find_sharpest_phase(phases_by_format)
    if sharp:
        fmt, phase, p = sharp
        out += " " + _phase_sentence_hi(fmt, phase, p, multi)

    breakdown = data.get('competition_breakdown', {})
    nonzero = {c: s for c, s in breakdown.items() if s.get('balls', 0) > 0}
    if len(nonzero) >= 2:
        comp_hi = {'ipl': 'आईपीएल', 't20i': 'T20I', 'odi': 'वनडे',
                   'test': 'टेस्ट', 'bbl': 'बीबीएल', 'psl': 'पीएसएल', 'cpl': 'सीपीएल'}
        parts = [f"{comp_hi.get(c, c)} ({s['balls']} गेंदें, औसत {_fmt(s.get('avg'))})"
                 for c, s in sorted(nonzero.items(), key=lambda kv: kv[1]['balls'], reverse=True)]
        out += " यह सामना फैला है " + ", ".join(parts) + " में।"

    if n_balls < SMALL_SAMPLE_THRESHOLD:
        out += f" नमूना सीमित है ({n_balls} गेंदें); पैटर्न संकेत देता है, निष्कर्ष नहीं।"
    return out


def generate_report(data: dict, language: str = 'en') -> str:
    if language == 'hi':
        return _report_hi(data)
    elif language == 'en':
        return _report_en(data)
    raise ValueError(f"Unsupported language: {language}. Use 'en' or 'hi'.")