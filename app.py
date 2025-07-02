from flask import Flask, render_template, request, flash, send_file, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
import pandas as pd, os, io, re, time
from datetime import datetime, timedelta
from dateutil import parser

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sales.db'
app.config['SECRET_KEY'] = 'changeme'
db = SQLAlchemy(app)

class Order(db.Model):
    id     = db.Column(db.Integer, primary_key=True)
    date   = db.Column(db.DateTime, nullable=False)
    nota   = db.Column(db.String(50))
    code   = db.Column(db.String(50), nullable=False)
    name   = db.Column(db.String(200), nullable=False)
    qty    = db.Column(db.Integer, nullable=False)
    harga1 = db.Column(db.Integer)
    harga2 = db.Column(db.Integer)
    disc1  = db.Column(db.Integer)
    disc2  = db.Column(db.Integer)
    harga3 = db.Column(db.Integer)
    jumlah = db.Column(db.Integer)

def seed_initial():
    if not Order.query.first():
        path = os.path.join(app.root_path, 'orders_seed.csv')
        if os.path.exists(path):
            df = pd.read_csv(path)
            df['name'] = df['name'].fillna('Tidak diketahui')
            df = df.dropna(subset=['date','code'])
            df['date'] = pd.to_datetime(df['date'])
            df.to_sql('order', db.engine, if_exists='append', index=False,
                      method='multi', chunksize=50)

def parse_date(s):
    if not s: return None
    s = re.sub(r'\s+','',s)
    try:
        return datetime.strptime(s, '%Y-%m-%d')
    except ValueError:
        try:
            return parser.parse(s, dayfirst=True)
        except:
            return None

@app.route('/')
def dashboard():
    start_dt = parse_date(request.args.get('start'))
    end_dt   = parse_date(request.args.get('end'))
    
    # Add a day to end_dt to include the full day
    if end_dt:
        end_dt = end_dt + timedelta(days=1)
    
    # Query for filtered data
    q = Order.query
    if start_dt: q = q.filter(Order.date >= start_dt)
    if end_dt:   q = q.filter(Order.date < end_dt)

    orders_count = q.count()
    items_sold   = q.with_entities(func.sum(Order.qty)).scalar() or 0
    revenue      = q.with_entities(func.sum(Order.qty*Order.harga2)).scalar() or 0
    cost         = q.with_entities(func.sum(Order.qty*Order.harga1)).scalar() or 0
    profit       = revenue - cost

    # Grafik 1: Top 10 produk semua waktu (dengan total harga)
    all_time_top = (Order.query.with_entities(
                        Order.code, 
                        Order.name,
                        func.sum(Order.qty).label('total_qty'),
                        func.sum(Order.qty*Order.harga2).label('total_revenue')
                    )
                    .group_by(Order.code)
                    .order_by(func.sum(Order.qty).desc())
                    .limit(10).all())
    all_time_labels = [f"{r.name} ({r.code})" for r in all_time_top]
    all_time_qty_values = [r.total_qty for r in all_time_top]
    all_time_revenue_values = [r.total_revenue for r in all_time_top]

    # Grafik 2: Top 10 produk berdasarkan filter tanggal (dengan total harga)
    filtered_top = (q.with_entities(
                        Order.code, 
                        Order.name,
                        func.sum(Order.qty).label('total_qty'),
                        func.sum(Order.qty*Order.harga2).label('total_revenue')
                    )
                    .group_by(Order.code)
                    .order_by(func.sum(Order.qty).desc())
                    .limit(10).all())
    bar_labels = [f"{r.name} ({r.code})" for r in filtered_top]
    bar_qty_values = [r.total_qty for r in filtered_top]
    bar_revenue_values = [r.total_revenue for r in filtered_top]

    # Grafik 3: Trend laba per hari
    trend = (q.with_entities(func.date(Order.date).label('d'),
                             func.sum(Order.qty*Order.harga2 -
                                      Order.qty*Order.harga1).label('laba'))
               .group_by(func.date(Order.date))
               .order_by(func.date(Order.date)).all())
    trend_labels = [r.d for r in trend]
    trend_values = [r.laba for r in trend]

    # Timestamp untuk mencegah cache
    timestamp = int(time.time())

    return render_template('dashboard.html',
                           orders_count=orders_count,
                           items_sold=items_sold,
                           revenue=revenue,
                           profit=profit,
                           all_time_labels=all_time_labels,
                           all_time_qty_values=all_time_qty_values,
                           all_time_revenue_values=all_time_revenue_values,
                           bar_labels=bar_labels,
                           bar_qty_values=bar_qty_values,
                           bar_revenue_values=bar_revenue_values,
                           trend_labels=trend_labels,
                           trend_values=trend_values,
                           start=request.args.get('start'),
                           end=request.args.get('end'),
                           timestamp=timestamp)

@app.route('/orders')
def orders():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    start_dt = parse_date(request.args.get('start'))
    end_dt   = parse_date(request.args.get('end'))
    search_query = request.args.get('search', '')
    
    # Add a day to end_dt to include the full day
    if end_dt:
        end_dt = end_dt + timedelta(days=1)
    
    query = Order.query
    
    # Apply date filters
    if start_dt: 
        query = query.filter(Order.date >= start_dt)
    if end_dt:
        query = query.filter(Order.date < end_dt)
        
    # Apply search filter if provided
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Order.nota.ilike(search_term),
                Order.code.ilike(search_term),
                Order.name.ilike(search_term)
            )
        )
    
    # Hitung total untuk semua data yang terfilter
    total_items = query.with_entities(func.sum(Order.qty)).scalar() or 0
    total_revenue = query.with_entities(func.sum(Order.qty*Order.harga2)).scalar() or 0
    
    # Order by date desc
    query = query.order_by(Order.date.desc())
    
    try:
        pagination = query.paginate(page=page, per_page=per_page)
    except:
        pagination = query.paginate(page=1, per_page=per_page)
    
    return render_template('orders.html', 
                          orders=pagination.items, 
                          pagination=pagination,
                          total_items=total_items,
                          total_revenue=total_revenue,
                          start=request.args.get('start'),
                          end=request.args.get('end'),
                          search=search_query)

@app.route('/orders/export')
def export_orders():
    start_dt = parse_date(request.args.get('start'))
    end_dt   = parse_date(request.args.get('end'))
    search_query = request.args.get('search', '')
    
    # Add a day to end_dt to include the full day
    if end_dt:
        end_dt = end_dt + timedelta(days=1)
    
    query = Order.query
    
    # Apply date filters
    if start_dt: 
        query = query.filter(Order.date >= start_dt)
    if end_dt:
        query = query.filter(Order.date < end_dt)
        
    # Apply search filter if provided
    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            or_(
                Order.nota.ilike(search_term),
                Order.code.ilike(search_term),
                Order.name.ilike(search_term)
            )
        )
    
    df = pd.read_sql(query.statement, db.engine)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
        df.to_excel(w, index=False, sheet_name='Orders')
    buf.seek(0)
    return send_file(buf, as_attachment=True, download_name='orders.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == '__main__':
    with app.app_context():
        db.create_all(); seed_initial()
    app.run(debug=True)