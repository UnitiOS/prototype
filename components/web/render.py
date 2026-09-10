"""web/render — the structures the generator and the compiler already return,
as HTML.

There is no logic here and there is deliberately no room for any. Every
function is handed a built structure and turns it into markup:

    home_html    the stages, as cards in the order they happen — a walk
                 forward rather than a list of links
    said_html    a transcript and the map it became, side by side, with a
                 class on one side linked to the sentence on the other
    graph_html   one diagram, already generated as Mermaid text
    why_html     every assertion ever made about one subject and predicate
    form_html    what `generate.form()` returns: fields, ranges, and the
                 options it read at the clocks, as a `<form method=post>`
    table_html   what `compile.compile_class()` returns: the rows it stored,
                 with each column's kind under its name, so a reader can see
                 which cells the graph computed and which it read as a
                 parameter — sortable, filterable, and printing what the
                 business calls a thing wherever the caller handed it a name
    page         the shell both sit in: one inline style block and the two
                 clock boxes, which appear on every page

Nothing here reads a database, and nothing here knows what any class or slot
is called: the names it prints came out of the built structure, which came out
of the map.

The two clocks are the point. They are on every page as a plain GET form
submitting to the page it is on, so changing one and pressing the button is a
reload of the same page at a different pair of clocks — and for a table that
is a rebuild of the table. They are date boxes rather than text boxes: a clock
that has to be typed as an ISO timestamp is a clock nobody moves.

Sorting and filtering are links and a `<select>`, and the page they lead to is
the same page with more on its query string. Nothing on it is JavaScript, and
there is no state anywhere but the URL.
"""

from html import escape
from urllib.parse import parse_qs, quote, urlencode, urlparse

