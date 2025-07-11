import pandas as pd
import os
from flask import Flask, render_template, request, url_for, redirect, flash, jsonify, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_, text
from datetime import datetime, timedelta
from functools import wraps
# --- IMPORT UNTUK LOGIN ---
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
from io import StringIO, BytesIO

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
    jenis = db.Column(db.String(100), default='')

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

# --- MODEL BARU: Purchase (Pembelian) ---
class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    regno = db.Column(db.String(50), unique=True, nullable=False)
    no_faktur = db.Column(db.String(50))
    supplier = db.Column(db.String(150))
    kode = db.Column(db.String(50), nullable=False)
    nama = db.Column(db.String(200), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    harga1 = db.Column(db.Float)
    harga2 = db.Column(db.Float)
    jumlah = db.Column(db.Float)

# --- MODEL BARU: Supplier ---
class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama_supplier = db.Column(db.String(150), nullable=False)
    nama_kontak = db.Column(db.String(150))
    no_rekening = db.Column(db.String(100))

class Changelog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(150))
    details = db.Column(db.Text)

# --- MODEL BARU: BookEntry (Pembukuan) ---
class BookEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255))
    nota = db.Column(db.String(50))
    pemasukan = db.Column(db.Float, default=0)
    pelunasan_supplier = db.Column(db.Float, default=0)
    pengeluaran = db.Column(db.Float, default=0)
    lain_lain = db.Column(db.Float, default=0)
    keterangan_lain = db.Column(db.String(255))
    shift = db.Column(db.String(10), default='Pagi')

class CashDrawer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    amount = db.Column(db.Float, default=0)

class Setting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(200))

# Helper to write log

def log_action(action, details):
    try:
        uid = current_user.id if current_user.is_authenticated else None
    except Exception:
        uid = None
    entry = Changelog(user_id=uid, action=action, details=details)
    db.session.add(entry)
    db.session.commit()

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
    
    # Pengisian data stok & order default dinonaktifkan agar tidak menimpa data aktual

def parse_date(date_string):
    if not date_string: return None
    try: return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError: return None

# --- Rute Pembukuan ---
@app.route('/bookkeeping', methods=['GET', 'POST'])
@login_required
@superadmin_required
def bookkeeping():
    # Handle cash drawer update (uses selected_date hidden field)
    if request.method == 'POST':
        cd_amount = float(request.form.get('cash_drawer', 0))
        date_str = request.form.get('selected_date')
        target_date = parse_date(date_str).date() if date_str else datetime.utcnow().date()
        cd = CashDrawer.query.filter_by(date=target_date).first()
        if not cd:
            cd = CashDrawer(date=target_date)
            db.session.add(cd)
        cd.amount = cd_amount
        db.session.commit()
        log_action('cash_drawer_update', f'Updated cash drawer {cd_amount} ({target_date})')
        flash('Saldo Cash Drawer diperbarui.', 'success')
        # Preserve current filters when redirecting
        return redirect(url_for('bookkeeping', start=date_str, end=date_str))

    # Query entries
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc')
    start_str = request.args.get('start', '')
    end_str = request.args.get('end', '')

    # Parse date filters
    start_date = parse_date(start_str) if start_str else None
    if start_date:
        start_date = start_date.date() if isinstance(start_date, datetime) else start_date
    end_date = parse_date(end_str) if end_str else None
    if end_date:
        end_date = end_date.date() if isinstance(end_date, datetime) else end_date

    q = BookEntry.query
    if search:
        q = q.filter(BookEntry.description.ilike(f"%{search}%"))
    if start_date:
        q = q.filter(BookEntry.date >= start_date)
    if end_date:
        q = q.filter(BookEntry.date <= end_date)
    if hasattr(BookEntry, sort_by):
        sort_col = getattr(BookEntry, sort_by)
        q = q.order_by(sort_col.desc() if order == 'desc' else sort_col.asc())
    else:
        q = q.order_by(BookEntry.date.desc())

    pagination = q.paginate(page=page, per_page=15, error_out=False)

    # Determine current single date for recap/cash drawer (default today)
    current_date = start_date if start_date and (not end_date or start_date == end_date) else datetime.utcnow().date()

    total_pemasukan = q.with_entities(func.sum(BookEntry.pemasukan)).scalar() or 0
    total_pengeluaran = q.with_entities(func.sum(BookEntry.pelunasan_supplier + BookEntry.pengeluaran + BookEntry.lain_lain)).scalar() or 0
    saldo = total_pemasukan - total_pengeluaran

    # Fetch cash drawer for selected date; if missing, use previous saldo as default
    cd_rec = CashDrawer.query.filter_by(date=current_date).first()

    if cd_rec:
        cash_drawer = cd_rec.amount
    else:
        # Compute saldo up to previous date as starting cash
        prev_q = BookEntry.query.filter(BookEntry.date < current_date)
        pemas_prev = prev_q.with_entities(func.sum(BookEntry.pemasukan)).scalar() or 0
        peng_prev = prev_q.with_entities(func.sum(BookEntry.pelunasan_supplier + BookEntry.pengeluaran + BookEntry.lain_lain)).scalar() or 0
        cash_drawer = pemas_prev - peng_prev
    selisih = cash_drawer - saldo
    next_nota = (get_last_nota() or 80737) + 1

    return render_template('bookkeeping.html', pagination=pagination, search=search,
                           total_pemasukan=total_pemasukan, total_pengeluaran=total_pengeluaran,
                           saldo=saldo, cash_drawer=cash_drawer, selisih=selisih, datetime=datetime,
                           next_nota=next_nota, start=start_str, end=end_str, current_date=current_date)

# --- CRUD BookEntry ---
@app.route('/bookkeeping/new', methods=['GET','POST'])
@login_required
@superadmin_required
def new_book_entry():
    if request.method == 'POST':
        use_nota = request.form.get('use_nota', 'yes')
        set_seri = request.form.get('set_seri') if use_nota == 'yes' else None
        last_nota = get_last_nota()
        if set_seri and use_nota == 'yes':
            nota_val = int(set_seri)
            set_last_nota(nota_val)
        elif use_nota == 'yes':
            nota_val = (last_nota + 1) if last_nota is not None else None
            if nota_val is not None:
                set_last_nota(nota_val)
        else:
            nota_val = None
        desc = request.form['description'] or (f"Nota {nota_val}" if nota_val else '')
        entry = BookEntry(
            date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
            description=desc,
            nota=str(nota_val) if nota_val else None,
            pemasukan=float(request.form.get('pemasukan') or 0),
            pelunasan_supplier=float(request.form.get('pelunasan_supplier') or 0),
            pengeluaran=float(request.form.get('pengeluaran') or 0),
            lain_lain=float(request.form.get('lain_lain') or 0),
            keterangan_lain=request.form.get('ket_lain',''),
            shift=request.form.get('shift','Pagi')
        )
        db.session.add(entry)
        db.session.commit()
        log_action('add_book_entry', f'Added book entry id {entry.id}')
        flash('Entri pembukuan berhasil ditambahkan.', 'success')
        return redirect(url_for('bookkeeping'))
    today_str=datetime.utcnow().strftime('%Y-%m-%d')
    return render_template('book_entry_form.html', title='Tambah Entri Pembukuan', form_action=url_for('new_book_entry'), today=today_str)

