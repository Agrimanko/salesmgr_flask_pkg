import pandas as pd
import os
from flask import Flask, render_template, request, url_for, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from datetime import datetime, timedelta

# --- Konfigurasi Aplikasi ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.instance_path, 'sales.db')}"
app.config['SECRET_KEY'] = 'ganti-dengan-kunci-rahasia-anda-yang-lebih-aman'
db = SQLAlchemy(app)

# --- Model Database ---
class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kode = db.Column(db.String(50), unique=True, nullable=False)
    nama = db.Column(db.String(200), nullable=False)
    harga1 = db.Column(db.Float, default=0)
    harga2 = db.Column(db.Float, default=0)
    qty = db.Column(db.Integer, default=0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    regno = db.Column(db.String(50), unique=True, nullable=False)
    kode = db.Column(db.String(50), nullable=False)
    nama = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    harga1 = db.Column(db.Float)
    harga2 = db.Column(db.Float)
    jumlah = db.Column(db.Float)

# --- Fungsi Seeding ---
def seed_database():
    if Stock.query.first() or Order.query.first():
        return
    try:
        df_stock = pd.read_csv(os.path.join(app.root_path, 'stock_seed.csv'))
        df_stock.to_sql('stock', db.engine, if_exists='append', index=False)
    except Exception as e:
        print(f"Peringatan: Gagal seeding 'stock_seed.csv'. Error: {e}")
    try:
        df_orders = pd.read_csv(os.path.join(app.root_path, 'orders_seed.csv'), parse_dates=['date'])
        df_orders.to_sql('order', db.engine, if_exists='append', index=False)
    except Exception as e:
        print(f"Peringatan: Gagal seeding 'orders_seed.csv'. Error: {e}")

# --- Fungsi Bantuan ---
def parse_date(date_string):
    if not date_string: return None
    try: return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError: return None

# --- Rute Aplikasi ---
@app.route('/')
def dashboard():
    start_str = request.args.get('start', '')
    end_str = request.args.get('end', '')
    start_dt = parse_date(start_str)
    end_dt = parse_date(end_str)
    q = Order.query
    if start_dt: q = q.filter(Order.date >= start_dt)
    if end_dt: q = q.filter(Order.date < end_dt + timedelta(days=1))
    total_orders = q.with_entities(func.count(Order.id)).scalar() or 0
    total_revenue = q.with_entities(func.sum(Order.jumlah)).scalar() or 0
    total_profit = q.with_entities(func.sum(Order.jumlah - (Order.qty * Order.harga1))).scalar() or 0
    items_in_stock = db.session.query(func.count(Stock.id)).filter(Stock.qty > 0).scalar() or 0
    top_10_products = (q.with_entities(Order.nama, func.sum(Order.qty).label('total_qty'))
                        .group_by(Order.nama).order_by(func.sum(Order.qty).desc()).limit(10).all())
    chart_labels = [item.nama for item in top_10_products]
    chart_values = [item.total_qty for item in top_10_products]
    all_time_top_10 = (db.session.query(Order.nama, func.sum(Order.qty).label('total_qty'))
                        .group_by(Order.nama).order_by(func.sum(Order.qty).desc()).limit(10).all())
    all_time_chart_labels = [item.nama for item in all_time_top_10]
    all_time_chart_values = [item.total_qty for item in all_time_top_10]
    return render_template('dashboard_new.html',
                           total_orders=total_orders, total_revenue=total_revenue,
                           total_profit=total_profit, items_in_stock=items_in_stock,
                           chart_labels=chart_labels, chart_values=chart_values,
                           all_time_chart_labels=all_time_chart_labels,
                           all_time_chart_values=all_time_chart_values,
                           start=start_str, end=end_str)

@app.route('/stock')
def stock_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    # 'view' bisa bernilai 'available', 'empty', atau 'all'
    view_mode = request.args.get('view', 'all') # Defaultnya adalah 'all'
    
    # LOGIKA BARU: Mulai dengan query dasar
    q = Stock.query
    title = "Manajemen Stok" # Judul default

    # Langkah 1: Terapkan pencarian terlebih dahulu pada SEMUA stok
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Stock.kode.ilike(search_term), Stock.nama.ilike(search_term)))
    
    # Langkah 2: BARU setelah itu, filter berdasarkan mode tampilan (tersedia/kosong)
    if view_mode == 'empty':
        q = q.filter(Stock.qty <= 0)
        title = "Stok Kosong"
    elif view_mode == 'available':
        q = q.filter(Stock.qty > 0)
        title = "Stok Tersedia"
    # Jika view_mode 'all', tidak ada filter tambahan
        
    # Urutkan dan lakukan paginasi
    pagination = q.order_by(Stock.nama).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('stock.html', pagination=pagination, title=title, search=search, view=view_mode)

