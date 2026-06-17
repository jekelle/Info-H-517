# -*- coding: utf-8 -*-
"""
What Actually Moves the Chains?
Westfield Shamrocks vs NFL 2024 Play-Calling Analytics

Author : Jay R. Kelley
Course : I-590 Data Visualization, Spring 2026, IU Indianapolis
Project: Final Dash Web Application

A coaching tool that compares Westfield High School play-calling tendencies
against the NFL 2024 benchmark (nflverse / nflfastR). Five interactive
visualizations, one shared cross-filter, colorblind-safe palette, anomaly
annotations, and Munzner-aligned encodings throughout.
"""

# ============================================================
# IMPORTS
# ============================================================
import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output


# ============================================================
# CONSTANTS
# ============================================================
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

# Okabe Ito palette, eight color colorblind safe set.
# Reference: Okabe and Ito (2008), used by ggplot2 and Plotly Safe.
PALETTE = {
    'pass':         '#0072B2',  # blue
    'run':          '#E69F00',  # orange
    'punt':         '#999999',
    'field_goal':   '#56B4E9',
    'kickoff':      '#CC79A7',
    'QB1':'#0072B2',
    'QB2':     '#CC79A7',
    'highlight_pos':'#009E73',  # green, used for positive callouts
    'highlight_neg':'#D55E00',  # vermillion, used for negative callouts
    'neutral':      '#BBBBBB',
}

# Brand palette for the dashboard chrome (Westfield navy and gold).
BRAND = {
    'navy':       '#0A2240',
    'gold':       '#C8A464',
    'bg':         '#F7F8FA',
    'card':       '#FFFFFF',
    'text':       '#1A1A1A',
    'muted':      '#5A6470',
    'border':     '#E1E4EA',
}

FONT_STACK = '"Inter", "Helvetica Neue", Arial, sans-serif'


# ============================================================
# DATA LOADERS
# ============================================================
def make_westfield(n=500, seed=RANDOM_SEED):
    """
    Generate Westfield play by play that matches the manual Hudl charting
    schema. Concept skill rates and QB profiles are seeded to match the
    spring 2026 QB report (QB1 Grade A ELITE, QB2 Grade B DEV).
    """
    rng = np.random.default_rng(seed)

    pass_concepts = ['Four Verts', 'Stick', 'Post', 'Sail', 'Baltimore',
                     'Slants', 'Curl', 'Drag', 'Fade', 'Smash']
    run_concepts  = ['Inside Zone', 'Outside Zone', 'Power', 'Counter',
                     'Trap', 'QB Draw']

    concept_skill = {
        'Baltimore': 0.78, 'Four Verts': 0.70, 'Stick': 0.62, 'Smash': 0.58,
        'Post': 0.55, 'Slants': 0.50, 'Curl': 0.46, 'Drag': 0.42,
        'Fade': 0.18, 'Sail': 0.15,
        'Power': 0.62, 'QB Draw': 0.60, 'Outside Zone': 0.55,
        'Inside Zone': 0.52, 'Counter': 0.50, 'Trap': 0.44,
    }

    game_dates = pd.date_range('2025-08-22', '2025-11-29', periods=14).date
    opponents  = ['Carmel', 'Brownsburg', 'Hamilton SE', 'Noblesville',
                  'Avon', 'Cathedral', 'Ben Davis', 'Lawrence Central',
                  'North Central', 'Center Grove', 'Pike', 'Zionsville',
                  'Penn', 'Carmel (rematch)']

    rows = []
    for i in range(n):
        game_idx  = int(rng.integers(0, 14))
        down      = int(rng.choice([1, 2, 3, 4], p=[0.42, 0.30, 0.22, 0.06]))
        pass_prob = {1: 0.38, 2: 0.45, 3: 0.68, 4: 0.50}[down]
        is_pass   = rng.random() < pass_prob
        play_type = 'pass' if is_pass else 'run'
        concept   = (rng.choice(pass_concepts) if is_pass
                     else rng.choice(run_concepts))
        field     = rng.choice(
            ['Own 1-10', 'Own 11-20', 'Own 21-40', 'Midfield',
             'Opp 21-40', 'Opp 11-20', 'Red Zone'],
            p=[0.05, 0.10, 0.20, 0.25, 0.20, 0.12, 0.08])
        quarter   = int(rng.choice([1, 2, 3, 4]))
        qb        = rng.choice(['QB1', 'QB2'], p=[0.54, 0.46])

        base  = 7 if is_pass else 4
        skill = concept_skill.get(concept, 0.5)
        yards = int(rng.normal(base * (0.6 + skill), 4))
        yards = max(-6, min(yards, 55))

        success = rng.random() < skill
        if rng.random() < 0.04 and is_pass:
            result, yards = 'Sack', -6
        elif field == 'Red Zone' and yards >= 6 and success:
            result, yards = 'TD', max(yards, 6)
        elif down == 3 and success:
            result = 'First Down'
        elif yards >= 10 and success:
            result = 'First Down'
        elif is_pass and not success:
            result = 'Incompletion'
        elif is_pass:
            result = 'Completion'
        elif yards <= 0:
            result = 'TFL'
        else:
            result = 'Run Gain'

        ttt = None
        if is_pass:
            mean_ttt = 2.55 + (0.18 if qb == 'QB2' else 0.0) + \
                       (0.12 if down == 3 else 0.0)
            ttt = round(float(rng.normal(mean_ttt, 0.35)), 1)
            ttt = max(1.6, min(ttt, 5.0))

        rows.append({
            'id': i + 1, 'qb': qb, 'concept': concept, 'result': result,
            'yards': yards, 'down': down, 'field': field, 'ttt': ttt,
            'date': game_dates[game_idx],
            'opponent': opponents[game_idx], 'quarter': quarter,
            'play_type': play_type,
        })
    return pd.DataFrame(rows)


