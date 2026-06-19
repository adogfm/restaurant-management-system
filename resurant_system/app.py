# app.py - 完整的 Flask 应用
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from datetime import datetime
from database import Database

# 获取当前文件所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')

app = Flask(__name__,
            template_folder=TEMPLATE_DIR)
app.secret_key = 'restaurant-boss-key-2023'

# 创建数据库实例
db = Database()


# ===== 页面路由 =====
@app.route('/')
def index():
    """首页"""
    if 'user' not in session:
        return render_template('login.html')
    return redirect('/dashboard')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # 简单的老板登录验证
        if username == 'boss' and password == '123456':
            session['user'] = {'username': '老板', 'role': 'boss'}
            flash('登录成功！', 'success')
            return redirect('/dashboard')
        else:
            flash('用户名或密码错误', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """退出"""
    session.pop('user', None)
    return redirect('/')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')

    # 获取各种统计数据
    today_stats = db.get_today_orders_summary() or {}
    yesterday_stats = db.get_yesterday_orders_summary() or {}
    month_stats = db.get_current_month_summary() or {}
    all_stats = db.get_all_time_summary() or {}

    # 当前桌台状态
    table_stats = db.get_current_table_status() or []

    # 菜品排行榜
    hot_dishes = db.get_hot_dishes_ranking() or []

    # 当前进行中的订单
    pending_orders = db.get_pending_orders() or []

    # 计算一些额外指标
    additional_stats = {}

    # 计算今日与昨日的对比
    if today_stats and yesterday_stats:
        today_total = today_stats.get('今日总营收', 0) or 0
        yesterday_total = yesterday_stats.get('昨日总营收', 0) or 0
        if yesterday_total > 0:
            growth_rate = ((today_total - yesterday_total) / yesterday_total) * 100
            additional_stats['营收增长率'] = f"{growth_rate:.1f}%"
        else:
            additional_stats['营收增长率'] = "新记录"

    # 计算月平均
    if month_stats:
        month_total = month_stats.get('本月总营收', 0) or 0
        month_days = month_stats.get('本月天数', 1) or 1
        additional_stats['日均营收'] = f"¥{month_total / max(month_days, 1):.2f}"

    return render_template('dashboard.html',
                           today_stats=today_stats,
                           yesterday_stats=yesterday_stats,
                           month_stats=month_stats,
                           all_stats=all_stats,
                           additional_stats=additional_stats,
                           table_stats=table_stats,
                           hot_dishes=hot_dishes,
                           pending_orders=pending_orders,
                           user=session['user'])


@app.route('/dishes')
def dishes():
    """菜品管理"""
    if 'user' not in session:
        return redirect('/')

    dishes = db.get_all_dishes() or []
    return render_template('dishes.html', dishes=dishes, user=session['user'])


@app.route('/add_dish', methods=['GET', 'POST'])
def add_dish():
    """添加菜品（添加图片上传功能）"""
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        dish_no = request.form['dish_no']
        dish_name = request.form['dish_name']
        price = float(request.form['price'])
        description = request.form['description']
        cost_price = float(request.form['cost_price'])
        dish_status = request.form['dish_status']
        category = request.form['category']

        # ============ 新增：处理图片上传 ============
        image_url = ''
        if 'dish_image' in request.files:
            file = request.files['dish_image']
            # 检查文件是否存在且文件名不为空
            if file and file.filename != '':
                # 检查文件扩展名
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # 创建上传目录
                    import os
                    upload_dir = 'static/uploads/dishes'
                    if not os.path.exists(upload_dir):
                        os.makedirs(upload_dir)

                    # 生成安全的文件名：菜品编号_时间戳.扩展名
                    import time
                    timestamp = int(time.time())
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = f"{dish_no}_{timestamp}.{ext}"

                    # 保存文件
                    filepath = os.path.join(upload_dir, filename)
                    file.save(filepath)

                    # 设置图片URL
                    image_url = f'/{upload_dir}/{filename}'
                    print(f"【图片上传】保存成功: {image_url}")
                else:
                    print("【图片上传】不支持的文件类型")
            else:
                # 如果没有上传图片，使用表单中的URL（保持原有功能）
                image_url = request.form.get('image_url', '')
        else:
            # 如果请求中没有文件字段，使用表单中的URL
            image_url = request.form.get('image_url', '')
        # ============ 图片上传处理结束 ============

        dish_data = (dish_no, dish_name, price, description,
                     cost_price, dish_status, category, image_url)

        result = db.add_dish(dish_data)

        if result:
            flash('菜品添加成功！', 'success')
            return redirect(url_for('dishes'))
        else:
            flash('菜品添加失败，请检查菜品编号是否重复', 'error')

    return render_template('add_dish.html', user=session['user'])


@app.route('/edit_dish/<dish_no>', methods=['GET', 'POST'])
def edit_dish(dish_no):
    """编辑菜品（添加图片上传功能）"""
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        dish_name = request.form['dish_name']
        price = float(request.form['price'])
        description = request.form['description']
        cost_price = float(request.form['cost_price'])
        dish_status = request.form['dish_status']
        category = request.form['category']

        # ============ 新增：处理图片上传 ============
        image_url = ''
        if 'dish_image' in request.files:
            file = request.files['dish_image']
            # 检查文件是否存在且文件名不为空
            if file and file.filename != '':
                # 检查文件扩展名
                allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
                if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
                    # 创建上传目录
                    import os
                    upload_dir = 'static/uploads/dishes'
                    if not os.path.exists(upload_dir):
                        os.makedirs(upload_dir)

                    # 生成安全的文件名：菜品编号_时间戳.扩展名
                    import time
                    timestamp = int(time.time())
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = f"{dish_no}_{timestamp}.{ext}"

                    # 保存文件
                    filepath = os.path.join(upload_dir, filename)
                    file.save(filepath)

                    # 设置图片URL
                    image_url = f'/{upload_dir}/{filename}'
                    print(f"【图片上传】保存成功: {image_url}")
                else:
                    print("【图片上传】不支持的文件类型")
            else:
                # 如果没有上传新图片，使用表单中的URL
                image_url = request.form.get('image_url', '')
        else:
            # 如果请求中没有文件字段，使用表单中的URL
            image_url = request.form.get('image_url', '')
        # ============ 图片上传处理结束 ============

        dish_data = (dish_name, price, description, cost_price,
                     dish_status, category, image_url)

        result = db.update_dish(dish_no, dish_data)

        if result:
            flash('菜品更新成功！', 'success')
            return redirect(url_for('dishes'))
        else:
            flash('菜品更新失败', 'error')

    # GET 请求，获取菜品信息
    dish = db.get_dish_by_id(dish_no)

    if dish:
        return render_template('edit_dish.html', dish=dish, user=session['user'])
    else:
        flash('菜品不存在！', 'error')
        return redirect(url_for('dishes'))


@app.route('/delete_dish/<dish_no>')
def delete_dish(dish_no):
    """删除菜品"""
    if 'user' not in session:
        return redirect('/')

    try:
        print(f"【删除菜品】尝试删除菜品: {dish_no}")

        # 1. 先检查菜品是否存在
        dish = db.get_dish_by_id(dish_no)
        if not dish:
            flash('菜品不存在！', 'error')
            return redirect(url_for('dishes'))

        dish_name = dish.get('dish_name', dish_no)

        # 2. 检查是否有订单依赖
        connection = db.connect()
        if connection:
            cursor = connection.cursor()

            try:
                # 检查订单明细表
                cursor.execute("""
                    SELECT COUNT(*) as order_count 
                    FROM 订单明细 
                    WHERE dish_no = %s
                """, (dish_no,))
                order_count_result = cursor.fetchone()
                order_count = order_count_result[0] if order_count_result else 0

                if order_count > 0:
                    flash(f'菜品"{dish_name}"已被{order_count}个订单引用，无法删除！', 'error')
                    cursor.close()
                    connection.close()
                    return redirect(url_for('dishes'))

            except Exception as check_error:
                print(f"【删除菜品】检查订单依赖时出错: {check_error}")

            finally:
                cursor.close()
                connection.close()

        # 3. 尝试删除菜品
        result = db.delete_dish(dish_no)

        if result:
            flash(f'菜品"{dish_name}"删除成功！', 'success')
            print(f"【删除菜品】删除成功: {dish_no}")
        else:
            # 可能是数据库外键约束导致的错误
            flash(f'菜品"{dish_name}"删除失败，可能已被订单引用', 'error')

    except Exception as e:
        print(f"【删除菜品】异常: {e}")
        import traceback
        traceback.print_exc()
        flash(f'删除失败: {str(e)}', 'error')

    return redirect(url_for('dishes'))


@app.route('/orders')
def orders():
    """订单管理"""
    if 'user' not in session:
        return redirect('/')

    orders = db.get_all_orders() or []
    return render_template('orders.html', orders=orders, user=session['user'])


@app.route('/add_order', methods=['GET', 'POST'])
def add_order():
    """创建订单"""
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        print("=" * 60)
        print("【开始处理订单提交】")
        print(f"所有表单字段: {list(request.form.keys())}")  # 打印所有字段

        try:
            order_no = request.form['order_no']
            table_no = request.form['table_no']
            customer_phone = request.form['customer_phone']
            order_status = '进行中'
            order_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            print(f"1. 订单号: {order_no}")
            print(f"2. 桌台号: {table_no}")
            print(f"3. 顾客电话: {customer_phone}")
            print(f"4. 下单时间: {order_time}")

            # 获取菜品数据
            dish_items = []
            total_amount = 0

            print("5. 检查菜品选择:")
            dish_count = 0

            # 打印所有dish_开头的字段
            for key in request.form:
                if key.startswith('dish_'):
                    print(f"   找到菜品字段: {key} -> 菜品编号: {request.form[key]}")

            for key in request.form:
                if key.startswith('dish_'):
                    dish_no = request.form[key]
                    quantity_key = f'quantity_{dish_no}'
                    special_key = f'special_{dish_no}'

                    print(f"   处理菜品: {dish_no}")
                    print(f"   数量字段: {quantity_key}")
                    print(f"   特殊要求字段: {special_key}")

                    if quantity_key in request.form:
                        quantity_str = request.form[quantity_key]
                        quantity = int(quantity_str) if quantity_str and quantity_str.strip() else 0

                        if quantity > 0:
                            special_request = request.form.get(special_key, '')

                            print(f"   - 菜品编号: {dish_no}, 数量: {quantity}, 特殊要求: '{special_request}'")

                            # 获取菜品价格
                            dish = db.get_dish_by_id(dish_no)
                            if dish:
                                dish_price = dish['price']
                                dish_items.append({
                                    'dish_no': dish_no,
                                    'quantity': quantity,
                                    'special_request': special_request,
                                    'price': dish_price
                                })
                                total_amount += dish_price * quantity
                                dish_count += 1
                                print(f"   - 菜品价格: ¥{dish_price}, 小计: ¥{dish_price * quantity}")
                            else:
                                print(f"   ⚠️ 菜品 {dish_no} 在数据库中不存在！")
                    else:
                        print(f"   ⚠️ 没有找到数量字段: {quantity_key}")

            print(f"6. 总计选择 {dish_count} 个菜品，总金额: ¥{total_amount:.2f}")

            if not dish_items:
                flash('请至少选择一个菜品！', 'error')
                return redirect(url_for('add_order'))

            # 准备订单数据 - 传递原始金额，database.py会计算折扣
            order_data = (order_no, total_amount, order_status, customer_phone, table_no, order_time)
            print(f"7. 订单数据（原始金额）: {order_data}")

            # 准备订单明细数据
            order_items = []
            for item in dish_items:
                order_items.append((order_no, item['dish_no'], item['special_request'], item['quantity']))
            print(f"8. 订单明细: {order_items}")

            # 添加订单
            print("9. 调用 db.add_order()...")
            result = db.add_order(order_data, order_items)

            print(f"10. db.add_order() 返回结果: {result}")

            if not result:
                print("【尝试诊断问题】")
                # 测试数据库连接
                try:
                    conn = db.connect()
                    if conn:
                        cursor = conn.cursor()

                        # 检查顾客是否存在
                        cursor.execute("SELECT phone, points FROM 顾客 WHERE phone = %s", (customer_phone,))
                        customer = cursor.fetchone()
                        if customer:
                            print(f"顾客存在: {customer[0]}, 积分: {customer[1]}")
                        else:
                            print(f"顾客 {customer_phone} 不存在")

                        # 检查桌台状态
                        cursor.execute("SELECT status FROM 桌台 WHERE table_no = %s", (table_no,))
                        table = cursor.fetchone()
                        if table:
                            print(f"桌台 {table_no} 状态: {table[0]}")
                        else:
                            print(f"桌台 {table_no} 不存在")

                        cursor.close()
                        conn.close()
                except Exception as e:
                    print(f"诊断错误: {e}")

            print("=" * 60)

            if result:
                flash('订单创建成功！', 'success')
            else:
                flash('订单创建失败，请检查数据是否正确', 'error')

        except Exception as e:
            print(f"【创建订单异常】: {str(e)}")
            import traceback
            traceback.print_exc()  # 打印完整错误堆栈
            flash(f'系统错误: {str(e)}', 'error')

        return redirect(url_for('orders'))

    # GET 请求，显示表单
    # 获取可用菜品
    dishes = db.get_all_dishes() or []
    # 只显示上架的菜品
    available_dishes = [dish for dish in dishes if dish.get('dish_status') == '上架']

    print(f"【GET请求】可用菜品数量: {len(available_dishes)}")

    # 获取空闲桌台
    tables = db.get_all_tables() or []
    available_tables = [table for table in tables if table.get('status') == '空闲']

    print(f"【GET请求】空闲桌台数量: {len(available_tables)}")
    for table in available_tables:
        print(f"   - {table.get('table_no')}: {table.get('location_type')} - {table.get('capacity')}人")

    # 生成订单号
    try:
        # 获取当前年月
        current_year_month = datetime.now().strftime('%Y%m')  # 如：202501

        # 获取所有订单
        all_orders = db.get_all_orders() or []
        print(f"【GET请求】现有订单总数: {len(all_orders)}")

        # 找出当前年月的订单
        current_month_orders = []
        for order in all_orders:
            if 'order_no' in order:
                order_no = order['order_no']
                if order_no.startswith(f'ORD{current_year_month}'):
                    current_month_orders.append(order_no)

        print(f"【GET请求】当前月份订单: {current_month_orders}")

        if current_month_orders:
            # 提取当前年月订单的最大序号
            max_seq = 0
            for order_no in current_month_orders:
                try:
                    # 尝试提取最后3位数字
                    if len(order_no) >= 3:
                        seq_part = order_no[-3:]
                        if seq_part.isdigit():
                            seq = int(seq_part)
                            if seq > max_seq:
                                max_seq = seq
                except:
                    continue

            # 生成下一个序号
            next_seq = max_seq + 1
            order_no = f'ORD{current_year_month}{next_seq:03d}'
        else:
            # 当前月份第一个订单
            order_no = f'ORD{current_year_month}001'

        print(f"【GET请求】生成的订单号: {order_no}")

    except Exception as e:
        print(f"【GET请求】生成订单号出错: {e}")
        # 如果出错，使用时间戳
        import time
        timestamp = int(time.time())
        order_no = f'ORD{timestamp}'

    return render_template('add_order.html',
                           dishes=available_dishes,
                           tables=available_tables,
                           order_no=order_no,
                           user=session['user'])


@app.route('/order_detail/<order_no>')
def order_detail(order_no):
    """订单详情"""
    if 'user' not in session:
        return redirect('/')

    order, order_items = db.get_order_detail(order_no)

    if not order:
        flash('订单不存在！', 'error')
        return redirect(url_for('orders'))

    return render_template('order_detail.html',
                           order=order,
                           order_items=order_items or [],
                           user=session['user'])


@app.route('/complete_order/<order_no>')
def complete_order(order_no):
    """完成订单"""
    if 'user' not in session:
        return redirect('/')

    result = db.complete_order(order_no)

    if result:
        flash('订单已完成，桌台已释放！', 'success')
    else:
        flash('操作失败', 'error')

    return redirect(url_for('orders'))


@app.route('/delete_order/<order_no>')
def delete_order(order_no):
    """删除订单"""
    if 'user' not in session:
        return redirect('/')

    result = db.delete_order(order_no)

    if result:
        flash('订单已取消！', 'success')
    else:
        flash('订单取消失败', 'error')

    return redirect(url_for('orders'))


@app.route('/tables')
def tables():
    """桌台管理"""
    if 'user' not in session:
        return redirect('/')

    tables = db.get_all_tables() or []
    return render_template('tables.html', tables=tables, user=session['user'])


@app.route('/update_table_status/<table_no>', methods=['POST'])
def update_table_status(table_no):
    """更新桌台状态"""
    if 'user' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401

    new_status = request.form['status']
    result = db.update_table_status(table_no, new_status)

    if result:
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': '更新失败'}), 400


# ===== API 接口 =====
@app.route('/api/hot_dishes')
def api_hot_dishes():
    """API：获取热销菜品排行榜"""
    hot_dishes = db.get_hot_dishes_ranking() or []
    return jsonify(hot_dishes)


@app.route('/api/today_stats')
def api_today_stats():
    """API：获取今日统计"""
    today_stats = db.get_today_orders_summary() or {}
    return jsonify(today_stats)


@app.route('/api/current_tables')
def api_current_tables():
    """API：获取当前桌台状态"""
    table_stats = db.get_current_table_status() or []
    return jsonify(table_stats)


@app.route('/api/pending_orders')
def api_pending_orders():
    """API：获取进行中的订单"""
    pending_orders = db.get_pending_orders() or []
    return jsonify(pending_orders)


# ===== 测试和工具路由 =====
@app.route('/test_db')
def test_db():
    """测试数据库连接"""
    conn = db.connect()
    if conn:
        db.close()
        return "数据库连接成功！"
    else:
        return "数据库连接失败！"


@app.route('/test_data')
def test_data():
    """插入测试数据"""
    result = db.insert_sample_data()
    if result:
        return "测试数据插入成功！"
    else:
        return "测试数据插入失败！"


@app.route('/clear_data')
def clear_data():
    """清空测试数据（谨慎使用）"""
    if 'user' not in session:
        return redirect('/')

    # 这里可以添加清空数据的逻辑
    flash('清空数据功能尚未实现', 'warning')
    return redirect('/dashboard')


@app.route('/export_data')
def export_data():
    """导出数据（示例）"""
    if 'user' not in session:
        return redirect('/')

    # 获取所有数据
    dishes = db.get_all_dishes() or []
    orders = db.get_all_orders() or []
    tables = db.get_all_tables() or []

    data = {
        'dishes': dishes,
        'orders': orders,
        'tables': tables,
        'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    return jsonify(data)


# ===== 错误处理 =====
@app.errorhandler(404)
def page_not_found(e):
    """404 页面"""
    return render_template('404.html', error=e), 404


@app.errorhandler(500)
def internal_server_error(e):
    """500 错误"""
    return render_template('500.html', error=e), 500


@app.route('/api/customer_discount/<phone>')
def api_customer_discount(phone):
    """API：获取顾客折扣信息"""
    try:
        print(f"【API】查询顾客折扣信息: {phone}")

        # 使用database.py中的方法获取顾客信息
        customer = db.get_customer_by_phone(phone)
        print(f"【API】数据库查询结果: {customer}")

        if customer:
            # 打印所有字段，调试用
            print(f"【API】顾客完整信息:")
            for key, value in customer.items():
                print(f"    {key}: {value}")
        else:
            print(f"【API】顾客 {phone} 不存在")

        if not customer:
            print(f"【API】顾客 {phone} 不存在")
            return jsonify({
                'success': True,
                'has_customer': False,
                'phone': phone,
                'points': 0,
                'discount_rate': 1.0,
                'discount_level': '普通会员'
            })

        # 确保正确获取积分
        points = customer.get('points', 0)
        name = customer.get('name', f'顾客{phone[-4:]}')

        print(f"【API】顾客信息 - 姓名: {name}, 积分: {points}")

        # 根据积分确定折扣率
        if points >= 10000:
            discount_rate = 0.8
            discount_level = '钻石会员'
        elif points >= 5000:
            discount_rate = 0.85
            discount_level = '白金会员'
        elif points >= 2000:
            discount_rate = 0.9
            discount_level = '黄金会员'
        elif points >= 1000:
            discount_rate = 0.95
            discount_level = '白银会员'
        else:
            discount_rate = 1.0
            discount_level = '普通会员'

        print(f"【API】折扣计算 - 等级: {discount_level}, 折扣率: {discount_rate}")

        return jsonify({
            'success': True,
            'has_customer': True,
            'phone': phone,
            'name': name,
            'points': points,
            'discount_rate': discount_rate,
            'discount_level': discount_level
        })

    except Exception as e:
        print(f"【API】查询顾客折扣失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== 顾客管理路由 ====================

@app.route('/customers')
def customers_page():
    """顾客管理页面"""
    if 'user' not in session:
        return redirect('/')
    return render_template('customers.html', user=session['user'])


@app.route('/api/customers', methods=['GET'])
def get_customers():
    """获取所有顾客（API）"""
    try:
        # 获取搜索参数
        phone = request.args.get('phone', '').strip()
        name = request.args.get('name', '').strip()
        gender = request.args.get('gender', '').strip()
        level = request.args.get('level', '').strip()

        conn = db.connect()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500

        cursor = conn.cursor()

        # 构建SQL查询
        sql = 'SELECT * FROM 顾客 WHERE 1=1'
        params = []

        if phone:
            sql += ' AND phone LIKE %s'
            params.append(f'%{phone}%')

        if name:
            sql += ' AND name LIKE %s'
            params.append(f'%{name}%')

        if gender:
            sql += ' AND gender = %s'
            params.append(gender)

        # 按等级筛选（根据积分判断）
        if level == '普通':
            sql += ' AND points < 1000'
        elif level == 'VIP':
            sql += ' AND points >= 1000 AND points < 5000'
        elif level == 'SVIP':
            sql += ' AND points >= 5000'

        sql += ' ORDER BY register_time DESC'

        cursor.execute(sql, params)

        customers = []
        for row in cursor.fetchall():
            customer = dict(zip([col[0] for col in cursor.description], row))
            customers.append(customer)

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'data': customers,
            'total': len(customers)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/customers', methods=['POST'])
def add_customer():
    """添加顾客（API）"""
    try:
        data = request.json
        phone = data.get('phone')
        name = data.get('name')
        gender = data.get('gender', 'U')
        birth_date = data.get('birth_date')
        points = data.get('points', 0)

        # 验证必填字段
        if not phone or not name:
            return jsonify({'success': False, 'error': '手机号和姓名不能为空'}), 400

        conn = db.connect()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500

        cursor = conn.cursor()

        # 检查手机号是否已存在
        cursor.execute('SELECT phone FROM 顾客 WHERE phone = %s', (phone,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': '该手机号已存在'}), 400

        # 插入新顾客
        sql = '''
            INSERT INTO 顾客 (phone, name, gender, birth_date, points, register_time) 
            VALUES (%s, %s, %s, %s, %s, NOW())
        '''
        cursor.execute(sql, (phone, name, gender, birth_date, points))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '顾客添加成功'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/customers/<phone>', methods=['PUT'])
def update_customer(phone):
    """更新顾客信息（API）"""
    try:
        data = request.json
        name = data.get('name')
        gender = data.get('gender', 'U')
        birth_date = data.get('birth_date')
        points = data.get('points', 0)

        if not name:
            return jsonify({'success': False, 'error': '姓名不能为空'}), 400

        conn = db.connect()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500

        cursor = conn.cursor()

        sql = '''
            UPDATE 顾客 
            SET name = %s, gender = %s, birth_date = %s, points = %s 
            WHERE phone = %s
        '''
        cursor.execute(sql, (name, gender, birth_date, points, phone))
        conn.commit()

        affected_rows = cursor.rowcount

        cursor.close()
        conn.close()

        if affected_rows == 0:
            return jsonify({'success': False, 'error': '顾客不存在'}), 404

        return jsonify({'success': True, 'message': '顾客信息更新成功'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/customers/<phone>', methods=['DELETE'])
def delete_customer(phone):
    """删除顾客（API）"""
    try:
        print(f"【删除顾客】尝试删除顾客: {phone}")

        conn = db.connect()
        if not conn:
            print("【删除顾客】数据库连接失败")
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500

        cursor = conn.cursor()

        # 1. 检查顾客是否存在
        cursor.execute('SELECT name FROM 顾客 WHERE phone = %s', (phone,))
        customer = cursor.fetchone()

        if not customer:
            print(f"【删除顾客】顾客 {phone} 不存在")
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': '顾客不存在'}), 404

        customer_name = customer[0]
        print(f"【删除顾客】找到顾客: {customer_name}")

        # 2. 检查顾客是否有未完成的订单
        cursor.execute('''
            SELECT COUNT(*) FROM 订单 
            WHERE customer_phone = %s AND order_status != '已完成'
        ''', (phone,))
        pending_orders = cursor.fetchone()[0]

        print(f"【删除顾客】未完成订单数: {pending_orders}")

        if pending_orders > 0:
            cursor.close()
            conn.close()
            return jsonify({
                'success': False,
                'error': f'顾客"{customer_name}"有{pending_orders}个未完成订单，不能删除'
            }), 400

        # 3. 删除顾客
        cursor.execute('DELETE FROM 顾客 WHERE phone = %s', (phone,))
        conn.commit()

        affected_rows = cursor.rowcount
        print(f"【删除顾客】删除影响行数: {affected_rows}")

        cursor.close()
        conn.close()

        if affected_rows == 0:
            return jsonify({'success': False, 'error': '顾客删除失败'}), 400

        return jsonify({
            'success': True,
            'message': f'顾客"{customer_name}"删除成功'
        })

    except Exception as e:
        print(f"【删除顾客】异常: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== 员工管理路由 ====================

@app.route('/employees')
def employees_page():
    """员工管理页面"""
    if 'user' not in session:
        return redirect('/')
    return render_template('employees.html', user=session['user'])


@app.route('/api/employees', methods=['GET'])
def get_employees():
    """获取所有员工（API）"""
    try:
        conn = db.connect()
        if not conn:
            return jsonify({'error': '数据库连接失败'}), 500

        cursor = conn.cursor()
        cursor.execute('SELECT * FROM 员工 ORDER BY hire_date DESC')
        employees = []
        for row in cursor.fetchall():
            employee = dict(zip([col[0] for col in cursor.description], row))
            employees.append(employee)

        cursor.close()
        conn.close()
        return jsonify(employees)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/employees', methods=['POST'])
def add_employee():
    """添加员工（API）"""
    try:
        data = request.json
        emp_no = data.get('emp_no')
        name = data.get('name')
        position = data.get('position')
        salary = data.get('salary')
        hire_date = data.get('hire_date')
        emp_status = data.get('emp_status', '在职')
        phone = data.get('phone')
        department = data.get('department')

        # 验证必填字段
        required_fields = ['emp_no', 'name', 'position', 'salary', 'hire_date', 'department']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field}不能为空'}), 400

        conn = db.connect()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500

        cursor = conn.cursor()

        # 检查员工编号是否已存在
        cursor.execute('SELECT emp_no FROM 员工 WHERE emp_no = %s', (emp_no,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'error': '该员工编号已存在'}), 400

        # 插入新员工
        sql = '''
            INSERT INTO 员工 (emp_no, name, position, salary, hire_date, emp_status, phone, department) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        '''
        cursor.execute(sql, (emp_no, name, position, salary, hire_date, emp_status, phone, department))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': '员工添加成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/employees/<emp_no>', methods=['PUT'])
def update_employee(emp_no):
    """更新员工信息（API）"""
    try:
        data = request.json
        name = data.get('name')
        position = data.get('position')
        salary = data.get('salary')
        hire_date = data.get('hire_date')
        emp_status = data.get('emp_status', '在职')
        phone = data.get('phone')
        department = data.get('department')

        # 验证必填字段
        required_fields = ['name', 'position', 'salary', 'hire_date', 'department']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field}不能为空'}), 400

        conn = db.connect()
        if not conn:
            return jsonify({'error': '数据库连接失败'}), 500

        cursor = conn.cursor()

        sql = '''
            UPDATE 员工 
            SET name = %s, position = %s, salary = %s, hire_date = %s, 
                emp_status = %s, phone = %s, department = %s 
            WHERE emp_no = %s
        '''
        cursor.execute(sql, (name, position, salary, hire_date, emp_status, phone, department, emp_no))
        conn.commit()

        affected_rows = cursor.rowcount

        cursor.close()
        conn.close()

        if affected_rows == 0:
            return jsonify({'error': '员工不存在'}), 404

        return jsonify({'success': True, 'message': '员工信息更新成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/employees/<emp_no>', methods=['DELETE'])
def delete_employee(emp_no):
    """删除员工（API）"""
    try:
        conn = db.connect()
        if not conn:
            return jsonify({'success': False, 'error': '数据库连接失败'}), 500

        cursor = conn.cursor()

        # 检查员工是否有关联数据（例如是否是经理等）
        # 这里可以根据业务需求添加更多的检查

        cursor.execute('DELETE FROM 员工 WHERE emp_no = %s', (emp_no,))
        conn.commit()

        affected_rows = cursor.rowcount

        cursor.close()
        conn.close()

        if affected_rows == 0:
            return jsonify({'success': False, 'error': '员工不存在'}), 404

        return jsonify({'success': True, 'message': '员工删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== 主程序 =====
if __name__ == '__main__':
    print("=" * 50)
    print("餐厅管理系统启动")
    print("1. 主页面: http://localhost:5000")
    print("\n登录账号: boss / 123456")
    print("=" * 50)

    # 启动应用
    app.run(debug=True, host='0.0.0.0', port=5000)