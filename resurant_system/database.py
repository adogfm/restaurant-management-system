# database.py
import mysql.connector
from mysql.connector import Error
import os


class Database:
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'user': 'root',
            'password': '123456',
            'database': 'restaurantdb',
            'port': 3306
        }
        self.connection = None

    def connect(self) -> object:
        """连接数据库"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            return self.connection
        except Error as e:
            print(f"数据库连接失败: {e}")
            return None

    def close(self):
        """关闭连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        """执行SQL查询"""
        connection = self.connect()
        if not connection:
            return None

        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)  # 关键：返回字典格式
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if query.strip().upper().startswith('SELECT'):
                if fetch_one:
                    result = cursor.fetchone()
                elif fetch_all:
                    result = cursor.fetchall()
                else:
                    result = cursor.fetchall()
            else:
                connection.commit()
                result = cursor.rowcount

            return result
        except Error as e:
            print(f"查询执行失败: {e}")
            print(f"SQL: {query}")
            connection.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            self.close()

    # ===== 菜品相关操作 =====
    def get_all_dishes(self):
        """获取所有菜品"""
        query = "SELECT * FROM 菜品 ORDER BY dish_no"
        return self.execute_query(query, fetch_all=True)

    def get_dish_by_id(self, dish_no):
        """根据ID获取菜品"""
        query = "SELECT * FROM 菜品 WHERE dish_no = %s"
        return self.execute_query(query, (dish_no,), fetch_one=True)

    def add_dish(self, dish_data):
        """添加菜品"""
        query = """
        INSERT INTO 菜品 
        (dish_no, dish_name, price, description, cost_price, dish_status, category, image_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_query(query, dish_data)

    def update_dish(self, dish_no, dish_data):
        """更新菜品"""
        query = """
        UPDATE 菜品 
        SET dish_name=%s, price=%s, description=%s, cost_price=%s, 
            dish_status=%s, category=%s, image_url=%s
        WHERE dish_no=%s
        """
        # 将dish_no添加到参数末尾
        params = dish_data + (dish_no,)
        return self.execute_query(query, params)

    def delete_dish(self, dish_no):
        """删除菜品"""
        query = "DELETE FROM 菜品 WHERE dish_no = %s"
        return self.execute_query(query, (dish_no,))

    # ===== 订单相关操作 =====
    def get_all_orders(self):
        """获取所有订单"""
        query = """
        SELECT * FROM 订单 
        ORDER BY order_time DESC
        """
        return self.execute_query(query, fetch_all=True)

    def get_order_detail(self, order_no):
        """获取订单详情"""
        # 订单基本信息
        order_query = "SELECT * FROM 订单 WHERE order_no = %s"
        order = self.execute_query(order_query, (order_no,), fetch_one=True)

        # 订单明细
        items_query = """
        SELECT od.*, d.dish_name, d.price, d.cost_price
        FROM 订单明细 od
        JOIN 菜品 d ON od.dish_no = d.dish_no
        WHERE od.order_no = %s
        """
        items = self.execute_query(items_query, (order_no,), fetch_all=True)

        return order, items

    def add_order(self, order_data, order_items):
        """添加订单"""
        connection = self.connect()
        if not connection:
            print("【数据库】连接失败")
            return None

        cursor = None
        try:
            cursor = connection.cursor()

            print("=" * 50)
            print("【数据库操作详细日志】")
            print(f"接收到的订单数据: {order_data}")
            print(f"接收到的订单明细数量: {len(order_items)}")

            # 解包订单数据
            order_no, total_amount, order_status, customer_phone, table_no, order_time = order_data
            print(f"订单号: {order_no}")
            print(f"原始金额: {total_amount}")
            print(f"状态: {order_status}")
            print(f"电话: {customer_phone}")
            print(f"桌号: {table_no}")
            print(f"时间: {order_time}")

            # 1. 先检查顾客是否存在，如果不存在则添加
            print(f"\n【检查顾客】电话: {customer_phone}")
            cursor.execute("SELECT phone, points FROM 顾客 WHERE phone = %s", (customer_phone,))
            customer_result = cursor.fetchone()

            if not customer_result:
                print(f"顾客 {customer_phone} 不存在，自动添加...")
                try:
                    add_customer_query = """
                    INSERT INTO 顾客 
                    (phone, name, register_time) 
                    VALUES (%s, %s, %s)
                    """
                    customer_name = f"顾客{customer_phone[-4:]}"
                    cursor.execute(add_customer_query, (customer_phone, customer_name, order_time))
                    print(f"✅ 已自动添加顾客: {customer_name} ({customer_phone})")
                    customer_points = 0
                except Exception as e:
                    print(f"❌ 添加顾客失败: {e}")
                    return False
            else:
                customer_points = customer_result[1] if customer_result[1] else 0
                print(f"✓ 顾客已存在，当前积分: {customer_points}")

            # 2. 根据积分计算折扣
            print(f"\n【计算积分折扣】")
            original_amount = float(total_amount)  # 转换为float

            # 根据积分确定折扣率
            if customer_points >= 10000:
                discount_rate = 0.8
                discount_level = '钻石会员(8折)'
            elif customer_points >= 5000:
                discount_rate = 0.85
                discount_level = '白金会员(8.5折)'
            elif customer_points >= 2000:
                discount_rate = 0.9
                discount_level = '黄金会员(9折)'
            elif customer_points >= 1000:
                discount_rate = 0.95
                discount_level = '白银会员(9.5折)'
            else:
                discount_rate = 1.0
                discount_level = '普通会员(无折扣)'

            discounted_amount = original_amount * discount_rate
            discount_amount = original_amount - discounted_amount

            if discount_rate < 1.0:
                print(f"✓ 顾客积分: {customer_points}，享受{discount_level}")
                print(f"✓ 原金额: ¥{original_amount:.2f}，折扣: -¥{discount_amount:.2f}，实付: ¥{discounted_amount:.2f}")
                final_amount = discounted_amount  # 折扣后金额
            else:
                print(f"✓ 顾客积分: {customer_points}，{discount_level}")
                print(f"✓ 订单金额: ¥{original_amount:.2f}")
                final_amount = original_amount

            # 3. 检查桌台状态
            cursor.execute("SELECT status FROM 桌台 WHERE table_no = %s", (table_no,))
            table_result = cursor.fetchone()
            if not table_result:
                print(f"❌ 错误：桌台 {table_no} 不存在")
                return False

            table_status = table_result[0]
            if table_status != '空闲':
                print(f"❌ 错误：桌台 {table_no} 状态为 '{table_status}'，不是空闲状态")
                return False

            print(f"✓ 桌台 {table_no} 状态检查通过")

            # 4. 插入订单（使用最终金额）
            print("\n【插入订单表】")
            order_query = """
            INSERT INTO 订单 
            (order_no, total_amount, order_status, customer_phone, table_no, order_time)
            VALUES (%s, %s, %s, %s, %s, %s)
            """

            # 使用最终金额（折扣后）
            final_order_data = (order_no, final_amount, order_status, customer_phone, table_no, order_time)
            print(f"插入的订单数据: {final_order_data}")

            try:
                cursor.execute(order_query, final_order_data)
                print(f"✓ 订单插入成功")
            except Exception as e:
                print(f"❌ 订单插入失败: {e}")
                import traceback
                traceback.print_exc()
                return False

            # 5. 插入订单明细
            if order_items:
                print(f"\n【插入订单明细】")
                for i, item in enumerate(order_items):
                    order_no_item, dish_no, special_request, quantity = item

                    # 检查菜品是否存在
                    cursor.execute("SELECT dish_name, price FROM 菜品 WHERE dish_no = %s", (dish_no,))
                    dish_info = cursor.fetchone()
                    if not dish_info:
                        print(f"❌ 错误：菜品 {dish_no} 不存在")
                        connection.rollback()
                        return False

                    dish_name, dish_price = dish_info
                    print(f"  明细{i + 1}: {dish_name}({dish_no}) ×{quantity} = ¥{dish_price * quantity}")

                    # 插入订单明细
                    detail_query = """
                    INSERT INTO 订单明细 
                    (order_no, dish_no, special_request, quantity)
                    VALUES (%s, %s, %s, %s)
                    """
                    try:
                        cursor.execute(detail_query, item)
                    except Exception as e:
                        print(f"❌ 订单明细插入失败: {e}")
                        connection.rollback()
                        return False

                print(f"✓ 共插入 {len(order_items)} 个订单明细")

            # 6. 更新顾客积分（1元=1积分，按原价计算）
            print(f"\n【更新顾客积分】")
            points_to_add = int(original_amount)  # 按原价计算积分，鼓励消费
            update_points_query = """
            UPDATE 顾客 
            SET points = points + %s
            WHERE phone = %s
            """
            cursor.execute(update_points_query, (points_to_add, customer_phone))
            print(f"✓ 顾客 {customer_phone} 获得 {points_to_add} 积分")

            # 获取更新后的积分
            cursor.execute("SELECT points FROM 顾客 WHERE phone = %s", (customer_phone,))
            new_points = cursor.fetchone()[0]
            print(f"✓ 顾客当前总积分: {new_points}")

            # 7. 更新桌台状态
            print(f"\n【更新桌台状态】")
            table_query = "UPDATE 桌台 SET status = '占用' WHERE table_no = %s"
            cursor.execute(table_query, (table_no,))
            print(f"✓ 桌台 {table_no} 状态已更新为 '占用'")

            # 8. 提交事务
            connection.commit()
            print("✓ 事务提交成功")
            print("=" * 50)
            return True

        except Exception as e:
            print(f"❌ 【数据库操作失败】: {e}")
            print(f"错误类型: {type(e).__name__}")

            import traceback
            traceback.print_exc()

            if connection:
                try:
                    connection.rollback()
                    print("✓ 已回滚事务")
                except:
                    pass
            return False
        finally:
            if cursor:
                cursor.close()
            self.close()

    def complete_order(self, order_no):
        """完成订单"""
        connection = self.connect()
        if not connection:
            return False

        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)  # 使用字典格式

            # 更新订单状态
            update_query = "UPDATE 订单 SET order_status = '已完成' WHERE order_no = %s"
            cursor.execute(update_query, (order_no,))

            # 获取桌台号
            table_query = "SELECT table_no FROM 订单 WHERE order_no = %s"
            cursor.execute(table_query, (order_no,))
            table_result = cursor.fetchone()

            if table_result:
                # 释放桌台
                free_table_query = "UPDATE 桌台 SET status = '空闲' WHERE table_no = %s"
                cursor.execute(free_table_query, (table_result['table_no'],))

            connection.commit()
            return True

        except Error as e:
            print(f"订单完成失败: {e}")
            connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            self.close()

    def delete_order(self, order_no):
        """删除订单"""
        connection = self.connect()
        if not connection:
            return False

        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)  # 使用字典格式

            # 获取桌台号
            table_query = "SELECT table_no FROM 订单 WHERE order_no = %s"
            cursor.execute(table_query, (order_no,))
            table_result = cursor.fetchone()

            # 删除订单明细
            detail_query = "DELETE FROM 订单明细 WHERE order_no = %s"
            cursor.execute(detail_query, (order_no,))

            # 删除订单
            order_query = "DELETE FROM 订单 WHERE order_no = %s"
            cursor.execute(order_query, (order_no,))

            if table_result:
                # 释放桌台
                free_table_query = "UPDATE 桌台 SET status = '空闲' WHERE table_no = %s"
                cursor.execute(free_table_query, (table_result['table_no'],))

            connection.commit()
            return True

        except Error as e:
            print(f"订单删除失败: {e}")
            connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            self.close()

    # ===== 桌台相关操作 =====
    def get_all_tables(self):
        """获取所有桌台"""
        query = "SELECT * FROM 桌台 ORDER BY location_type, table_no"
        return self.execute_query(query, fetch_all=True)

    def update_table_status(self, table_no, status):
        """更新桌台状态"""
        query = "UPDATE 桌台 SET status = %s WHERE table_no = %s"
        return self.execute_query(query, (status, table_no))

    # ===== 查询功能 =====
    def get_hot_dishes_ranking(self):
        """菜品排行榜查询"""
        query = """
        SELECT 
            d.dish_no AS 菜品编号,
            d.dish_name AS 菜品名称,
            d.category AS 菜品类别,
            SUM(od.quantity) AS 销售份数,
            COUNT(DISTINCT od.order_no) AS 订单次数,
            SUM(od.quantity * d.price) AS 销售额,
            SUM(od.quantity * d.price) - SUM(od.quantity * d.cost_price) AS 总利润
        FROM 订单明细 od
        JOIN 菜品 d ON od.dish_no = d.dish_no
        JOIN 订单 o ON od.order_no = o.order_no
        GROUP BY d.dish_no, d.dish_name, d.category
        ORDER BY 销售份数 DESC, 销售额 DESC
        LIMIT 10
        """
        return self.execute_query(query, fetch_all=True)

    def get_today_orders_summary(self):
        """今日订单概况（真正意义上的今天）"""
        query = """
        SELECT 
            COUNT(*) AS 今日订单总数,
            IFNULL(SUM(total_amount), 0) AS 今日总营收,
            IFNULL(AVG(total_amount), 0) AS 平均订单金额,
            COUNT(DISTINCT customer_phone) AS 今日顾客数,
            SUM(total_amount) - IFNULL(SUM(od.quantity * d.cost_price), 0) AS 今日总利润
        FROM 订单 o
        LEFT JOIN 订单明细 od ON o.order_no = od.order_no
        LEFT JOIN 菜品 d ON od.dish_no = d.dish_no
        WHERE DATE(o.order_time) = CURDATE()
        """
        return self.execute_query(query, fetch_one=True)

    def get_yesterday_orders_summary(self):
        """昨日订单概况"""
        query = """
        SELECT 
            COUNT(*) AS 昨日订单总数,
            IFNULL(SUM(total_amount), 0) AS 昨日总营收,
            IFNULL(AVG(total_amount), 0) AS 昨日平均金额,
            COUNT(DISTINCT customer_phone) AS 昨日顾客数
        FROM 订单 o
        WHERE DATE(o.order_time) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)
        """
        return self.execute_query(query, fetch_one=True)

    def get_current_month_summary(self):
        """本月订单概况"""
        query = """
        SELECT 
            COUNT(*) AS 本月订单总数,
            IFNULL(SUM(total_amount), 0) AS 本月总营收,
            COUNT(DISTINCT customer_phone) AS 本月顾客数,
            DAY(MAX(order_time)) AS 本月天数
        FROM 订单 o
        WHERE YEAR(o.order_time) = YEAR(CURDATE())
          AND MONTH(o.order_time) = MONTH(CURDATE())
        """
        return self.execute_query(query, fetch_one=True)

    def get_all_time_summary(self):
        """历史总订单概况"""
        query = """
        SELECT 
            COUNT(*) AS 总订单数,
            IFNULL(SUM(total_amount), 0) AS 历史总营收,
            IFNULL(AVG(total_amount), 0) AS 历史平均金额,
            COUNT(DISTINCT customer_phone) AS 总顾客数,
            MIN(order_time) AS 最早订单时间,
            MAX(order_time) AS 最近订单时间
        FROM 订单 o
        """
        return self.execute_query(query, fetch_one=True)

    def get_current_table_status(self):
        """当前桌台状态"""
        query = """
        SELECT 
            location_type AS 区域,
            COUNT(*) AS 总桌数,
            SUM(CASE WHEN status = '空闲' THEN 1 ELSE 0 END) AS 空闲桌数,
            SUM(CASE WHEN status = '占用' THEN 1 ELSE 0 END) AS 占用桌数,
            SUM(CASE WHEN status = '预订' THEN 1 ELSE 0 END) AS 预订桌数,
            SUM(CASE WHEN status = '清洁中' THEN 1 ELSE 0 END) AS 清洁中桌数
        FROM 桌台
        GROUP BY location_type
        ORDER BY 
            CASE location_type 
                WHEN '窗边' THEN 1
                WHEN '大厅' THEN 2
                WHEN '包间' THEN 3
                WHEN '吧台' THEN 4
                WHEN '走廊' THEN 5
                WHEN 'VIP区' THEN 6
                ELSE 7
            END
        """
        return self.execute_query(query, fetch_all=True)

    def get_pending_orders(self):
        """当前进行中的订单"""
        query = """
        SELECT 
            order_no AS 订单号,
            table_no AS 桌号,
            order_status AS 状态,
            order_time AS 下单时间,
            TIMESTAMPDIFF(MINUTE, order_time, NOW()) AS 已等待分钟,
            total_amount AS 订单金额
        FROM 订单
        WHERE order_status IN ('进行中', '待支付')
        ORDER BY order_time ASC
        """
        return self.execute_query(query, fetch_all=True)

    # ===== 顾客相关操作 =====
    def get_vip_customers(self, min_points=1000):
        """获取VIP顾客列表"""
        query = """
        SELECT * FROM 顾客 
        WHERE points >= %s 
        ORDER BY points DESC
        """
        return self.execute_query(query, (min_points,), fetch_all=True)

    def get_customer_orders(self, phone):
        """获取顾客的订单历史"""
        query = """
        SELECT 
            o.order_no,
            o.total_amount,
            o.order_status,
            o.table_no,
            o.order_time,
            COUNT(od.dish_no) as dish_count
        FROM 订单 o
        LEFT JOIN 订单明细 od ON o.order_no = od.order_no
        WHERE o.customer_phone = %s
        GROUP BY o.order_no
        ORDER BY o.order_time DESC
        """
        return self.execute_query(query, (phone,), fetch_all=True)

    def get_all_customers(self):
        """获取所有顾客"""
        query = """
        SELECT 
            phone,
            name,
            gender,
            birth_date,
            points,
            register_time,
            IF(points >= 10000, '钻石会员',
                IF(points >= 5000, '白金会员',
                    IF(points >= 2000, '黄金会员',
                        IF(points >= 1000, '白银会员', '普通会员')
                    )
                )
            ) as member_level
        FROM 顾客 
        ORDER BY register_time DESC
        """
        return self.execute_query(query, fetch_all=True)

    def get_customer_by_phone(self, phone):
        """根据电话获取顾客"""
        query = "SELECT * FROM 顾客 WHERE phone = %s"
        return self.execute_query(query, (phone,), fetch_one=True)

    def add_customer(self, customer_data):
        """添加顾客"""
        query = """
        INSERT INTO 顾客 
        (phone, name, gender, birth_date, points, register_time) 
        VALUES (%s, %s, %s, %s, %s, NOW())
        """
        return self.execute_query(query, customer_data)

    def update_customer(self, phone, customer_data):
        """更新顾客信息"""
        query = """
        UPDATE 顾客 
        SET name = %s, gender = %s, birth_date = %s, points = %s 
        WHERE phone = %s
        """
        return self.execute_query(query, (*customer_data, phone))

    def delete_customer(self, phone):
        """删除顾客"""
        query = "DELETE FROM 顾客 WHERE phone = %s"
        return self.execute_query(query, (phone,))

    def check_customer_exists(self, phone):
        """检查顾客是否存在"""
        query = "SELECT COUNT(*) as count FROM 顾客 WHERE phone = %s"
        result = self.execute_query(query, (phone,), fetch_one=True)
        return result and result['count'] > 0

    def search_customers(self, phone=None, name=None, gender=None):
        """搜索顾客"""
        query = "SELECT * FROM 顾客 WHERE 1=1"
        params = []

        if phone:
            query += " AND phone LIKE %s"
            params.append(f"%{phone}%")

        if name:
            query += " AND name LIKE %s"
            params.append(f"%{name}%")

        if gender and gender != '':
            query += " AND gender = %s"
            params.append(gender)

        query += " ORDER BY register_time DESC"
        return self.execute_query(query, tuple(params) if params else None, fetch_all=True)

    # ===== 员工相关操作 =====
    def get_all_employees(self):
        """获取所有员工"""
        query = "SELECT * FROM 员工 ORDER BY hire_date DESC"
        return self.execute_query(query, fetch_all=True)

    def get_employee_by_id(self, emp_no):
        """根据编号获取员工"""
        query = "SELECT * FROM 员工 WHERE emp_no = %s"
        return self.execute_query(query, (emp_no,), fetch_one=True)

    def add_employee(self, employee_data):
        """添加员工"""
        query = """
        INSERT INTO 员工 
        (emp_no, name, position, salary, hire_date, emp_status, phone, department) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_query(query, employee_data)

    def update_employee(self, emp_no, employee_data):
        """更新员工信息"""
        query = """
        UPDATE 员工 
        SET name = %s, position = %s, salary = %s, hire_date = %s, 
            emp_status = %s, phone = %s, department = %s 
        WHERE emp_no = %s
        """
        return self.execute_query(query, (*employee_data, emp_no))

    def delete_employee(self, emp_no):
        """删除员工"""
        query = "DELETE FROM 员工 WHERE emp_no = %s"
        return self.execute_query(query, (emp_no,))

    def check_employee_exists(self, emp_no):
        """检查员工是否存在"""
        query = "SELECT COUNT(*) as count FROM 员工 WHERE emp_no = %s"
        result = self.execute_query(query, (emp_no,), fetch_one=True)
        return result and result['count'] > 0

    def search_employees(self, emp_no=None, name=None, department=None, position=None, status=None):
        """搜索员工"""
        query = "SELECT * FROM 员工 WHERE 1=1"
        params = []

        if emp_no:
            query += " AND emp_no LIKE %s"
            params.append(f"%{emp_no}%")

        if name:
            query += " AND name LIKE %s"
            params.append(f"%{name}%")

        if department and department != '':
            query += " AND department = %s"
            params.append(department)

        if position and position != '':
            query += " AND position LIKE %s"
            params.append(f"%{position}%")

        if status and status != '':
            query += " AND emp_status = %s"
            params.append(status)

        query += " ORDER BY hire_date DESC"
        return self.execute_query(query, tuple(params) if params else None, fetch_all=True)
    def add_customer(self, customer_data):
        """添加新顾客"""
        query = """
        INSERT INTO 顾客 
        (phone, name, birth_date, gender, points, register_time)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        return self.execute_query(query, customer_data)

    def update_customer(self, phone, customer_data):
        """更新顾客信息"""
        query = """
        UPDATE 顾客 
        SET name=%s, birth_date=%s, gender=%s, points=%s
        WHERE phone=%s
        """
        params = customer_data + (phone,)
        return self.execute_query(query, params)

    def delete_customer(self, phone):
        """删除顾客"""
        query = "DELETE FROM 顾客 WHERE phone = %s"
        return self.execute_query(query, (phone,))

    # ===== 插入测试数据 =====
    def insert_sample_data(self):
        """插入测试数据"""
        connection = self.connect()
        if not connection:
            return False

        cursor = None
        try:
            cursor = connection.cursor()

            # 清空表数据（可选，按需使用）
            # cursor.execute("DELETE FROM 订单明细")
            # cursor.execute("DELETE FROM 订单")
            # cursor.execute("DELETE FROM 菜品")
            # cursor.execute("DELETE FROM 桌台")
            # cursor.execute("DELETE FROM 顾客")
            # cursor.execute("DELETE FROM 员工")

            # 插入菜品数据
            dishes = [
                ('D001', '宫保鸡丁', 58.00, '经典川菜，鸡肉鲜嫩，花生香脆', 25.00, '上架', '川菜', ''),
                ('D002', '清蒸鲈鱼', 88.00, '鲜活鲈鱼清蒸，原汁原味', 40.00, '上架', '粤菜', ''),
                ('D003', '鱼香肉丝', 32.00, '猪肉丝搭配木耳，鱼香味浓郁', 15.00, '上架', '川菜', ''),
                ('D004', '麻婆豆腐', 28.00, '豆腐嫩滑，麻辣鲜香', 12.00, '上架', '川菜', ''),
                ('D005', '蒜蓉西兰花', 24.00, '西兰花清炒，蒜香浓郁', 8.00, '上架', '家常菜', ''),
                ('D006', '糖醋排骨', 65.00, '排骨炸至酥脆，糖醋汁调味', 30.00, '上架', '家常菜', ''),
                ('D007', '西湖牛肉羹', 25.00, '牛肉末与豆腐丝，鲜美可口', 10.00, '上架', '汤类', ''),
                ('D008', '水煮肉片', 58.00, '肉片滑嫩，豆芽垫底，麻辣过瘾', 25.00, '上架', '川菜', ''),
                ('D009', '干炒牛河', 25.00, '河粉干炒不粘锅，牛肉鲜嫩', 10.00, '上架', '主食', ''),
                ('D010', '清炒时蔬', 22.00, '当日新鲜时令蔬菜清炒', 7.00, '上架', '家常菜', '')
            ]

            dish_query = """
            INSERT IGNORE INTO 菜品 
            (dish_no, dish_name, price, description, cost_price, dish_status, category, image_url)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(dish_query, dishes)

            # 插入桌台数据
            tables = [
                ('A01', 4, '空闲', '大厅'),
                ('A02', 6, '空闲', '大厅'),
                ('A03', 8, '空闲', '大厅'),
                ('B01', 2, '空闲', '窗边'),
                ('B02', 4, '空闲', '窗边'),
                ('B03', 6, '占用', '窗边'),
                ('C01', 8, '空闲', '包间'),
                ('C02', 10, '空闲', '包间'),
                ('D01', 4, '空闲', '吧台'),
                ('D02', 6, '空闲', '吧台'),
                ('V01', 6, '空闲', 'VIP区'),
                ('V02', 8, '空闲', 'VIP区')
            ]

            table_query = """
            INSERT IGNORE INTO 桌台 
            (table_no, capacity, status, location_type)
            VALUES (%s, %s, %s, %s)
            """
            cursor.executemany(table_query, tables)

            connection.commit()
            print("测试数据插入成功！")
            return True

        except Error as e:
            print(f"插入测试数据失败: {e}")
            connection.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            self.close()


