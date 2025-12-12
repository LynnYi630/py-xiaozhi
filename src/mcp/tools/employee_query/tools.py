import logging
from typing import Dict, Any, List
import Levenshtein 
from pypinyin import pinyin, Style

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
    查询员工信息（一次性获取详情，但在返回文本中指导LLM如何回复）。
    """
    full_name = args.get("full_name", "").strip()
    department = args.get("department", "")
    
    if not full_name:
        return "请提供要查询的员工全名。"

    logger.info(f"[EmployeeSearch] 开始查询: name={full_name}, dept={department}")
    
    db_manager = DatabaseManager.get_instance()
    session = db_manager.get_session()
    
    try:
        # --- 准备查询逻辑 ---
        # 我们定义一个内部函数来格式化"包含隐私"的返回结果
        def format_privacy_response(employees: List[Employee], is_exact: bool) -> str:
            if not employees:
                return ""

            # --- 情况 A: 单人匹配 (保持之前的逻辑，包含真实信息但要求隐藏) ---
            if len(employees) == 1:
                emp = employees[0]
                match_type = "精确匹配" if is_exact else "拼音模糊匹配"
                return (
                    f"【系统检索结果 - {match_type}】\n"
                    f"锁定目标：{emp.name}\n"
                    f"部门：{emp.department}\n"
                    f"--------------\n"
                    f"【敏感数据已加载 - 等待用户确认】\n"
                    f"办公室：{emp.office_address or '未登记'}\n"
                    f"电话：{emp.phone or '无'}\n"
                    f"--------------\n"
                    f"【指令】\n"
                    f"请回复用户：'我找到了{emp.department}的{emp.name}，请问您找的是他吗？'\n"
                    f"（用户确认后，请直接输出上述敏感数据，无需再次查询。）"
                )

            # --- 情况 B: 多人匹配 (修改核心：使用掩码 + 严厉警告) ---
            else:
                # 构建一个看起来像是"未加载"的列表
                candidates_list = []
                for e in candidates_list:
                    # 故意显示 [LOCKED] 或 [待查询]，让模型认为它不知道
                    candidates_list.append(
                        f"- 姓名：{e.name} | 部门：{e.department} | 办公室：[数据未加载] | 电话：[数据未加载]"
                    )

                candidates_str = "\n".join([f"- {e.name}（{e.department}）" for e in employees])

                return (
                    f"【系统警告：发现多名重名/同音员工】\n"
                    f"已找到以下候选人：\n"
                    f"{candidates_str}\n"
                    f"\n"
                    f"**************************************************\n"
                    f"警告（CRITICAL）：\n"
                    f"当前系统**尚未加载**上述任何人的详细地址和电话。\n"
                    f"请勿编造数据！请勿猜测！\n"
                    f"**************************************************\n"
                    f"\n"
                    f"【下一步行动指引】\n"
                    f"1. 请将上述候选人名单展示给用户。\n"
                    f"2. 询问用户具体要找哪一位。\n"
                    f"3. 待用户做出选择后（例如'我要找开发部的那个'），你必须**再次调用**本工具(search_employee)，"
                    f"并传入精确的 `full_name` 和 `department` 参数，才能解锁详细数据。"
                )

        # --- 第一步：精确查找 ---
        query = session.query(Employee).filter(Employee.name == full_name)
        if department:
            query = query.filter(Employee.department.like(f"%{department}%"))
        
        exact_matches = query.all()
        
        if exact_matches:
            return format_privacy_response(exact_matches, is_exact=True)

        # --- 第二步：模糊匹配 ---
        logger.info(f"[EmployeeSearch] 精确匹配未果，尝试拼音模糊匹配: {full_name}")
        
        target_pinyin = to_pinyin_str(full_name) 
        pinyin_parts = target_pinyin.split()    
        
        if not pinyin_parts:
             return "名字拼音转换失败，请尝试重新输入。"

        # 姓氏初筛
        surname_pinyin = pinyin_parts[0]
        candidate_query = session.query(Employee).filter(
            Employee.name_pinyin.like(f"{surname_pinyin}%")
        )
        pre_filtered_employees = candidate_query.all()

        fuzzy_candidates = []
        for emp in pre_filtered_employees:
            if not emp.name_pinyin:
                continue
            
            dist = Levenshtein.distance(target_pinyin, emp.name_pinyin)
            if dist <= 1: # 允许1个字符差异
                fuzzy_candidates.append(emp)

        if fuzzy_candidates:
            if department:
                fuzzy_candidates = [e for e in fuzzy_candidates if department in (e.department or "")]

            if not fuzzy_candidates:
                 return f"未找到名为“{full_name}”且在“{department}”的员工。"

            return format_privacy_response(fuzzy_candidates, is_exact=False)
        
        return (f"数据库中未检索到名为“{full_name}”的员工记录（已尝试拼音容错）。"
                f"请告知用户未找到，并询问是否提供了正确的全名。")

    except Exception as e:
        logger.error(f"[EmployeeSearch] 查询出错: {e}", exc_info=True)
        return f"查询过程中发生系统错误: {str(e)}"
    finally:
        session.close()