def make_nfl(n=10000, seed=RANDOM_SEED):
    """
    Generate NFL play by play matching the trimmed nflfastR schema.
    Team strength shifts seed top tier QBs (KC, BUF, DET, BAL, PHI) above
    the bottom tier so the EPA leaderboard reads realistically.
    """
    rng = np.random.default_rng(seed)
    teams = ['ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL',
             'DEN', 'DET', 'GB',  'HOU', 'IND', 'JAX', 'KC',  'LV',  'LAC',
             'LAR', 'MIA', 'MIN', 'NE',  'NO',  'NYG', 'NYJ', 'PHI', 'PIT',
             'SEA', 'SF',  'TB',  'TEN', 'WAS']
    strong = {'KC': 0.18, 'BUF': 0.16, 'DET': 0.14, 'BAL': 0.13,
              'PHI': 0.12, 'GB': 0.10, 'MIN': 0.09, 'CIN': 0.07}
    weak   = {'CAR': -0.20, 'NYG': -0.17, 'NE': -0.15, 'TEN': -0.14,
              'LV': -0.12, 'JAX': -0.10, 'CLE': -0.08}
    team_shift = {t: strong.get(t, weak.get(t, rng.normal(0, 0.04)))
                  for t in teams}

    df = pd.DataFrame({
        'game_date': pd.to_datetime(rng.choice(
            pd.date_range('2024-09-05', '2025-01-05'), n)),
        'posteam':   rng.choice(teams, n),
        'play_type': rng.choice(
            ['pass', 'run', 'punt', 'field_goal', 'kickoff'],
            n, p=[0.55, 0.35, 0.06, 0.03, 0.01]),
        'down':      rng.choice([1, 2, 3, 4], n, p=[0.40, 0.30, 0.25, 0.05]),
        'ydstogo':   rng.integers(1, 21, n),
        'yards_gained':      rng.normal(5.2, 8, n).round(1),
        'air_yards':         rng.normal(8.0, 6, n).round(1),
        'yards_after_catch': rng.normal(4.0, 4, n).round(1),
        'wp':                rng.uniform(0.05, 0.95, n).round(2),
    })
    df['epa'] = (rng.normal(0.0, 1.4, n)
                 + df['posteam'].map(team_shift)).round(2)
    return df


# Load once at app start. Real CSVs win if uploaded alongside app.py.
WF_PATH  = 'Westfield_Plays_500.csv'
NFL_PATH = 'play_by_play_2024_TRUNCATED.csv'

if os.path.exists(WF_PATH):
    wf = pd.read_csv(WF_PATH)
else:
    wf = make_westfield()

if os.path.exists(NFL_PATH):
    nfl = pd.read_csv(NFL_PATH)
else:
    nfl = make_nfl()


# ============================================================
# CHART BUILDERS
# Every builder takes the filter values it cares about and returns a
# fully styled Plotly figure. Filter handling lives in callbacks below.
# ============================================================
def style_figure(fig, height=420):
    """Apply consistent typography and chrome to every figure."""
    fig.update_layout(
        template='plotly_white',
        height=height,
        font=dict(family=FONT_STACK, size=13, color=BRAND['text']),
        title_x=0.5, title_font_size=15,
        margin=dict(l=60, r=40, t=70, b=50),
        legend=dict(orientation='h', y=-0.18, x=0.5, xanchor='center'),
        hoverlabel=dict(font_family=FONT_STACK, font_size=12,
                        bgcolor='white', bordercolor=BRAND['border']),
    )
    return fig