@app.route('/bookkeeping/edit/<int:id>', methods=['GET','POST'])
@login_required
@superadmin_required
def edit_book_entry(id):
    entry = BookEntry.query.get_or_404(id)
    if request.method == 'POST':
        entry.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        entry.description=request.form['description']
        entry.pemasukan=float(request.form.get('pemasukan') or 0)
        entry.pelunasan_supplier=float(request.form.get('pelunasan_supplier') or 0)
        entry.pengeluaran=float(request.form.get('pengeluaran') or 0)
        entry.lain_lain=float(request.form.get('lain_lain') or 0)
        entry.keterangan_lain=request.form.get('ket_lain','')
        entry.shift=request.form.get('shift','Pagi')
        db.session.commit()
        log_action('edit_book_entry', f'Edited book entry id {id}')
        flash('Entri pembukuan diperbarui.', 'success')
        return redirect(url_for('bookkeeping'))
    return render_template('book_entry_form.html', title='Edit Entri Pembukuan', form_action=url_for('edit_book_entry', id=id), entry=entry)

@app.route('/bookkeeping/delete/<int:id>', methods=['POST'])
@login_required
@superadmin_required
def delete_book_entry(id):
    entry = BookEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    log_action('delete_book_entry', f'Deleted book entry id {id}')
    flash('Entri pembukuan dihapus.', 'success')
    return redirect(url_for('bookkeeping'))

@app.route('/bookkeeping/get_all_ids')
@login_required
@superadmin_required
def get_all_book_entry_ids():
    search = request.args.get('search', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()
    q = BookEntry.query
    if search:
        q = q.filter(BookEntry.description.ilike(f"%{search}%"))
    if start:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(BookEntry.date >= start_dt)
        except Exception:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            q = q.filter(BookEntry.date <= end_dt)
        except Exception:
            pass
    ids = [item.id for item in q.with_entities(BookEntry.id).all()]
    return jsonify({'ids': ids})

@app.route('/bookkeeping/batch_delete', methods=['POST'])
@login_required
@superadmin_required
def batch_delete_book_entry():
    data = request.get_json()
    ids_to_delete = data.get('ids', [])
    if not ids_to_delete:
        return jsonify({'success': False, 'message': 'Tidak ada entri yang dipilih.'}), 400
    try:
        BookEntry.query.filter(BookEntry.id.in_(ids_to_delete)).delete(synchronize_session=False)
        db.session.commit()
        log_action('delete_bookentry_batch', f'Deleted {len(ids_to_delete)} book entries')
        return jsonify({'success': True, 'message': f'{len(ids_to_delete)} entri berhasil dihapus.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi error: {str(e)}'}), 500

@app.route('/bookkeeping/batch_update', methods=['POST'])
@login_required
@superadmin_required
def batch_update_book_entry():
    data = request.get_json()
    ids = data.get('ids')
    field = data.get('field')
    find_text = data.get('find_text')
    replace_text = data.get('replace_text')
    if not all([ids, field, find_text is not None, replace_text is not None]):
        return jsonify({'success': False, 'message': 'Data tidak lengkap.'}), 400
    allowed_fields = ['description', 'nota', 'keterangan_lain']
    if field not in allowed_fields:
        return jsonify({'success': False, 'message': 'Kolom tidak valid.'}), 400
    try:
        items_to_update = BookEntry.query.filter(BookEntry.id.in_(ids)).all()
        updated_count = 0
        for item in items_to_update:
            current_value = getattr(item, field, "")
            if isinstance(current_value, str) and find_text in current_value:
                new_value = current_value.replace(find_text, replace_text)
                setattr(item, field, new_value)
                updated_count += 1
        db.session.commit()
        log_action('update_bookentry_batch', f'Batch updated {field} for {updated_count} entries')
        return jsonify({'success': True, 'message': f'{updated_count} dari {len(ids)} entri berhasil diperbarui.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi error: {str(e)}'}), 500

@app.route('/bookkeeping/import', methods=['GET','POST'])
@login_required
@superadmin_required
def import_book_entries():
    if request.method == 'POST':
        file = request.files.get('file')
        csv_text = request.form.get('csv_text','').strip()
        import pandas as pd
        df = None
        try:
            if file and file.filename:
                if file.filename.lower().endswith(('.xls','.xlsx')):
                    df = pd.read_excel(file)
                else:
                    df = pd.read_csv(file)
            elif csv_text:
                df = pd.read_csv(StringIO(csv_text), header=None, names=['tanggal','deskripsi','pemasukan','pelunasan_supplier','pengeluaran'])
        except Exception as e:
            flash(f'Gagal membaca data: {e}', 'danger')
            return redirect(url_for('bookkeeping'))
        if df is None:
            flash('Tidak ada data yang diimport.', 'warning')
            return redirect(url_for('bookkeeping'))
        # Bersihkan kolom angka
        for col in ['pemasukan','pelunasan_supplier','pengeluaran']:
            if col in df.columns:
                df[col] = (df[col].astype(str).str.replace('[^0-9.-]','', regex=True).replace('',0).astype(float))
            else:
                df[col]=0
        # Isi tanggal kosong dengan ffill
        df['tanggal'] = df['tanggal'].replace('', pd.NA).ffill()
        inserted=0
        last_date=None
        for _,row in df.iterrows():
            desc=str(row['deskripsi']).strip()
            tgl_raw=str(row['tanggal']).strip()
            if not tgl_raw or any(keyword in desc.upper() for keyword in ['JUMLAH','TOTAL','SALDO']):
                continue
            try:
                # handle formats like '1-May'
                date_obj = pd.to_datetime(tgl_raw, dayfirst=True).date()
            except Exception:
                continue
            last_date=date_obj
            pemasukan=row['pemasukan'] or 0
            pel=row['pelunasan_supplier'] or 0
            peng=row['pengeluaran'] or 0
            nota_val=None
            if 'NOTA' in desc.upper():
                parts=desc.upper().split()
                try:
                    idx=parts.index('NOTA')
                    nota_val=parts[idx+1]
                except Exception:
                    pass
            be=BookEntry(date=date_obj, description=desc, nota=nota_val,
                          pemasukan=pemasukan, pelunasan_supplier=pel, pengeluaran=peng)
            db.session.add(be)
            inserted+=1
        db.session.commit()
        log_action('import_book_entry', f'Imported {inserted} entries')
        flash(f'Berhasil mengimpor {inserted} entri.', 'success')
        return redirect(url_for('bookkeeping'))
    # For GET we redirect back
    return redirect(url_for('bookkeeping'))

# --- Rute Otentikasi ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user, remember=request.form.get('remember'))
            log_action('login', f'User {user.username} logged in')
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
            log_action('add_user', f'Added user {username} with role {role}')
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
        
        if 'picture' in request.files:
            picture_file = request.files['picture']
            if picture_file and allowed_file(picture_file.filename):
                picture_fn = save_picture(picture_file)
                user.profile_pic = picture_fn

        db.session.commit()
        log_action('edit_user', f'Edited user id {id}')
        flash('Data pengguna berhasil diperbarui.', 'success')
        return redirect(url_for('manage_admins'))
    
    image_file = url_for('static', filename='profile_pics/' + user.profile_pic)
    return render_template('admin_form.html', title="Edit Pengguna", user=user, image_file=image_file, form_action=url_for('edit_admin', id=id))

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
    log_action('delete_user', f'Deleted user id {id}')
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

# --- Rute Stok (Ganti fungsi ini) ---
@app.route('/stock')
@login_required
def stock_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    view_mode = request.args.get('view', 'all')
    sort_by = request.args.get('sort_by', 'nama')
    order = request.args.get('order', 'asc')
    
    # Mengambil daftar kolom yang dicentang dari URL
    search_columns = request.args.getlist('cols')
    jenis_filter = request.args.get('jenis', '').strip()

    q = Stock.query
    title = "Manajemen Stok"

    # Terapkan filter pencarian jika ada teks yang dicari
    if search:
        search_term = f"%{search}%"
        # Jika tidak ada kolom yang dipilih, cari di semua kolom default (kode dan nama)
        if not search_columns:
            search_columns = ['kode', 'nama']
        
        # Bangun filter OR dinamis berdasarkan kolom yang dipilih
        filters = []
        if 'kode' in search_columns:
            filters.append(Stock.kode.ilike(search_term))
        if 'nama' in search_columns:
            filters.append(Stock.nama.ilike(search_term))
        
        if filters:
            q = q.filter(or_(*filters))

    # Terapkan filter jenis
    if jenis_filter:
        q = q.filter(Stock.jenis == jenis_filter)

    # Terapkan filter status stok
    if view_mode == 'empty':
        q = q.filter(Stock.qty <= 0)
        title = "Stok Kosong"
    elif view_mode == 'available':
        q = q.filter(Stock.qty > 0)
        title = "Stok Tersedia"
    
    # Terapkan pengurutan
    if hasattr(Stock, sort_by):
        sort_column_attr = getattr(Stock, sort_by)
        q = q.order_by(sort_column_attr.desc() if order == 'desc' else sort_column_attr.asc())
    else:
        q = q.order_by(Stock.nama.asc())

    pagination = q.paginate(page=page, per_page=10, error_out=False)
    
    # Ambil daftar distinct jenis untuk dropdown filter
    jenis_list = [row[0] for row in db.session.query(Stock.jenis).distinct().order_by(Stock.jenis.asc()).all() if row[0]]
    
    return render_template('stock.html', 
                           pagination=pagination, 
                           title=title, 
                           search=search, 
                           view=view_mode,
                           jenis_filter=jenis_filter,
                           jenis_list=jenis_list,
                           sort_by=sort_by,
                           order=order,
                           # Kirim kolom yang dipilih kembali ke template
                           search_columns=search_columns
                          )


# --- Fungsi get_all_stock_ids (Ganti juga fungsi ini) ---
@app.route('/stock/get_all_ids')
@login_required
def get_all_stock_ids():
    search = request.args.get('search', '').strip()
    view_mode = request.args.get('view', 'all')
    search_columns = request.args.getlist('cols')
    jenis_filter = request.args.get('jenis', '').strip()

    q = Stock.query
    
    if search:
        search_term = f"%{search}%"
        if not search_columns:
            search_columns = ['kode', 'nama']
        
        filters = []
        if 'kode' in search_columns:
            filters.append(Stock.kode.ilike(search_term))
        if 'nama' in search_columns:
            filters.append(Stock.nama.ilike(search_term))
            
        if filters:
            q = q.filter(or_(*filters))

    if view_mode == 'empty':
        q = q.filter(Stock.qty <= 0)
    elif view_mode == 'available':
        q = q.filter(Stock.qty > 0)

    if jenis_filter:
        q = q.filter(Stock.jenis == jenis_filter)

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
            kode=kode,
            nama=request.form['nama'],
            jenis=request.form.get('jenis', '').strip(),
            harga1=float(request.form.get('harga1', 0)),
            harga2=float(request.form.get('harga2', 0)),
            qty=int(request.form.get('qty', 0))
        )
        db.session.add(new_item)
        db.session.commit()
        log_action('add_stock', f'Added stock {kode}')
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
        item.jenis = request.form.get('jenis','').strip()
        item.harga1 = float(request.form.get('harga1', 0))
        item.harga2 = float(request.form.get('harga2', 0))
        item.qty = int(request.form.get('qty', 0))
        db.session.commit()
        log_action('edit_stock', f'Edited stock id {id}')
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
        log_action('delete_stock_batch', f'Deleted {len(ids_to_delete)} stock items')
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
    allowed_fields = ['nama', 'kode', 'jenis'] 
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
        log_action('update_stock_batch', f'Batch updated stock field {field} for {updated_count} items')
        return jsonify({'success': True, 'message': f'{updated_count} dari {len(ids)} barang berhasil diperbarui.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi error: {str(e)}'}), 500