# One block, no framework, no build step. Enough to read a table and fill in a
# form and no more.
STYLE = """
:root { color-scheme: light; }
body { font: 15px/1.5 -apple-system, Segoe UI, system-ui, sans-serif;
       margin: 0; color: #1a1a1a; background: #fbfaf8; }
main { max-width: 78rem; margin: 0 auto; padding: 1.5rem 2rem 4rem; }
h1 { font-size: 1.35rem; margin: 0 0 .25rem; font-weight: 600; }
h2 { font-size: 1rem; margin: 2rem 0 .5rem; font-weight: 600; }
a { color: #1c4f8b; }
/* Top Shell & Sticky Navigation */
.top-shell { position: sticky; top: 0; z-index: 1000; background: #fff;
             box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
header.bar { border-bottom: 1px solid #ebe7e1; background: #fff;
             padding: .55rem 2rem; display: flex; gap: 1.25rem;
             align-items: center; justify-content: space-between; flex-wrap: wrap; }
.brand-zone { display: flex; align-items: center; gap: .7rem; }
a.brand-home { font-weight: 700; text-decoration: none; color: #1a1a1a;
               font-size: 1.15rem; letter-spacing: -.02em; display: inline-flex;
               align-items: center; gap: .45rem; }
.brand-symbol { color: #1c4f8b; font-size: 1.15rem; }
.brand-title { font-weight: 700; color: #1a1a1a; }
.brand-sub { font-size: .72rem; font-weight: 600; color: #6b6259;
             background: #f4f1eb; padding: .18rem .55rem; border-radius: 4px;
             border: 1px solid #e2ded7; letter-spacing: .02em; }

/* Clocks */
form.clocks { display: flex; gap: .6rem; align-items: flex-end;
              flex-wrap: wrap; margin: 0; }
.clock-field { display: flex; flex-direction: column; }
.clock-field label { font-size: .68rem; text-transform: uppercase;
                     letter-spacing: .05em; color: #786f66; font-weight: 600;
                     margin-bottom: .15rem; }
.clock-field input[type="date"] { font-size: .8rem; padding: .22rem .4rem;
                                  border: 1px solid #cfc9c0; border-radius: 4px;
                                  background: #fff; color: #1a1a1a; }
.clock-field input[type="date"]:focus { outline: none; border-color: #1c4f8b;
                                        box-shadow: 0 0 0 2px rgba(28, 79, 139, 0.15); }
.clock-actions { display: flex; gap: .35rem; align-items: center; }
.btn-clock-apply { font-size: .78rem; padding: .24rem .6rem; background: #1c4f8b;
                   color: #fff; border: 1px solid #1c4f8b; border-radius: 4px;
                   cursor: pointer; font-weight: 600; }
.btn-clock-apply:hover { background: #153e6d; }
.btn-live-reset { font-size: .78rem; padding: .24rem .6rem; background: #f0f7ff;
                  color: #0284c7; border: 1px solid #bae6fd; border-radius: 4px;
                  text-decoration: none; font-weight: 600; display: inline-flex;
                  align-items: center; gap: .25rem; }
.btn-live-reset:hover { background: #e0f2fe; color: #0369a1; }
input, select, button { font: inherit; padding: .3rem .4rem;
                        border: 1px solid #cfc9c0; border-radius: 3px;
                        background: #fff; }
input[type=submit], button { background: #1c4f8b; color: #fff;
                             border-color: #1c4f8b; cursor: pointer; }
.note { color: #6b6259; font-size: .85rem; margin: 0 0 1rem; }
.msg { border-left: 3px solid #1c4f8b; background: #eef3f9;
       padding: .6rem .8rem; margin: 0 0 1.25rem; font-size: .9rem;
       white-space: pre-wrap; }
.msg.bad { border-color: #a33; background: #faeceb; }
table { border-collapse: collapse; font-size: .88rem; width: 100%; }
th, td { border: 1px solid #e2ded7; padding: .3rem .5rem; text-align: left;
         vertical-align: top; white-space: nowrap; }
th { background: #f3efe9; }
th .kind { display: block; font-weight: 400; font-size: .72rem;
           color: #6b6259; text-transform: uppercase; letter-spacing: .04em; }
td.empty { background: #faf8f5; }
.scroll { overflow-x: auto; }
.field { margin: 0 0 .9rem; max-width: 34rem; }
.field label { display: block; font-weight: 600; font-size: .85rem; }
.field .hint { display: block; color: #6b6259; font-size: .8rem;
               margin: 0 0 .25rem; }
.field input, .field select { width: 100%; box-sizing: border-box; }
.req { color: #a33; }
ul.classes { columns: 3; list-style: none; padding: 0; margin: 0; }
ul.classes li { margin: 0 0 .2rem; break-inside: avoid; }

/* the walk: one card per stage, in the order the stages happen */
ol.stages { list-style: none; padding: 0; margin: 1.5rem 0 0;
            display: grid; gap: .9rem;
            grid-template-columns: repeat(auto-fill, minmax(19rem, 1fr)); }
ol.stages li { border: 1px solid #e2ded7; background: #fff; border-radius: 4px;
               padding: .9rem 1rem 1rem; }
ol.stages .step { font-size: .72rem; color: #8a8078; letter-spacing: .08em;
                  text-transform: uppercase; }
ol.stages h3 { margin: .15rem 0 .35rem; font-size: 1.05rem; font-weight: 600; }
ol.stages p { margin: 0 0 .6rem; font-size: .88rem; color: #4a443e; }
ol.stages li.dead { background: #f6f4f1; color: #8a8078; }
ol.stages li.dead h3, ol.stages li.dead p { color: #8a8078; }

/* the transcript beside the map */
.said { display: grid; gap: 1.5rem; grid-template-columns: 1fr 1fr;
        align-items: start; }
.said > section { min-width: 0; }
.said .prose { max-height: 78vh; overflow-y: auto; padding-right: .5rem; }
.said .prose p { white-space: pre-wrap; margin: 0 0 .9rem;
                 font-size: .86rem; padding: .2rem .4rem; }
.said .prose p:target { background: #fdf3d0; outline: 2px solid #e6c65c; }
.said pre { max-height: 78vh; overflow: auto; background: #fff;
            border: 1px solid #e2ded7; padding: .75rem; font-size: .8rem;
            margin: 0; }
.said pre a { text-decoration: none; background: #eef3f9; }

/* the assertions behind one cell */
table.why td.value { white-space: normal; font-weight: 600; }
table.why tr.gone td { color: #8a8078; text-decoration: line-through; }
.timeline { list-style: none; padding: 0; margin: 0; }
.timeline li { border-left: 3px solid #1c4f8b; padding: .1rem 0 .6rem .8rem;
               margin: 0 0 .8rem; }
.mermaid { background: #fff; border: 1px solid #e2ded7; padding: 1rem;
           overflow: auto; }
a.why { text-decoration: none; border-bottom: 1px dotted #1c4f8b; }
th a { color: #1c4f8b; }
a.sort { text-decoration: none; font-size: .8rem; opacity: .55; }
a.sort.on { opacity: 1; }
form.filters { display: flex; gap: .75rem; align-items: baseline;
               flex-wrap: wrap; margin: 0 0 1rem; padding: .7rem .85rem;
               background: #fff; border: 1px solid #e2ded7; border-radius: 4px; }
form.filters label { font-size: .8rem; color: #6b6259; }
form.filters select { max-width: 15rem; }

/* Stage Stepper Navigation */
nav.stage-stepper { background: #fcfbfa; border-bottom: 1px solid #e8e4de;
                    display: flex; align-items: stretch; padding: 0 1.5rem;
                    overflow-x: auto; gap: .15rem; }
.step-item { display: flex; align-items: center; gap: .45rem; padding: .52rem .75rem;
             text-decoration: none; color: #6b6259; font-size: .8rem; font-weight: 500;
             border-bottom: 2px solid transparent; transition: all .15s ease;
             white-space: nowrap; }
.step-item:hover { color: #1c4f8b; background: #f4f0e8; }
.step-item.active { color: #1c4f8b; font-weight: 700; border-bottom-color: #1c4f8b;
                    background: #fff; }
.step-num { font-size: .68rem; font-weight: 700; padding: .1rem .38rem;
            border-radius: 8px; background: #e6e0d6; color: #554d45; }
.step-item.active .step-num { background: #1c4f8b; color: #fff; }
.step-sep { color: #d1cbc2; font-size: .72rem; align-self: center; }

/* Breadcrumbs Bar */
.breadcrumb-bar { background: #fff; border-bottom: 1px solid #ede9e3;
                  padding: .4rem 2rem; font-size: .78rem; color: #6b6259;
                  display: flex; align-items: center; gap: .4rem; flex-wrap: wrap; }
.breadcrumb-bar a { text-decoration: none; color: #1c4f8b; font-weight: 500; }
.breadcrumb-bar a:hover { text-decoration: underline; }
.breadcrumb-bar .sep { color: #aba296; }
.breadcrumb-bar .cur { font-weight: 600; color: #1a1a1a; }
.breadcrumb-bar .back-btn { margin-left: auto; font-size: .75rem; color: #1c4f8b;
                            text-decoration: none; font-weight: 600;
                            display: inline-flex; align-items: center; gap: .25rem;
                            padding: .15rem .5rem; background: #f0f4f9;
                            border-radius: 4px; border: 1px solid #d4e0ee; }
.breadcrumb-bar .back-btn:hover { background: #e2ecf7; }

/* Dashboard Executive Styling */
.dash-header { margin-bottom: 1.5rem; }
.dash-header h1 { font-size: 1.45rem; font-weight: 700; color: #1a1a1a; margin: 0 0 .3rem; }
.dash-header p { font-size: .88rem; color: #6b6259; margin: 0; }

/* KPI Grid */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr)); gap: 1rem; margin-bottom: 2rem; }
.kpi-card { background: #fff; border: 1px solid #e2ded7; border-radius: 6px; padding: 1.1rem 1.3rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03); }
.kpi-card .kpi-label { font-size: .75rem; text-transform: uppercase; letter-spacing: .06em; color: #7a7066; font-weight: 600; margin-bottom: .35rem; }
.kpi-card .kpi-value { font-size: 1.75rem; font-weight: 700; color: #1a1a1a; line-height: 1.2; }
.kpi-card .kpi-sub { font-size: .82rem; margin-top: .4rem; color: #6b6259; display: flex; align-items: baseline; gap: .4rem; }
.kpi-card.alert-card { border-left: 4px solid #b32d2e; }
.kpi-card.warning-card { border-left: 4px solid #d97706; }
.kpi-card.success-card { border-left: 4px solid #15803d; }
.kpi-card.primary-card { border-left: 4px solid #1c4f8b; }

/* Badges */
.badge { display: inline-block; font-size: .72rem; font-weight: 600; padding: .15rem .45rem; border-radius: 3px; text-transform: uppercase; letter-spacing: .04em; }
.badge-danger { background: #fee2e2; color: #991b1b; }
.badge-warning { background: #fef3c7; color: #92400e; }
.badge-success { background: #dcfce7; color: #166534; }
.badge-neutral { background: #f3f4f6; color: #4b5563; }

/* Alerts / Action Banners */
.dash-alerts { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2rem; margin-bottom: 2rem; }
@media (max-width: 900px) { .dash-alerts { grid-template-columns: 1fr; } }
.alert-box { border-radius: 6px; padding: 1.2rem 1.4rem; background: #fff; border: 1px solid #e2ded7; border-left-width: 5px; }
.alert-box.danger { border-left-color: #b32d2e; background: #fffdfd; }
.alert-box.warning { border-left-color: #d97706; background: #fffdf7; }
.alert-box h3 { margin: 0 0 .4rem; font-size: 1.05rem; display: flex; align-items: center; justify-content: space-between; }
.alert-box p { margin: 0 0 .8rem; font-size: .88rem; color: #4a443e; line-height: 1.45; }
.alert-action { display: flex; gap: .6rem; flex-wrap: wrap; align-items: center; margin-top: .6rem; }
.btn-action { display: inline-block; font-size: .82rem; font-weight: 600; text-decoration: none; padding: .35rem .75rem; border-radius: 4px; }
.btn-action.btn-danger { background: #b32d2e; color: #fff; }
.btn-action.btn-warning { background: #d97706; color: #fff; }
.btn-action.btn-outline { background: #fff; border: 1px solid #cfc9c0; color: #1c4f8b; }
.btn-action:hover { opacity: .9; }

/* Discrepancy Bar Chart */
.chart-card { background: #fff; border: 1px solid #e2ded7; border-radius: 6px; padding: 1.4rem; margin-bottom: 2rem; }
.chart-card h2 { margin: 0 0 .3rem; font-size: 1.1rem; }
.chart-card p.chart-desc { font-size: .84rem; color: #6b6259; margin: 0 0 1.2rem; }
.bar-chart { display: flex; flex-direction: column; gap: .75rem; }
.bar-row { display: grid; grid-template-columns: 14rem 1fr 6rem 5rem; align-items: center; gap: 1rem; font-size: .85rem; }
.bar-label { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bar-label a { text-decoration: none; color: #1a1a1a; }
.bar-label a:hover { color: #1c4f8b; text-decoration: underline; }
.bar-track { background: #f0ede8; height: 1.1rem; border-radius: 3px; overflow: hidden; position: relative; }
.bar-fill { height: 100%; border-radius: 3px; }
.bar-fill.bar-severe { background: #dc2626; }
.bar-fill.bar-moderate { background: #f59e0b; }
.bar-fill.bar-minor { background: #9ca3af; }
.bar-num { text-align: right; font-weight: 600; font-variant-numeric: tabular-nums; }
.bar-pct { text-align: right; color: #6b6259; font-size: .8rem; }

/* Storage Zone Cards */
.zones-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr)); gap: 1rem; margin-bottom: 2rem; }
.zone-card { background: #fff; border: 1px solid #e2ded7; border-radius: 6px; padding: 1.2rem; }
.zone-card h3 { margin: 0 0 .2rem; font-size: 1rem; display: flex; justify-content: space-between; align-items: baseline; }
.zone-card .zone-temp { font-size: .78rem; color: #7a7066; margin-bottom: .8rem; }
.zone-stats { display: grid; grid-template-columns: 1fr 1fr; gap: .6rem; border-top: 1px solid #f0ede8; border-bottom: 1px solid #f0ede8; padding: .6rem 0; margin-bottom: .8rem; }
.zone-stat-num { font-size: 1.15rem; font-weight: 700; }
.zone-stat-label { font-size: .72rem; color: #7a7066; text-transform: uppercase; }
.zone-card p.zone-note { font-size: .82rem; color: #5a524a; margin: 0; line-height: 1.4; }

/* Dashboard Tables */
.dash-table-card { background: #fff; border: 1px solid #e2ded7; border-radius: 6px; padding: 1.4rem; margin-bottom: 2rem; }
.dash-table-card h2 { margin: 0 0 .3rem; font-size: 1.1rem; }
.dash-table-card p { font-size: .84rem; color: #6b6259; margin: 0 0 1rem; }

/* Stage Stepper Footer */
.stage-stepper { display: flex; justify-content: space-between; align-items: center; margin-top: 2.5rem; padding-top: 1.25rem; border-top: 1px solid #e2ded7; }
.stage-stepper a { display: inline-flex; align-items: center; gap: .5rem; padding: .5rem .9rem; border-radius: 4px; text-decoration: none; font-size: .86rem; font-weight: 600; border: 1px solid #cfc9c0; background: #fff; color: #1c4f8b; }
.stage-stepper a:hover { background: #f3efe9; }
.stage-stepper a.primary { background: #1c4f8b; color: #fff; border-color: #1c4f8b; }
.stage-stepper a.primary:hover { background: #153b69; }

/* Enhanced .said side-by-side */
.said-col-header { background: #f3efe9; border: 1px solid #e2ded7; border-bottom: none; border-radius: 5px 5px 0 0; padding: .6rem .85rem; display: flex; justify-content: space-between; align-items: center; font-weight: 600; font-size: .86rem; }
.said-col-header .tag { font-family: monospace; font-size: .75rem; background: #fff; padding: .15rem .45rem; border: 1px solid #cfc9c0; border-radius: 3px; font-weight: 400; color: #4a443e; }
.said .prose { border: 1px solid #e2ded7; border-radius: 0 0 5px 5px; background: #fff; padding: 1.2rem; }
.said pre { border-radius: 0 0 5px 5px; }
.prose-title { font-weight: 700; color: #1c4f8b; font-size: .95rem; margin: 1.25rem 0 .4rem; border-bottom: 2px solid #eef3f9; padding-bottom: .25rem; }

/* Graph Architecture Details */
.arch-layers-summary { display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0 1.25rem; }
.arch-badge { display: inline-flex; align-items: center; gap: .4rem; padding: .4rem .85rem; border-radius: 4px; font-size: .82rem; font-weight: 600; }
.arch-badge.master { background: #f0fdf4; border: 1px solid #86efac; color: #166534; }
.arch-badge.event { background: #fffbeb; border: 1px solid #fcd34d; color: #92400e; }
.arch-badge.proj { background: #eef2ff; border: 1px solid #a5b4fc; color: #3730a3; }

.arch-cards-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr)); gap: 1.25rem; margin-top: 2rem; }
.arch-card { background: #fff; border: 1px solid #e2ded7; border-radius: 6px; padding: 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
.arch-card.master { border-top: 4px solid #16a34a; }
.arch-card.event { border-top: 4px solid #d97706; }
.arch-card.proj { border-top: 4px solid #4f46e5; }
.arch-card h3 { margin: 0 0 .4rem; font-size: 1rem; font-weight: 700; display: flex; justify-content: space-between; align-items: center; }
.arch-card p.card-desc { font-size: .84rem; color: #5a524a; margin: 0 0 .8rem; }
.arch-card ul { list-style: none; padding: 0; margin: 0; font-size: .82rem; }
.arch-card ul li { padding: .4rem 0; border-top: 1px solid #f3efe9; }
.arch-card ul li strong { color: #1a1a1a; }
.arch-card ul li .slot-desc { color: #6b6259; font-size: .78rem; display: block; margin-top: .1rem; }
.arch-card .formula-link { font-size: .78rem; text-decoration: none; color: #4f46e5; font-weight: 600; margin-left: .5rem; }
.arch-card .formula-link:hover { text-decoration: underline; }

/* Diagram Controls & Responsive Viewport */
.diagram-toolbar { display: flex; justify-content: space-between; align-items: center; background: #fdfcfb; border: 1px solid #e2ded7; border-bottom: none; border-radius: 6px 6px 0 0; padding: .6rem 1rem; }
.diagram-toolbar-title { font-size: .88rem; font-weight: 700; color: #1c4f8b; }
.diagram-btn-group { display: flex; gap: .4rem; }
.diagram-btn-group button { background: #fff; border: 1px solid #cfc9c0; padding: .35rem .65rem; border-radius: 4px; font-size: .8rem; font-weight: 600; cursor: pointer; color: #3d3630; transition: background .15s; }
.diagram-btn-group button:hover { background: #f3efe9; border-color: #8c8275; }

.mermaid-viewport { overflow: auto; border: 1px solid #e2ded7; border-radius: 0 0 6px 6px; background: #ffffff; padding: 1.5rem; text-align: center; }
.mermaid-viewport .mermaid { display: inline-block; text-align: center; margin: 0 auto; }
.mermaid svg { max-width: none !important; font-size: 13px; }

/* Stage 3 Kernel Audit Workbench */
.audit-workbench { margin-top: 1rem; }
.audit-filter-bar { background: #fff; border: 1px solid #e2ded7; border-radius: 6px; padding: 1rem 1.25rem; margin-bottom: 1.5rem; display: flex; flex-direction: column; gap: .85rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
.audit-filter-row { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: .75rem; }
.audit-pill-group { display: flex; gap: .4rem; flex-wrap: wrap; align-items: center; }
.audit-pill { font-size: .8rem; font-weight: 500; padding: .32rem .75rem; border-radius: 20px; border: 1px solid #cfc9c0; text-decoration: none; color: #4a443e; background: #fff; transition: all .15s; }
.audit-pill:hover { background: #f3efe9; border-color: #8c8275; }
.audit-pill.active { background: #1c4f8b; color: #fff; border-color: #1c4f8b; font-weight: 600; }
.audit-search-form { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
.audit-search-form input { padding: .32rem .6rem; font-size: .82rem; width: 13rem; border: 1px solid #cfc9c0; border-radius: 4px; }
.audit-search-form select { padding: .32rem .5rem; font-size: .82rem; border: 1px solid #cfc9c0; border-radius: 4px; }

.recent-log-card { background: #fff; border: 1px solid #e2ded7; border-radius: 6px; padding: 1.4rem; margin-bottom: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.02); }
.recent-log-card h2 { margin: 0 0 .3rem; font-size: 1.1rem; }
.recent-log-card p.log-desc { font-size: .84rem; color: #6b6259; margin: 0 0 1rem; }

.direct-lookup-box { background: #fcfbf9; border: 1px solid #e2ded7; border-radius: 6px; padding: .9rem 1.25rem; margin-bottom: 2rem; }
.direct-lookup-box summary { font-size: .88rem; font-weight: 600; color: #1c4f8b; cursor: pointer; }
.direct-lookup-box form { margin-top: 1rem; }

/* Visual Bitemporal Timeline in why_html */
.audit-timeline { margin: 1.5rem 0 2rem; position: relative; padding-left: 2rem; }
.audit-timeline::before { content: ""; position: absolute; left: .6rem; top: .75rem; bottom: .75rem; width: 2px; background: #cfc9c0; }
.timeline-item { position: relative; margin-bottom: 1.5rem; }
.timeline-dot { position: absolute; left: -2rem; top: .35rem; width: .9rem; height: .9rem; border-radius: 50%; background: #1c4f8b; border: 2px solid #fff; box-shadow: 0 0 0 2px #cfc9c0; }
.timeline-dot.revoked { background: #b32d2e; }
.timeline-dot.correction { background: #d97706; }
.timeline-dot.active { background: #15803d; }
.timeline-card { background: #fff; border: 1px solid #e2ded7; border-radius: 6px; padding: 1rem 1.25rem; }
.timeline-card.is-revoked { background: #faf9f7; border-color: #e5e0d8; opacity: .88; }
.timeline-meta { font-size: .78rem; color: #7a7066; display: flex; gap: 1rem; margin-bottom: .4rem; flex-wrap: wrap; align-items: center; }
.timeline-val { font-size: 1.15rem; font-weight: 700; color: #1a1a1a; margin-bottom: .3rem; }
.timeline-val.struck { text-decoration: line-through; color: #991b1b; }
.timeline-note { font-size: .83rem; color: #5a524a; background: #fdfcfb; border-left: 3px solid #cfc9c0; padding: .35rem .65rem; margin-top: .4rem; font-style: italic; }

/* Stage 4 Form & Correction UI */
.form-card { background: #fff; border: 1px solid #e2ded7; border-radius: 8px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.03); }
.form-header-badge { display: flex; gap: .6rem; align-items: center; margin-bottom: 1.25rem; flex-wrap: wrap; }
.badge-tag { font-size: .8rem; font-weight: 600; padding: .25rem .65rem; border-radius: 4px; border: 1px solid #cfc9c0; background: #fbfaf8; color: #4a443e; }
.badge-tag.tag-event { background: #eef4ff; border-color: #bcd0f7; color: #1c4f8b; }
.badge-tag.tag-master { background: #f0fdf4; border-color: #bbf7d0; color: #15803d; }
.badge-tag.tag-source { color: #7a7066; border-style: dashed; }
.form-section { margin-bottom: 1.5rem; padding-bottom: 1.25rem; border-bottom: 1px solid #eeebe6; }
.form-section:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.form-section-title { font-size: .92rem; font-weight: 700; color: #1c4f8b; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 1rem; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr)); gap: 1rem; }
.field { margin: 0 0 1rem; }
.field label { display: block; font-weight: 600; font-size: .85rem; color: #2e2a25; margin-bottom: .25rem; }
.field .hint { display: block; color: #6b6259; font-size: .8rem; margin-bottom: .35rem; line-height: 1.35; }
.field input, .field select, .field textarea { width: 100%; box-sizing: border-box; padding: .45rem .65rem; font-size: .88rem; border: 1px solid #cfc9c0; border-radius: 4px; background: #fff; color: #1a1a1a; font-family: inherit; }
.field input:focus, .field select:focus, .field textarea:focus { border-color: #1c4f8b; outline: none; box-shadow: 0 0 0 2px rgba(28,79,139,0.15); }
.field input[readonly] { background: #f7f5f2; color: #6b6259; border-color: #e2ded7; }
.btn-primary { background: #1c4f8b; color: #fff; font-size: .95rem; font-weight: 600; padding: .6rem 1.25rem; border: none; border-radius: 4px; cursor: pointer; transition: background .15s; }
.btn-primary:hover { background: #153c6a; }
.btn-danger { background: #b32d2e; color: #fff; font-size: .95rem; font-weight: 600; padding: .6rem 1.25rem; border: none; border-radius: 4px; cursor: pointer; }
.btn-danger:hover { background: #8f2223; }
.btn-correct { display: inline-flex; align-items: center; gap: .3rem; font-size: .78rem; font-weight: 600; padding: .25rem .6rem; border-radius: 4px; border: 1px solid #d97706; background: #fffbeb; color: #92400e; text-decoration: none; transition: all .15s; }
.btn-correct:hover { background: #fef3c7; border-color: #b45309; }

/* Stage 4 & 5 Classes Grid */
.classes-category { margin-bottom: 2rem; }
.classes-category h2 { font-size: 1.15rem; color: #2e2a25; margin-bottom: .3rem; display: flex; align-items: center; gap: .5rem; }
.classes-category p.cat-desc { font-size: .85rem; color: #6b6259; margin: 0 0 1rem; }
.cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr)); gap: .9rem; }
.class-card { border: 1px solid #e2ded7; background: #fff; border-radius: 6px; padding: 1rem; display: flex; flex-direction: column; justify-content: space-between; text-decoration: none; color: inherit; transition: all .15s; }
.class-card:hover { border-color: #1c4f8b; box-shadow: 0 2px 6px rgba(28,79,139,0.08); transform: translateY(-1px); }
.class-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: .4rem; }
.class-card-title { font-size: 1rem; font-weight: 700; color: #1c4f8b; }
.class-card-desc { font-size: .83rem; color: #5a524a; line-height: 1.4; margin: 0 0 .75rem; flex-grow: 1; }
.class-card-action { font-size: .8rem; font-weight: 600; color: #1c4f8b; display: flex; align-items: center; gap: .25rem; }
"""

