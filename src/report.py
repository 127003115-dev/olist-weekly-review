"""Generate four labelled matplotlib charts and a five-page evidence report.

All calculations originate in SQL query outputs or SQL summaries, not pandas.
"""
import csv
import json
import sqlite3
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from pipeline import ROOT
from analyze import analyze

def read(name):
    with (ROOT/'reports/results'/f'{name}.csv').open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))

def main():
    analyze()
    folder=ROOT/'reports'; charts=folder/'charts';charts.mkdir(exist_ok=True)
    audit=json.loads((folder/'quality.json').read_text())
    monthly=read('01_monthly_revenue');daily=read('03_rolling_orders')
    repeat=read('04_repeat_purchase')[0]; groups=read('05_delivery_reviews')
    late=next(r for r in groups if r['breakdown']=='delivery_group' and r['delivery_group']=='Late')
    ontime=next(r for r in groups if r['breakdown']=='delivery_group' and r['delivery_group']=='On time / early')
    buckets=read('07_delay_buckets'); adjusted=read('08_month_state_comparison')[0]
    top=read('02_top_categories'); sp=[r for r in top if r['customer_state']=='SP']
    con=sqlite3.connect(ROOT/'data/olist.sqlite')
    summary=con.execute('''SELECT COUNT(*),SUM(item_cents)/100.0,
      SUM(delay_days>0),SUM(review_score IS NOT NULL),AVG(delay_days),
      MIN(purchased_at),MAX(purchased_at) FROM mart_delivered_orders''').fetchone()
    dates=con.execute('SELECT MIN(purchased_at),MAX(purchased_at) FROM mart_orders').fetchone()
    con.close()
    total,gmv,late_n,reviewed,delay_avg,first,last=summary
    gap=float(ontime['avg_review_score'])-float(late['avg_review_score'])
    ratio=float(late['low_review_pct'])/float(ontime['low_review_pct'])
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                          'axes.labelcolor':'#26364a','text.color':'#26364a','figure.facecolor':'white'})
    def save(fig,name):
        fig.tight_layout();fig.savefig(charts/f'{name}.png',dpi=180,bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.4,2.35))
    ax.plot([datetime.fromisoformat(r['month']) for r in monthly],[float(r['revenue_brl'])/1000 for r in monthly],color='#117f88',lw=2)
    ax.set(title='1. Monthly delivered merchandise GMV',ylabel='GMV (BRL thousands)',xlabel='Purchase month; freight excluded')
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3));ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.grid(axis='y',alpha=.2);save(fig,'monthly_gmv')
    fig,ax=plt.subplots(figsize=(7.4,2.35))
    ax.plot([datetime.fromisoformat(r['day']) for r in daily],[float(r['rolling_7day_average']) if r['rolling_7day_average'] else float('nan') for r in daily],color='#3562a6',lw=1.5)
    ax.set(title='2. Seven-day rolling average of placed orders',ylabel='Orders per day',xlabel='Purchase date; all valid statuses, zero days included')
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3));ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.grid(axis='y',alpha=.2);save(fig,'rolling_orders')
    fig,ax=plt.subplots(figsize=(7.4,2.5))
    bars=ax.bar([r['label'] for r in buckets],[float(r['low_review_pct']) for r in buckets],color=['#117f88','#e6a546','#dc793e','#b84649'])
    for b,r in zip(bars,buckets):ax.text(b.get_x()+b.get_width()/2,b.get_height()+1,f"{float(r['low_review_pct']):.1f}%\nn={int(r['orders']):,}",ha='center',fontsize=8)
    ax.set(title='3. Low reviews rise with delivery lateness',ylabel='Reviews scored 1-2 (%)',xlabel='Actual delivery date minus promised date')
    ax.set_ylim(0,100);ax.grid(axis='y',alpha=.15);save(fig,'delay_reviews')
    fig,ax=plt.subplots(figsize=(7.4,2.2))
    names=[r['category'].replace('_',' ') for r in sp]
    bars=ax.barh(names[::-1],[float(r['revenue_brl'])/1000 for r in sp[::-1]],color='#3562a6')
    ax.set(title='4. Top three product categories in Sao Paulo (SP)',xlabel='Delivered merchandise GMV (BRL thousands)')
    ax.grid(axis='x',alpha=.2);save(fig,'sp_categories')

    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyCustom',fontName='Helvetica',fontSize=9.2,leading=13,spaceAfter=7,textColor=colors.HexColor('#26364a')))
    styles.add(ParagraphStyle(name='SmallCustom',fontName='Helvetica',fontSize=7.4,leading=10,spaceAfter=5,textColor=colors.HexColor('#42546a')))
    styles['Title'].fontSize=23;styles['Title'].leading=27;styles['Title'].textColor=colors.HexColor('#13314b')
    styles['Heading1'].fontSize=17;styles['Heading1'].leading=21;styles['Heading1'].textColor=colors.HexColor('#13314b')
    styles['Heading2'].fontSize=11;styles['Heading2'].leading=15;styles['Heading2'].spaceBefore=7
    story=[]
    def p(text,style='BodyCustom'):story.append(Paragraph(text,styles[style]))
    def h(text):p(text,'Heading2')
    def table(data,widths):
        rows=[[Paragraph(str(c),styles['SmallCustom']) for c in row] for row in data]
        t=Table(rows,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f0f5')),('VALIGN',(0,0),(-1,-1),'TOP'),
           ('LINEBELOW',(0,0),(-1,0),.7,colors.HexColor('#bccbd6')),('BOTTOMPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4)]))
        story.append(t);story.append(Spacer(1,8))
    def img(name,height):story.append(Image(str(charts/f'{name}.png'),width=490,height=height))
    def new():story.append(PageBreak())
    p('Weekly business review','Title')
    p('Olist marketplace | Historical order cohorts | Python + SQLite', 'SmallCustom')
    p(f'<b>Key finding:</b> among reviewed, valid delivered orders, late arrivals have an average review score of {float(late["avg_review_score"]):.2f} versus {float(ontime["avg_review_score"]):.2f} for on-time arrivals. Their low-review rate is {ratio:.1f} times as high. Prioritize delivery reliability and test whether intervention improves satisfaction.')
    table([['Source orders','Valid delivered orders','Delivered merchandise GMV'],
           [f'{audit["source_counts"]["orders"]:,}',f'{total:,}',f'BRL {gmv:,.2f}']], [163,163,164])
    h('Metric contract: one North Star, four supporting / guardrail metrics')
    table([['Metric and exact formula','Business purpose'],
      ['North Star: weekly on-time fulfilled orders = COUNT(valid orders with final status delivered and actual calendar delivery date &lt;= promised date), grouped by Monday purchase week.','Counts completed customer promises; volume alone can hide poor delivery.'],
      ['On-time delivery rate = 100 x on-time fulfilled orders / all valid delivered orders in the same purchase week.','Reliability guardrail while order volume grows.'],
      ['Low-review rate = 100 x valid delivered orders with canonical score 1 or 2 / valid delivered orders with a canonical review, in the same purchase week.','Measures dissatisfaction among responding customers.'],
      ['Delivered merchandise GMV = SUM(item price cents) / 100 for valid delivered orders, by purchase week; freight excluded.','Tracks merchandise value fulfilled; not marketplace net revenue.'],
      ['Failed-order rate = 100 x valid orders with final status canceled or unavailable / all valid placed orders in the same purchase week.','Guards against improving delivery statistics by failing more orders.']], [330,160])
    h('Scope and weekly use')
    p(f'All-source purchase range: {dates[0][:10]} to {dates[1][:10]}. Currency: BRL, unadjusted for inflation. Weekly cohorts are Monday-Sunday; historical final outcomes are used. For a live WBR, review cohorts after 45 days and mark unresolved orders separately; do not interpret these final outcomes as information available at purchase time.')
    p('Zero denominators return NULL. Quarantined orders stay in the audited mart but are excluded from metric views. Customer reviews are optional, so review coverage must accompany any satisfaction comparison. The dataset lacks marketplace fees, returns and a change log; it supports GMV and historical cohorts, not net revenue or point-in-time retention.','SmallCustom')
    new();p('Pipeline and data quality','Heading1')
    p('Nine CSVs load into raw text tables. Clean staging normalizes timestamps and city/state fields, represents money in integer cents and selects one canonical review per order. Item and payment totals are aggregated separately before the one-row-per-order mart. A fresh temporary database replaces the published database only after all required checks pass.')
    h('Observed quality failures and explicit source policy')
    important=['01_order_keys','02_customer_keys','03_orphan_customers','04_delivery_chronology','05_payment_reconciliation','06_delivered_missing_date','07_review_scores','08_item_keys','09_orphan_items','10_missing_payment','11_missing_review','12_order_timestamps','13_negative_money','14_clean_delivery_alarm','15_mart_grain_alarm']
    rows=[['Check','Failing rows','Handling / rationale']]
    for name in important:
        r=next(r for r in audit['checks'] if r['check']==name)
        action={'abort':'Alarm if nonzero; no silent repairs.','quarantine':'Retain raw/mart; exclude from valid views.','flag':'Retain; expose flag / missingness in audit.'}[r['action']]
        rows.append([r['description'],str(r['failing_rows']),action])
    table(rows,[232,58,200])
    p(f'Additional dimension/payment key and payment-order relationship checks all pass (see quality.csv). {audit["quarantined_orders"]} distinct orders are quarantined. {audit["review_rows_removed"]:,} extra review rows are collapsed using latest answer timestamp, then creation timestamp, review ID and source row order. Raw reviews remain intact. Counts above are per check; overlapping failures are not additive.','SmallCustom')
    p('Default execution raises a quality alarm on every nonzero check. After review, --apply-source-policy permits only documented flag/quarantine cases; structural, invalid-money, clean-layer and grain failures still stop publication. Payment mismatch tolerance is BRL 1.00, a business reconciliation tolerance rather than proof of equality; no amounts are rewritten and GMV comes from items.','SmallCustom')
    new();p('SQL results: growth and demand','Heading1')
    p('Part C is executed entirely in SQLite SQL using CTEs and window functions. Complete CSV results for every query are included in reports/results; values shown here are compact excerpts.')
    img('monthly_gmv',163)
    recent=monthly[-3:]
    table([['Purchase month','Delivered GMV (BRL)','MoM growth (%)']]+[[r['month'][:7],f"{float(r['revenue_brl']):,.2f}",r['growth_pct'] or 'NULL'] for r in recent],[163,163,164])
    p('Revenue definition: delivered merchandise GMV, attributed to purchase month, excluding freight, canceled/unavailable orders and quarantine. Interior zero-GMV months are retained before LAG. First-month / zero-base growth is NULL. Exclude the final source month and trailing months with no delivered purchases; August 2018 is shown but subject to end-of-extract fulfillment censoring.','SmallCustom')
    img('rolling_orders',161)
    peak=max((r for r in daily if r['rolling_7day_average']),key=lambda r:float(r['rolling_7day_average']))
    p(f'The highest seven-day average is {float(peak["rolling_7day_average"]):.2f} orders/day on {peak["day"]}. A recursive calendar fills zero-order days before a seven-row window; the first six days return NULL because a full window is unavailable. Counts include all valid order statuses. Late-extract demand is incomplete.','SmallCustom')
    h('Repeat purchase rate: choose the correct customer key')
    p(f'{int(repeat["repeat_customers"]):,} of {int(repeat["customers"]):,} customers made at least two valid delivered purchases: <b>{float(repeat["repeat_purchase_pct"]):.3f}%</b>. GROUP BY customer_unique_id identifies people across order-specific customer_id values. This observed-window rate gives customers unequal follow-up time; it is not a cohort retention estimate.')
    new();p('SQL results: fulfillment and satisfaction','Heading1')
    img('delay_reviews',178)
    table([['Delivered & reviewed','Orders','Mean delay (days)','Mean review','Score 1-2 (%)']]+[[r['delivery_group'],f"{int(r['orders']):,}",f"{float(r['avg_delay_days']):.2f}",f"{float(r['avg_review_score']):.2f}",f"{float(r['low_review_pct']):.2f}"] for r in [ontime,late]],[142,62,105,78,103])
    p(f'All {total:,} valid delivered orders average {delay_avg:.2f} calendar days versus the estimate; negative means early. {late_n:,} ({100*late_n/total:.2f}%) arrived late. The reviewed sample covers {reviewed:,}/{total:,} deliveries ({100*reviewed/total:.2f}%). Review-score-level results (1-5) are also saved in 05_delivery_reviews.csv.','SmallCustom')
    p(f'Within customer-state / purchase-month cells containing at least 20 late and 20 on-time reviewed deliveries, {int(adjusted["cells_with_lower_late_score"])} of {int(adjusted["cells"])} cells have lower late-arrival scores. The late-order-weighted gap is {float(adjusted["weighted_score_gap"]):.2f} points. This supports the descriptive pattern after two simple stratifications; it does not establish causality.','SmallCustom')
    img('sp_categories',151)
    p('Top categories are ranked per customer state using DENSE_RANK on item-price GMV. Ties at rank three are retained. The chart shows SP as an example; 02_top_categories.csv contains all states. Neither payment rows nor reviews are joined at item grain, preventing revenue fan-out.','SmallCustom')
    new();p('Memo to the Vice President','Heading1')
    p('<b>To:</b> VP, Marketplace Operations<br/><b>Subject:</b> Pilot a delivery exception desk to protect customer satisfaction')
    h('Decision requested')
    p('Authorize a six-week pilot of a delivery exception desk owned by the logistics operations lead. Each morning, prioritize in-flight orders due within 48 hours that have no carrier handoff or no tracking update for 48 hours. Assign a named owner to resolve the seller/carrier issue the same day and send the customer a truthful delivery update. This targets promises at risk before they are missed.')
    h('Why this is the priority')
    p(f'In the historical Olist snapshot, {late_n:,} of {total:,} valid delivered orders ({100*late_n/total:.2f}%) arrived after the promised calendar date. Among reviewed deliveries, late orders average {float(late["avg_review_score"]):.2f}/5 versus {float(ontime["avg_review_score"]):.2f}/5 for on-time or early orders: a {gap:.2f}-point gap. Reviews scored 1-2 occur on {float(late["low_review_pct"]):.2f}% of late orders versus {float(ontime["low_review_pct"]):.2f}% of on-time orders ({ratio:.1f}x). The delay-bucket chart shows how dissatisfaction varies as lateness increases.')
    p(f'The result is not solely a comparison of different months or states: {int(adjusted["cells_with_lower_late_score"])} of {int(adjusted["cells"])} sufficiently populated state/month cells show the same direction. Nevertheless, difficult shipments, seller behavior and product issues could affect both delivery and reviews. Reviews are voluntary, and the snapshot provides final outcomes rather than daily operational history. The evidence supports a pilot, not a promised causal uplift.')
    h('How to run and judge the pilot')
    p('Randomly assign eligible at-risk orders to the exception desk or current operations, stratifying by customer state and seller. Keep original promised dates fixed; do not improve the metric by extending them. Collect a standardized post-delivery survey in both groups. The source dataset has no tracking-event history, so live carrier events must be connected before this eligibility rule can be evaluated prospectively.')
    p('Pre-register a target of a 20% relative reduction in late-delivery rate among eligible orders and a reduction in the score-1/2 share, evaluated on mature purchase cohorts. These are proposed pilot targets, not predicted effects. Compare survey response rates and confidence intervals; determine sample size from live baseline volume before launch. Keep incremental cost below BRL 5 per treated order and require no increase in cancellations or unavailable orders.')
    h('Business implication')
    p('Weekly on-time fulfilled orders should be the North Star: growth is valuable when customer promises are kept. Pair it with fulfillment GMV, on-time rate, low-review rate and failed-order rate. Expand the desk only if the randomized pilot improves reliability and satisfaction within the cost guardrail; otherwise revisit the intervention rather than claiming the historical association proves success.')
    p('Source: Olist, Brazilian E-Commerce Public Dataset by Olist (2016-2018), Kaggle: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce. Customer identity documentation: https://www.kaggle.com/olistbr/brazilian-ecommerce/metadata. Analysis and code created for this project; no public notebook code used.','SmallCustom')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#657589'))
        canvas.drawString(48,27,'Olist | Weekly business review | Historical analysis')
        canvas.drawRightString(A4[0]-48,27,f'{doc.page} / 5')
    path=folder/'weekly_business_review.pdf'
    SimpleDocTemplate(str(path),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=42,bottomMargin=43).build(story,onFirstPage=footer,onLaterPages=footer)
    from pypdf import PdfReader
    count=len(PdfReader(path).pages)
    if count!=5: raise RuntimeError(f'Report must have exactly five designed pages; got {count}. Adjust layout.')
    facts={'delivered_orders':total,'gmv_brl':gmv,'late_orders':late_n,'reviewed_orders':reviewed,
           'mean_delay_days':delay_avg,'late':late,'on_time':ontime,'repeat':repeat,'stratified':adjusted}
    (folder/'summary.json').write_text(json.dumps(facts,indent=2))
    print(f'Created {path} ({count} pages)')

if __name__=='__main__':main()
