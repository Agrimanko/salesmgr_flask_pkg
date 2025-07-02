import pandas as pd
import os
from flask import Flask, render_template, request, url_for, redirect, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from datetime import datetime, timedelta
from functools import wraps
# --- IMPORT UNTUK LOGIN ---
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image

# --- Konfigurasi Aplikasi ---
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(app.instance_path, 'sales.db')}"
app.config['SECRET_KEY'] = 'ganti-dengan-kunci-rahasia-anda-yang-jauh-lebih-aman'
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'profile_pics')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

# --- Konfigurasi Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Anda harus login untuk mengakses halaman ini."
login_manager.login_message_category = "warning"

# --- Model Database ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(80), nullable=False, default='admin')
    profile_pic = db.Column(db.String(100), nullable=False, default='default.png')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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

# --- Fungsi Bantuan & Decorator ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'superadmin':
            flash('Anda tidak memiliki izin untuk mengakses halaman ini.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_picture(form_picture):
    random_hex = os.urandom(8).hex()
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.config['UPLOAD_FOLDER'], picture_fn)
    
    output_size = (150, 150)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn

def seed_database():
    if not User.query.first():
        print("Membuat pengguna default...")
        superadmins = ['dyah', 'dika', 'radit']
        admins = ['johan', 'wanti', 'hari']
        for sa_name in superadmins:
            user = User(username=sa_name, role='superadmin')
            user.set_password('kazuki21')
            db.session.add(user)
        for admin_name in admins:
            user = User(username=admin_name, role='admin')
            user.set_password('password')
            db.session.add(user)
        db.session.commit()
        print("Pengguna default berhasil dibuat.")
    
    if not (Stock.query.first() or Order.query.first()):
        try:
            df_stock = pd.read_csv(os.path.join(app.root_path, 'stock_seed.csv'))
            df_stock.to_sql('stock', db.engine, if_exists='append', index=False)
        except Exception as e: print(f"Peringatan: Gagal seeding 'stock_seed.csv'. Error: {e}")
        try:
            df_orders = pd.read_csv(os.path.join(app.root_path, 'orders_seed.csv'), parse_dates=['date'])
            df_orders.to_sql('order', db.engine, if_exists='append', index=False)
        except Exception as e: print(f"Peringatan: Gagal seeding 'orders_seed.csv'. Error: {e}")

def parse_date(date_string):
    if not date_string: return None
    try: return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError: return None