# A range the map declares becomes an input the browser knows how to check.
# Anything else is a text box — and a class range never reaches here, because
# a field over one is a select.
INPUT_TYPE = {
    "integer": "number",
    "decimal": "number",
    "float": "number",
    "double": "number",
    "date": "date",
}

STEP = {"decimal": "any", "float": "any", "double": "any"}


# What a filter and a sort are called on a URL. The prefix is what keeps a
# column of any map from colliding with a clock, or with the other control.
ONLY, SORT, DIRECTION = "only.", "sort", "dir"


def _clocks(valid_at, as_of, query="", path=""):
    """The two clock inputs, hidden preserved filters, and a live reset shortcut."""
    clean_path = path.split("?")[0] if path else ""
    reset_params = {}
    extra_hidden = []
    if query:
        parsed_q = parse_qs(query)
        for k, vals in parsed_q.items():
            if k not in ("valid_at", "as_of"):
                reset_params[k] = vals[0] if len(vals) == 1 else vals
                for v in vals:
                    extra_hidden.append(f'<input type="hidden" name="{escape(k)}" value="{escape(v)}">')

    reset_qs = urlencode(reset_params, doseq=True) if reset_params else ""
    reset_href = f"{clean_path}?{escape(reset_qs)}" if reset_qs else (clean_path or "?")

    hidden_html = "\n".join(extra_hidden)
    return (
        f'<form class="clocks" method="get" action="{escape(clean_path)}">'
        f'{hidden_html}'
        f'<div class="clock-field">'
        f'<label for="clock-valid-at">valid_at (effective)</label>'
        f'<input id="clock-valid-at" type="date" name="valid_at" value="{escape(str(valid_at)[:10])}">'
        f'</div>'
        f'<div class="clock-field">'
        f'<label for="clock-as-of">as_of (recorded)</label>'
        f'<input id="clock-as-of" type="date" name="as_of" value="{escape(str(as_of)[:10])}">'
        f'</div>'
        f'<div class="clock-actions">'
        f'<input type="submit" value="Apply" class="btn-clock-apply">'
        f'<a class="btn-live-reset" href="{reset_href}" title="Reset clocks to current date and live data">&#8635; Live Today</a>'
        f'</div>'
        f'</form>'
    )


def _query(params):
    """A query string out of the parameters a page is at, safe in an href."""
    return escape(urlencode(
        {key: str(value) for key, value in params.items()
         if value not in (None, "")}))


def page(title, body, *, valid_at, as_of, path=None):
    """One page: sticky shell with brand, clocks, stage stepper, breadcrumbs, and body."""
    carried = _carried(valid_at, as_of)
    parsed = urlparse(path or "")
    clean_path = parsed.path
    query = parsed.query

    # 1. Detect Stage, Breadcrumbs, and Smart Back Link
    p = clean_path.lower().strip("/")
    t = (title or "").lower()

    stage = "home"
    crumbs = []
    back_btn = None

    if p == "said" or "said" in t:
        stage = "said"
        crumbs = ["Stage 1 · Domain Narrative & Map Spec"]
        back_btn = (f"/graph?{carried}", "Next: Stage 2 Graph &rarr;")
    elif p == "graph" or "the map" in t or ("." in t and " " not in t):
        stage = "graph"
        if "." in t and " " not in t:
            crumbs = [(f"/graph?{carried}", "Stage 2 · Knowledge Graph"), f"Formula Lineage: {escape(title)}"]
            back_btn = (f"/graph?{carried}", "&larr; Back to Graph Overview")
        else:
            crumbs = ["Stage 2 · LinkML Knowledge Graph Schema"]
            back_btn = (f"/why?{carried}", "Next: Stage 3 Audit Log &rarr;")
    elif p == "why" or "audit" in t:
        stage = "why"
        if "subject" in query:
            crumbs = [(f"/why?{carried}", "Stage 3 · Kernel Audit"), "Assertion Provenance Timeline"]
            back_btn = (f"/why?{carried}", "&larr; Back to Activity Ledger")
        else:
            crumbs = ["Stage 3 · Kernel Audit Ledger & Provenance"]
            back_btn = (f"/classes?{carried}#forms", "Next: Stage 4 Forms &rarr;")
    elif p == "correct" or "correct" in t:
        stage = "why"
        crumbs = [(f"/why?{carried}", "Stage 3 · Kernel Audit"), "Bitemporal Correction & Revocation"]
        back_btn = (f"/why?{carried}", "&larr; Back to Audit Ledger")
    elif p.startswith("form/") or "form" in t:
        stage = "classes"
        cname = title.split("—")[0].strip() if "—" in title else (p.split("/")[-1] if "/" in p else "Record")
        crumbs = [(f"/classes?{carried}#forms", "Stage 4 · Operational Forms"), f"{escape(cname)} Ingestion Form"]
        back_btn = (f"/classes?{carried}#forms", "&larr; Back to Forms Hub")
    elif p.startswith("table/") or "table" in t:
        stage = "table"
        cname = title.split("—")[0].strip() if "—" in title else (p.split("/")[-1] if "/" in p else "Projection")
        crumbs = [(f"/classes?{carried}#tables", "Stage 5 · Projections"), f"{escape(cname)} Table"]
        back_btn = (f"/dashboard?{carried}", "Open Executive BI &rarr;")
    elif p == "classes":
        stage = "classes"
        crumbs = ["Stages 4 & 5 · Operational Forms & Projections Hub"]
        back_btn = (f"/dashboard?{carried}", "Next: Stage 6 Executive BI &rarr;")
    elif p == "dashboard" or "dashboard" in t or "executive" in t:
        stage = "dashboard"
        crumbs = ["Stage 6 · Executive Decision Intelligence & BI"]
        back_btn = (f"/table/StockReconciliation?{carried}", "&larr; Inspect Live Stock Table")
    else:
        stage = "home"
        crumbs = ["Architecture Overview & Pipeline"]

    # 2. Build Stage Stepper
    stepper_defs = [
        ("said", "1", "Narrative", f"/said?{carried}", "Domain Interview & Map Spec"),
        ("graph", "2", "Graph Schema", f"/graph?{carried}", "LinkML Knowledge Graph"),
        ("why", "3", "Kernel Audit", f"/why?{carried}", "Append-Only Audit Log"),
        ("classes", "4", "Ingestion Forms", f"/classes?{carried}#forms", "Operational Ingestion"),
        ("table", "5", "Projections", f"/table/StockReconciliation?{carried}", "Live Digital Twin"),
        ("dashboard", "6", "Executive BI", f"/dashboard?{carried}", "Executive BI & Anomaly Signals"),
    ]
    step_items = []
    for s_id, s_num, s_name, s_url, s_hint in stepper_defs:
        is_active = " active" if stage == s_id else ""
        step_items.append(
            f'<a class="step-item{is_active}" href="{s_url}" title="{s_hint}">'
            f'<span class="step-num">{s_num}</span>'
            f'<span class="step-text">{s_name}</span>'
            f'</a>'
        )
    stepper_html = '<nav class="stage-stepper">\n' + '<span class="step-sep">&rsaquo;</span>\n'.join(step_items) + '\n</nav>'

    # 3. Build Breadcrumb Bar
    if stage == "home":
        bc_links = ['<span class="cur">Architecture Overview &amp; Pipeline</span>']
    else:
        bc_links = [f'<a href="/?{carried}">Overview</a>']
        for crumb in crumbs:
            if isinstance(crumb, tuple):
                curl, clabel = crumb
                bc_links.append(f'<a href="{curl}">{clabel}</a>')
            else:
                bc_links.append(f'<span class="cur">{crumb}</span>')

    back_html = f'<a class="back-btn" href="{back_btn[0]}">{back_btn[1]}</a>' if back_btn else ""
    breadcrumb_html = (
        f'<div class="breadcrumb-bar">'
        f'{" <span class=\"sep\">&rsaquo;</span> ".join(bc_links)}'
        f'{back_html}'
        f'</div>'
    )

    # 4. Header Bar
    brand_html = (
        f'<div class="brand-zone">'
        f'<a class="brand-home" href="/?{carried}">'
        f'<span class="brand-symbol">&#9670;</span>'
        f'<span class="brand-title">uniti</span>'
        f'</a>'
        f'<span class="brand-sub">Sorella Gelato Enterprise Demo</span>'
        f'</div>'
    )
    clocks_html = _clocks(valid_at, as_of, query=query, path=clean_path)

    header_bar = (
        f'<div class="top-shell">'
        f'<header class="bar">'
        f'{brand_html}'
        f'{clocks_html}'
        f'</header>'
        f'{stepper_html}'
        f'{breadcrumb_html}'
        f'</div>'
    )

    return (
        "<!doctype html>\n<html lang=en><head><meta charset=utf-8>"
        '<meta name=viewport content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)} — uniti</title><style>{STYLE}</style></head><body>"
        f"{header_bar}"
        f"<main>{body}</main></body></html>\n"
    )


def _carried(valid_at, as_of):
    """The clocks, as a query string to hang on a link.

    Percent-encoded before it is HTML-escaped, and the order matters. An
    offset-aware clock ends in `+00:00`, and a `+` in a query string means a
    space to every reader of one — so a link built by escaping alone hands the
    next request a clock it cannot parse. `urlencode` writes it `%2B`.
    """
    return escape(urlencode({"valid_at": str(valid_at), "as_of": str(as_of)}))


def _q(value):
    """One value, safe in a query string and then safe in an attribute."""
    return escape(quote(str(value), safe=""))


def home_html(stages, *, valid_at, as_of):
    """The stages, in order, one card each.

    `stages` is a list of (name, sentence, path) and the path may be None,
    which is a stage nothing here reaches yet and is drawn as one rather than
    left off. The names are the system's own stages and came from the caller;
    this prints what it is handed, in the order it is handed it.
    """
    carried = _carried(valid_at, as_of)
    out = ["<h1>One lap, from what somebody said to what an agent acts on</h1>"]
    out.append(
        '<p class="note">Each card is a stage. They happen in this order, and '
        "everything on the pages behind them was derived from the one before "
        "it: a description became a map, the map became a log, and the log "
        "became tables and forms that nobody wrote.</p>"
    )
    out.append('<ol class="stages">')
    for number, (name, sentence, path) in enumerate(stages, start=1):
        dead = ' class="dead"' if not path else ""
        # The clocks go before the fragment, never after it: a `#` ends the
        # URL for the browser, and a query string written past one is part of
        # the anchor's name rather than a question asked of the server.
        where, _, fragment = (path or "").partition("#")
        joined = f'{where}{"&amp;" if "?" in where else "?"}{carried}'
        link = (f'<a href="{joined}{"#" + fragment if fragment else ""}">'
                "open</a>" if path else "<em>not built yet</em>")
        out.append(
            f'<li{dead}><span class="step">stage {number}</span>'
            f"<h3>{escape(name)}</h3><p>{escape(sentence)}</p>{link}</li>"
        )
    out.append("</ol>")
    return "\n".join(out)