# --- Rute Order ---
@app.route('/orders')
@login_required
def orders_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    # Always default to date in desc order (newest first)
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc')
    
    # Check if any filter parameters are present, and if so, reset to date sorting
    has_filters = False
    
    # Advanced search per column
    regno = request.args.get('regno', '').strip()
    kode = request.args.get('kode', '').strip()
    nama = request.args.get('nama', '').strip()
    qty = request.args.get('qty', '').strip()
    # Date range filter only
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()
    
    # Check if filters are applied
    if regno or kode or nama or qty or start or end:
        has_filters = True
    
    # Force date sorting when date filters are applied, unless explicitly sorting by another column
    if start or end:
        explicit_sort = request.args.get('explicit_sort', 'false')
        if explicit_sort != 'true':
            sort_by = 'date'
            order = 'asc'
    
    # Enforce date sorting by newest first if sort params are empty or not specified
    if not sort_by:
        sort_by = 'date'
    if not order:
        order = 'desc'

    q = Order.query
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Order.regno.ilike(search_term), Order.kode.ilike(search_term), Order.nama.ilike(search_term)))
    if regno:
        q = q.filter(Order.regno.ilike(f"%{regno}%"))
    if kode:
        q = q.filter(Order.kode.ilike(f"%{kode}%"))
    if nama:
        q = q.filter(Order.nama.ilike(f"%{nama}%"))
    if qty:
        try:
            q = q.filter(Order.qty == int(qty))
        except ValueError:
            pass
    # Date range filter
    if start:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Order.date >= start_dt)
        except Exception:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            q = q.filter(Order.date < end_dt + timedelta(days=1))
        except Exception:
            pass
    if hasattr(Order, sort_by):
        sort_column = getattr(Order, sort_by)
        if order == 'asc':
            q = q.order_by(sort_column.asc())
        else:
            q = q.order_by(sort_column.desc())
    else:
        q = q.order_by(Order.date.desc())
    pagination = q.paginate(page=page, per_page=10, error_out=False)
    # Total revenue for filtered orders
    total_revenue = q.with_entities(func.sum(Order.jumlah)).scalar() or 0
    return render_template('orders_new.html', 
                           pagination=pagination, 
                           search=search,
                           sort_by=sort_by,
                           order=order,
                           regno=regno,
                           kode=kode,
                           nama=nama,
                           qty=qty,
                           start=start,
                           end=end,
                           total_revenue=total_revenue)
    
@app.route('/sales')
@login_required
def sales_list():
    return orders_list()

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
        log_action('add_order', f'Added order {regno}')
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
        log_action('edit_order', f'Edited order id {id}')
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
        # Process in chunks to avoid SQLite "too many SQL variables" error
        chunk_size = 100  # SQLite default limit is 999, use conservative value
        total_deleted = 0
        
        for i in range(0, len(ids_to_delete), chunk_size):
            chunk = ids_to_delete[i:i + chunk_size]
            orders = Order.query.filter(Order.id.in_(chunk)).all()
            
            for order in orders:
                stock_item = Stock.query.filter_by(kode=order.kode).first()
                if stock_item:
                    stock_item.qty += order.qty
                db.session.delete(order)
                total_deleted += 1
            
            # Commit each chunk to avoid large transactions
            db.session.commit()
        
        log_action('delete_order_batch', f'Deleted {total_deleted} orders')
        return jsonify({'success': True, 'message': f'{total_deleted} order berhasil dihapus dan stok telah dikembalikan.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal menghapus: {str(e)}'}), 500

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

