import logging
from typing import Dict, Any, List
from sqlalchemy import or_
from pypinyin import pinyin, Style
import Levenshtein  # <--- 修改1：引入专业库

from src.utils.logging_config import get_logger
from .database import DatabaseManager
from .models import Employee

logger = get_logger(__name__)

# --- 辅助函数：转拼音 ---
def to_pinyin_str(text: str) -> str:
    """
    将中文转换为带空格的全拼
    输入: '黄耀科'
    输出: 'huang yao ke'
    """
    # NORMAL 模式是不带声调的
    pinyins = pinyin(text, style=Style.NORMAL)
    # 过滤非中文字符的空值或异常
    clean_pinyins = [p[0] for p in pinyins if p]
    return " ".join(clean_pinyins)

async def search_employee(args: Dict[str, Any]) -> str:
    """
    查询员工信息。
    """
    full_name = args.get("full_name", "").strip()
    department = args.get("department", "")
    
    if not full_name:
        return "请提供要查询的员工全名。"

    logger.info(f"[EmployeeSearch] 开始查询: name={full_name}, dept={department}")
    
    db_manager = DatabaseManager.get_instance()
    session = db_manager.get_session()
    
    try:
        # --- 第一步：精确查找 (优先匹配汉字完全一致的) ---
        # 理由：如果名字完全一样，就不需要去算拼音距离了，这是最高优先级
        query = session.query(Employee).filter(Employee.name == full_name)
        if department:
            # 部门名称通常用户说的不准确，所以用 LIKE
            query = query.filter(Employee.department.like(f"%{department}%"))
        
        exact_matches = query.all()
        
        if exact_matches:
            if len(exact_matches) == 1:
                emp = exact_matches[0]
                return (f"为您找到一位员工：{emp.name}（{emp.department or '未知部门'}）。"
                        f"请确认这是您要找的人吗？")
            else:
                candidates_str = "、".join([f"{e.name}({e.department})" for e in exact_matches])
                return f"找到多位名为 {full_name} 的员工：{candidates_str}。请问您要找的是哪一位？"

        # --- 第二步：模糊匹配 (拼音 + Levenshtein + 数据库前缀筛选) ---
        logger.info(f"[EmployeeSearch] 精确匹配未果，尝试拼音模糊匹配: {full_name}")
        
        target_pinyin = to_pinyin_str(full_name) # e.g. "huang yao ke"
        pinyin_parts = target_pinyin.split()     # ['huang', 'yao', 'ke']
        
        if not pinyin_parts:
             return "名字拼音转换失败，请尝试重新输入。"

        # <--- 修改2：先用姓氏（拼音首词）在数据库层面做初筛 --->
        surname_pinyin = pinyin_parts[0] # "huang"
        
        # SQL: SELECT * FROM employees WHERE name_pinyin LIKE 'huang%'
        # 这样避免了把全公司几万人的数据都拉到内存里算距离
        candidate_query = session.query(
            Employee.id, Employee.name, Employee.department, Employee.name_pinyin
        ).filter(
            Employee.name_pinyin.like(f"{surname_pinyin}%")
        )
        
        # 拉取初筛结果到内存
        pre_filtered_employees = candidate_query.all()
        logger.debug(f"[EmployeeSearch] 姓氏'{surname_pinyin}'初筛结果数量: {len(pre_filtered_employees)}")

        fuzzy_candidates = []
        for emp in pre_filtered_employees:
            if not emp.name_pinyin:
                continue
            
            # <--- 修改1：使用 python-Levenshtein 库计算距离 --->
            # distance 计算的是字符操作次数。
            dist = Levenshtein.distance(target_pinyin, emp.name_pinyin)
            
            # 容错机制：距离小于等于1（允许一个字母的差异，或少一个音）
            # 注意：如果名字很短（2个字），距离为1可能误差较大，可以根据长度动态调整阈值，这里维持原逻辑
            if dist <= 1:
                fuzzy_candidates.append(emp)

        if fuzzy_candidates:
            # 二次过滤：如果有部门信息，再筛一遍
            if department:
                fuzzy_candidates = [e for e in fuzzy_candidates if department in (e.department or "")]

            if not fuzzy_candidates:
                 return (f"未找到名为“{full_name}”且在“{department}”的员工。")

            # 构建回复
            candidates_list = []
            for emp in fuzzy_candidates:
                candidates_list.append(f"{emp.name}（{emp.department}）")
            
            candidates_str = "、".join(candidates_list)
            return (f"未找到“{full_name}”的精确匹配，但找到了近似结果：{candidates_str}。"
                    f"请问这里面有您要找的人吗？")
        
        return (f"没有查询到结果。未找到名为“{full_name}”的员工（已尝试拼音模糊搜索）。"
                f"请尝试提供标准全名。")

    except Exception as e:
        logger.error(f"[EmployeeSearch] 查询出错: {e}", exc_info=True)
        return f"查询过程中发生系统错误: {str(e)}"
    finally:
        session.close()

# get_employee_detail 函数保持不变，它只负责精确ID或Name的查询