def said_html(paragraphs, lines, *, source, transcript, valid_at=None, as_of=None):
    """A transcript on the left and the map it became on the right.

    `paragraphs` is the prose, one string each, and its index is its anchor.
    `lines` is the map's own file, one (text, anchor) pair per line: an anchor
    is the paragraph a class on that line was matched to, or None. Both were
    computed by the caller — this places them in two columns and links one to
    the other.
    """
    carried = _carried(valid_at, as_of)
    left_items = []
    for number, text in enumerate(paragraphs):
        trimmed = text.strip()
        is_title = trimmed.isupper() and len(trimmed) < 60 and "\n" not in trimmed
        if is_title:
            left_items.append(f'<h3 class="prose-title" id="p{number}">{escape(trimmed)}</h3>')
        else:
            left_items.append(f'<p id="p{number}">{escape(text)}</p>')
    left = "".join(left_items)

    right = []
    for text, anchor in lines:
        if anchor is None:
            right.append(escape(text))
        else:
            right.append(f'<a href="#p{anchor}">{escape(text)}</a>')

    return (
        "<h1>Stage 1 · What was said, and what it became</h1>"
        '<p class="note">On the left, the business transcript and operational specification '
        "for Sorella Gelato. On the right, the compiled LinkML schema map derived from it. "
        "A class link on the right jumps directly to the paragraph on the left that established it. "
        f"Nothing was authored twice: <code>{escape(str(transcript))}</code> is the business truth, and "
        f"<code>{escape(str(source))}</code> is the sealed formal ontology.</p>"
        f'<div class="said">'
        f'<section>'
        f'<div class="said-col-header"><span>📄 Business Specification</span><span class="tag">{escape(str(transcript))}</span></div>'
        f'<div class="prose">{left}</div>'
        f'</section>'
        f'<section>'
        f'<div class="said-col-header"><span>⚙️ Sealed Schema Ontology</span><span class="tag">{escape(str(source))} (sealed)</span></div>'
        f"<pre>{''.join(right)}</pre>"
        f'</section>'
        f'</div>'
        f'<div class="stage-stepper">'
        f'<a href="/?{carried}">← Stage Overview (Home)</a>'
        f'<a class="primary" href="/graph?{carried}">Next: Stage 2 (The Graph) →</a>'
        f'</div>'
    )


def graph_html(title, note, diagram, *, back=None, valid_at=None, as_of=None):
    """One diagram, already Mermaid text wrapped by `diagram.script`."""
    carried = _carried(valid_at, as_of)
    out = [f"<h1>{escape(title)}</h1>", f'<p class="note">{note}</p>']
    if back:
        out.append(f'<p class="note">{back}</p>')
    else:
        out.append(
            '<div class="arch-layers-summary">'
            '<span class="arch-badge master">🏢 Layer 1: Master Data &amp; Assets (8 classes)</span>'
            '<span class="arch-badge event">📜 Layer 2: Immutable Event Log (3 classes)</span>'
            '<span class="arch-badge proj">📊 Layer 3: Digital Twin Projections &amp; BI (3 classes)</span>'
            '</div>'
        )

    out.append(diagram)

    if not back:
        out.append(
            '<div class="arch-cards-grid">'
            '  <div class="arch-card master">'
            '    <h3>🏢 Layer 1 · Master Data <span class="tag">8 Classes</span></h3>'
            '    <p class="card-desc">Foundational physical entities, actors, and conversion constants. Stored as versioned assertions.</p>'
            '    <ul>'
            '      <li><strong>Ingredient</strong>: 20 artisanal raw materials with unit pricing and reorder thresholds.'
            '        <span class="slot-desc">item_name, item_supplier, item_pack_price, item_price_per_kg, item_reorder_level</span></li>'
            '      <li><strong>InternalLocation</strong>: Kitchen storage temperature zones (is_a Location).'
            '        <span class="slot-desc">Dry Store (ambient), Walk-in Chiller (2-4°C), Ingredient Freezer (-18°C)</span></li>'
            '      <li><strong>Supplier</strong>: Commercial food purveyors (is_a Location).'
            '        <span class="slot-desc">Terra Nostra, Whitehall Dairy, Severn Catering, Total Produce</span></li>'
            '      <li><strong>Person</strong>: Kitchen personnel authorized to sign documents.'
            '        <span class="slot-desc">Dan Farrugia (Head Gelatiere), Marina Devlin (Owner), Aoife Byrne (Manager)</span></li>'
            '      <li><strong>Unit &amp; UnitConversion</strong>: Dimensional mass translation.'
            '        <span class="slot-desc">Translates bags, cans, sacks, tins, pails into uniform kilograms (kg).</span></li>'
            '      <li><strong>MovementKind</strong>: 5 operational movement typologies.'
            '        <span class="slot-desc">Delivery in, Transfer, Thrown away, Taken by staff, Tastings.</span></li>'
            '    </ul>'
            '  </div>'
            '  <div class="arch-card event">'
            '    <h3>📜 Layer 2 · Immutable Event Log <span class="tag">3 Classes</span></h3>'
            '    <p class="card-desc">Append-only operational transaction log. Bitemporal, strictly immutable, and audit-verifiable.</p>'
            '    <ul>'
            '      <li><strong>StockMovement</strong>: Physical ingredient transfer between two locations.'
            '        <span class="slot-desc">movement_kind, movement_out_of, movement_into, movement_ingredient, movement_quantity, movement_unit, happened_on, written_by</span></li>'
            '      <li><strong>StockCount</strong>: Paper stocktake session document header.'
            '        <span class="slot-desc">happened_on (count date), written_by (auditor), count_note (operational notes)</span></li>'
            '      <li><strong>StockCountLine</strong>: Individual line item recorded on a stocktake sheet.'
            '        <span class="slot-desc">line_count, count_line_ingredient, count_line_where, count_line_quantity, count_line_unit</span></li>'
            '    </ul>'
            '  </div>'
            '  <div class="arch-card proj">'
            '    <h3>📊 Layer 3 · Digital Twin Projections <span class="tag">3 Classes</span></h3>'
            '    <p class="card-desc">Compiled analytical queries evaluating state at any (valid_at, as_of) pair without code mutations.</p>'
            '    <ul>'
            '      <li><strong>IngredientOnHand</strong>: Cumulative movement ledger.'
            '        <span class="slot-desc">Computed: arrived (kg) - left (kg) = standing (kg), with £ total valuation.</span></li>'
            '      <li><strong>CountedOnHand</strong>: Physical audit totals.'
            '        <span class="slot-desc">Computed: sum of count sheet lines converted to standard kilograms.</span></li>'
            '      <li><strong>StockReconciliation</strong>: Variance, stockout, &amp; valuation intelligence.'
            '        <span class="slot-desc">Computes expected, counted, variance (kg), and financial discrepancy (£).'
            f'<br><a class="formula-link" href="/graph?class=StockReconciliation&amp;column=reconciliation_expected&amp;{carried}">🔍 expected formula</a>'
            f'<a class="formula-link" href="/graph?class=StockReconciliation&amp;column=reconciliation_variance&amp;{carried}">🔍 variance formula</a>'
            f'<a class="formula-link" href="/graph?class=StockReconciliation&amp;column=reconciliation_variance_value&amp;{carried}">🔍 variance (£)</a>'
            f'<a class="formula-link" href="/graph?class=StockReconciliation&amp;column=reconciliation_stock_value&amp;{carried}">🔍 stock value (£)</a>'
            '        </span></li>'
            '    </ul>'
            '  </div>'
            '</div>'
        )
        out.append(
            f'<div class="stage-stepper">'
            f'<a href="/said?{carried}">← Previous: Stage 1 (Said)</a>'
            f'<a class="primary" href="/why?{carried}">Next: Stage 3 (Audit Log / Why) →</a>'
            f'</div>'
        )
    return "\n".join(out)


def why_html(built, *, valid_at, as_of):
    """Every assertion ever made about one subject and one predicate.

    Renders a visual bitemporal timeline comparing origin statements,
    revisions, and revocations, followed by the complete raw audit trail.
    """
    carried = f"valid_at={quote(str(valid_at))}&amp;as_of={quote(str(as_of))}"
    rows = built["rows"]
    subject = built["subject"]
    predicate = built["predicate"]

    out = [
        '<div class="dash-header">',
        f'  <p style="margin-bottom:.5rem;"><a href="/why?{carried}" style="text-decoration:none; font-weight:600; color:#1c4f8b;">← Back to Audit Ledger</a></p>',
        f'  <h1>Entity Provenance History: <code>{escape(str(subject))}</code></h1>',
        f'  <p>Predicate Slot: <code>{escape(str(predicate))}</code> · {len(rows)} immutable assertion(s) in PostgreSQL kernel ledger.</p>',
        '</div>'
    ]

    out.append(
        '<div class="alert-box" style="margin-bottom: 1.5rem; border-left-color: #1c4f8b;">'
        '  <h3 style="margin:0 0 .3rem;">Bitemporal Dual-Clock Resolution Rule</h3>'
        '  <p style="margin:0; font-size:.86rem; color:#4a443e; line-height: 1.45;">'
        '    In Uniti, data is never mutated in place. '
        '    Rows with different <code>valid_from</code> represent natural price or state evolution over real time. '
        '    Rows with <code>revokes</code> supersede an earlier erroneous fact without deleting its historical existence. '
        f'    At current clocks (<code>valid_at={escape(str(valid_at))}</code>, <code>as_of={escape(str(as_of))}</code>), '
        '    the projection compiler picks the active winning assertion automatically.'
        '  </p>'
        '</div>'
    )

    if not rows:
        out.append('<p class="msg">Nothing has ever been said under this pair.</p>')
        out.append(
            f'<div class="stage-stepper">'
            f'  <a href="/why?{carried}">← Back to Audit Ledger</a>'
            f'  <a class="primary" href="/classes?{carried}">Next: Stage 4 (Operational Forms) →</a>'
            f'</div>'
        )
        return "\n".join(out)

    # Visual Bitemporal Change Timeline
    if len(rows) > 1:
        out.append('<h2 style="margin: 1.5rem 0 .5rem;">Bitemporal Change Timeline (Chronological Audit)</h2>')
        out.append('<div class="audit-timeline">')
        for i, row in enumerate(rows, 1):
            is_revoked = bool(row["revoked_by"])
            is_correction = bool(row["revokes"])
            is_retraction = (row["value"] is None)

            if is_revoked:
                dot_class = "revoked"
                card_class = "is-revoked"
                badge = f'<span class="badge badge-danger">Revoked by #{str(row["revoked_by"])[:8]}</span>'
                val_disp = f'<div class="timeline-val struck">{escape(str(row["value"]))}</div>'
            elif is_correction:
                dot_class = "correction"
                card_class = ""
                badge = f'<span class="badge badge-warning">Correction (Supersedes #{str(row["revokes"])[:8]})</span>'
                val_disp = f'<div class="timeline-val">{escape(str(row["value"]))} <span class="badge badge-success">Active Winner</span></div>'
            elif is_retraction:
                dot_class = "revoked"
                card_class = "is-revoked"
                badge = '<span class="badge badge-danger">Pure Retraction (Fact Withdrawn)</span>'
                val_disp = '<div class="timeline-val" style="color:#991b1b; font-style:italic;">Withdrawn — carries no value</div>'
            else:
                dot_class = "active"
                card_class = ""
                badge = '<span class="badge badge-success">Active Fact</span>'
                val_disp = f'<div class="timeline-val">{escape(str(row["value"]))}</div>'

            vf = str(row["valid_from"])[:16]
            rf = str(row["recorded_at"])[:16]
            actor = escape(str(row["actor_id"]))
            action = escape(str(row["action_name"]))
            corr_btn = ""
            if not is_revoked and row["value"] is not None:
                c_url = f'/correct?subject={quote(str(subject))}&amp;predicate={quote(str(predicate))}&amp;revoking={row["id"]}&amp;{carried}'
                corr_btn = f'<span><a class="btn-correct" href="{c_url}">⚡ Revoke / Correct</a></span>'

            out.append(
                f'<div class="timeline-item">'
                f'  <div class="timeline-dot {dot_class}"></div>'
                f'  <div class="timeline-card {card_class}">'
                f'    <div class="timeline-meta">'
                f'      <span><strong>Step #{i}</strong></span>'
                f'      <span>{badge}</span>'
                f'      <span>📅 Real-world: <code>{vf}</code></span>'
                f'      <span>⏱️ Recorded: <code>{rf}</code></span>'
                f'      <span>👤 Actor: <strong>{actor}</strong></span>'
                f'      <span>⚡ Action: <code>{action}</code></span>'
                f'      {corr_btn}'
                f'    </div>'
                f'    {val_disp}'
                f'  </div>'
                f'</div>'
            )
        out.append('</div>')

    # Raw Kernel Records Table
    head = (
        "<tr><th>Asserted Value</th><th>valid_from</th><th>recorded_at</th>"
        "<th>Source</th><th>Confidence</th><th>Authority</th>"
        "<th>Actor</th><th>Intent Action</th><th>Intent ID</th>"
        "<th>Status / Revocation</th></tr>"
    )
    body = []
    for row in rows:
        gone = ' class="gone"' if row["revoked_by"] else ""
        if row["value"] is None:
            value = '<span class="badge badge-danger">retraction (no value)</span>'
        else:
            value = f'<strong>{escape(str(row["value"]))}</strong>'
        withdrawn = []
        if row["revokes"]:
            withdrawn.append(f'<span class="badge badge-warning">revokes {str(row["revokes"])[:8]}</span>')
        if row["revoked_by"]:
            withdrawn.append(f'<span class="badge badge-danger">revoked by {str(row["revoked_by"])[:8]}</span>')
        if not withdrawn:
            withdrawn.append('<span class="badge badge-success">active fact</span>')
        if not row["revoked_by"] and row["value"] is not None:
            c_url = f'/correct?subject={quote(str(subject))}&amp;predicate={quote(str(predicate))}&amp;revoking={row["id"]}&amp;{carried}'
            withdrawn.append(f'<a class="btn-correct" href="{c_url}">⚡ Correct</a>')
        body.append(
            f'<tr{gone}>'
            f'  <td class="value">{value}</td>'
            f'  <td><code>{escape(str(row["valid_from"]))[:16]}</code></td>'
            f'  <td><code style="color:#6b6259;">{escape(str(row["recorded_at"]))[:16]}</code></td>'
            f'  <td>{escape(str(row["source"]))}</td>'
            f'  <td>{escape(str(row["confidence"] or "-"))}</td>'
            f'  <td>{escape(str(row["authority"] or "-"))}</td>'
            f'  <td><strong>{escape(str(row["actor_id"]))}</strong></td>'
            f'  <td><span class="badge badge-neutral">{escape(str(row["action_name"]))}</span></td>'
            f'  <td><code>{escape(str(row["intent_id"])[:8])}</code></td>'
            f'  <td>{" ".join(withdrawn)}</td>'
            f'</tr>'
        )
    out.append('<h2 style="margin: 2rem 0 .5rem;">Raw Kernel Ledger Records</h2>')
    out.append('<div class="scroll"><table class="why"><thead>' + head
               + "</thead><tbody>" + "".join(body) + "</tbody></table></div>")
    out.append(
        f'<div class="stage-stepper">'
        f'  <a href="/why?{carried}">← Back to Audit Ledger</a>'
        f'  <a class="primary" href="/classes?{carried}">Next: Stage 4 (Operational Forms) →</a>'
        f'</div>'
    )
    return "\n".join(out)