@app.route('/order/clear_all', methods=['POST'])
@login_required
def clear_all_orders():
    """Menghapus semua data order dengan cara yang efisien untuk SQLite"""
    confirmation_key = request.form.get('confirmation_key')
    if confirmation_key != 'KONFIRMASI-HAPUS-SEMUA':
        flash('Kunci konfirmasi tidak valid. Data tidak dihapus.', 'danger')
        return redirect(url_for('orders_list'))
    
    try:
        # 1. Ambil semua kode barang dan qty untuk update stok
        stock_updates = db.session.query(Order.kode, func.sum(Order.qty).label('total_qty'))\
                                  .group_by(Order.kode).all()
        
        # 2. Update stok untuk setiap kode barang
        for kode, qty in stock_updates:
            stock_item = Stock.query.filter_by(kode=kode).first()
            if stock_item:
                stock_item.qty += qty
        
        # 3. Hitung jumlah order sebelum dihapus
        count = db.session.query(func.count(Order.id)).scalar() or 0
        
        # 4. Hapus semua order dengan SQL langsung (lebih efisien)
        db.session.execute(text("DELETE FROM \"order\""))
        db.session.commit()
        
        log_action('clear_all_orders', f'Deleted all {count} orders')
        flash(f'Berhasil menghapus semua data penjualan ({count} record).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus data: {str(e)}', 'danger')
    
    return redirect(url_for('orders_list'))

@app.route('/order/print_data', methods=['GET','POST'])
@login_required
def get_print_data():
    ids_json = None
    if request.method == 'POST':
        try:
            ids_json = request.get_json().get('ids')
        except Exception:
            ids_json = None
    search = request.args.get('search', '').strip()
    # Always default to date in desc order (newest first)
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc')
    
    # Check if any filter parameters are present, and if so, reset to date sorting
    has_filters = False
    
    # Advanced search per column
    regno = request.args.get('regno', '').strip()
    kode = request.args.get('kode', '').strip()
    nama = request.args.get('nama', '').strip()
    qty = request.args.get('qty', '').strip()
    
    # Date range filter only
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()
    
    # Check if filters are applied
    if regno or kode or nama or qty or start or end:
        has_filters = True
    
    # Force date sorting when date filters are applied, unless explicitly sorting by another column
    if start or end:
        explicit_sort = request.args.get('explicit_sort', 'false')
        if explicit_sort != 'true':
            sort_by = 'date'
            order = 'asc'
    
    # Enforce date sorting by newest first if sort params are empty or not specified
    if not sort_by:
        sort_by = 'date'
    if not order:
        order = 'desc'

    q = Order.query
    if ids_json:
        q = q.filter(Order.id.in_(ids_json))
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Order.regno.ilike(search_term), 
                         Order.kode.ilike(search_term), 
                         Order.nama.ilike(search_term)))
    if regno:
        q = q.filter(Order.regno.ilike(f"%{regno}%"))
    if kode:
        q = q.filter(Order.kode.ilike(f"%{kode}%"))
    if nama:
        q = q.filter(Order.nama.ilike(f"%{nama}%"))
    if qty:
        try:
            q = q.filter(Order.qty == int(qty))
        except ValueError:
            pass
            
    # Date range filter
    if start:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Order.date >= start_dt)
        except Exception:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            q = q.filter(Order.date < end_dt + timedelta(days=1))
        except Exception:
            pass
            
    # Apply sorting
    if hasattr(Order, sort_by):
        sort_column = getattr(Order, sort_by)
        if order == 'asc':
            q = q.order_by(sort_column.asc())
        else:
            q = q.order_by(sort_column.desc())
    else:
        q = q.order_by(Order.date.desc())
    
    # Get all orders that match filters without pagination
    orders = q.all()
    
    # Calculate total
    total_revenue = q.with_entities(func.sum(Order.jumlah)).scalar() or 0
    
    # Format and return data
    order_data = []
    for order in orders:
        order_data.append({
            'date': order.date.strftime('%Y-%m-%d'),
            'regno': order.regno,
            'kode': order.kode,
            'nama': order.nama,
            'qty': order.qty,
            'jumlah': order.jumlah
        })
    
    return jsonify({
        'orders': order_data,
        'total_revenue': total_revenue,
        'total_count': len(order_data),
        'filters': {
            'start': start,
            'end': end,
            'regno': regno,
            'kode': kode,
            'nama': nama,
            'qty': qty,
            'search': search
        }
    })

# --- Rute Purchase (Pembelian) ---
@app.route('/purchases')
@login_required
def purchases_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc')
    # Filters same as orders
    regno = request.args.get('regno', '').strip()
    kode = request.args.get('kode', '').strip()
    nama = request.args.get('nama', '').strip()
    qty = request.args.get('qty', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()

    q = Purchase.query
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Purchase.regno.ilike(search_term), Purchase.kode.ilike(search_term), Purchase.nama.ilike(search_term)))
    if regno:
        q = q.filter(Purchase.regno.ilike(f"%{regno}%"))
    if kode:
        q = q.filter(Purchase.kode.ilike(f"%{kode}%"))
    if nama:
        q = q.filter(Purchase.nama.ilike(f"%{nama}%"))
    if qty:
        try:
            q = q.filter(Purchase.qty == int(qty))
        except ValueError:
            pass
    if start:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Purchase.date >= start_dt)
        except Exception:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            q = q.filter(Purchase.date < end_dt + timedelta(days=1))
        except Exception:
            pass
    if hasattr(Purchase, sort_by):
        sort_column = getattr(Purchase, sort_by)
        if order == 'asc':
            q = q.order_by(sort_column.asc())
        else:
            q = q.order_by(sort_column.desc())
    else:
        q = q.order_by(Purchase.date.desc())

    pagination = q.paginate(page=page, per_page=10, error_out=False)
    total_cost = q.with_entities(func.sum(Purchase.jumlah)).scalar() or 0
    return render_template('purchases_new.html', pagination=pagination, search=search, sort_by=sort_by, order=order, regno=regno, kode=kode, nama=nama, qty=qty, start=start, end=end, total_cost=total_cost)