def empty_figure(message):
    """Used when filter combo yields no rows."""
    fig = go.Figure()
    fig.add_annotation(text=message, xref='paper', yref='paper',
                       x=0.5, y=0.5, showarrow=False,
                       font=dict(size=14, color=BRAND['muted']))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return style_figure(fig, height=300)


# ---------- Viz 1: Pass / run mix by down ----------
def build_passrun_mix(wf, nfl, down='All'):
    """
    Faceted grouped bars comparing pass / run share at each down between
    Westfield and NFL 2024. Responds to the shared Down filter.
    """
    def share_table(df, label):
        d = df[df.play_type.isin(['pass', 'run'])].copy()
        if down != 'All':
            d = d[d['down'] == int(down)]
        if d.empty:
            return d
        g = d.groupby(['down', 'play_type']).size().reset_index(name='n')
        g['pct'] = g.groupby('down')['n'].transform(lambda x: x / x.sum() * 100)
        g['dataset'] = label
        return g

    wf_g  = share_table(wf,  'Westfield (HS)')
    nfl_g = share_table(nfl, 'NFL 2024')
    combined = pd.concat([wf_g, nfl_g], ignore_index=True)

    if combined.empty:
        return empty_figure('No plays match the current filter.')

    fig = px.bar(
        combined, x='down', y='pct', color='play_type',
        facet_col='dataset', barmode='group',
        color_discrete_map={'pass': PALETTE['pass'], 'run': PALETTE['run']},
        category_orders={'down': [1, 2, 3, 4], 'play_type': ['pass', 'run']},
        labels={'pct': '% of plays', 'down': 'Down', 'play_type': 'Play type'},
        custom_data=['n', 'play_type'],
    )
    fig.update_traces(
        hovertemplate=('<b>Down %{x}</b><br>'
                       '%{customdata[1]}: %{y:.1f}%<br>'
                       'n = %{customdata[0]}<extra></extra>'),
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split('=')[-1],
                                                font_size=13))
    fig.update_yaxes(ticksuffix='%', range=[0, 100])
    fig.update_xaxes(tickmode='array', tickvals=[1, 2, 3, 4])

    title = ('Pass / run share by down, Westfield vs NFL 2024'
             if down == 'All'
             else f'Pass / run share, down {down}, Westfield vs NFL 2024')
    fig.update_layout(title=title, bargap=0.25, legend_title_text='')

    # Anomaly annotation: HS pass rate on 3rd down well above NFL.
    if down in ('All', 3):
        wf_3 = combined[(combined['dataset'] == 'Westfield (HS)') &
                        (combined['down'] == 3) &
                        (combined['play_type'] == 'pass')]
        if not wf_3.empty:
            fig.add_annotation(
                text=f"Westfield throws on {wf_3['pct'].iloc[0]:.0f}% of 3rd downs",
                xref='paper', yref='paper', x=0.02, y=1.10,
                showarrow=False, font=dict(size=11, color=PALETTE['highlight_neg']),
                align='left',
            )
    return style_figure(fig, height=440)


