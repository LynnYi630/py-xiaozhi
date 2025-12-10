from sqlalchemy import Column, Integer, String, Timestamp
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Employee(Base):
    __tablename__ = 'employees'

    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    name = Column(String(50), nullable=False, comment='姓名')
    phone = Column(String(20), comment='电话')
    office_address = Column(String(255), comment='办公室地址')
    job_title = Column(String(100), comment='职务')
    department = Column(String(100), comment='部门')
    supervisor = Column(String(50), comment='上级人员')
    created_at = Column(Timestamp, nullable=False, server_default=func.now(), comment='创建时间')
    updated_at = Column(Timestamp, nullable=False, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    name_pinyin = Column(String(100), comment='姓名全拼，不带声调')

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "department": self.department,
            "job_title": self.job_title,
            "office_address": self.office_address,
            "phone": self.phone,
            "name_pinyin": self.name_pinyin
        }