# --- Import Pembelian ---
@app.route('/purchase/import', methods=['POST'])
@login_required
def import_purchases():
    """Import purchase data from CSV/Excel or pasted CSV with columns:
    regno_pembelian,TGL_PEMBELIAN,NOFAKTUR_PEMBELIAN,SUPPLIER,kode_barang,NAMA_BARPEMBELIAN,HARGA_PEMBELIAN,JUMLAH_PEMBELIAN"""
    file = request.files.get('file')
    csv_text = request.form.get('csv_text', '').strip()
    skip_duplicates = request.form.get('skip_duplicates') == 'on'
    df = None
    try:
        if file and file.filename:
            if file.filename.lower().endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                df = pd.read_csv(file)
        elif csv_text:
            df = pd.read_csv(StringIO(csv_text))
    except Exception as e:
        flash(f'Gagal membaca data: {e}', 'danger')
        return redirect(url_for('purchases_list'))

    if df is None or df.empty:
        flash('Tidak ada data yang diimport.', 'warning')
        return redirect(url_for('purchases_list'))

    inserted = 0
    skipped = 0
    errors = []
    existing_regnos = {r[0] for r in db.session.query(Purchase.regno).all()}
    
    for _, row in df.iterrows():
        try:
            # Kolom standar baru
            date_raw = row.get('tgl_pembelian') or row.get('TGL_PEMBELIAN')
            if pd.isna(date_raw):
                continue
            date_obj = pd.to_datetime(str(date_raw), dayfirst=False)

            regno = str(row.get('regno_pembelian') or '').strip()
            if regno in existing_regnos:
                if skip_duplicates:
                    skipped += 1
                    continue
                # tambahkan suffix agar unik
                suffix = 1
                base = regno
                while f"{base}-{suffix}" in existing_regnos:
                    suffix += 1
                regno = f"{base}-{suffix}"

            if not regno:
                regno = f"PB{datetime.now().strftime('%y%m%d%H%M%S')}{inserted:03d}"
            existing_regnos.add(regno)

            no_faktur = str(row.get('nofaktur_pembelian') or '').strip()
            supplier_name = str(row.get('supplier') or '').strip()

            kode = str(row.get('kbarang_pembelian') or '').strip()
            nama_brg = str(row.get('nama_pembelian') or '').strip()

            try:
                qty_val = int(row.get('qty_pembelian') or 0)
            except Exception:
                qty_val = 0

            try:
                harga_beli = float(row.get('harga_pembelian') or 0)
            except Exception:
                harga_beli = 0

            try:
                total_beli = float(row.get('total_pembelian') or 0)
            except Exception:
                total_beli = qty_val * harga_beli

            # Jika salah satu dari qty atau total kosong, hitung otomatis
            if qty_val == 0 and harga_beli>0:
                qty_val = int(round(total_beli / harga_beli)) if total_beli else 1
            if total_beli == 0:
                total_beli = qty_val * harga_beli

            new_purchase = Purchase(
                date=date_obj,
                regno=regno,
                no_faktur=no_faktur,
                supplier=supplier_name,
                kode=kode,
                nama=nama_brg,
                qty=qty_val,
                harga2=harga_beli,
                jumlah=total_beli
            )

            # Update stock (menambah qty)
            if kode:
                stock_item = Stock.query.filter_by(kode=kode).first()
                if stock_item:
                    stock_item.qty += qty_val
            db.session.add(new_purchase)
            inserted += 1
        except Exception as e:
            db.session.rollback()
            errors.append(str(e))
            continue

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error saat menyimpan data: {e}', 'danger')
        return redirect(url_for('purchases_list'))

    log_action('import_purchases', f'Imported {inserted}, skipped {skipped}')
    msg = f'Import selesai: {inserted} berhasil'
    if skipped:
        msg += f', {skipped} dilewati (duplikat)'
    if errors:
        msg += f', {len(errors)} error'
    flash(msg, 'info')
    
    return redirect(url_for('purchases_list'))

# --- Rute Supplier ---
@app.route('/suppliers')
@login_required
def supplier_list():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    
    q = Supplier.query
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(
            Supplier.nama_supplier.ilike(search_term),
            Supplier.nama_kontak.ilike(search_term),
            Supplier.no_rekening.ilike(search_term)
        ))
    
    pagination = q.order_by(Supplier.nama_supplier.asc()).paginate(page=page, per_page=15, error_out=False)
    return render_template('suppliers.html', pagination=pagination, search=search)

@app.route('/supplier/new', methods=['GET', 'POST'])
@login_required
def new_supplier():
    if request.method == 'POST':
        new_supplier_item = Supplier(
            nama_supplier=request.form['nama_supplier'],
            nama_kontak=request.form['nama_kontak'],
            no_rekening=request.form['no_rekening']
        )
        db.session.add(new_supplier_item)
        db.session.commit()
        flash('Supplier baru berhasil ditambahkan.', 'success')
        return redirect(url_for('supplier_list'))
    return render_template('supplier_form.html', title="Tambah Supplier Baru")

@app.route('/supplier/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    if request.method == 'POST':
        supplier.nama_supplier = request.form['nama_supplier']
        supplier.nama_kontak = request.form['nama_kontak']
        supplier.no_rekening = request.form['no_rekening']
        db.session.commit()
        flash('Data supplier berhasil diperbarui.', 'success')
        return redirect(url_for('supplier_list'))
    return render_template('supplier_form.html', title="Edit Supplier", supplier=supplier)

@app.route('/supplier/delete/<int:id>', methods=['POST'])
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    db.session.delete(supplier)
    db.session.commit()
    flash('Supplier berhasil dihapus.', 'success')
    return redirect(url_for('supplier_list'))

# --- Endpoint for stock autocomplete ---
@app.route('/stock/search')
@login_required
def stock_search():
    query = request.args.get('q', '').strip()
    results = []
    if query:
        q = Stock.query.filter(or_(Stock.kode.ilike(f"%{query}%"), Stock.nama.ilike(f"%{query}%"))).order_by(Stock.nama.asc()).limit(10)
        results = [{ 'kode': item.kode, 'nama': item.nama } for item in q]
    return jsonify(results)

# --- Rute Changelog ---
@app.route('/changelog')
@login_required
@superadmin_required
def changelog_view():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    q = db.session.query(Changelog, User.username.label('username')).outerjoin(User, Changelog.user_id == User.id)
    if search:
        q = q.filter(or_(Changelog.action.ilike(f"%{search}%"), Changelog.details.ilike(f"%{search}%"), User.username.ilike(f"%{search}%")))
    pagination = q.order_by(Changelog.timestamp.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template('changelog.html', pagination=pagination, search=search)

# Nota helpers

def get_last_nota():
    s = Setting.query.get('last_nota')
    if s and s.value.isdigit():
        return int(s.value)
    return None

def set_last_nota(val):
    s = Setting.query.get('last_nota')
    if not s:
        s = Setting(key='last_nota', value=str(val))
        db.session.add(s)
    else:
        s.value = str(val)
    db.session.commit()

# --- Batch operations for Changelog ---
@app.route('/changelog/get_all_ids')
@login_required
@superadmin_required
def get_all_changelog_ids():
    search = request.args.get('search', '').strip()
    q = Changelog.query
    if search:
        q = q.filter(or_(Changelog.action.ilike(f"%{search}%"), Changelog.details.ilike(f"%{search}%")))
    ids = [item.id for item in q.with_entities(Changelog.id).all()]
    return jsonify({'ids': ids})

@app.route('/changelog/batch_delete', methods=['POST'])
@login_required
@superadmin_required
def batch_delete_changelog():
    data = request.get_json()
    ids_to_delete = data.get('ids', [])
    if not ids_to_delete:
        return jsonify({'success': False, 'message': 'Tidak ada log yang dipilih.'}), 400
    try:
        Changelog.query.filter(Changelog.id.in_(ids_to_delete)).delete(synchronize_session=False)
        db.session.commit()
        log_action('delete_changelog_batch', f'Deleted {len(ids_to_delete)} changelog entries')
        return jsonify({'success': True, 'message': f'{len(ids_to_delete)} log berhasil dihapus.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Terjadi error: {str(e)}'}), 500

# --- Export dan Import Order ---
@app.route('/order/export')
@login_required
def export_orders():
    """
    Export filtered orders to CSV or Excel. Accepts the same filter params used by /orders
    via query string and a 'format' param (csv|xlsx).
    """
    file_format = request.args.get('format', 'csv').lower()
    # Ambil semua parameter filter seperti pada orders_list
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc')
    regno = request.args.get('regno', '').strip()
    kode = request.args.get('kode', '').strip()
    nama = request.args.get('nama', '').strip()
    qty = request.args.get('qty', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()

    q = Order.query
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Order.regno.ilike(search_term), Order.kode.ilike(search_term), Order.nama.ilike(search_term)))
    if regno:
        q = q.filter(Order.regno.ilike(f"%{regno}%"))
    if kode:
        q = q.filter(Order.kode.ilike(f"%{kode}%"))
    if nama:
        q = q.filter(Order.nama.ilike(f"%{nama}%"))
    if qty:
        try:
            q = q.filter(Order.qty == int(qty))
        except ValueError:
            pass
    if start:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Order.date >= start_dt)
        except Exception:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            q = q.filter(Order.date < end_dt + timedelta(days=1))
        except Exception:
            pass
    if hasattr(Order, sort_by):
        sort_col = getattr(Order, sort_by)
        q = q.order_by(sort_col.asc() if order == 'asc' else sort_col.desc())
    else:
        q = q.order_by(Order.date.desc())

    orders = q.all()
    df = pd.DataFrame([{
        'date': o.date.strftime('%Y-%m-%d'),
        'regno': o.regno,
        'kode': o.kode,
        'nama': o.nama,
        'qty': o.qty,
        'harga1': o.harga1,
        'harga2': o.harga2,
        'jumlah': o.jumlah
    } for o in orders])

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if file_format == 'xlsx':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Orders')
        output.seek(0)
        return send_file(output,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True,
                         download_name=f'orders_{timestamp}.xlsx')
    else:
        csv_data = df.to_csv(index=False)
        response = make_response(csv_data)
        response.headers['Content-Disposition'] = f'attachment; filename=orders_{timestamp}.csv'
        response.mimetype = 'text/csv'
        return response