# ---------- Viz 2: 3rd down concept conversion (Westfield) ----------
def build_concept_success(wf, qb='Both', opponent='All', min_n=4):
    """
    Sorted horizontal bars with n labels. Flags Sail and Fade as cut
    candidates with a red bracket annotation.
    """
    third = wf[wf['down'] == 3].copy()
    if qb != 'Both':
        third = third[third['qb'] == qb]
    if opponent != 'All':
        third = third[third['opponent'] == opponent]
    if third.empty:
        return empty_figure('No 3rd-down plays match the current filter.')

    grouped = (third.groupby('concept')
               .agg(n=('id', 'count'),
                    converted=('result',
                               lambda r: r.isin(['First Down', 'TD']).sum()))
               .reset_index())
    grouped['rate'] = (grouped['converted'] / grouped['n'] * 100).round(1)
    grouped = grouped[grouped['n'] >= min_n].sort_values('rate')
    if grouped.empty:
        return empty_figure(f'No concepts have n ≥ {min_n} in this slice.')

    grouped['n_label'] = 'n=' + grouped['n'].astype(str)

    fig = px.bar(
        grouped, x='rate', y='concept', orientation='h',
        text='n_label', color='rate',
        color_continuous_scale='Teal',
        labels={'rate': 'Conversion rate (%)', 'concept': 'Concept'},
        custom_data=['n', 'converted'],
    )
    fig.update_traces(
        textposition='outside', textfont=dict(size=11),
        hovertemplate=('<b>%{y}</b><br>'
                       'Conversion: %{x:.1f}%<br>'
                       'Converted: %{customdata[1]} of %{customdata[0]}'
                       '<extra></extra>'),
    )
    title_pieces = ['3rd-down concept conversion']
    if qb != 'Both':
        title_pieces.append(qb)
    if opponent != 'All':
        title_pieces.append(f'vs {opponent}')
    title_pieces.append(f'(n ≥ {min_n})')
    fig.update_layout(
        title=' · '.join(title_pieces),
        coloraxis_showscale=False,
        margin=dict(l=140, r=80, t=70, b=50),
    )
    fig.update_xaxes(ticksuffix='%', range=[0, 115])

    # Cut-candidate annotation, only when both Sail and Fade visible.
    cut = grouped[grouped['concept'].isin(['Sail', 'Fade'])]
    if len(cut) >= 1 and cut['rate'].max() < 30:
        y_target = cut['concept'].iloc[0]
        fig.add_annotation(
            x=35, y=y_target,
            text='Cut candidates: low conversion across enough reps to trust',
            showarrow=True, arrowhead=2, ax=80, ay=0,
            font=dict(size=11, color=PALETTE['highlight_neg']),
            arrowcolor=PALETTE['highlight_neg'], bgcolor='white',
            bordercolor=PALETTE['highlight_neg'], borderwidth=1, borderpad=4,
        )

    # Elite-concept annotation, top performer.
    top = grouped.iloc[-1]
    if top['rate'] >= 70:
        fig.add_annotation(
            x=top['rate'], y=top['concept'],
            text=f"Top performer: {top['concept']} at {top['rate']:.0f}%",
            showarrow=True, arrowhead=2, ax=-80, ay=0,
            font=dict(size=11, color=PALETTE['highlight_pos']),
            arrowcolor=PALETTE['highlight_pos'], bgcolor='white',
            bordercolor=PALETTE['highlight_pos'], borderwidth=1, borderpad=4,
        )

    return style_figure(fig, height=500)


# ---------- Viz 3: Field zone × quarter heatmap ----------
def build_field_heatmap(wf, opponent='All'):
    """
    Diverging heatmap: yards per play by field zone (rows) and quarter
    (columns). Red-blue scale anchored on the league average so positive
    cells are immediately readable.
    """
    df = wf.copy()
    if opponent != 'All':
        df = df[df['opponent'] == opponent]
    if df.empty:
        return empty_figure('No plays match the current filter.')

    zone_order = ['Own 1-10', 'Own 11-20', 'Own 21-40', 'Midfield',
                  'Opp 21-40', 'Opp 11-20', 'Red Zone']
    pivot = (df.groupby(['field', 'quarter'])['yards']
             .mean().reset_index()
             .pivot(index='field', columns='quarter', values='yards')
             .reindex(zone_order))
    counts = (df.groupby(['field', 'quarter'])['yards']
              .count().reset_index()
              .pivot(index='field', columns='quarter', values='yards')
              .reindex(zone_order))

    z = pivot.values
    n = counts.values
    text = np.where(np.isnan(z), '', np.round(z, 1).astype(str))

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[f'Q{c}' for c in pivot.columns],
        y=pivot.index,
        colorscale='RdBu', zmid=0, zmin=-4, zmax=10,
        text=text, texttemplate='%{text}',
        textfont=dict(size=11),
        customdata=n,
        hovertemplate=('<b>%{y} · %{x}</b><br>'
                       'Yards per play: %{z:.2f}<br>'
                       'n = %{customdata}<extra></extra>'),
        colorbar=dict(title='Yds / play', thickness=14, len=0.7),
    ))

    title = ('Yards per play, field zone × quarter'
             if opponent == 'All'
             else f'Yards per play, field zone × quarter, vs {opponent}')
    fig.update_layout(title=title,
                      xaxis_title='Quarter', yaxis_title='Field zone')

    # Red-zone gap callout (one of the project's flagged anomalies).
    rz_row = pivot.loc['Red Zone'] if 'Red Zone' in pivot.index else None
    if rz_row is not None and rz_row.notna().any() and rz_row.mean() < 3:
        fig.add_annotation(
            text='Red zone gap: no package installed, every QB grade flagged 0%',
            xref='paper', yref='paper', x=0.02, y=1.10,
            showarrow=False, align='left',
            font=dict(size=11, color=PALETTE['highlight_neg']),
        )
    return style_figure(fig, height=440)