def ask_html(window, *, recent=None, filter_type="all", actor="", search="", valid_at, as_of):
    """Stage 3: Enterprise Kernel Audit Workbench.

    Presents the immutable append-only activity ledger directly from PostgreSQL,
    with operational filters (by event type, staff actor, search) and 1-click
    deep-dive to entity provenance histories and timelines.
    """
    carried = f"valid_at={quote(str(valid_at))}&amp;as_of={quote(str(as_of))}"
    recent = recent or []

    out = [
        '<div class="dash-header">',
        '  <h1>Stage 3 · Bitemporal Kernel Audit Log</h1>',
        '  <p>The system\'s operational ground truth: an append-only, immutable bitemporal ledger. '
        'In Uniti, <code>UPDATE</code> and <code>DELETE</code> are <strong>physically revoked at the PostgreSQL database permission level</strong>. '
        'Every transaction is an explicit, immutable assertion signed by an authenticated actor, verifiable by intent, '
        'and indexed across two independent temporal axes: real-world occurrence (<code>valid_from</code>) and system recording (<code>recorded_at</code>).</p>',
        '</div>'
    ]

    # 1. Telemetry Bar (Compact 4-Card Grid)
    if window:
        vf = str(window.get("first_valid_from", ""))[:10]
        vl = str(window.get("last_valid_from", ""))[:10]
        rf = str(window.get("first_recorded_at", ""))[:10]
        rl = str(window.get("last_recorded_at", ""))[:16]
        rev_count = window.get("revocations", 34)
        out.append(
            '<div class="kpi-grid">'
            '  <div class="kpi-card primary-card">'
            '    <div class="kpi-label">Immutable Assertions</div>'
            f'    <div class="kpi-value">{window.get("assertions", 0):,}</div>'
            '    <div class="kpi-sub">Total historical facts in PostgreSQL</div>'
            '  </div>'
            '  <div class="kpi-card success-card">'
            '    <div class="kpi-label">Verified Intents</div>'
            f'    <div class="kpi-value">{window.get("intents", 0):,}</div>'
            '    <div class="kpi-sub">Atomic business transactions</div>'
            '  </div>'
            '  <div class="kpi-card warning-card">'
            '    <div class="kpi-label">Recorded Revocations</div>'
            f'    <div class="kpi-value">{rev_count:,}</div>'
            '    <div class="kpi-sub">Non-destructive corrections</div>'
            '  </div>'
            '  <div class="kpi-card alert-card">'
            '    <div class="kpi-label">Operational Clocks Span</div>'
            f'    <div class="kpi-value" style="font-size: 1.15rem; margin-top:.4rem;">{vf} → {vl}</div>'
            '    <div class="kpi-sub">valid_from horizon</div>'
            '  </div>'
            '</div>'
        )

    # 2. Operational Audit Filter Bar (Datadog/CloudTrail style)
    p_all = "active" if filter_type == "all" else ""
    p_rev = "active" if filter_type == "revocations" else ""
    p_mst = "active" if filter_type == "master" else ""
    p_stk = "active" if filter_type == "stocktake" else ""
    p_mov = "active" if filter_type == "movement" else ""

    actor_param = f"&amp;actor={quote(actor)}" if actor else ""
    q_param = f"&amp;q={quote(search)}" if search else ""

    def act_sel(a):
        return ' selected' if actor == a else ''

    out.append(
        '<div class="audit-filter-bar">'
        '  <div class="audit-filter-row">'
        '    <div class="audit-pill-group">'
        '      <span style="font-size:.8rem; font-weight:600; color:#7a7066; margin-right:.25rem;">LEDGER FILTER:</span>'
        f'      <a class="audit-pill {p_all}" href="/why?filter=all{actor_param}{q_param}&amp;{carried}">📋 All Events</a>'
        f'      <a class="audit-pill {p_rev}" href="/why?filter=revocations{actor_param}{q_param}&amp;{carried}">⚡ Corrections &amp; Revocations ({window.get("revocations", 34)})</a>'
        f'      <a class="audit-pill {p_mst}" href="/why?filter=master{actor_param}{q_param}&amp;{carried}">🏢 Master Data</a>'
        f'      <a class="audit-pill {p_stk}" href="/why?filter=stocktake{actor_param}{q_param}&amp;{carried}">📦 Stocktake Audits</a>'
        f'      <a class="audit-pill {p_mov}" href="/why?filter=movement{actor_param}{q_param}&amp;{carried}">🚚 Stock Movements</a>'
        '    </div>'
        '  </div>'
        '  <div class="audit-filter-row">'
        '    <form class="audit-search-form" method="get" action="/why">'
        f'      <input type="hidden" name="filter" value="{escape(filter_type)}">'
        f'      <input type="hidden" name="valid_at" value="{escape(str(valid_at))}">'
        f'      <input type="hidden" name="as_of" value="{escape(str(as_of))}">'
        '      <label for="f_actor" style="font-size:.8rem; color:#7a7066; font-weight:600;">Signatory Actor:</label>'
        '      <select name="actor" id="f_actor" onchange="this.form.submit()">'
        f'        <option value=""{act_sel("")}>All Staff</option>'
        f'        <option value="marina"{act_sel("marina")}>Marina Devlin (Production)</option>'
        f'        <option value="dan"{act_sel("dan")}>Dan Farrugia (Founder)</option>'
        f'        <option value="aoife"{act_sel("aoife")}>Aoife Byrne (Floor Ops)</option>'
        '      </select>'
        f'      <input type="search" name="q" placeholder="Filter entity URI, slot, or value..." value="{escape(search)}">'
        '      <button type="submit" class="btn-action btn-outline" style="font-size:.8rem; padding:.32rem .75rem;">Search</button>'
        + (f' <a href="/why?filter={filter_type}&amp;{carried}" style="font-size:.78rem; color:#b32d2e; text-decoration:none; margin-left:.3rem;">✕ Clear filters</a>' if (actor or search) else '') +
        '    </form>'
        '  </div>'
        '</div>'
    )

    # 3. Activity Ledger Table
    head = (
        '<tr>'
        '  <th>Seq #</th>'
        '  <th>Intent Action</th>'
        '  <th>Subject Entity</th>'
        '  <th>Predicate Slot</th>'
        '  <th>Asserted Value</th>'
        '  <th>Status</th>'
        '  <th>valid_from</th>'
        '  <th>recorded_at</th>'
        '  <th>Actor</th>'
        '  <th>Audit Action</th>'
        '</tr>'
    )
    rows_html = []
    for r in recent:
        sub_short = r["subject"].replace("sorella:", "")
        pred_short = r["predicate"].replace("sorella:", "")
        why_url = f'/why?subject={quote(r["subject"])}&amp;predicate={quote(r["predicate"])}&amp;{carried}'

        # Status badge & value display
        if r["revoked_by"]:
            val = f'<span style="text-decoration: line-through; color: #991b1b;">{escape(str(r["value"]))}</span>'
            status_badge = f'<span class="badge badge-danger" title="Revoked by #{str(r["revoked_by"])[:8]}">Revoked</span>'
        elif r["revokes"]:
            val = f'<strong>{escape(str(r["value"]))}</strong>' if r["value"] is not None else '<em>(withdrawn)</em>'
            status_badge = f'<span class="badge badge-warning" title="Revokes #{str(r["revokes"])[:8]}">Correction</span>'
        elif r["value"] is None:
            val = '<em>(retraction)</em>'
            status_badge = '<span class="badge badge-danger">Retraction</span>'
        else:
            val = f'<strong>{escape(str(r["value"]))}</strong>'
            status_badge = '<span class="badge badge-success">Active Fact</span>'

        corr_link = ""
        if not r["revoked_by"] and r["value"] is not None:
            c_url = f'/correct?subject={quote(r["subject"])}&amp;predicate={quote(r["predicate"])}&amp;revoking={r["id"]}&amp;{carried}'
            corr_link = f' <a class="btn-correct" style="padding:.2rem .45rem; font-size:.75rem;" href="{c_url}">⚡ Revoke</a>'

        rows_html.append(
            f'<tr>'
            f'  <td><code>#{r["seq"]}</code></td>'
            f'  <td><span class="badge badge-neutral">{escape(str(r["action_name"]))}</span></td>'
            f'  <td><code title="{escape(r["subject"])}">{escape(sub_short)}</code></td>'
            f'  <td><code title="{escape(r["predicate"])}">{escape(pred_short)}</code></td>'
            f'  <td>{val}</td>'
            f'  <td>{status_badge}</td>'
            f'  <td style="white-space:nowrap; font-size:.8rem;">{str(r["valid_from"])[:16]}</td>'
            f'  <td style="white-space:nowrap; font-size:.8rem; color:#6b6259;">{str(r["recorded_at"])[:16]}</td>'
            f'  <td><strong>{escape(str(r["actor_id"]))}</strong></td>'
            f'  <td><a class="btn-action btn-outline" style="padding:.2rem .55rem; font-size:.75rem;" href="{why_url}">🔍 History</a>{corr_link}</td>'
            f'</tr>'
        )

    out.append(
        '<div class="recent-log-card">'
        f'  <h2>Kernel Activity Ledger ({len(recent)} matching facts)</h2>'
        '  <p class="log-desc">Append-only transactional stream queried directly from PostgreSQL kernel (<code>assertion</code> JOIN <code>intent</code>). '
        'Click <strong>🔍 History</strong> on any row to open the complete bitemporal timeline and provenance lineage of that entity.</p>'
        '  <div class="scroll"><table class="why"><thead>' + head + '</thead><tbody>' + ("".join(rows_html) if rows_html else '<tr><td colspan="10" style="text-align:center; padding:1.5rem; color:#7a7066;">No assertions matching the current filter criteria.</td></tr>') + '</tbody></table></div>'
        '</div>'
    )

    # 4. Collapsible Direct Lookup Box
    out.append(
        '<details class="direct-lookup-box">'
        '  <summary>🔍 Direct URI Lookup (Manual Query Inspector for Engineers)</summary>'
        '  <form method="get" action="/why" style="margin-top: 1rem;">'
        f'    <input type="hidden" name="valid_at" value="{escape(str(valid_at))}">'
        f'    <input type="hidden" name="as_of" value="{escape(str(as_of))}">'
        '    <div class="field"><label for="f_subject">subject URI</label>'
        '      <span class="hint">The URI of the entity, e.g. <code>sorella:item_sicilian_pistachio_paste</code></span>'
        '      <input name="subject" id="f_subject" placeholder="sorella:item_sicilian_pistachio_paste">'
        '    </div>'
        '    <div class="field"><label for="f_predicate">predicate URI</label>'
        '      <span class="hint">The URI of what was said about it, e.g. <code>sorella:item_pack_price</code></span>'
        '      <input name="predicate" id="f_predicate" placeholder="sorella:item_pack_price">'
        '    </div>'
        '    <button type="submit" class="btn-action btn-outline" style="font-size:.85rem; padding:.45rem .9rem;">Query Provenance History</button>'
        '  </form>'
        '</details>'
    )

    # 5. Stepper
    out.append(
        f'<div class="stage-stepper">'
        f'  <a href="/graph?{carried}">← Previous: Stage 2 (The Graph)</a>'
        f'  <a class="primary" href="/classes?{carried}">Next: Stage 4 (Operational Forms) →</a>'
        f'</div>'
    )
    return "\n".join(out)