@app.route('/order/import', methods=['POST'])
@login_required
def import_orders():
    """
    Import orders from uploaded CSV / Excel or pasted CSV. Minimal columns: date, kode, nama, qty.
    """
    file = request.files.get('file')
    csv_text = request.form.get('csv_text', '').strip()
    skip_duplicates = request.form.get('skip_duplicates') == 'on'
    df = None
    try:
        if file and file.filename:
            if file.filename.lower().endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                df = pd.read_csv(file)
        elif csv_text:
            df = pd.read_csv(StringIO(csv_text))
    except Exception as e:
        flash(f'Gagal membaca data: {e}', 'danger')
        return redirect(url_for('orders_list'))

    if df is None or df.empty:
        flash('Tidak ada data yang diimport.', 'warning')
        return redirect(url_for('orders_list'))

    inserted = 0
    skipped = 0
    errors = []
    # Ambil semua regno yang sudah ada di database untuk cek duplikat
    existing_regnos = {r[0] for r in db.session.query(Order.regno).all()}
    
    for _, row in df.iterrows():
        try:
            date_raw = row.get('date') or row.get('tanggal') or row.get('Date')
            if pd.isna(date_raw):
                continue
            if not isinstance(date_raw, (datetime, pd.Timestamp)):
                date_obj = pd.to_datetime(str(date_raw), dayfirst=False)
            else:
                date_obj = date_raw
            if isinstance(date_obj, pd.Timestamp):
                date_obj = date_obj.to_pydatetime()

            regno = str(row.get('regno') or row.get('nota') or '').strip()
            if not regno:
                last_order = Order.query.order_by(Order.id.desc()).first()
                if last_order and last_order.regno.startswith('N'):
                    try:
                        last_num = int(last_order.regno[7:])
                    except Exception:
                        last_num = 0
                    new_num = last_num + 1
                else:
                    new_num = 1
                regno = f"N{datetime.now().strftime('%y%m%d')}{new_num:04d}"
            
            # Cek apakah regno sudah ada
            original_regno = regno
            if regno in existing_regnos:
                if skip_duplicates:
                    skipped += 1
                    continue
                else:
                    # Tambahkan suffix untuk membuat regno unik
                    suffix = 1
                    while f"{regno}-{suffix}" in existing_regnos:
                        suffix += 1
                    regno = f"{regno}-{suffix}"

            kode = str(row.get('kode') or row.get('code') or '').strip()
            nama = str(row.get('nama') or row.get('name') or '').strip()
            try:
                qty_val = int(row.get('qty') or row.get('Qty') or 0)
            except Exception:
                qty_val = 0

            try:
                harga2_val = float(row.get('harga2') or row.get('Harga Jual') or 0)
            except Exception:
                harga2_val = 0.0

            jumlah_val = row.get('jumlah') or row.get('Jumlah')
            try:
                jumlah_val = float(jumlah_val) if jumlah_val is not None else None
            except Exception:
                jumlah_val = None

            if not all([kode, nama, qty_val]):
                continue

            stock_item = Stock.query.filter_by(kode=kode).first()
            harga1_val = stock_item.harga1 if stock_item else 0
            if stock_item:
                stock_item.qty = max(0, stock_item.qty - qty_val)

            new_order = Order(
                date=date_obj,
                regno=regno,
                kode=kode,
                nama=nama,
                qty=qty_val,
                harga1=harga1_val,
                harga2=harga2_val,
                jumlah=jumlah_val if jumlah_val is not None else qty_val * harga2_val
            )
            db.session.add(new_order)
            # Tambahkan regno baru ke set untuk cek duplikat berikutnya
            existing_regnos.add(regno)
            inserted += 1
            # Commit setiap 100 record untuk menghindari transaksi besar
            if inserted % 100 == 0:
                db.session.commit()
        except Exception as e:
            db.session.rollback()  # Rollback jika ada error
            errors.append(f"Baris {inserted+skipped+1}: {str(e)}")
            continue

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error saat menyimpan data: {str(e)}', 'danger')
        return redirect(url_for('orders_list'))
        
    log_action('import_orders', f'Imported {inserted} orders')
    
    # Tampilkan pesan hasil import
    if inserted > 0 and skipped == 0 and not errors:
        flash(f'Berhasil mengimpor {inserted} order.', 'success')
    else:
        message = f'Import selesai: {inserted} berhasil'
        if skipped > 0:
            message += f', {skipped} dilewati (duplikat)'
        if errors:
            message += f', {len(errors)} error'
            # Tampilkan 5 error pertama
            for i, err in enumerate(errors[:5]):
                flash(err, 'warning')
            if len(errors) > 5:
                flash(f'...dan {len(errors)-5} error lainnya', 'warning')
        flash(message, 'info')
        
    return redirect(url_for('orders_list'))

@app.route('/stock/export')
@login_required
def export_stocks():
    """Export data stok ke CSV atau Excel, mengikuti filter search & view"""
    fmt = request.args.get('format', 'csv')
    search = request.args.get('search', '').strip()
    view_mode = request.args.get('view', '').strip()  # '' | 'available' | 'empty'

    q = Stock.query
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Stock.kode.ilike(search_term), Stock.nama.ilike(search_term)))

    if view_mode == 'empty':
        q = q.filter(Stock.qty <= 0)
    elif view_mode == 'available':
        q = q.filter(Stock.qty > 0)

    items = q.all()
    if not items:
        flash('Tidak ada data stok untuk diexport.', 'warning')
        return redirect(url_for('stock_list', search=search, view=view_mode))

    import pandas as pd
    df = pd.DataFrame([{ 'kode': s.kode, 'nama': s.nama, 'jenis': s.jenis, 'qty': s.qty,
                         'harga1': s.harga1, 'harga2': s.harga2 } for s in items])
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    if fmt == 'xlsx':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Stock')
        output.seek(0)
        return send_file(output,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True,
                         download_name=f'stock_{timestamp}.xlsx')
    else:
        csv_data = df.to_csv(index=False)
        response = make_response(csv_data)
        response.headers['Content-Disposition'] = f'attachment; filename=stock_{timestamp}.csv'
        response.mimetype = 'text/csv'
        return response