# ---------- Viz 4: QB time-to-throw ----------
def build_qb_ttt(wf, down='All', qb='Both'):
    """
    Side by side box plots of time to throw on pass plays, by QB and down.
    Responds to the shared Down filter and the QB selector.
    """
    df = wf[(wf['play_type'] == 'pass') & (wf['ttt'].notna())].copy()
    if down != 'All':
        df = df[df['down'] == int(down)]
    if qb != 'Both':
        df = df[df['qb'] == qb]
    if df.empty:
        return empty_figure('No pass plays match the current filter.')

    fig = px.box(
        df, x='down', y='ttt', color='qb',
        color_discrete_map={'QB1': PALETTE['QB1'],
                            'QB2':      PALETTE['QB2']},
        category_orders={'down': [1, 2, 3, 4],
                         'qb': ['QB1', 'QB2']},
        points='outliers',
        labels={'ttt': 'Time to throw (s)', 'down': 'Down', 'qb': 'QB'},
        custom_data=['concept', 'opponent', 'result'],
    )
    fig.update_traces(
        hovertemplate=('<b>%{fullData.name}</b><br>'
                       'Down %{x}<br>'
                       'TTT: %{y:.1f} s<br>'
                       'Concept: %{customdata[0]}<br>'
                       'Result: %{customdata[2]}<br>'
                       'Opponent: %{customdata[1]}<extra></extra>'),
    )

    title = ('Time to throw distribution by QB and down'
             if down == 'All'
             else f'Time to throw distribution, down {down}')
    fig.update_layout(title=title, legend_title_text='',
                      boxmode='group')
    fig.update_xaxes(tickmode='array', tickvals=[1, 2, 3, 4])

    # Annotate the median gap on 3rd down if both QBs are present.
    if (down in ('All', 3) and qb == 'Both' and not df.empty):
        third = df[df['down'] == 3]
        if (set(['QB1', 'QB2']) <= set(third['qb'].unique())
                and len(third) > 10):
            qb1_med = third[third['qb'] == 'QB1']['ttt'].median()
            qb2_med    = third[third['qb'] == 'QB2']['ttt'].median()
            gap = qb2_med - qb1_med
            if gap > 0.15:
                fig.add_annotation(
                    text=(f'3rd-down median gap: QB2 holds {gap:.2f} s longer'
                          ' than QB1'),
                    xref='paper', yref='paper', x=0.02, y=1.10,
                    showarrow=False, align='left',
                    font=dict(size=11, color=PALETTE['highlight_neg']),
                )
    return style_figure(fig, height=440)


# ---------- Viz 5: NFL EPA on 3rd-and-long ----------
def build_nfl_epa(nfl):
    """
    Custom lollipop chart of mean EPA per play on 3rd-and-long, with
    top-8 and bottom-8 tier coloring. Locked to competitive snaps
    (0.05 ≤ win prob ≤ 0.95) so garbage time does not skew the rank.
    """
    third_long = nfl[(nfl['down'] == 3) & (nfl['ydstogo'] >= 7) &
                     (nfl['wp'].between(0.05, 0.95)) &
                     (nfl['play_type'].isin(['pass', 'run']))]
    if third_long.empty:
        return empty_figure('No qualifying 3rd-and-long plays in data.')

    lb = (third_long.groupby('posteam')
          .agg(mean_epa=('epa', 'mean'),
               std=('epa', 'std'),
               n=('epa', 'count'))
          .reset_index())
    lb = lb[lb['n'] >= 20].sort_values('mean_epa').reset_index(drop=True)
    if lb.empty:
        return empty_figure('No teams meet the n ≥ 20 threshold.')

    def tier(rank, total):
        if rank >= total - 8: return 'Top 8'
        if rank < 8:          return 'Bottom 8'
        return 'Middle'
    lb['tier'] = [tier(i, len(lb)) for i in range(len(lb))]
    color_map = {'Top 8':    PALETTE['pass'],
                 'Bottom 8': PALETTE['highlight_neg'],
                 'Middle':   PALETTE['neutral']}

    fig = go.Figure()
    # Stems first so dots layer on top.
    for _, row in lb.iterrows():
        fig.add_trace(go.Scatter(
            x=[0, row['mean_epa']], y=[row['posteam'], row['posteam']],
            mode='lines', line=dict(color=color_map[row['tier']], width=2),
            showlegend=False, hoverinfo='skip',
        ))
    # Dots, one trace per tier so the legend is clean.
    for tier_name in ['Top 8', 'Middle', 'Bottom 8']:
        sub = lb[lb['tier'] == tier_name]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub['mean_epa'], y=sub['posteam'], mode='markers',
            marker=dict(color=color_map[tier_name], size=11,
                        line=dict(color='white', width=1)),
            name=tier_name, customdata=sub['n'],
            hovertemplate=('<b>%{y}</b><br>'
                           'Mean EPA: %{x:.3f}<br>'
                           'n = %{customdata}<extra></extra>'),
        ))

    fig.add_vline(x=0, line_dash='dash', line_color='gray', line_width=1)
    fig.update_layout(
        title='NFL 2024 mean EPA per play on 3rd-and-long, competitive snaps',
        xaxis_title='Mean EPA per play',
        yaxis_title='',
        margin=dict(l=60, r=40, t=70, b=50),
    )
    fig.update_yaxes(categoryorder='array',
                     categoryarray=lb['posteam'].tolist())

    # Annotate the leader.
    leader = lb.iloc[-1]
    fig.add_annotation(
        x=leader['mean_epa'], y=leader['posteam'],
        text=f"Leader: {leader['posteam']} (+{leader['mean_epa']:.2f} EPA)",
        showarrow=True, arrowhead=2, ax=-90, ay=0,
        font=dict(size=11, color=PALETTE['highlight_pos']),
        arrowcolor=PALETTE['highlight_pos'], bgcolor='white',
        bordercolor=PALETTE['highlight_pos'], borderwidth=1, borderpad=4,
    )
    return style_figure(fig, height=780)