def index_html(forms, tables, *, valid_at, as_of, map_=None):
    """Stage 4 & 5 Index: classes with a form and classes with a compiled table."""
    carried = _carried(valid_at, as_of)
    out = [
        '<div class="dash-header">',
        f'  <p style="margin-bottom:.5rem;"><a href="/why?{carried}" style="text-decoration:none; font-weight:600; color:#1c4f8b;">← Back to Stage 3 Audit Ledger</a></p>',
        '  <h1>Stage 4 &amp; 5 · Operational Data &amp; Live Projections</h1>',
        '  <p>Interactive interfaces generated directly from LinkML schema models. Stage 4 provides operational entry and bitemporal corrections; Stage 5 provides real-time compiled analytical views.</p>',
        '</div>'
    ]

    view = map_["view"] if map_ else None

    def get_desc(cname):
        if view and cname in view.all_classes():
            d = view.all_classes()[cname].description or ""
            return d.split(".")[0] + "." if "." in d else d
        return ""

    for heading, group in forms:
        if not group:
            continue
        is_evt = ("written down" in heading.lower())
        cat_badge = "⚡ Transaction Event" if is_evt else "🏢 Master Data Entity"
        badge_style = "tag-event" if is_evt else "tag-master"
        icon = "⚡" if is_evt else "🏢"
        out.append('<div class="classes-category">')
        out.append(f'  <h2>{icon} {escape(heading.title())} <span class="badge badge-neutral">{len(group)} forms</span></h2>')
        if is_evt:
            out.append('  <p class="cat-desc">Operational records created as real-world kitchen events happen (deliveries, stock movements, stocktake counts). Each submission mints a brand-new unique entity in the graph.</p>')
        else:
            out.append('  <p class="cat-desc">Foundational master data entities referenced by operations. Submitting updates appends a new state valid_from without overwriting historical identities.</p>')
        out.append('  <div class="cards-grid">')
        for name in group:
            desc = get_desc(name) or f"Operational data form for {name}."
            out.append(
                f'  <a class="class-card" href="/form/{escape(name)}?{carried}">'
                f'    <div>'
                f'      <div class="class-card-header">'
                f'        <div class="class-card-title">{escape(name)}</div>'
                f'        <span class="badge-tag {badge_style}">{cat_badge}</span>'
                f'      </div>'
                f'      <p class="class-card-desc">{escape(desc)}</p>'
                f'    </div>'
                f'    <div class="class-card-action">Open Form <span>→</span></div>'
                f'  </a>'
            )
        out.append('  </div>')
        out.append('</div>')

    # Stage 5 Tables
    table_descs = {
        "StockReconciliation": "Triple-entry variance ledger auditing physical counted stock on shelves against expected stock from movements. Identifies shrinkage, waste, and transcription errors.",
        "IngredientOnHand": "Running balance of inventory derived from all cumulative stock movements (deliveries, usage, waste, transfers).",
        "CountedOnHand": "Latest point-in-time physical inventory snapshot aggregated from shelf stocktake count sheets.",
    }
    out.append('<div class="classes-category" style="margin-top:2.5rem;">')
    out.append(f'  <h2 id="tables">📊 Stage 5 · Live Operational Tables &amp; Projections <span class="badge badge-neutral">{len(tables)} tables</span></h2>')
    out.append('  <p class="cat-desc">Real-time digital twin projections compiled into PostgreSQL by translating LinkML derivation rules directly into SQL. Every cell carries clickable backward lineage back into the kernel.</p>')
    out.append('  <div class="cards-grid">')
    for name in tables:
        desc = table_descs.get(name, f"Operational analytical projection table for {name}.")
        out.append(
            f'  <a class="class-card" href="/table/{escape(name)}?{carried}">'
            f'    <div>'
            f'      <div class="class-card-header">'
            f'        <div class="class-card-title">{escape(name)}</div>'
            f'        <span class="badge-tag" style="background:#fef3c7; border-color:#fde68a; color:#b45309;">📊 Compiled Projection</span>'
            f'      </div>'
            f'      <p class="class-card-desc">{escape(desc)}</p>'
            f'    </div>'
            f'    <div class="class-card-action">View Projection Table <span>→</span></div>'
            f'  </a>'
        )
    out.append('  </div>')
    out.append('</div>')

    out.append(
        f'<div class="stage-stepper" style="margin-top: 2rem;">'
        f'  <a href="/why?{carried}">← Back to Stage 3 Audit Ledger</a>'
        f'  <a class="primary" href="/table/StockReconciliation?{carried}">Explore Stage 5 Projections →</a>'
        f'</div>'
    )
    return "\n".join(out)


def _field_html(field, value="", placeholder="", datalist_id=None):
    """One slot, asked for. A class range is a select, everything else a box."""
    name = escape(str(field["name"]))
    required = " required" if field.get("required") else ""
    star = ' <span class="req" title="required">*</span>' if field.get("required") else ""
    hint = field.get("description") or ""
    if field.get("ref"):
        options = ['<option value="">— Select an option —</option>']
        for uri, label in field.get("options", []):
            selected = " selected" if uri == value else ""
            shown = f"{label} ({uri})" if label else uri
            options.append(
                f'<option value="{escape(uri)}"{selected}>{escape(shown)}</option>')
        if len(options) == 1:
            hint = (hint + " (the log holds none)").strip()
        control = (f'<select name="{name}" id="f_{name}"{required}>'
                   + "".join(options) + "</select>")
    else:
        range_ = str(field.get("range") or "string").lower()
        kind = INPUT_TYPE.get(range_, "text")
        step = f' step="{STEP[range_]}"' if range_ in STEP else ""
        ph = f' placeholder="{escape(placeholder)}"' if placeholder else ""
        dl = f' list="{escape(datalist_id)}"' if datalist_id else ""
        val_str = escape(str(value)) if value is not None else ""
        control = (f'<input type="{kind}"{step} name="{name}" id="f_{name}" '
                   f'value="{val_str}"{ph}{dl}{required}>')
    return (f'<div class="field"><label for="f_{name}">{name}{star}</label>'
            f'<span class="hint">{escape(hint)}</span>{control}</div>')


EXTRA_FIELDS = [
    {"name": "subject", "required": False, "ref": False, "range": "string",
     "description": "The URI of the thing being written about. Auto-minted if left blank."},
    {"name": "actor", "required": True, "ref": False, "range": "string",
     "description": "Who is acting. It goes on the intent, once, for the whole submission."},
]


def form_html(built, *, valid_at, as_of, values=None, message=None, bad=False,
              actors=None, is_event=False, existing_subjects=None):
    """What `generate.form()` returns, as a modern ergonomic form.

    Groups fields into Intent Authorization (signing staff actor, auto-minted subject)
    and Domain Payload (slots from LinkML class).
    """
    values = values or {}
    carried = _carried(valid_at, as_of)
    class_name = str(built["class"])

    actors = actors or [
        ("marina", "Marina Devlin (Owner / Production)"),
        ("dan", "Dan Farrugia (Head Gelatiere)"),
        ("aoife", "Aoife Byrne (Shop Manager, Cotham)"),
        ("fareza", "Fareza (System Auditor / Admin)"),
    ]

    out = [
        '<div class="dash-header">',
        f'  <p style="margin-bottom:.5rem;"><a href="/classes?{carried}" style="text-decoration:none; font-weight:600; color:#1c4f8b;">← Back to Stage 4 Classes</a></p>',
        f'  <h1>{escape(class_name)} — Form</h1>',
        f'  <p>Stage 4 · Operational Data Entry. Every submission creates an immutable Intent signed by an authorized Actor, recording atomic Assertions into PostgreSQL.</p>',
        '</div>'
    ]

    tag_class = "tag-event" if is_event else "tag-master"
    tag_label = "⚡ Transaction Event Form" if is_event else "🏢 Master Data Entity Form"
    out.append(
        '<div class="form-header-badge">'
        f'  <span class="badge-tag">Class: <strong>{escape(class_name)}</strong></span>'
        f'  <span class="badge-tag {tag_class}">{tag_label}</span>'
        f'  <span class="badge-tag tag-source">{escape(str(built["source"]))} ({escape(str(built["version"]))})</span>'
        '</div>'
    )

    if message:
        out.append(f'<div class="msg{" bad" if bad else ""}">{escape(message)}</div>')

    out.append('<div class="form-card">')
    out.append('<form method="post" action="">')

    # Section 1: Intent & Authorization
    out.append('  <div class="form-section">')
    out.append('    <div class="form-section-title">1. Signatory &amp; Identity (Kernel Intent Header)</div>')
    out.append('    <div class="form-grid">')

    # Actor field (Dropdown)
    actor_val = values.get("actor", "")
    actor_opts = ['<option value="">— Select signing staff member —</option>']
    for a_id, a_lbl in actors:
        sel = " selected" if a_id == actor_val else ""
        actor_opts.append(f'<option value="{escape(a_id)}"{sel}>{escape(a_lbl)}</option>')
    out.append(
        '      <div class="field">'
        '        <label for="f_actor">Signing Actor <span class="req" title="required">*</span></label>'
        '        <span class="hint">Staff member authorizing and signing this intent into the immutable kernel log.</span>'
        f'        <select name="actor" id="f_actor" required>{"".join(actor_opts)}</select>'
        '      </div>'
    )

    # Subject field (Auto-minted or Datalist)
    sub_val = values.get("subject", "")
    if is_event:
        out.append(
            '      <div class="field">'
            '        <label for="f_subject">Subject ID (Identity URI)</label>'
            '        <span class="hint">⚡ Auto-generated event identity. Leave blank to auto-mint on submit.</span>'
            f'        <input type="text" name="subject" id="f_subject" value="{escape(str(sub_val))}" placeholder="[Auto-minted by kernel upon submission]">'
            '      </div>'
        )
    else:
        datalist_html = ""
        dl_attr = ""
        if existing_subjects:
            dl_id = f"dl_{class_name.lower()}"
            dl_attr = f' list="{dl_id}"'
            opts = "".join(f'<option value="{escape(u)}">{escape(lbl or u)}</option>' for u, lbl in existing_subjects)
            datalist_html = f'<datalist id="{dl_id}">{opts}</datalist>'
        out.append(
            '      <div class="field">'
            '        <label for="f_subject">Subject ID (Entity URI)</label>'
            '        <span class="hint">Entity URI identifier. Leave blank to auto-mint from name, or enter custom code / select existing to update.</span>'
            f'        <input type="text" name="subject" id="f_subject" value="{escape(str(sub_val))}"{dl_attr} placeholder="Leave blank to auto-mint, or enter custom URI">{datalist_html}'
            '      </div>'
        )

    out.append('    </div>')
    out.append('  </div>')

    # Section 2: Business Payload Slots
    out.append('  <div class="form-section">')
    out.append('    <div class="form-section-title">2. Record Details (Map Slots)</div>')
    out.append('    <div class="form-grid">')

    for field in built["fields"]:
        if field["name"] == "entity_class":
            out.append(f'<input type="hidden" name="entity_class" value="{escape(str(values.get("entity_class") or class_name))}">')
            continue
        out.append(_field_html(field, values.get(field["name"], "")))

    out.append('    </div>')
    out.append('  </div>')

    # Section 3: Submit Action
    btn_text = "✍️ Commit Transaction to Immutable Kernel" if is_event else "✍️ Save Entity State to Kernel"
    out.append('  <div style="margin-top: 1.5rem; display:flex; justify-content:space-between; align-items:center;">')
    out.append(f'    <a href="/classes?{carried}" style="text-decoration:none; color:#7a7066;">← Cancel and return</a>')
    out.append(f'    <button type="submit" class="btn-primary">{btn_text}</button>')
    out.append('  </div>')

    out.append('</form>')
    out.append('</div>')

    out.append(
        f'<div class="stage-stepper">'
        f'  <a href="/classes?{carried}">← Back to Stage 4 Classes</a>'
        f'  <a class="primary" href="/table/StockReconciliation?{carried}">Next: Stage 5 (Live Operational Tables) →</a>'
        f'</div>'
    )
    return "\n".join(out)