@app.route('/stock/import', methods=['POST'])
@login_required
def import_stocks():
    """Import stok dari CSV / Excel atau teks yang ditempel. Kolom minimal: kode, nama, qty"""
    file = request.files.get('file')
    csv_text = request.form.get('csv_text', '').strip()
    skip_duplicates = request.form.get('skip_duplicates') == 'on'
    df = None
    try:
        if file and file.filename:
            if file.filename.lower().endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file)
            else:
                df = pd.read_csv(file)
        elif csv_text:
            df = pd.read_csv(StringIO(csv_text))
    except Exception as e:
        flash(f'Gagal membaca data: {e}', 'danger')
        return redirect(url_for('stock_list'))

    if df is None or df.empty:
        flash('Tidak ada data yang diimport.', 'warning')
        return redirect(url_for('stock_list'))

    inserted = 0
    updated = 0
    errors = []

    existing_kodes = {s.kode: s for s in Stock.query.all()}

    for _, row in df.iterrows():
        try:
            kode = str(row.get('kode') or row.get('code') or '').strip()
            if not kode:
                continue
            nama = str(row.get('nama') or row.get('name') or '').strip()
            jenis = str(row.get('jenis') or row.get('type') or '').strip()
            qty_val = int(row.get('qty') or row.get('Qty') or 0)
            harga1_val = float(row.get('harga1') or row.get('Harga Beli') or 0)
            harga2_val = float(row.get('harga2') or row.get('Harga Jual') or 0)

            if kode in existing_kodes:
                if skip_duplicates:
                    continue
                # update existing
                stock_item = existing_kodes[kode]
                stock_item.nama = nama or stock_item.nama
                stock_item.jenis = jenis or stock_item.jenis
                stock_item.qty = qty_val if qty_val is not None else stock_item.qty
                stock_item.harga1 = harga1_val if harga1_val is not None else stock_item.harga1
                stock_item.harga2 = harga2_val if harga2_val is not None else stock_item.harga2
                updated += 1
            else:
                new_item = Stock(kode=kode, nama=nama, jenis=jenis, qty=qty_val,
                                 harga1=harga1_val, harga2=harga2_val)
                db.session.add(new_item)
                existing_kodes[kode] = new_item
                inserted += 1
            # commit in chunks
            if (inserted + updated) % 200 == 0:
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            errors.append(str(e))
            continue

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error saat menyimpan data: {e}', 'danger')
        return redirect(url_for('stock_list'))

    log_action('import_stocks', f'Inserted {inserted}, Updated {updated}')
    flash(f'Import selesai: {inserted} ditambah, {updated} diperbarui, {len(errors)} error.', 'info')
    return redirect(url_for('stock_list'))

@app.route('/purchase/export')
@login_required
def export_purchases():
    fmt = request.args.get('format', 'csv')
    # gather filters similar to purchases_list
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc')
    regno = request.args.get('regno', '').strip()
    kode = request.args.get('kode', '').strip()
    nama = request.args.get('nama', '').strip()
    qty = request.args.get('qty', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()

    q = Purchase.query
    if search:
        search_term = f"%{search}%"
        q = q.filter(or_(Purchase.regno.ilike(search_term), Purchase.kode.ilike(search_term), Purchase.nama.ilike(search_term)))
    if regno:
        q = q.filter(Purchase.regno.ilike(f"%{regno}%"))
    if kode:
        q = q.filter(Purchase.kode.ilike(f"%{kode}%"))
    if nama:
        q = q.filter(Purchase.nama.ilike(f"%{nama}%"))
    if qty:
        try:
            q = q.filter(Purchase.qty == int(qty))
        except ValueError:
            pass
    if start:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Purchase.date >= start_dt)
        except Exception:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            q = q.filter(Purchase.date < end_dt + timedelta(days=1))
        except Exception:
            pass

    if hasattr(Purchase, sort_by):
        sort_col = getattr(Purchase, sort_by)
        q = q.order_by(sort_col.asc() if order=='asc' else sort_col.desc())

    items = q.all()
    if not items:
        flash('Tidak ada data pembelian untuk diexport.', 'warning')
        return redirect(url_for('purchases_list'))

    import pandas as pd
    df = pd.DataFrame([{ 'date': p.date.strftime('%Y-%m-%d'), 'regno': p.regno, 'no_faktur': p.no_faktur,
                         'supplier': p.supplier, 'kode': p.kode, 'nama': p.nama, 'qty': p.qty,
                         'harga1': p.harga1, 'harga2': p.harga2, 'jumlah': p.jumlah } for p in items])
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    if fmt == 'xlsx':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Purchases')
        output.seek(0)
        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name=f'purchases_{timestamp}.xlsx')
    else:
        csv_data = df.to_csv(index=False)
        response = make_response(csv_data)
        response.headers['Content-Disposition'] = f'attachment; filename=purchases_{timestamp}.csv'
        response.mimetype = 'text/csv'
        return response

# --- Helper to get all purchase ids according to current filters ---
@app.route('/purchase/get_all_ids')
@login_required
def get_all_purchase_ids():
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    order = request.args.get('order', 'desc')
    regno = request.args.get('regno', '').strip()
    kode = request.args.get('kode', '').strip()
    nama = request.args.get('nama', '').strip()
    qty = request.args.get('qty', '').strip()
    start = request.args.get('start', '').strip()
    end = request.args.get('end', '').strip()

    q = Purchase.query
    if search:
        st = f"%{search}%"
        q = q.filter(or_(Purchase.regno.ilike(st), Purchase.kode.ilike(st), Purchase.nama.ilike(st)))
    if regno:
        q = q.filter(Purchase.regno.ilike(f"%{regno}%"))
    if kode:
        q = q.filter(Purchase.kode.ilike(f"%{kode}%"))
    if nama:
        q = q.filter(Purchase.nama.ilike(f"%{nama}%"))
    if qty:
        try:
            q = q.filter(Purchase.qty == int(qty))
        except ValueError:
            pass
    if start:
        try:
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Purchase.date >= start_dt)
        except Exception:
            pass
    if end:
        try:
            end_dt = datetime.strptime(end, '%Y-%m-%d')
            q = q.filter(Purchase.date < end_dt + timedelta(days=1))
        except Exception:
            pass

    ids = [p.id for p in q.with_entities(Purchase.id).all()]
    return jsonify({'ids': ids})

# --- Batch delete purchases ---
@app.route('/purchase/batch_delete', methods=['POST'])
@login_required
def batch_delete_purchase():
    data = request.get_json()
    ids_to_delete = data.get('ids', [])
    if not ids_to_delete:
        return jsonify({'success': False, 'message': 'Tidak ada item yang dipilih.'}), 400
    try:
        chunk_size = 100
        total_deleted = 0
        for i in range(0, len(ids_to_delete), chunk_size):
            chunk = ids_to_delete[i:i+chunk_size]
            purchases = Purchase.query.filter(Purchase.id.in_(chunk)).all()
            for pur in purchases:
                stock_item = Stock.query.filter_by(kode=pur.kode).first()
                if stock_item:
                    stock_item.qty = max(0, stock_item.qty - pur.qty)
                db.session.delete(pur)
                total_deleted += 1
            db.session.commit()
        log_action('delete_purchase_batch', f'Deleted {total_deleted} purchases')
        return jsonify({'success': True, 'message': f'{total_deleted} pembelian berhasil dihapus dan stok diperbarui.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Gagal menghapus: {str(e)}'}), 500

