# ------------------------------------------------------------------
# 文件: py-xiaozhi/src/mcp/tools/visitor_management/database.py
# ------------------------------------------------------------------

import mysql.connector
from .models import Visitor

# --- 数据库连接信息 (建议未来移入配置文件) ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'jinma'
}

class VisitorDatabase:
    """封装所有与访客数据库相关的操作"""

    def __init__(self):
        # 可以在这里初始化数据库，例如检查表是否存在
        pass

    def add_visitor(self, visitor: Visitor) -> tuple[int, str]:
        """
        将一个Visitor对象插入数据库
        :param visitor: Visitor数据模型实例
        :return: 一个元组 (新记录的ID, 错误信息或None)
        """
        db_connection = None
        db_cursor = None
        try:
            db_connection = mysql.connector.connect(**DB_CONFIG)
            db_cursor = db_connection.cursor()

            visitor_data = visitor.to_dict()
            
            columns = ', '.join(visitor_data.keys())
            placeholders = ', '.join(['%s'] * len(visitor_data))
            sql_query = f"INSERT INTO visitors ({columns}) VALUES ({placeholders})"
            
            values = tuple(visitor_data.values())
            
            db_cursor.execute(sql_query, values)
            db_connection.commit()
            
            return db_cursor.lastrowid, None

        except mysql.connector.Error as err:
            print(f"数据库操作失败: {err}")
            return -1, str(err)
        finally:
            if db_cursor:
                db_cursor.close()
            if db_connection and db_connection.is_connected():
                db_connection.close()