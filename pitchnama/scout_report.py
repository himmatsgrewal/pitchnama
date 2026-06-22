"""
scout_report.py — Bilingual scout report generation for PitchNama.

Voice: broadcast pundit (Star Sports / Sky Cricket register) — tight,
story-style, plain English / plain Hindi. Translates raw numbers into
meaning ("a 31% drop", "removes him every 35 balls"), names the edge in
human terms, surfaces one meaningful phase nuance, and calls out a
format split when there's a real contrast.
"""

from typing import Optional


SMALL_SAMPLE_THRESHOLD = 30
PHASE_MIN_BALLS = 10            # raised from 3 — don't lead with tiny-sample factoids
PHASE_DIVERGENCE_THRESHOLD = 0.25   # only real findings make the cut
FORMAT_CONTRAST_MIN_BALLS = 30      # each side of the contrast needs this many
FORMAT_CONTRAST_RATIO = 2.0         # best-avg must be at least this × worst-avg


# ---------- Helpers ----------

def _fmt(value: Optional[float], spec: str = '.0f', dash: str = '—') -> str:
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


PHASE_EN = {
    'Powerplay': 'the powerplay',
    'Middle': 'the middle overs',
    'Death': 'the death',
    'First 30 overs': 'early in the innings',
    'Overs 30-80': 'the middle phase',
    'Overs 80+': 'with the old ball',
}

PHASE_HI = {
    'Powerplay': 'पावरप्ले',
    'Middle': 'मिडल ओवर्स',
    'Death': 'डेथ ओवर्स',
    'First 30 overs': 'पारी की शुरुआत',
    'Overs 30-80': 'मध्य चरण',
    'Overs 80+': 'पुरानी गेंद के साथ',
}

FORMAT_HI = {'T20': 'T20', 'ODI': 'वनडे', 'Test': 'टेस्ट'}

COMP_EN_NICE = {'ipl': 'the IPL', 't20i': 'T20Is', 'odi': 'ODIs',
                'test': 'Tests', 'bbl': 'the BBL', 'psl': 'the PSL', 'cpl': 'the CPL'}

COMP_HI_NICE = {'ipl': 'आईपीएल', 't20i': 'T20I', 'odi': 'वनडे',
                'test': 'टेस्ट', 'bbl': 'बीबीएल', 'psl': 'पीएसएल', 'cpl': 'सीपीएल'}


def _edge_strength(m_avg: Optional[float], b_avg: Optional[float], m_wkts: int) -> str:
    """One of: strong_bowler, clear_bowler, slight_bowler, even,
    slight_batter, clear_batter, strong_batter, unknown."""
    if m_wkts == 0:
        # Never been dismissed — that's a strong batter edge regardless of SR
        return 'strong_batter'
    if m_avg is None or b_avg is None or b_avg == 0:
        return 'unknown'
    ratio = m_avg / b_avg
    if ratio < 0.6: return 'strong_bowler'
    if ratio < 0.8: return 'clear_bowler'
    if ratio < 0.92: return 'slight_bowler'
    if ratio > 1.6: return 'strong_batter'
    if ratio > 1.25: return 'clear_batter'
    if ratio > 1.08: return 'slight_batter'
    return 'even'


def _find_sharpest_phase(phases_by_format: dict):
    """Find the single phase with the largest meaningful SR divergence.
    Returns (format, phase_name, phase_dict) or None."""
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


def _find_format_contrast(breakdown: dict):
    """If two formats/competitions show a striking split, return
    (best_code, best_avg, best_balls, worst_code, worst_avg, worst_balls).
    Otherwise None."""
    meaningful = [(c, s) for c, s in breakdown.items()
                  if s.get('balls', 0) >= FORMAT_CONTRAST_MIN_BALLS
                  and s.get('avg') is not None]
    if len(meaningful) < 2:
        return None
    meaningful.sort(key=lambda kv: kv[1]['avg'], reverse=True)
    best_c, best_s = meaningful[0]
    worst_c, worst_s = meaningful[-1]
    if worst_s['avg'] <= 0 or best_s['avg'] < worst_s['avg'] * FORMAT_CONTRAST_RATIO:
        return None
    return (best_c, best_s['avg'], best_s['balls'],
            worst_c, worst_s['avg'], worst_s['balls'])