# --- Batch update purchases ---
@app.route('/purchase/batch_update', methods=['POST'])
@login_required
def batch_update_purchase():
    data = request.get_json()
    ids = data.get('ids')
    field = data.get('field')
    find_text = data.get('find_text')
    replace_text = data.get('replace_text')
    if not all([ids, field, find_text is not None, replace_text is not None]):
        return jsonify({'success': False, 'message': 'Data tidak lengkap.'}), 400
    allowed_fields = ['nama', 'kode', 'regno', 'supplier', 'no_faktur']
    if field not in allowed_fields:
        return jsonify({'success': False, 'message': 'Kolom tidak valid.'}), 400
    try:
        items = Purchase.query.filter(Purchase.id.in_(ids)).all()
        updated = 0
        for p in items:
            val = getattr(p, field, '')
            if isinstance(val, str) and find_text in val:
                setattr(p, field, val.replace(find_text, replace_text))
                updated += 1
        db.session.commit()
        return jsonify({'success': True, 'message': f'{updated} dari {len(ids)} pembelian berhasil diperbarui.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/purchase/edit/<int:id>', methods=['GET','POST'])
@login_required
def edit_purchase(id):
    pur = Purchase.query.get_or_404(id)
    if request.method=='POST':
        # adjust stock quantity difference
        old_qty = pur.qty
        pur.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        pur.regno = request.form['regno']
        pur.no_faktur = request.form.get('no_faktur','').strip()
        pur.supplier = request.form.get('supplier','').strip()
        pur.kode = request.form['kode']
        pur.nama = request.form['nama']
        pur.qty = int(request.form.get('qty',0))
        pur.harga2 = float(request.form.get('harga',0))
        pur.jumlah = float(request.form.get('jumlah', pur.qty*pur.harga2))
        diff = pur.qty - old_qty
        stock_item = Stock.query.filter_by(kode=pur.kode).first()
        if stock_item:
            stock_item.qty += diff
        db.session.commit()
        flash('Data pembelian berhasil diperbarui','success')
        return redirect(url_for('purchases_list'))
    return render_template('purchase_form.html', title='Edit Pembelian', item=pur)

@app.route('/purchase/delete/<int:id>', methods=['POST'])
@login_required
def delete_purchase(id):
    pur = Purchase.query.get_or_404(id)
    stock_item = Stock.query.filter_by(kode=pur.kode).first()
    if stock_item:
        stock_item.qty = max(0, stock_item.qty - pur.qty)
    db.session.delete(pur)
    db.session.commit()
    flash('Pembelian dihapus. Stok diperbarui.','success')
    return redirect(url_for('purchases_list'))

@app.route('/purchase/clear_all', methods=['POST'])
@login_required
def clear_all_purchases():
    confirmation_key = request.form.get('confirmation_key')
    if confirmation_key != 'KONFIRMASI-HAPUS-SEMUA':
        flash('Kunci konfirmasi tidak valid. Data tidak dihapus.', 'danger')
        return redirect(url_for('purchases_list'))
    try:
        stock_updates = db.session.query(Purchase.kode, func.sum(Purchase.qty).label('total_qty')).group_by(Purchase.kode).all()
        for kode, qty in stock_updates:
            st = Stock.query.filter_by(kode=kode).first()
            if st:
                st.qty = max(0, st.qty - qty)
        count = db.session.query(func.count(Purchase.id)).scalar() or 0
        db.session.execute(text('DELETE FROM purchase'))
        db.session.commit()
        log_action('clear_all_purchases', f'Deleted {count} purchases')
        flash(f'Berhasil menghapus semua data pembelian ({count} record).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal menghapus data: {e}', 'danger')
    return redirect(url_for('purchases_list'))

@app.route('/purchase/print_data', methods=['GET','POST'])
@login_required
def purchase_print_data():
    ids_json = None
    if request.method == 'POST':
        try: ids_json = request.get_json().get('ids')
        except Exception: ids_json=None
    search = request.args.get('search','').strip()
    sort_by = request.args.get('sort_by','date')
    order = request.args.get('order','desc')
    regno = request.args.get('regno','').strip()
    kode = request.args.get('kode','').strip()
    nama = request.args.get('nama','').strip()
    qty = request.args.get('qty','').strip()
    start = request.args.get('start','').strip()
    end = request.args.get('end','').strip()

    q = Purchase.query
    if ids_json:
        q = q.filter(Purchase.id.in_(ids_json))
    if search:
        st=f"%{search}%"
        q=q.filter(or_(Purchase.regno.ilike(st), Purchase.kode.ilike(st), Purchase.nama.ilike(st)))
    if regno:
        q=q.filter(Purchase.regno.ilike(f"%{regno}%"))
    if kode:
        q=q.filter(Purchase.kode.ilike(f"%{kode}%"))
    if nama:
        q=q.filter(Purchase.nama.ilike(f"%{nama}%"))
    if qty:
        try:q=q.filter(Purchase.qty==int(qty))
        except:pass
    if start:
        try:start_dt=datetime.strptime(start,'%Y-%m-%d'); q=q.filter(Purchase.date>=start_dt)
        except:pass
    if end:
        try:end_dt=datetime.strptime(end,'%Y-%m-%d'); q=q.filter(Purchase.date<end_dt+timedelta(days=1))
        except:pass
    if hasattr(Purchase,sort_by):
        col=getattr(Purchase,sort_by)
        q=q.order_by(col.asc() if order=='asc' else col.desc())
    else:
        q=q.order_by(Purchase.date.desc())
    items=q.all()
    total_cost=q.with_entities(func.sum(Purchase.jumlah)).scalar() or 0

    data=[{
        'date':p.date.strftime('%Y-%m-%d'),
        'regno':p.regno,
        'kode':p.kode,
        'nama':p.nama,
        'qty':p.qty,
        'jumlah':p.jumlah
    } for p in items]
    return jsonify({
        'purchases':data,
        'total_cost':total_cost,
        'total_count':len(data),
        'filters':{
            'start':start,
            'end':end,
            'regno':regno,
            'kode':kode,
            'nama':nama,
            'qty':qty,
            'search':search
        }
    })

if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(app.instance_path): os.makedirs(app.instance_path)
        if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
        # --- schema migration for BookEntry.nota ---
        insp = db.inspect(db.engine)
        if 'book_entry' in insp.get_table_names():
            cols = [c['name'] for c in insp.get_columns('book_entry')]
            if 'nota' not in cols:
                db.session.execute(text('ALTER TABLE book_entry ADD COLUMN nota VARCHAR(50)'))
                db.session.commit()
            if 'keterangan_lain' not in cols:
                db.session.execute(text('ALTER TABLE book_entry ADD COLUMN keterangan_lain VARCHAR(255)'))
                db.session.commit()
            if 'shift' not in cols:
                db.session.execute(text("ALTER TABLE book_entry ADD COLUMN shift VARCHAR(10) DEFAULT 'Pagi'"))
                db.session.commit()
            if 'pengeluaran' not in cols:
                db.session.execute(text('ALTER TABLE book_entry ADD COLUMN pengeluaran FLOAT DEFAULT 0'))
                db.session.commit()
        # --- schema migration for Stock.jenis ---
        if 'stock' in insp.get_table_names():
            scols = [c['name'] for c in insp.get_columns('stock')]
            if 'jenis' not in scols:
                db.session.execute(text('ALTER TABLE stock ADD COLUMN jenis VARCHAR(100)'))
                db.session.commit()
        # --- schema migration for Purchase.supplier and no_faktur ---
        if 'purchase' in insp.get_table_names():
            pcols = [c['name'] for c in insp.get_columns('purchase')]
            if 'supplier' not in pcols:
                db.session.execute(text('ALTER TABLE purchase ADD COLUMN supplier VARCHAR(150)'))
            if 'no_faktur' not in pcols:
                db.session.execute(text('ALTER TABLE purchase ADD COLUMN no_faktur VARCHAR(50)'))
                
                db.session.commit()
        db.create_all()
        # Seed 10 dummy book entries if none exists
        if not BookEntry.query.first():
            base = 80738
            for i in range(10):
                num = base + i
                be = BookEntry(date=datetime.utcnow().date(), description=f"Nota {num}", nota=str(num), pemasukan=100000+i*5000, pelunasan_supplier=0, lain_lain=0)
                db.session.add(be)
            set_last_nota(base+9)
            db.session.commit()
        seed_database()
    app.run(debug=True)