# --- Rute Otentikasi ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user, remember=request.form.get('remember'))
            return redirect(url_for('dashboard'))
        flash('Username atau password salah.', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Rute Aplikasi (Dilindungi) ---
@app.route('/')
@login_required
def dashboard():
    today_str = datetime.now().strftime('%Y-%m-%d')
    start_str = request.args.get('start', today_str)
    end_str = request.args.get('end', today_str)
    start_dt = parse_date(start_str)
    end_dt = parse_date(end_str)
    q = Order.query
    if start_dt: q = q.filter(Order.date >= start_dt)
    if end_dt: q = q.filter(Order.date < end_dt + timedelta(days=1))
    
    total_orders = q.with_entities(func.count(Order.id)).scalar() or 0
    items_in_stock = db.session.query(func.count(Stock.id)).filter(Stock.qty > 0).scalar() or 0
    total_revenue = 0
    total_profit = 0

    if current_user.role == 'superadmin':
        total_revenue = q.with_entities(func.sum(Order.jumlah)).scalar() or 0
        total_profit = q.with_entities(func.sum(Order.jumlah - (Order.qty * Order.harga1))).scalar() or 0
    
    # Grafik Top 10 Produk berdasarkan filter
    top_10_products = (q.with_entities(Order.nama, func.sum(Order.qty).label('total_qty'))
                        .group_by(Order.nama).order_by(func.sum(Order.qty).desc()).limit(10).all())
    chart_labels = [item.nama for item in top_10_products]
    chart_values = [item.total_qty for item in top_10_products]

    # --- PERBAIKAN: Tambahkan kembali kalkulasi untuk grafik semua waktu ---
    all_time_top_10 = (db.session.query(Order.nama, func.sum(Order.qty).label('total_qty'))
                        .group_by(Order.nama).order_by(func.sum(Order.qty).desc()).limit(10).all())
    all_time_chart_labels = [item.nama for item in all_time_top_10]
    all_time_chart_values = [item.total_qty for item in all_time_top_10]
    
    return render_template('dashboard_new.html',
                           total_orders=total_orders, total_revenue=total_revenue,
                           total_profit=total_profit, items_in_stock=items_in_stock,
                           chart_labels=chart_labels, chart_values=chart_values,
                           all_time_chart_labels=all_time_chart_labels, # <-- Tambahkan ini
                           all_time_chart_values=all_time_chart_values, # <-- Tambahkan ini
                           start=start_str, end=end_str, today_str=today_str)

# --- Rute Manajemen Admin ---
@app.route('/admin/manage')
@login_required
@superadmin_required
def manage_admins():
    users = User.query.order_by(User.id).all()
    return render_template('manage_admins.html', users=users)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
@superadmin_required
def add_admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        if User.query.filter_by(username=username).first():
            flash('Username sudah ada.', 'danger')
        else:
            new_user = User(username=username, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Pengguna baru berhasil ditambahkan.', 'success')
            return redirect(url_for('manage_admins'))
    return render_template('admin_form.html', title="Tambah Pengguna", form_action=url_for('add_admin'))

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@superadmin_required
def edit_admin(id):
    user = User.query.get_or_404(id)
    if request.method == 'POST':
        user.username = request.form['username']
        user.role = request.form['role']
        password = request.form['password']
        if password:
            user.set_password(password)
        db.session.commit()
        flash('Data pengguna berhasil diperbarui.', 'success')
        return redirect(url_for('manage_admins'))
    return render_template('admin_form.html', title="Edit Pengguna", user=user, form_action=url_for('edit_admin', id=id))

@app.route('/admin/delete/<int:id>', methods=['POST'])
@login_required
@superadmin_required
def delete_admin(id):
    if id == current_user.id:
        flash('Anda tidak bisa menghapus akun Anda sendiri.', 'danger')
        return redirect(url_for('manage_admins'))
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    flash('Pengguna berhasil dihapus.', 'success')
    return redirect(url_for('manage_admins'))

# --- Rute Profil Pengguna ---
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'picture' in request.files:
            picture_file = request.files['picture']
            if picture_file and allowed_file(picture_file.filename):
                picture_fn = save_picture(picture_file)
                current_user.profile_pic = picture_fn
                db.session.commit()
                flash('Foto profil berhasil diperbarui.', 'success')
                return redirect(url_for('profile'))
    image_file = url_for('static', filename='profile_pics/' + current_user.profile_pic)
    return render_template('profile.html', title="Profil Saya", image_file=image_file)

# --- Rute Stok ---
@app.route('/stock')
@login_required
def stock_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    view_mode = request.args.get('view', 'all')
    q = Stock.query
    title = "Manajemen Stok"
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Stock.kode.ilike(search_term), Stock.nama.ilike(search_term)))
    if view_mode == 'empty':
        q = q.filter(Stock.qty <= 0)
        title = "Stok Kosong"
    elif view_mode == 'available':
        q = q.filter(Stock.qty > 0)
        title = "Stok Tersedia"
    pagination = q.order_by(Stock.nama).paginate(page=page, per_page=10, error_out=False)
    return render_template('stock.html', pagination=pagination, title=title, search=search, view=view_mode)

# ... (Sisa rute Stok dan Order tidak perlu diubah, jadi saya sertakan di sini untuk kelengkapan) ...
@app.route('/stock/get_all_ids')
@login_required
def get_all_stock_ids():
    search = request.args.get('search', '').strip()
    view_mode = request.args.get('view', 'all')
    q = Stock.query
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Stock.kode.ilike(search_term), Stock.nama.ilike(search_term)))
    if view_mode == 'empty':
        q = q.filter(Stock.qty <= 0)
    elif view_mode == 'available':
        q = q.filter(Stock.qty > 0)
    ids = [item.id for item in q.with_entities(Stock.id).all()]
    return jsonify({'ids': ids})

@app.route('/stock/new', methods=['GET', 'POST'])
@login_required
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
@login_required
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

