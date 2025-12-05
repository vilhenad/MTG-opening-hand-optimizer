"""Deck Optimizer - Compact Streamlit Web App"""

import streamlit as st
from math import comb
from functools import lru_cache
from itertools import product

st.set_page_config(page_title="Deck Optimizer", page_icon="⚔️", layout="wide")

st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    h1 {margin-bottom: 0.5rem !important;}
    h3 {margin-top: 0.5rem !important; margin-bottom: 0.5rem !important;}
</style>""", unsafe_allow_html=True)

DECK_SIZE, HAND_SIZE = 100, 7

@lru_cache(maxsize=50000)
def hg(k, N, K, n):
    if k < 0 or k > min(K, n) or k < max(0, n - (N - K)): return 0.0
    return comb(K, k) * comb(N - K, n - k) / comb(N, n)

def prob_extra(deck, cat, draws, m):
    if m == 0: return 1.0
    if draws == 0: return 0.0
    return sum(hg(k, deck, cat, draws) for k in range(m, min(cat, draws) + 1))

def calc_prob(cats, mins, extras, turns):
    other = DECK_SIZE - sum(cats)
    if other < 0 or sum(mins) > HAND_SIZE: return 0.0
    if any(c < m for c, m in zip(cats, mins)): return 0.0
    
    prob, n = 0.0, len(cats)
    def gen(i, rem, cur):
        if i == n:
            if 0 <= rem <= other: yield cur + [rem]
            return
        for d in range(mins[i], min(cats[i], rem) + 1):
            yield from gen(i + 1, rem - d, cur + [d])
    
    for hand in gen(0, HAND_SIZE, []):
        drawn, oth = hand[:-1], hand[-1]
        p = 1.0
        for c, d in zip(cats, drawn): p *= comb(c, d)
        p *= comb(other, oth) / comb(DECK_SIZE, HAND_SIZE)
        if p > 0:
            for c, d, e, t in zip(cats, drawn, extras, turns):
                if e > 0 and t > 0: p *= prob_extra(DECK_SIZE - HAND_SIZE, c - d, t, e)
            prob += p
    return prob

def with_mull(cats, mins, extras, turns, mull):
    p = calc_prob(cats, mins, extras, turns)
    return 1 - (1 - p) ** (mull + 1) if mull > 0 else p

def find_best(ranges, mins, extras, turns, mull, min_rem):
    best, bp = None, -1
    for v in product(*[range(r[0], r[1]+1) for r in ranges]):
        c, rem = list(v), DECK_SIZE - sum(v)
        if rem < min_rem: continue
        p = with_mull(c, mins, extras, turns, mull)
        if p > bp: bp, best = p, {'c': c, 'rem': rem, 'p': p}
    return best

# STATE
if 'cats' not in st.session_state:
    st.session_state.cats = [
        {'name': 'Lands', 'count': 38, 'min': 2, 'extra': 1, 'turns': 3, 'range': (30, 50)},
        {'name': 'Ramp spells', 'count': 15, 'min': 1, 'extra': 0, 'turns': 0, 'range': (5, 25)},
        {'name': 'Haste creatures', 'count': 15, 'min': 1, 'extra': 0, 'turns': 0, 'range': (5, 25)},
    ]

st.markdown("### Categories")
cols = st.columns(len(st.session_state.cats) + 1)

for i, cat in enumerate(st.session_state.cats):
    with cols[i]:
        cat['name'] = st.text_input("Name", cat['name'], key=f"n{i}")
        cat['count'] = st.number_input("Count in Deck", 0, 70, cat['count'], key=f"c{i}")
        cat['min'] = st.number_input("Min in Hand", 0, 7, cat['min'], key=f"m{i}")
        cat['extra'] = st.number_input("Extra to Draw", 0, 10, cat.get('extra', 0), key=f"e{i}")
        if cat['extra'] > 0:
            cat['turns'] = st.number_input("By Turn", 1, 10, max(1, cat.get('turns', 3)), key=f"t{i}")
        else:
            cat['turns'] = 0
        cat['range'] = st.slider("Search range for optimization", 0, 70, cat.get('range', (5,20)), key=f"rng{i}")
        if len(st.session_state.cats) > 1 and st.button("🗑️ Remove", key=f"r{i}"): 
            st.session_state.cats.pop(i); st.rerun()

with cols[-1]:
    st.write("")
    if st.button("➕ Add"):
        st.session_state.cats.append({'name': f'New', 'count': 10, 'min': 1, 'extra': 0, 'turns': 0, 'range': (5, 20)})
        st.rerun()

# Settings row
remaining = DECK_SIZE - sum(c['count'] for c in st.session_state.cats)
c1, c2, c3 = st.columns(3)
with c1:
    if remaining >= 0: st.success(f"Remaining: **{remaining}**")
    else: st.error(f"Over: **{-remaining}**")
with c2:
    mull = st.number_input("🔄 Mulligans", 0, 7, 0)
    mull_text = f"⚠️ Bottom {mull-1} card(s)" if mull > 1 else ("Free mulligan" if mull == 1 else "—")
    st.caption(mull_text)
with c3:
    min_rem = st.slider("Min Remaining Slots", 0, 60, 40)

# Data
counts = [c['count'] for c in st.session_state.cats]
mins = [c['min'] for c in st.session_state.cats]
extras = [c.get('extra', 0) for c in st.session_state.cats]
turns = [c.get('turns', 0) for c in st.session_state.cats]
names = [c['name'] for c in st.session_state.cats]
ranges = [c.get('range', (5, 20)) for c in st.session_state.cats]

# Results
c1, c2 = st.columns(2)
with c1:
    prob = with_mull(counts, mins, extras, turns, mull)
    st.metric("📊 Current", f"{prob*100:.2f}%")

with c2:
    best = find_best(ranges, mins, extras, turns, mull, min_rem)
    if best:
        delta = best['p'] - prob
        st.metric("⭐ Optimal ℹ️", f"{best['p']*100:.1f}%", 
                 delta=f"+{delta*100:.1f}%" if delta > 0.001 else None,
                 help="Searches all combinations within each category's search range to find the configuration with the highest probability while maintaining at least the minimum remaining slots.")
        st.success(" | ".join(f"**{n}**: {c}" for n, c in zip(names, best['c'])) + f" *(rem: {best['rem']})*")
    else:
        st.warning("No valid config")