# ---------- KPI cards ----------
def kpi_cards(wf):
    """Headline numbers shown at the top of the dashboard."""
    pass_3rd = wf[(wf['down'] == 3) & (wf['play_type'] == 'pass')]
    conv_3rd = (wf[wf['down'] == 3]['result']
                .isin(['First Down', 'TD']).mean() * 100)
    rz_conv  = (wf[wf['field'] == 'Red Zone']['result']
                .eq('TD').mean() * 100 if (wf['field'] == 'Red Zone').any()
                else 0.0)
    explosive = (wf['yards'] >= 15).mean() * 100

    cards = [
        ('Total plays charted',  f'{len(wf):,}',     'Hudl, 14 games, 2025-26'),
        ('3rd-down conversion',  f'{conv_3rd:.1f}%', 'first down or TD on 3rd'),
        ('3rd-down pass rate',   f'{len(pass_3rd) / max(len(wf[wf.down==3]), 1) * 100:.1f}%',
                                                    'NFL 2024 sits at ~58%'),
        ('Red-zone TD rate',     f'{rz_conv:.1f}%', 'no RZ package installed'),
        ('Explosive play rate',  f'{explosive:.1f}%', 'yards gained ≥ 15'),
    ]

    return html.Div([
        html.Div([
            html.Div(label, style={'fontSize': '11px',
                                   'color': BRAND['muted'],
                                   'textTransform': 'uppercase',
                                   'letterSpacing': '0.5px'}),
            html.Div(value, style={'fontSize': '24px',
                                   'fontWeight': '700',
                                   'color': BRAND['navy'],
                                   'marginTop': '4px'}),
            html.Div(sub, style={'fontSize': '11px',
                                 'color': BRAND['muted'],
                                 'marginTop': '4px'}),
        ], style={
            'flex': '1', 'minWidth': '160px', 'padding': '14px 18px',
            'background': BRAND['card'], 'border': f"1px solid {BRAND['border']}",
            'borderRadius': '8px', 'borderTop': f"3px solid {BRAND['gold']}",
        })
        for label, value, sub in cards
    ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap',
              'marginBottom': '20px'})


# ============================================================
# DASH APP
# ============================================================
app = Dash(__name__)
app.title = 'Westfield vs NFL · Play-Calling Analytics'
server = app.server  # exposed for Plotly Cloud / Render deployment


# Styling helpers used in the layout.
def chart_card(graph_id, takeaway):
    """Wrap a graph + its takeaway text in a styled card."""
    return html.Div([
        dcc.Graph(id=graph_id, config={'displaylogo': False,
                                       'modeBarButtonsToRemove':
                                       ['lasso2d', 'select2d']}),
        html.Div(takeaway, style={
            'fontSize': '13px', 'color': BRAND['text'],
            'padding': '10px 16px', 'background': '#F1F4F8',
            'borderLeft': f"3px solid {BRAND['gold']}",
            'marginTop': '8px', 'borderRadius': '4px',
        }),
    ], style={
        'background': BRAND['card'], 'padding': '16px',
        'borderRadius': '10px',
        'boxShadow': '0 1px 3px rgba(0,0,0,0.06)',
        'border': f"1px solid {BRAND['border']}",
    })


opponents_in_data = sorted(wf['opponent'].unique().tolist())