@app.route('/stock/batch_delete', methods=['POST'])
@login_required
def batch_delete_stock():
    data = request.get_json()
    ids_to_delete = data.get('ids', [])
    if not ids_to_delete:
        return jsonify({'success': False, 'message': 'Tidak ada item yang dipilih.'}), 400
    try:
        Stock.query.filter(Stock.id.in_(ids_to_delete)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True, 'message': f'{len(ids_to_delete)} barang berhasil dihapus.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi error: {str(e)}'}), 500

@app.route('/stock/batch_update', methods=['POST'])
@login_required
def batch_update_stock():
    data = request.get_json()
    ids = data.get('ids')
    field = data.get('field')
    find_text = data.get('find_text')
    replace_text = data.get('replace_text')
    if not all([ids, field, find_text is not None, replace_text is not None]):
        return jsonify({'success': False, 'message': 'Data tidak lengkap.'}), 400
    allowed_fields = ['nama', 'kode'] 
    if field not in allowed_fields:
        return jsonify({'success': False, 'message': 'Kolom tidak valid.'}), 400
    try:
        items_to_update = Stock.query.filter(Stock.id.in_(ids)).all()
        updated_count = 0
        for item in items_to_update:
            current_value = getattr(item, field, "")
            if isinstance(current_value, str) and find_text in current_value:
                new_value = current_value.replace(find_text, replace_text)
                setattr(item, field, new_value)
                updated_count += 1
        db.session.commit()
        return jsonify({'success': True, 'message': f'{updated_count} dari {len(ids)} barang berhasil diperbarui.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi error: {str(e)}'}), 500

@app.route('/orders')
@login_required
def orders_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    q = Order.query
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Order.regno.ilike(search_term), Order.kode.ilike(search_term), Order.nama.ilike(search_term)))
    pagination = q.order_by(Order.date.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('orders_new.html', pagination=pagination, search=search)
    
@app.route('/order/get_all_ids')
@login_required
def get_all_order_ids():
    search = request.args.get('search', '').strip()
    q = Order.query
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Order.regno.ilike(search_term), Order.kode.ilike(search_term), Order.nama.ilike(search_term)))
    ids = [item.id for item in q.with_entities(Order.id).all()]
    return jsonify({'ids': ids})

@app.route('/order/new', methods=['GET', 'POST'])
@login_required
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
@login_required
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

@app.route('/order/batch_delete', methods=['POST'])
@login_required
def batch_delete_order():
    data = request.get_json()
    ids_to_delete = data.get('ids', [])
    if not ids_to_delete:
        return jsonify({'success': False, 'message': 'Tidak ada item yang dipilih.'}), 400
    try:
        orders = Order.query.filter(Order.id.in_(ids_to_delete)).all()
        for order in orders:
            stock_item = Stock.query.filter_by(kode=order.kode).first()
            if stock_item:
                stock_item.qty += order.qty
            db.session.delete(order)
        db.session.commit()
        return jsonify({'success': True, 'message': f'{len(ids_to_delete)} order berhasil dihapus dan stok telah dikembalikan.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi error: {str(e)}'}), 500

@app.route('/order/batch_update', methods=['POST'])
@login_required
def batch_update_order():
    data = request.get_json()
    ids = data.get('ids')
    field = data.get('field')
    find_text = data.get('find_text')
    replace_text = data.get('replace_text')
    if not all([ids, field, find_text is not None, replace_text is not None]):
        return jsonify({'success': False, 'message': 'Data tidak lengkap.'}), 400
    allowed_fields = ['nama', 'kode', 'regno'] 
    if field not in allowed_fields:
        return jsonify({'success': False, 'message': 'Kolom tidak valid.'}), 400
    try:
        items_to_update = Order.query.filter(Order.id.in_(ids)).all()
        updated_count = 0
        for item in items_to_update:
            current_value = getattr(item, field, "")
            if isinstance(current_value, str) and find_text in current_value:
                new_value = current_value.replace(find_text, replace_text)
                setattr(item, field, new_value)
                updated_count += 1
        db.session.commit()
        return jsonify({'success': True, 'message': f'{updated_count} dari {len(ids)} order berhasil diperbarui.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi error: {str(e)}'}), 500

if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(app.instance_path): os.makedirs(app.instance_path)
        if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
        db.create_all()
        seed_database()
    app.run(debug=True)