@app.route('/stock/new', methods=['GET', 'POST'])
def new_stock():
    if request.method == 'POST':
        kode = request.form['kode'].strip()
        if not kode:
            flash('Kode barang tidak boleh kosong!', 'danger')
            return redirect(url_for('new_stock'))
        if Stock.query.filter_by(kode=kode).first():
            flash('Kode barang sudah ada!', 'danger')
            return redirect(url_for('new_stock'))
        new_item = Stock(
            kode=kode, nama=request.form['nama'],
            harga1=float(request.form.get('harga1', 0)),
            harga2=float(request.form.get('harga2', 0)),
            qty=int(request.form.get('qty', 0))
        )
        db.session.add(new_item)
        db.session.commit()
        flash('Barang baru berhasil ditambahkan!', 'success')
        return redirect(url_for('stock_list'))
    return render_template('stock_form.html', title="Tambah Barang Baru", form_action=url_for('new_stock'))

@app.route('/stock/edit/<int:id>', methods=['GET', 'POST'])
def edit_stock(id):
    item = Stock.query.get_or_404(id)
    if request.method == 'POST':
        item.kode = request.form['kode']
        item.nama = request.form['nama']
        item.harga1 = float(request.form.get('harga1', 0))
        item.harga2 = float(request.form.get('harga2', 0))
        item.qty = int(request.form.get('qty', 0))
        db.session.commit()
        flash('Data barang berhasil diperbarui!', 'success')
        return redirect(url_for('stock_list'))
    return render_template('stock_form.html', title="Edit Barang", item=item, form_action=url_for('edit_stock', id=id))

@app.route('/stock/delete/<int:id>', methods=['POST'])
def delete_stock(id):
    item = Stock.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Barang berhasil dihapus!', 'success')
    return redirect(url_for('stock_list'))

@app.route('/orders')
def orders_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    q = Order.query
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Order.regno.ilike(search_term), Order.kode.ilike(search_term), Order.nama.ilike(search_term)))
    pagination = q.order_by(Order.date.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('orders_new.html', pagination=pagination, search=search)

@app.route('/order/new', methods=['GET', 'POST'])
def new_order():
    if request.method == 'POST':
        kode_barang = request.form['kode'].strip()
        qty_jual = int(request.form.get('qty', 0))
        stock_item = Stock.query.filter_by(kode=kode_barang).first()
        if not stock_item:
            flash(f'Barang dengan kode {kode_barang} tidak ditemukan!', 'danger')
            return redirect(url_for('new_order'))
        last_order = Order.query.order_by(Order.id.desc()).first()
        if last_order and last_order.regno.startswith('N'):
            try: last_num = int(last_order.regno[7:])
            except: last_num = 0
            new_num = last_num + 1
        else: new_num = 1
        regno = f"N{datetime.now().strftime('%y%m%d')}{new_num:04d}"
        new_order_item = Order(
            date=datetime.strptime(request.form['date'], '%Y-%m-%d'), regno=regno,
            kode=kode_barang, nama=stock_item.nama, qty=qty_jual,
            harga1=stock_item.harga1, harga2=stock_item.harga2,
            jumlah=qty_jual * stock_item.harga2
        )
        stock_item.qty -= qty_jual
        db.session.add(new_order_item)
        db.session.commit()
        flash('Order baru berhasil ditambahkan, stok telah diperbarui!', 'success')
        return redirect(url_for('orders_list'))
    return render_template('order_form.html', title="Tambah Order Baru", form_action=url_for('new_order'))

@app.route('/order/edit/<int:id>', methods=['GET', 'POST'])
def edit_order(id):
    order = Order.query.get_or_404(id)
    stock_item = Stock.query.filter_by(kode=order.kode).first()
    qty_lama = order.qty
    if request.method == 'POST':
        qty_baru = int(request.form.get('qty', 0))
        selisih_qty = qty_baru - qty_lama
        if stock_item: stock_item.qty -= selisih_qty
        order.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        order.qty = qty_baru
        order.jumlah = qty_baru * order.harga2
        db.session.commit()
        flash('Order berhasil diperbarui, stok telah disesuaikan!', 'success')
        return redirect(url_for('orders_list'))
    return render_template('order_form.html', title="Edit Order", order=order, form_action=url_for('edit_order', id=id))

@app.route('/order/delete/<int:id>', methods=['POST'])
def delete_order(id):
    order = Order.query.get_or_404(id)
    stock_item = Stock.query.filter_by(kode=order.kode).first()
    if stock_item: stock_item.qty += order.qty
    db.session.delete(order)
    db.session.commit()
    flash('Order berhasil dihapus, stok telah dikembalikan!', 'success')
    return redirect(url_for('orders_list'))

if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(app.instance_path): os.makedirs(app.instance_path)
        db.create_all()
        seed_database()
    app.run(debug=True)