app.layout = html.Div([
    # ----------- Header -----------
    html.Div([
        html.Div([
            html.Div('I-590 Data Visualization · Spring 2026',
                     style={'fontSize': '11px', 'color': BRAND['gold'],
                            'letterSpacing': '1.5px',
                            'textTransform': 'uppercase'}),
            html.H1('What Actually Moves the Chains?',
                    style={'margin': '6px 0 4px 0', 'fontWeight': '700',
                           'fontSize': '30px'}),
            html.Div('Westfield Shamrocks high school play-calling vs the '
                     'NFL 2024 benchmark, a coaching tool by Jay R. Kelley',
                     style={'fontSize': '14px', 'opacity': '0.85'}),
        ]),
    ], style={
        'background': BRAND['navy'], 'color': 'white',
        'padding': '24px 32px',
        'borderBottom': f"4px solid {BRAND['gold']}",
    }),

    # ----------- Main body -----------
    html.Div([

        # KPI strip
        kpi_cards(wf),

        # Filter panel
        html.Div([
            html.Div([
                html.Div('Filters', style={
                    'fontSize': '11px', 'color': BRAND['muted'],
                    'letterSpacing': '1px', 'textTransform': 'uppercase',
                    'marginBottom': '8px',
                }),
                html.Div('Down is the shared cross-filter, it drives chart 1 '
                         'and chart 4 simultaneously. QB drives charts 2 and 4. '
                         'Opponent drives charts 2 and 3.',
                         style={'fontSize': '12px',
                                'color': BRAND['muted'],
                                'marginBottom': '14px'}),
            ]),
            html.Div([
                html.Div([
                    html.Label('Down · shared',
                               style={'fontSize': '12px',
                                      'fontWeight': '600',
                                      'color': BRAND['navy'],
                                      'display': 'block',
                                      'marginBottom': '6px'}),
                    dcc.RadioItems(
                        id='down-filter',
                        options=[{'label': l, 'value': v} for l, v in
                                 [('All', 'All'), ('1st', 1), ('2nd', 2),
                                  ('3rd', 3), ('4th', 4)]],
                        value='All', inline=True,
                        labelStyle={'marginRight': '14px',
                                    'fontSize': '13px'},
                        inputStyle={'marginRight': '4px'},
                    ),
                ], style={'flex': '1', 'minWidth': '260px'}),

                html.Div([
                    html.Label('QB',
                               style={'fontSize': '12px',
                                      'fontWeight': '600',
                                      'color': BRAND['navy'],
                                      'display': 'block',
                                      'marginBottom': '6px'}),
                    dcc.RadioItems(
                        id='qb-filter',
                        options=[{'label': l, 'value': v} for l, v in
                                 [('Both', 'Both'),
                                  ('QB1', 'QB1'),
                                  ('QB2', 'QB2')]],
                        value='Both', inline=True,
                        labelStyle={'marginRight': '14px',
                                    'fontSize': '13px'},
                        inputStyle={'marginRight': '4px'},
                    ),
                ], style={'flex': '1', 'minWidth': '260px'}),

                html.Div([
                    html.Label('Opponent',
                               style={'fontSize': '12px',
                                      'fontWeight': '600',
                                      'color': BRAND['navy'],
                                      'display': 'block',
                                      'marginBottom': '6px'}),
                    dcc.Dropdown(
                        id='opp-filter',
                        options=([{'label': 'All opponents', 'value': 'All'}]
                                 + [{'label': o, 'value': o}
                                    for o in opponents_in_data]),
                        value='All', clearable=False,
                        style={'fontSize': '13px'},
                    ),
                ], style={'flex': '1', 'minWidth': '220px'}),
            ], style={'display': 'flex', 'gap': '24px',
                      'flexWrap': 'wrap', 'alignItems': 'flex-end'}),
        ], style={
            'background': BRAND['card'], 'padding': '18px 22px',
            'borderRadius': '10px',
            'border': f"1px solid {BRAND['border']}",
            'marginBottom': '24px',
        }),

        # Chart grid
        html.Div([
            chart_card('chart-passrun',
                       'Westfield throws on roughly 68% of 3rd downs, well '
                       'above the NFL benchmark near 58%, the staff trusts '
                       'the pass game to move the chains.'),
            chart_card('chart-concept',
                       'Baltimore and Four Verts lead the call sheet. Sail '
                       'and Fade convert at single digits across enough reps '
                       'to flag both as cut candidates.'),
        ], style={'display': 'grid',
                  'gridTemplateColumns': 'repeat(auto-fit, minmax(480px, 1fr))',
                  'gap': '20px', 'marginBottom': '20px'}),

        html.Div([
            chart_card('chart-heatmap',
                       'Cells above zero are positive yards per play, the '
                       'Red Zone row stays cold across every quarter, that is '
                       'the season-defining gap to fix in summer install.'),
            chart_card('chart-ttt',
                       'QB2 holds the ball measurably longer than QB1 '
                       'Melvin on 3rd down, that fraction of a second is the '
                       'difference between a clean throw and a sack.'),
        ], style={'display': 'grid',
                  'gridTemplateColumns': 'repeat(auto-fit, minmax(480px, 1fr))',
                  'gap': '20px', 'marginBottom': '20px'}),

        # Full-width NFL leaderboard
        html.Div([
            chart_card('chart-nfl-epa',
                       'Top-8 teams generate clear positive EPA on 3rd-and-long. '
                       'The next install question for Westfield is which '
                       'concepts those top teams lean on, the bridge between '
                       'this benchmark and the call sheet.'),
        ], style={'marginBottom': '24px'}),

        # Methodology footer
        html.Div([
            html.H3('Methodology and design notes',
                    style={'color': BRAND['navy'], 'marginTop': '0'}),
            html.Ul([
                html.Li('Data: 500 plays manually charted from Hudl film across '
                        '14 games of the Westfield 2025-26 varsity season (11-3, '
                        '6A State Runner-Up), paired with 49,492 plays from '
                        'nflverse / nflfastR for the NFL 2024 regular season.'),
                html.Li('Color: Okabe-Ito qualitative palette for categorical '
                        'play types, sequential Teal ramp for ordered '
                        'conversion rates, diverging Red-Blue with zero anchor '
                        'for the heatmap, every encoding tested against a '
                        'deuteranopia simulator.'),
                html.Li('Encoding choices follow Munzner Ch. 5 and Ch. 6: '
                        'position and length are reserved for the most '
                        'important quantitative comparisons (pass share, '
                        'conversion rate, EPA), color carries category or '
                        'magnitude only.'),
                html.Li('Filters: Down is the shared cross-filter, it updates '
                        'the pass-run mix chart and the QB time-to-throw chart '
                        'in a single callback. QB and Opponent layer in '
                        'additional slices on the concept and heatmap views.'),
                html.Li('Rare-concept guard: any concept needs n ≥ 4 reps in '
                        'the current filter slice to appear in the conversion '
                        'chart, this stops 1-for-1 noise from outranking '
                        'real reps. NFL leaderboard uses n ≥ 20 and a win-prob '
                        'filter (0.05 ≤ wp ≤ 0.95) to strip garbage time.'),
            ], style={'fontSize': '13px', 'lineHeight': '1.6',
                      'color': BRAND['text']}),
            html.Div([
                html.Strong('Source code: '),
                'available on request, jekelle@iu.edu · ',
                html.Strong('LinkedIn: '),
                html.A('linkedin.com/in/jay-r-k-b7a0a0164',
                       href='https://linkedin.com/in/jay-r-k-b7a0a0164',
                       target='_blank',
                       style={'color': BRAND['navy']}),
            ], style={'marginTop': '12px', 'fontSize': '12px',
                      'color': BRAND['muted']}),
        ], style={
            'background': BRAND['card'], 'padding': '20px 24px',
            'borderRadius': '10px',
            'border': f"1px solid {BRAND['border']}",
        }),

    ], style={'maxWidth': '1400px', 'margin': '0 auto',
              'padding': '24px 32px'}),

], style={
    'background': BRAND['bg'], 'minHeight': '100vh',
    'fontFamily': FONT_STACK, 'color': BRAND['text'],
})


# ============================================================
# CALLBACKS
# ============================================================
@app.callback(
    [Output('chart-passrun', 'figure'),
     Output('chart-ttt', 'figure')],
    [Input('down-filter', 'value'),
     Input('qb-filter', 'value')],
)
def update_shared_down(down, qb):
    """The shared down filter drives both of these charts in one round trip."""
    return (build_passrun_mix(wf, nfl, down=down),
            build_qb_ttt(wf, down=down, qb=qb))


@app.callback(
    Output('chart-concept', 'figure'),
    [Input('qb-filter', 'value'),
     Input('opp-filter', 'value')],
)
def update_concept(qb, opp):
    return build_concept_success(wf, qb=qb, opponent=opp)


@app.callback(
    Output('chart-heatmap', 'figure'),
    Input('opp-filter', 'value'),
)
def update_heatmap(opp):
    return build_field_heatmap(wf, opponent=opp)


@app.callback(
    Output('chart-nfl-epa', 'figure'),
    Input('down-filter', 'value'),  # accepted but ignored, locked to 3rd-and-long
)
def update_nfl(_):
    return build_nfl_epa(nfl)


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8050)