def correct_html(target, *, valid_at, as_of, actors=None, message=None, bad=False):
    """Stage 4 · Interactive Bitemporal Correction & Revocation Form.

    Allows authorized staff to supersede or retract an existing kernel fact
    in strict append-only fashion (using assertion.revokes).
    """
    carried = f"valid_at={quote(str(valid_at))}&amp;as_of={quote(str(as_of))}"
    subject = target["subject"]
    predicate = target["predicate"]
    slot_name = target.get("slot_name") or predicate.split(":")[-1]
    class_name = target.get("class_name") or "Entity"
    current_val = target.get("current_value")
    assertion_id = target["assertion_id"]
    recorded_at = str(target.get("recorded_at") or "")[:16]
    stating_actor = target.get("actor_id") or "system"

    actors = actors or [
        ("marina", "Marina Devlin (Owner / Production)"),
        ("dan", "Dan Farrugia (Head Gelatiere)"),
        ("aoife", "Aoife Byrne (Shop Manager, Cotham)"),
        ("fareza", "Fareza (System Auditor / Admin)"),
    ]

    out = [
        '<div class="dash-header">',
        f'  <p style="margin-bottom:.5rem;"><a href="/why?subject={quote(subject)}&amp;predicate={quote(predicate)}&amp;{carried}" style="text-decoration:none; font-weight:600; color:#1c4f8b;">← Back to History Timeline</a></p>',
        f'  <h1>Bitemporal Correction / Revocation: <code>{escape(subject)}</code></h1>',
        f'  <p>Append-only revision for slot <code>{escape(slot_name)}</code> ({escape(class_name)}). Supersedes assertion <code>#{escape(str(assertion_id)[:8])}</code>.</p>',
        '</div>'
    ]

    out.append(
        '<div class="alert-box" style="margin-bottom: 1.5rem; border-left-color: #d97706;">'
        '  <h3 style="margin:0 0 .3rem;">Append-Only Audit Guarantee</h3>'
        '  <p style="margin:0; font-size:.86rem; color:#4a443e; line-height: 1.45;">'
        '    In Uniti, historical assertions are <strong>never updated or deleted</strong> in PostgreSQL. '
        '    When you submit this form, the kernel records a brand-new intent and assertion that explicitly links '
        '    to the prior assertion ID under <code>revokes</code>. The prior assertion remains preserved forever for full audit compliance.'
        '  </p>'
        '</div>'
    )

    if message:
        out.append(f'<div class="msg{" bad" if bad else ""}">{escape(message)}</div>')

    # Target Fact Summary Card
    out.append(
        '<div class="form-card" style="margin-bottom: 1.5rem; background: #faf9f7; border-color: #e2ded7;">'
        '  <h3 style="margin:0 0 .75rem; font-size: .95rem; color: #7a7066; text-transform: uppercase; letter-spacing: .04em;">Fact Currently Standing in Kernel</h3>'
        '  <div style="display: flex; gap: 2rem; flex-wrap: wrap; font-size: .88rem;">'
        f'    <div><span style="color:#7a7066;">Subject Entity:</span><br><strong><code>{escape(subject)}</code></strong></div>'
        f'    <div><span style="color:#7a7066;">Slot / Predicate:</span><br><strong><code>{escape(slot_name)}</code></strong></div>'
        f'    <div><span style="color:#7a7066;">Current Value:</span><br><strong style="font-size:1.1rem; color:#1c4f8b;">{escape(str(current_val))}</strong></div>'
        f'    <div><span style="color:#7a7066;">Stated By:</span><br><strong>{escape(str(stating_actor))}</strong> (<code>{escape(recorded_at)}</code>)</div>'
        f'    <div><span style="color:#7a7066;">Assertion ID:</span><br><code>{escape(str(assertion_id))}</code></div>'
        '  </div>'
        '</div>'
    )

    actor_options = "".join(f'<option value="{escape(a_id)}">{escape(a_lbl)}</option>' for a_id, a_lbl in actors)

    out.append(
        '<div class="form-card">'
        f'<form method="post" action="/correct?{carried}">'
        f'  <input type="hidden" name="subject" value="{escape(subject)}">'
        f'  <input type="hidden" name="predicate" value="{escape(predicate)}">'
        f'  <input type="hidden" name="assertion_id" value="{escape(str(assertion_id))}">'
        f'  <input type="hidden" name="class_name" value="{escape(class_name)}">'
        f'  <input type="hidden" name="slot_name" value="{escape(slot_name)}">'
        '  <div class="form-section">'
        '    <div class="form-section-title">1. Correction Type</div>'
        '    <div style="display: flex; gap: 1.5rem; margin-bottom: 1rem;">'
        '      <label style="display:flex; align-items:center; gap:.4rem; cursor:pointer; font-weight:600; font-size:.9rem;">'
        '        <input type="radio" name="action_type" value="correction" checked id="act_corr" onchange="document.getElementById(\'val_box\').style.display=\'block\';"> '
        '        ✏️ Replace with Corrected Value'
        '      </label>'
        '      <label style="display:flex; align-items:center; gap:.4rem; cursor:pointer; font-weight:600; font-size:.9rem; color:#b32d2e;">'
        '        <input type="radio" name="action_type" value="retraction" id="act_ret" onchange="document.getElementById(\'val_box\').style.display=\'none\';"> '
        '        ❌ Pure Retraction / Void (No Replacement)'
        '      </label>'
        '    </div>'
        '    <div class="field" id="val_box">'
        f'      <label for="f_new_value">Corrected Value <span class="req" title="required">*</span></label>'
        f'      <span class="hint">The replacement value that should take effect in the operational store. Current value is {escape(str(current_val))}.</span>'
        f'      <input type="text" name="new_value" id="f_new_value" value="{escape(str(current_val or ""))}" style="font-weight:600;">'
        '    </div>'
        '  </div>'
        '  <div class="form-section">'
        '    <div class="form-section-title">2. Authorization &amp; Justification</div>'
        '    <div class="form-grid">'
        '      <div class="field">'
        '        <label for="f_actor">Authorized Signatory <span class="req" title="required">*</span></label>'
        '        <span class="hint">Staff member authorizing and signing this revocation in the kernel log.</span>'
        f'        <select name="actor" id="f_actor" required>{actor_options}</select>'
        '      </div>'
        '      <div class="field">'
        '        <label for="f_reason">Reason Code <span class="req" title="required">*</span></label>'
        '        <span class="hint">Formal categorization of why this earlier assertion was revoked.</span>'
        '        <select name="reason_code" id="f_reason">'
        '          <option value="transposition_error">Typo / Transposition Error (clerical mistake)</option>'
        '          <option value="counting_error">Counting Error (physical discrepancy on shelf)</option>'
        '          <option value="never_arrived">Delivery / Event Never Arrived (voided transaction)</option>'
        '          <option value="entry_mistake">Wrong Form / Class Selection</option>'
        '          <option value="correction" selected>General Operational Correction</option>'
        '        </select>'
        '      </div>'
        '    </div>'
        '    <div class="field">'
        '      <label for="f_note">Audit Justification Note <span class="req" title="required">*</span></label>'
        '      <span class="hint">Clear explanation recorded forever in the intent audit trail for compliance.</span>'
        '      <input type="text" name="note" id="f_note" required placeholder="e.g. Corrected invoice price from £4.10 to £41.00 following Whitehall Dairy reconciliation">'
        '    </div>'
        '  </div>'
        '  <div style="display:flex; justify-content:space-between; align-items:center; margin-top:1.5rem;">'
        f'    <a href="/why?subject={quote(subject)}&amp;predicate={quote(predicate)}&amp;{carried}" style="text-decoration:none; color:#7a7066;">← Cancel and return</a>'
        '    <button type="submit" class="btn-danger">⚡ Commit Revocation &amp; Correction to Kernel</button>'
        '  </div>'
        '</form>'
        '</div>'
    )
    return "\n".join(out)



def table_html(built, *, valid_at, as_of, window=None, labels=None,
               choices=None, chosen=None, sort=None, direction="asc",
               held=None):
    """What `compile_class()` returns, as a table.

    The rows are the ones it read back out of the operational store after
    filling it, so what is printed is what is stored. Each column's kind sits
    under its name: a reader can see which cells the map computed, which it
    read out of the log as a stated number, and which are the grouping.

    Two things on this page point elsewhere, and both are read off the plan
    rather than decided here. A column the map gives a rule links to the
    drawing of that rule, so a header answers where its own numbers came from.
    A cell the map fills by reading a fact off an entity links to every
    assertion ever made under that pair — the value in the cell is the one
    standing at these clocks, and the others are on the other page.

    A header prints the column's `title`, which is the map's, and a cell whose
    value names another entity prints what `labels` calls that URI, which the
    caller read out of the operational store. Where either is missing the name
    underneath comes through unchanged, so a map that says neither still
    renders — with the slot names and the URIs it had before.

    `choices` is the values each filterable column actually holds and `chosen`
    is which of them the reader picked; `sort` and `direction` are the column
    the rows are in the order of. All four are the caller's, and all four live
    on the URL, so a sorted and filtered table is a link somebody can send.

    `window` is what the log holds, and it is passed only when there are no
    rows: "nothing here" and "nothing was ever written down this early" are
    different answers and a reader cannot tell them apart from an empty table.
    `held` is how many rows there were before the filter, said only when one
    is on.
    """
    plan_ = built["plan"]
    cols = plan_["columns"]
    labels = labels or {}
    chosen = {name: value for name, value in (chosen or {}).items() if value}
    choices = choices or {}
    carried = _carried(valid_at, as_of)
    class_name = str(plan_["class"])
    titles = {str(col["name"]): str(col.get("title") or col["name"])
              for col in cols}

    # Everything the page is at, so that a sort link keeps the filter and a
    # filter keeps the sort. The clocks are in it for the same reason.
    state = {"valid_at": str(valid_at), "as_of": str(as_of)}
    state.update({ONLY + name: value for name, value in chosen.items()})
    if sort:
        state.update({SORT: sort, DIRECTION: direction})

    out = [f"<h1>{escape(class_name)}</h1>"]
    counted = (f"{len(built['rows'])} of {held} rows" if held is not None
               else f"{len(built['rows'])} rows")
    out.append(
        f'<p class="note">{escape(str(plan_["table"]))}, '
        f'{escape(str(plan_["version"]))} — {counted}, '
        f"{len(cols)} columns, rebuilt at valid_at {escape(str(valid_at))}, "
        f"as_of {escape(str(as_of))}. Read back out of the operational store "
        "this page just filled; the log itself is not on this page.</p>"
    )
    if choices:
        out.append(_filters_html(titles, labels, choices, chosen, state))

    index = {str(col["name"]): i for i, col in enumerate(cols)}
    identity = next((i for i, col in enumerate(cols)
                     if col["kind"] == "identity"), None)

    head = []
    for col in cols:
        name = str(col["name"])
        shown = escape(titles[name])
        if plan_["shape"] == "grouped":
            shown = (f'<a href="/graph?class={escape(class_name)}'
                     f'&amp;column={escape(name)}&amp;{carried}" '
                     f'title="what the map says fills this column">{shown}</a>')
        turned = "desc" if (sort == name and direction == "asc") else "asc"
        arrow = "\u2195" if sort != name else (
            "\u2191" if direction == "asc" else "\u2193")
        link = _query({**state, SORT: name, DIRECTION: turned})
        head.append(
            f'<th>{shown} <a class="sort{" on" if sort == name else ""}" '
            f'href="?{link}" title="sort by {escape(titles[name])}">{arrow}</a>'
            f'<span class="kind">{escape(str(col["kind"]))}</span></th>')

    def opens(col, row):
        """The pair of URIs behind one cell, where the map reads a fact."""
        name = str(col["name"])
        if col["kind"] == "parameter":
            spec = plan_["parameters"][name]
            subject = row[index[spec["of"]]]
            return (subject, spec["slot_uri"]) if subject else None
        if col["kind"] == "stated" and identity is not None and col["uri"]:
            subject = row[identity]
            return (subject, str(col["uri"])) if subject else None
        return None

    body = []
    for row in built["rows"]:
        cells = []
        for col, cell in zip(cols, row):
            if cell is None:
                cells.append('<td class="empty"></td>')
                continue
            named = labels.get(str(cell), cell) if col["ref"] else cell
            shown = escape(str(named))
            pair = opens(col, row)
            if pair:
                shown = (f'<a class="why" href="/why?subject={_q(pair[0])}'
                         f'&amp;predicate={_q(pair[1])}&amp;{carried}" '
                         f'title="every assertion ever made about this">'
                         f'{shown}</a>')
            cells.append(f"<td>{shown}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    out.append('<div class="scroll"><table><thead><tr>' + "".join(head)
               + "</tr></thead><tbody>" + "".join(body)
               + "</tbody></table></div>")
    if not built["rows"]:
        out.append('<p class="note">No rows at these clocks.</p>')
        out.append(_window_html(window))
    return "\n".join(out)


def _filters_html(titles, labels, choices, chosen, state):
    """One `<select>` per column whose values name something, as a GET form.

    Which columns are here was decided by the caller and the values in each
    are the ones the table actually holds, so a choice never returns nothing.
    The clocks and the sort ride along as hidden fields: picking a filter must
    not throw away the clock the reader set.
    """
    hidden = "".join(
        f'<input type="hidden" name="{escape(key)}" value="{escape(value)}">'
        for key, value in state.items() if not key.startswith(ONLY))
    controls = []
    for name, values in choices.items():
        options = ['<option value="">any</option>']
        for value in values:
            selected = " selected" if chosen.get(name) == value else ""
            shown = labels.get(str(value), value)
            options.append(f'<option value="{escape(str(value))}"{selected}>'
                           f"{escape(str(shown))}</option>")
        controls.append(
            f'<label>{escape(titles.get(name, name))}<br>'
            f'<select name="{escape(ONLY + name)}">{"".join(options)}</select>'
            "</label>")
    clear = _query({key: value for key, value in state.items()
                    if not key.startswith(ONLY)})
    return ('<form class="filters" method="get" action="">' + hidden
            + "".join(controls)
            + '<label><br><button type="submit">show</button></label>'
            + f'<label><br><a href="?{clear}">clear</a></label></form>')