# ---------- English (broadcast pundit voice) ----------

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
    m_wkts = m.get('wickets', 0)
    b_wkts = b.get('wickets', 0)

    out = []

    # 1. Opener — name the edge in human terms.
    edge = _edge_strength(m_avg, b_avg, m_wkts)
    openers = {
        'strong_bowler': f"{bowler} has had {batter}'s number.",
        'clear_bowler':  f"{bowler} has had the better of this contest.",
        'slight_bowler': f"A slight edge to {bowler} in this matchup.",
        'strong_batter': f"{batter} has dominated {bowler}.",
        'clear_batter':  f"{batter} has had the upper hand here.",
        'slight_batter': f"A slight edge to {batter} in this matchup.",
        'even':          f"A finely poised contest between {batter} and {bowler}.",
        'unknown':       f"A new contest between {batter} and {bowler}.",
    }
    out.append(openers[edge])

    # 2. Volume + average — translate the numbers into meaning.
    if m_wkts == 0:
        out.append(
            f"In {n_matches} matches and {n_balls} balls in {scope}, "
            f"{bowler} has never dismissed {batter}."
        )
    elif m_avg is not None and b_avg is not None and b_avg > 0:
        delta_pct = abs(round((m_avg - b_avg) / b_avg * 100))
        if m_avg < b_avg:
            out.append(
                f"In {n_matches} matches and {n_balls} balls in {scope}, "
                f"{batter} averages just {_fmt(m_avg)} — a {delta_pct}% drop "
                f"from his career {_fmt(b_avg)}."
            )
        else:
            out.append(
                f"In {n_matches} matches and {n_balls} balls in {scope}, "
                f"{batter} averages {_fmt(m_avg)} — {delta_pct}% above his "
                f"career {_fmt(b_avg)}."
            )
    else:
        out.append(
            f"In {n_matches} matches and {n_balls} balls in {scope}, "
            f"{batter} has scored at {_fmt(m_sr)} a hundred balls."
        )

    # 3. Strike rate — only if meaningfully different.
    if m_sr is not None and b_sr is not None and b_sr > 0:
        sr_ratio = m_sr / b_sr
        if sr_ratio < 0.88:
            sr_pct = round((1 - sr_ratio) * 100)
            out.append(
                f"His strike rate sags too: {_fmt(m_sr)} here against a usual "
                f"{_fmt(b_sr)} — {sr_pct}% slower."
            )
        elif sr_ratio > 1.15:
            sr_pct = round((sr_ratio - 1) * 100)
            out.append(
                f"And he goes after this bowling: {_fmt(m_sr)} strike rate "
                f"against a usual {_fmt(b_sr)}, {sr_pct}% faster."
            )

    # 4. Dismissal frequency — the killer line for "had your number" stories.
    if m_wkts >= 3 and b_wkts > 0 and b['balls'] > 0:
        m_bpd = round(m['balls'] / m_wkts)
        b_bpd = round(b['balls'] / b_wkts)
        if m_bpd < b_bpd * 0.85:
            out.append(
                f"{bowler} removes him every {m_bpd} balls "
                f"when {batter} normally lasts {b_bpd}."
            )
        elif m_bpd > b_bpd * 1.15:
            out.append(
                f"{batter} hangs around longer than usual too — "
                f"out every {m_bpd} balls vs his usual {b_bpd}."
            )

    # 5. Phase finding — one meaningful one, only if not tiny sample.
    sharp = _find_sharpest_phase(data.get('phases_by_format', {}))
    if sharp:
        fmt, phase, p = sharp
        phase_label = PHASE_EN.get(phase, phase)
        m_phase_sr, b_phase_sr = p['matchup_sr'], p['baseline_sr']
        multi = data.get('format') is None and data.get('competition') is None
        fmt_prefix = f"In {fmt}, " if multi else ""
        if m_phase_sr < b_phase_sr:
            out.append(
                f"{fmt_prefix}{phase_label} is where {bowler} squeezes hardest: "
                f"{batter}'s usual {_fmt(b_phase_sr)} scoring rate falls to "
                f"{_fmt(m_phase_sr)} against him."
            )
        else:
            out.append(
                f"{fmt_prefix}{phase_label} is where {batter} cashes in: "
                f"his usual {_fmt(b_phase_sr)} rate climbs to {_fmt(m_phase_sr)}."
            )

    # 6. Format contrast — only if multi-scope AND there's a real split.
    if data.get('format') is None and data.get('competition') is None:
        contrast = _find_format_contrast(data.get('competition_breakdown', {}))
        if contrast:
            best_c, best_avg, best_balls, worst_c, worst_avg, worst_balls = contrast
            out.append(
                f"It's a split picture by format: {batter} has thrived in "
                f"{COMP_EN_NICE.get(best_c, best_c)} (averaging {_fmt(best_avg)} "
                f"over {best_balls} balls) but struggled in "
                f"{COMP_EN_NICE.get(worst_c, worst_c)} "
                f"({_fmt(worst_avg)} from {worst_balls})."
            )

    # 7. Small-sample caveat.
    if n_balls < SMALL_SAMPLE_THRESHOLD:
        out.append("Sample is modest — treat the pattern as suggestive, not conclusive.")

    return " ".join(out)


