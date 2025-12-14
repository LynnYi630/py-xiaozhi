from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

class DatabaseManager:
    _instance = None
    _engine = None
    _session_factory = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DatabaseManager()
        return cls._instance

    def __init__(self):
        if self._engine is None:
            self._init_db()

    def _init_db(self):
        try:
            config = ConfigManager.get_instance()
            # 假设 config.json 中有 database 字段，包含 mysql 配置
            # 格式需确保: mysql+pymysql://user:password@host:port/dbname
            db_cfg = config.get_config("DATABASE", {})
            
            # 这里为了演示，构建连接字符串，请根据实际配置结构调整
            user = db_cfg.get("user", "root")
            password = db_cfg.get("password", "password")
            host = db_cfg.get("host", "localhost")
            port = db_cfg.get("port", 3306)
            db_name = db_cfg.get("db_name", "company_db")
            
            database_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8mb4"
            
            self._engine = create_engine(
                database_url,
                pool_recycle=3600,
                pool_pre_ping=True,
                echo=False
            )
            self._session_factory = scoped_session(sessionmaker(bind=self._engine))
            logger.info("[EmployeeDB] 数据库连接已初始化")
        except Exception as e:
            logger.error(f"[EmployeeDB] 数据库初始化失败: {e}")
            raise

    def get_session(self):
        return self._session_factory()