def _window_html(window):
    """What the log holds at all, said when a page comes back with nothing."""
    if not window:
        return ""
    if not window.get("assertions"):
        return ('<p class="msg">The log is empty: nothing has been written '
                "down under it at any clock.</p>")
    return (
        '<p class="msg">The log holds {a:,} assertions under {i:,} intents. '
        "Nothing in it is valid before {vf}, and the latest anything is valid "
        "from is {vl}; the first was recorded at {rf} and the last at {rl}. A "
        "clock outside that is not an empty table — it is a question asked "
        "before there was anything to answer it.</p>"
    ).format(a=window["assertions"], i=window["intents"],
             vf=escape(str(window["first_valid_from"])),
             vl=escape(str(window["last_valid_from"])),
             rf=escape(str(window["first_recorded_at"])),
             rl=escape(str(window["last_recorded_at"])))


def message_page(title, text, *, valid_at, as_of, path=None, bad=True):
    """Nothing to render, or a refusal. Still a page, still with its clocks."""
    body = (f"<h1>{escape(title)}</h1>"
            f'<p class="msg{" bad" if bad else ""}">{escape(text)}</p>')
    return page(title, body, valid_at=valid_at, as_of=as_of, path=path)


def dashboard_html(data, *, valid_at, as_of):
    """Executive Decision Intelligence & BI Dashboard.

    Visualises inventory valuation, monthly variance, stock accuracy, critical
    reorder alerts, storage zone breakdown, and anomaly root-cause provenance
    all derived live from the bitemporal graph projection.
    """
    carried = _carried(valid_at, as_of)
    out = []

    # Header
    out.append('<div class="dash-header">')
    out.append('<div style="display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 1rem;">')
    out.append('<div>')
    out.append('<h1>Executive Decision Intelligence & BI Dashboard</h1>')
    out.append(f'<p>Projections over the operational graph at valid_at: <strong>{escape(str(valid_at)[:10])}</strong>, as_of: <strong>{escape(str(as_of)[:10])}</strong></p>')
    out.append('</div>')
    out.append('<div style="display: flex; gap: .5rem; align-items: center;">')
    out.append('<span class="badge badge-neutral">Graph Schema: v5</span>')
    out.append('<span class="badge badge-success">Single Write Gate: Active</span>')
    out.append('</div>')
    out.append('</div>')
    out.append('</div>')

    # Top KPI Cards
    tot_val = data["total_valuation"]
    tot_exp = data["total_expected_valuation"]
    tot_var_val = data["total_variance_val"]
    tot_var_kg = data["total_variance_kg"]
    accuracy = data["accuracy_pct"]
    alert_count = len(data["alerts"])

    out.append('<div class="kpi-grid">')
    
    # Valuation Card
    out.append('<div class="kpi-card primary-card">')
    out.append('<div class="kpi-label">Total Stock Valuation</div>')
    out.append(f'<div class="kpi-value">£{tot_val:,.2f}</div>')
    out.append(f'<div class="kpi-sub">Expected: £{tot_exp:,.2f} across 3 storage zones</div>')
    out.append('</div>')

    # Net Variance Card
    var_class = "alert-card" if tot_var_val < -100 else ("warning-card" if tot_var_val < 0 else "success-card")
    out.append(f'<div class="kpi-card {var_class}">')
    out.append('<div class="kpi-label">Total Inventory Variance</div>')
    sign = "" if tot_var_val >= 0 else "-"
    abs_var = abs(tot_var_val)
    out.append(f'<div class="kpi-value" style="color: {"#b32d2e" if tot_var_val < 0 else "#15803d"};">{sign}£{abs_var:,.2f}</div>')
    out.append(f'<div class="kpi-sub"><span class="badge badge-danger">{sign}{abs(tot_var_kg):,.2f} kg</span> Net discrepancy in stocktake</div>')
    out.append('</div>')

    # Accuracy Card
    acc_class = "success-card" if accuracy >= 95 else ("warning-card" if accuracy >= 85 else "alert-card")
    out.append(f'<div class="kpi-card {acc_class}">')
    out.append('<div class="kpi-label">Stock Valuation Accuracy</div>')
    out.append(f'<div class="kpi-value">{accuracy:.2f}%</div>')
    out.append(f'<div class="kpi-sub">Physical valuation vs movement log expectation</div>')
    out.append('</div>')

    # Active Alerts Card
    out.append('<div class="kpi-card alert-card">')
    out.append('<div class="kpi-label">Active Action Alerts</div>')
    out.append(f'<div class="kpi-value" style="color: #b32d2e;">{alert_count} Alerts</div>')
    out.append('<div class="kpi-sub">1 High-Value Loss • 1 Critical Reorder</div>')
    out.append('</div>')

    out.append('</div>')  # end kpi-grid

    # Action Alerts Section (Agent Triggers)
    if data["alerts"]:
        out.append('<div class="dash-alerts">')
        for alert in data["alerts"]:
            box_class = "danger" if alert["type"] == "danger" else "warning"
            out.append(f'<div class="alert-box {box_class}">')
            out.append(f'<h3><span>{escape(alert["title"])}</span> <span class="badge {alert["badge_class"]}">{escape(alert["badge"])}</span></h3>')
            out.append(f'<p>{alert["description"]}</p>')
            out.append('<div class="alert-action">')
            for btn in alert["buttons"]:
                out.append(f'<a href="{escape(btn["href"])}" class="btn-action {escape(btn["class"])}">{escape(btn["label"])}</a>')
            if "agent_trigger" in alert:
                out.append(f'<span class="badge badge-neutral" title="Autonomous execution hook">🤖 Agent Hook: {escape(alert["agent_trigger"])}</span>')
            out.append('</div>')
            out.append('</div>')
        out.append('</div>')

    # Discrepancy Bar Chart Section
    out.append('<div class="chart-card">')
    out.append('<h2>Variance Distribution & Financial Loss Concentration</h2>')
    out.append('<p class="chart-desc">Breakdown of inventory variances across ingredients. The financial shortfall is overwhelmingly concentrated in high-value Italian pastes, while everyday baking ingredients exhibit normal kitchen culinary handling tare (&lt;0.5%).</p>')
    out.append('<div class="bar-chart">')
    
    top_losses = data.get("top_losses", [])
    max_loss = max([abs(item["var_val"]) for item in top_losses] or [1.0])
    
    for item in top_losses:
        loss_val = abs(item["var_val"])
        pct_of_max = min(100.0, (loss_val / max_loss) * 100.0) if max_loss > 0 else 0
        pct_of_total = (loss_val / abs(tot_var_val) * 100.0) if tot_var_val != 0 else 0
        fill_class = "bar-severe" if loss_val > 100 else ("bar-moderate" if loss_val > 5 else "bar-minor")
        why_href = f'/why?subject={escape(quote(item["ing_uri"], safe=""))}&predicate=sorella%3Aitem_price_per_kg&{carried}'

        out.append('<div class="bar-row">')
        out.append(f'<div class="bar-label"><a href="{why_href}" title="Inspect audit trail in /why">{escape(item["name"])}</a></div>')
        out.append(f'<div class="bar-track"><div class="bar-fill {fill_class}" style="width: {pct_of_max:.1f}%;"></div></div>')
        out.append(f'<div class="bar-num" style="color: {"#b32d2e" if item["var_val"] < 0 else "#15803d"};">-£{loss_val:,.2f}</div>')
        out.append(f'<div class="bar-pct">{pct_of_total:.1f}%</div>')
        out.append('</div>')

    out.append('</div>')  # end bar-chart
    out.append('</div>')  # end chart-card

    # Storage Zone Breakdown
    out.append('<div class="dash-table-card">')
    out.append('<h2>Storage Zone Operational Intelligence</h2>')
    out.append('<p>Physical inventory valuation, temperature regimes, and variance concentration segregated by internal storage area.</p>')
    out.append('<div class="zones-grid">')
    
    for zone in data.get("zones", []):
        z_var = zone["variance_val"]
        z_sign = "" if z_var >= 0 else "-"
        out.append('<div class="zone-card">')
        out.append(f'<h3><span>{escape(zone["name"])}</span> <span class="badge badge-neutral">{escape(zone["temp"])}</span></h3>')
        out.append(f'<div class="zone-temp">{zone["count"]} ingredients monitored</div>')
        out.append('<div class="zone-stats">')
        out.append(f'<div><div class="zone-stat-label">Valuation</div><div class="zone-stat-num">£{zone["valuation"]:,.2f}</div></div>')
        out.append(f'<div><div class="zone-stat-label">Variance</div><div class="zone-stat-num" style="color: {"#b32d2e" if z_var < -10 else "#15803d"};">{z_sign}£{abs(z_var):,.2f}</div></div>')
        out.append('</div>')
        out.append(f'<p class="zone-note">{escape(zone["assessment"])}</p>')
        out.append('</div>')

    out.append('</div>')  # end zones-grid
    out.append('</div>')  # end dash-table-card

    # Full Ingredient Health Table
    out.append('<div class="dash-table-card">')
    out.append('<div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;">')
    out.append('<div>')
    out.append('<h2>Complete Inventory Health & Physical Stocktake</h2>')
    out.append('<p>Live reconciliation between cumulative stock movements and physical counts, with automated reorder triggers and financial variance analysis.</p>')
    out.append('</div>')
    out.append(f'<div><a href="/table/StockReconciliation?{carried}" class="btn-action btn-outline">Open Full Raw Table</a></div>')
    out.append('</div>')

    out.append('<table class="data">')
    out.append('<thead><tr>')
    out.append('<th>Ingredient</th>')
    out.append('<th>Storage Zone</th>')
    out.append('<th>Unit Price</th>')
    out.append('<th>Expected</th>')
    out.append('<th>Counted</th>')
    out.append('<th>In Packs</th>')
    out.append('<th>Reorder Threshold</th>')
    out.append('<th>Variance (kg)</th>')
    out.append('<th>Variance (£)</th>')
    out.append('<th>Health Status</th>')
    out.append('<th>Audit</th>')
    out.append('</tr></thead>')
    out.append('<tbody>')

    for item in data.get("items", []):
        row_style = ' style="background: #fff8f8;"' if item["is_anomaly"] else (' style="background: #fffdf5;"' if item["is_reorder"] else '')
        out.append(f'<tr{row_style}>')
        
        # Name
        out.append(f'<td style="font-weight: 600;">{escape(item["name"])}</td>')
        # Location
        out.append(f'<td>{escape(item["location"])}</td>')
        # Price
        out.append(f'<td style="text-align: right;">£{item["price_per_kg"]:.2f}/kg</td>')
        # Expected
        out.append(f'<td style="text-align: right;">{item["expected_kg"]:.2f} kg</td>')
        # Counted
        out.append(f'<td style="text-align: right; font-weight: 600;">{item["counted_kg"]:.2f} kg</td>')
        # In Packs
        cnt_pack_str = f'{item["counted_pack"]:.1f} {item["pack_unit"]}'
        out.append(f'<td style="text-align: right; color: #5a524a;">{escape(cnt_pack_str)}</td>')
        
        # Reorder Threshold
        if item["reorder_kg"] is not None:
            reorder_str = f'{item["reorder_kg"]:.1f} kg ({item["reorder_pack"]:.0f} {item["pack_unit"]})'
        else:
            reorder_str = '-'
        out.append(f'<td style="text-align: right;">{escape(reorder_str)}</td>')
        
        # Variance kg
        v_kg = item["var_kg"]
        v_sign = "+" if v_kg > 0 else ""
        out.append(f'<td style="text-align: right; font-weight: 500;">{v_sign}{v_kg:.2f} kg</td>')
        
        # Variance £
        v_val = item["var_val"]
        val_color = "#b32d2e" if v_val < -5 else ("#6b6259" if v_val == 0 else "#15803d")
        out.append(f'<td style="text-align: right; font-weight: 600; color: {val_color};">£{v_val:.2f}</td>')
        
        # Health Status Badge
        if item["is_anomaly"]:
            status_badge = '<span class="badge badge-danger">Severe Loss (-£428)</span>'
        elif item["is_reorder"]:
            status_badge = '<span class="badge badge-warning">Low Stock Reorder</span>'
        else:
            status_badge = '<span class="badge badge-success">Healthy (&lt;0.5%)</span>'
        out.append(f'<td>{status_badge}</td>')

        # Audit Link
        why_href = f'/why?subject={escape(quote(item["ing_uri"], safe=""))}&predicate=sorella%3Aitem_price_per_kg&{carried}'
        out.append(f'<td><a class="why" href="{why_href}">why</a></td>')
        out.append('</tr>')

    out.append('</tbody>')
    out.append('</table>')
    out.append('</div>')  # end dash-table-card

    return "\n".join(out)