# ---------- Hindi (broadcast pundit voice) ----------

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
    m_wkts = m.get('wickets', 0)
    b_wkts = b.get('wickets', 0)

    out = []

    # 1. Opener
    edge = _edge_strength(m_avg, b_avg, m_wkts)
    openers = {
        'strong_bowler': f"{bowler} ने {batter} पर पूरी पकड़ बना रखी है।",
        'clear_bowler':  f"इस मुकाबले में {bowler} का पलड़ा भारी रहा है।",
        'slight_bowler': f"{bowler} को इस सामना में हल्की बढ़त है।",
        'strong_batter': f"{batter} ने {bowler} पर दबदबा बनाया है।",
        'clear_batter':  f"इस मुकाबले में {batter} का पलड़ा भारी रहा है।",
        'slight_batter': f"{batter} को इस सामना में हल्की बढ़त है।",
        'even':          f"{batter} और {bowler} का यह सामना कांटे का है।",
        'unknown':       f"{batter} और {bowler} के बीच का सामना अभी शुरुआती दौर में है।",
    }
    out.append(openers[edge])

    # 2. Volume + average
    if m_wkts == 0:
        out.append(
            f"{scope} में {n_matches} मैचों और {n_balls} गेंदों में, "
            f"{bowler} {batter} को कभी आउट नहीं कर सके।"
        )
    elif m_avg is not None and b_avg is not None and b_avg > 0:
        delta_pct = abs(round((m_avg - b_avg) / b_avg * 100))
        if m_avg < b_avg:
            out.append(
                f"{scope} में {n_matches} मैचों और {n_balls} गेंदों में, "
                f"{batter} का औसत सिर्फ {_fmt(m_avg)} है — "
                f"उनके करियर औसत {_fmt(b_avg)} से {delta_pct}% कम।"
            )
        else:
            out.append(
                f"{scope} में {n_matches} मैचों और {n_balls} गेंदों में, "
                f"{batter} का औसत {_fmt(m_avg)} है — "
                f"उनके करियर औसत {_fmt(b_avg)} से {delta_pct}% ज़्यादा।"
            )

    # 3. Strike rate
    if m_sr is not None and b_sr is not None and b_sr > 0:
        sr_ratio = m_sr / b_sr
        if sr_ratio < 0.88:
            sr_pct = round((1 - sr_ratio) * 100)
            out.append(
                f"स्ट्राइक रेट भी गिरा है: यहाँ {_fmt(m_sr)}, "
                f"सामान्य {_fmt(b_sr)} के मुकाबले — {sr_pct}% धीमा।"
            )
        elif sr_ratio > 1.15:
            sr_pct = round((sr_ratio - 1) * 100)
            out.append(
                f"और वो इस गेंदबाज़ी पर हाथ खोलते हैं: स्ट्राइक रेट {_fmt(m_sr)}, "
                f"सामान्य {_fmt(b_sr)} से {sr_pct}% तेज़।"
            )

    # 4. Dismissal frequency
    if m_wkts >= 3 and b_wkts > 0 and b['balls'] > 0:
        m_bpd = round(m['balls'] / m_wkts)
        b_bpd = round(b['balls'] / b_wkts)
        if m_bpd < b_bpd * 0.85:
            out.append(
                f"{bowler} उन्हें हर {m_bpd} गेंदों पर आउट करते हैं, "
                f"जबकि {batter} आम तौर पर {b_bpd} गेंदें टिकते हैं।"
            )
        elif m_bpd > b_bpd * 1.15:
            out.append(
                f"{batter} सामान्य से ज़्यादा देर भी टिकते हैं — "
                f"हर {m_bpd} गेंदों पर आउट, सामान्य {b_bpd} के मुकाबले।"
            )

    # 5. Phase finding
    sharp = _find_sharpest_phase(data.get('phases_by_format', {}))
    if sharp:
        fmt, phase, p = sharp
        phase_label = PHASE_HI.get(phase, phase)
        m_phase_sr, b_phase_sr = p['matchup_sr'], p['baseline_sr']
        multi = data.get('format') is None and data.get('competition') is None
        fmt_prefix = f"{FORMAT_HI.get(fmt, fmt)} में, " if multi else ""
        if m_phase_sr < b_phase_sr:
            out.append(
                f"{fmt_prefix}{phase_label} में {bowler} सबसे ज़्यादा कसते हैं: "
                f"{batter} की सामान्य {_fmt(b_phase_sr)} स्कोरिंग रेट "
                f"इनके सामने {_fmt(m_phase_sr)} पर आ जाती है।"
            )
        else:
            out.append(
                f"{fmt_prefix}{phase_label} में {batter} खुलकर खेलते हैं: "
                f"उनकी सामान्य {_fmt(b_phase_sr)} रेट {_fmt(m_phase_sr)} तक पहुँच जाती है।"
            )

    # 6. Format contrast
    if data.get('format') is None and data.get('competition') is None:
        contrast = _find_format_contrast(data.get('competition_breakdown', {}))
        if contrast:
            best_c, best_avg, best_balls, worst_c, worst_avg, worst_balls = contrast
            out.append(
                f"फॉर्मैट के हिसाब से तस्वीर बँटी है: {batter} "
                f"{COMP_HI_NICE.get(best_c, best_c)} में छाए हुए हैं "
                f"({best_balls} गेंदों में {_fmt(best_avg)} का औसत), "
                f"लेकिन {COMP_HI_NICE.get(worst_c, worst_c)} में संघर्ष करते दिखे हैं "
                f"({worst_balls} गेंदों में {_fmt(worst_avg)})।"
            )

    # 7. Small-sample caveat
    if n_balls < SMALL_SAMPLE_THRESHOLD:
        out.append("नमूना सीमित है — पैटर्न संकेत देता है, निष्कर्ष नहीं।")

    return " ".join(out)


def generate_report(data: dict, language: str = 'en') -> str:
    if language == 'hi':
        return _report_hi(data)
    elif language == 'en':
        return _report_en(data)
    raise ValueError(f"Unsupported language: {language}. Use 'en' or 'hi'.")