# 测试数据库连接
def test_connection():
    db = Database()

    # 测试连接
    conn = db.connect()
    if conn:
        print("数据库连接成功！")
        db.close()
    else:
        print("数据库连接失败！")

    # 插入测试数据
    print("\n正在插入测试数据...")
    db.insert_sample_data()

    # 测试查询
    print("\n测试菜品查询...")
    dishes = db.get_all_dishes()
    if dishes:
        print(f"共查询到 {len(dishes)} 条菜品记录")
        for dish in dishes[:3]:  # 显示前3条
            print(f"  编号: {dish['dish_no']}, 名称: {dish['dish_name']}, 价格: ¥{dish['price']}")
    else:
        print("暂无菜品数据")

    print("\n测试桌台查询...")
    tables = db.get_all_tables()
    if tables:
        print(f"共查询到 {len(tables)} 个桌台")
        for table in tables[:3]:  # 显示前3条
            print(f"  桌号: {table['table_no']}, 状态: {table['status']}, 位置: {table['location_type']}")
    else:
        print("暂无桌台数据")

    print("\n测试菜品排行榜查询...")
    hot_dishes = db.get_hot_dishes_ranking()
    if hot_dishes:
        print("菜品排行榜（前10名）：")
        for i, dish in enumerate(hot_dishes, 1):
            print(f"{i}. {dish['菜品名称']} - 销售份数: {dish['销售份数']}")
    else:
        print("暂无菜品销售数据")

    print("\n测试今日订单概况查询...")
    today_stats = db.get_today_orders_summary()
    if today_stats:
        print(f"今日订单总数: {today_stats['今日订单总数']}")
        print(f"今日总营收: ¥{today_stats['今日总营收']:.2f}")
        print(f"平均订单金额: ¥{today_stats['平均订单金额']:.2f}")
    else:
        print("今日暂无订单数据")


if __name__ == '__main__':
    test_connection()