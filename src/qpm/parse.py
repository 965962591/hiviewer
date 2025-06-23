# -*- coding: utf-8 -*-
from lxml import etree as ET
import os
import xml.sax.saxutils as saxutils
import concurrent.futures
import copy
from functools import lru_cache
import time
from io import BytesIO
import gc
import configparser


# 设置SA.ini文件路径
from pathlib import Path
SA_CONFIG_FILE = Path(__file__).parent.parent.parent / "resource" / "tools" / "SA.ini"

# 预编译XPath表达式
XPATHS = {
    "current_frame": ET.XPath(".//Current_Frame"),
    "lux_index": ET.XPath("Lux_Index"),
    "average_luma": ET.XPath("Average_Luma"),
    "fps": ET.XPath("FPS"),
    "aecx_metering": ET.XPath(".//AECX_Metering"),
    "sat_ratio": ET.XPath("Sat_Ratio"),
    "dark_ratio": ET.XPath("Dark_Ratio"),
    "general_sas": ET.XPath(".//General_SAs"),
    "analyzer_name": ET.XPath("Analyzer_Name"),
    "analyzer_id": ET.XPath("Analyzer_ID"),
    "luma_component": ET.XPath(".//Luma_Component/Aggregated_Value/start"),
    "target_component_start": ET.XPath(".//Target_Component/Aggregated_Value/start"),
    "target_component_end": ET.XPath(".//Target_Component/Aggregated_Value/end"),
    "confidence_component": ET.XPath(".//Confidence_Component/Aggregated_Value/start"),
    "adjustment_ratio_start": ET.XPath(".//Adjustment_Ratio/start"),
    "adjustment_ratio_end": ET.XPath(".//Adjustment_Ratio/end"),
    "arithmetic_operators": ET.XPath("Arithmetic_Operators"),
    "output_db": ET.XPath(".//Output_DB"),
    "data_name": ET.XPath("dataName"),
    "operands": ET.XPath("Operands"),
    "operation_method": ET.XPath("Operation_Method"),
    "output_value": ET.XPath("Output_Value"),
    "awb_cct": ET.XPath('.//AWB_CurFrameDecision[@Index="1"]/CCT'),  # 新增的XPath
    "short_gain": ET.XPath('.//Exposure_Information[@Index="0"]/Gain'),
    "long_gain": ET.XPath('.//Exposure_Information[@Index="1"]/Gain'),
    "safe_gain": ET.XPath('.//Exposure_Information[@Index="2"]/Gain'),
    "all_channels_lists": ET.XPath('.//AECX_CoreStats/Channels_List'),
    "channel_data": ET.XPath('Channel_Data[@ID="6"]'),
    "value_grid": ET.XPath("Value_Grid"),
    "r_gain": ET.XPath('.//Tuning_AWB_Data/AWB_Gains[@Index="0"]'),
    "b_gain": ET.XPath('.//Tuning_AWB_Data/AWB_Gains[@Index="2"]'),
    "triangle_index": ET.XPath(".//AWB_TriangleGainAdjust/Triangle_Index"),
    "awb_sagen1data": ET.XPath(".//AWB_SAGen1Data"),
    "sa_description": ET.XPath("./SA_Description"),
    "awb_descriptions_direct": ET.XPath(".//AWB_SAGen1Data/SA_Description"),
    "assist_data": ET.XPath(".//AWB_SA_Face_Assist/Face_Assist_Confidence"),
    "aec_settled": ET.XPath(".//AEC_Settled"),
    # 新增 R_G_Ratio 和 B_G_Ratio 的 XPath
    "r_g_ratio": ET.XPath('.//AWB_Decision_Data[@ID="4"]/Point[@ID="1"]/R_G_Ratio'),
    "b_g_ratio": ET.XPath('.//AWB_Decision_Data[@ID="4"]/Point[@ID="1"]/B_G_Ratio'),
}

# 在文件开头添加模板定义
SA_TEMPLATE = ET.fromstring("""
<SA>
    <id/>
    <luma/>
    <target>
        <start/>
        <end/>
    </target>
    <confidence/>
    <adjratio>
        <start/>
        <end/>
    </adjratio>
    <step/>
</SA>
""")

OPERATOR_TEMPLATE = ET.fromstring("""
<operator>
    <operators_num/>
    <operators_method/>
</operator>
""")


# 新增：用于 save_results_to_xml 的配置字典
SINGLE_VALUE_CONFIG = [
    ("awb_cct", "CCT"),
    ("r_g_ratio", "R_G_Ratio"),
    ("b_g_ratio", "B_G_Ratio"),
    ("short_gain", "short_gain"),
    ("long_gain", "long_gain"),
    ("safe_gain", "safe_gain"),
    ("r_gain", "r_gain"),
    ("b_gain", "b_gain"),
    ("aec_settled", "aec_settled"),
    ("triangle_index", "triangle_index"),
]

SA_TEMPLATE_MAP = {
    "id": "id",
    "luma": "luma",
    "target/start": "target_start",
    "target/end": "target_end",
    "confidence": "confidence",
    "adjratio/start": "adjratio_start",
    "adjratio/end": "adjratio_end",
}



# 优化 calculate_operation 的性能
OPERATION_HANDLERS = {
    "Division(3)": lambda op, out: f"{op[0]} * {op[1]} / {op[2]} * {op[3]} = {out}",
    "Multiplication(2)": lambda op, out: f"{op[0]} * {op[1]} * {op[2]} * {op[3]} = {out}",
    "Addition(0)": lambda op, out: f"{op[0]} * {op[1]} + {op[2]} * {op[3]} = {out}",
    "Subtraction(1)": lambda op, out: f"{op[0]} * {op[1]} - {op[2]} * {op[3]} = {out}",
    "Min(5)": lambda op, out: f"min({op[0]} * {op[1]}, {op[2]} * {op[3]}) = {out}",
    "Max(4)": lambda op, out: f"max({op[0]} * {op[1]},{op[2]} * {op[3]}) = {out}",
    "CondSmaller(13)": lambda op, out: f"({op[0]} 小于 {op[1]} ? {op[2]} : {op[3]}) = {cond_smaller(op[0], op[1], op[2], op[3])}",
    "CondLarger(12)": lambda op, out: f"({op[0]} 大于 {op[1]} ? {op[2]} : {op[3]}) = {cond_larger(op[0], op[1], op[2], op[3])}",
    "CondEqual(14)": lambda op, out: f"({op[0]} 等于 {op[1]} ? {op[2]} : {op[3]}) = {cond_equal(op[0], op[1], op[2], op[3])}",
    "Largest(8)": lambda op, out: f"max({op[0]},{op[1]},{op[2]},{op[3]}) = {out}",
    "Smallest(6)": lambda op, out: f"min({op[0]},{op[1]},{op[2]},{op[3]}) = {out}",
}

@lru_cache(maxsize=128)
def get_sa_template():
    return ET.fromstring("""
    <SA>
        <id/>
        <luma/>
        <target>
            <start/>
            <end/>
        </target>
        <confidence/>
        <adjratio>
            <start/>
            <end/>
        </adjratio>
        <step/>
    </SA>
    """)


def parse_xml(file_path):
    """
    解析XML文件，处理可能的命名空间问题
    
    Args:
        file_path: XML文件路径
        
    Returns:
        lxml.etree._Element: 解析后的XML根节点
    """
    try:
        # 创建自定义的解析器
        parser = ET.XMLParser(recover=True, remove_blank_text=True, remove_comments=True)
        
        # 读取文件内容
        with open(file_path, 'rb') as f:
            content = f.read()
            
        # 尝试移除所有命名空间声明
        content = content.replace(b'xmlns:', b'ignore_')
        content = content.replace(b'xmlns=', b'ignore=')
            
        # 使用修改后的内容和自定义解析器解析XML
        tree = ET.fromstring(content, parser=parser)
        
        return tree
    except Exception as e:
        print(f"Error parsing XML file {file_path}: {str(e)}")
        raise


def extract_values(root, path):
    element = root.find(path)
    return [child.text for child in element]


def extract_lux_values(root):
    lux = XPATHS["current_frame"](root)[0]
    lux_index = XPATHS["lux_index"](lux)[0].text
    ava_luma = XPATHS["average_luma"](lux)[0].text
    fps = XPATHS["fps"](lux)[0].text
    return lux_index, ava_luma, fps


def extract_sat_values(root):
    sat = XPATHS["aecx_metering"](root)[0]
    sat_ratio = XPATHS["sat_ratio"](sat)[0].text
    dark_ratio = XPATHS["dark_ratio"](sat)[0].text
    return sat_ratio, dark_ratio


def extract_SA_values(sa_nodes_map, sa_name):
    """
    从预先构建的SA节点字典中提取单个SA的值。
    """
    target_sa = sa_nodes_map.get(sa_name)

    if target_sa is None:
        return None

    # 批量获取数据而不是多次调用XPath
    try:
        SA_name = XPATHS["analyzer_name"](target_sa)[0].text
        id = XPATHS["analyzer_id"](target_sa)[0].text
        luma = XPATHS["luma_component"](target_sa)[0].text
        target_start = XPATHS["target_component_start"](target_sa)[0].text
        target_end = XPATHS["target_component_end"](target_sa)[0].text
        confidence = XPATHS["confidence_component"](target_sa)[0].text
        adjratio_start = XPATHS["adjustment_ratio_start"](target_sa)[0].text
        adjratio_end = XPATHS["adjustment_ratio_end"](target_sa)[0].text
    except (IndexError, AttributeError):
        print(f"Error: Missing required data in {SA_name}")
        return None

    operators_name, calculations, operators_num, operators_method = [], [], [], []
    arithmetic_operators = XPATHS["arithmetic_operators"](target_sa)

    for operator in arithmetic_operators:
        output_db = XPATHS["output_db"](operator)
        if not output_db:
            continue

        output_db_name = XPATHS["data_name"](output_db[0])
        if not output_db_name or not output_db_name[0].text:
            break
            
        operands = [float(op.text) for op in XPATHS["operands"](operator)]
        operation_method = XPATHS["operation_method"](operator)[0].text
        output_value = XPATHS["output_value"](operator)[0].text

        calculation = calculate_operation(operands, operation_method, output_value)
        operators_name.append(output_db_name[0].text)
        calculations.append(calculation)
        operators_num.append(operands)
        operators_method.append(operation_method)
        
    # print(f"sa name:{SA_name},id:{id},luma:{luma},target start:{target_start},target end:{target_end},confidence:{confidence}")
    
    # 返回字典而不是元组，以提高可读性和可维护性
    return {
        "name": SA_name,
        "id": id,
        "luma": luma,
        "target_start": target_start,
        "target_end": target_end,
        "confidence": confidence,
        "operators_name": operators_name,
        "adjratio_start": adjratio_start,
        "adjratio_end": adjratio_end,
        "calculations": calculations,
        "operators_num": operators_num,
        "operators_method": operators_method,
    }




def calculate_operation(operands, operation_method, output_value):
    handler = OPERATION_HANDLERS.get(operation_method)
    if handler:
        return handler(operands, output_value)
    else:
        return f"Unknown operation method: {operation_method}"


def cond_smaller(value, threshold, true_value, false_value):
    return true_value if value < threshold else false_value


def cond_larger(value, threshold, true_value, false_value):
    return true_value if value > threshold else false_value


def cond_equal(value, threshold, true_value, false_value):
    return true_value if value == threshold else false_value


def calculate_safe_exp_values(
    root,
    file_name_without_ext,
    file_path,
    **kwargs
):
    # 从配置文件加载SA配置
    required_sas, optional_sas, sa_order, agg_sas = load_sa_config()

    # kwargs 包含了所有以 "_values" 结尾的SA数据，其值现在是字典
    sa_values_dict = {sa_name: kwargs.get(f"{sa_name}_values") for sa_name in required_sas + optional_sas}

    # 检查必需的参数是否存在
    missing_required = [sa for sa in required_sas if sa_values_dict.get(sa) is None]
    if missing_required:
        raise ValueError(f"缺少必需的SA参数: {', '.join(missing_required)}")

    # 使用字典键访问，提高可读性和健壮性
    framesa_values = sa_values_dict["FrameSA"]
    SafeAggSA_values = sa_values_dict["SafeAggSA"]
    ShortAggSA_values = sa_values_dict["ShortAggSA"]

    # 直接从字典获取值，避免了大量的位置解包
    Frame_confidence = float(framesa_values['confidence'])
    Frame_adjratio_start = float(framesa_values['adjratio_start'])
    Frame_adjratio_end = float(framesa_values['adjratio_end'])
    SafeAgg_adjratio_start = float(SafeAggSA_values['adjratio_start'])
    ShortAgg_adjratio_start = float(ShortAggSA_values['adjratio_start'])

    # 初始化结果列表
    results_str, result, result_confidence, name_list = [], [], [], []
    
    # 计算FrameSA的贡献
    framesa_adjratio = Frame_confidence * Frame_adjratio_start
    framesa_adjratio = round(framesa_adjratio, 5)

    print("\n--- 统一聚合处理 ---")
    print(f"SafeAggSA AdjRatio Start (基准值): {SafeAgg_adjratio_start}")
    print(f"FrameSA Confidence: {Frame_confidence}, AdjRatio Start: {Frame_adjratio_start}, AdjRatio End: {Frame_adjratio_end}")
    
    # 遍历所有活动的SA进行计算，逻辑更清晰
    print("  - 遍历活动的SA (基于SafeAggSA区间):")
    for sa_name in agg_sas:
        sa_data = sa_values_dict.get(sa_name)
        if not sa_data:
            continue

        confidence = float(sa_data['confidence'])
        adjratio_start = float(sa_data['adjratio_start'])
        adjratio_end = float(sa_data['adjratio_end'])

        print(f"    - 正在检查 SA: {sa_name}")
        if confidence == 0:
            print(f"      - 跳过 {sa_name}: Confidence 为 0")
            continue
        if adjratio_start < 0 or adjratio_end < 0:
            print(f"      - 跳过 {sa_name}: AdjRatio 包含负值 ({adjratio_start}, {adjratio_end})")
            continue

        # 判断应该使用哪个adjratio
        chosen_adjratio = None
        if adjratio_start >= SafeAgg_adjratio_start:
            chosen_adjratio = adjratio_start
            print(f"        - {adjratio_start} >= {SafeAgg_adjratio_start}，使用 adjratio_start ({adjratio_start})")
        elif adjratio_end <= SafeAgg_adjratio_start:
            chosen_adjratio = adjratio_end
            print(f"        - {adjratio_end} <= {SafeAgg_adjratio_start}，使用 adjratio_end ({adjratio_end})")
        else:
            print(f"        - {sa_name} 与 SafeAggSA 区间重叠，跳过")
        
        # 如果选定了adjratio，则进行计算
        if chosen_adjratio is not None and sa_name not in name_list:
            name_list.append(sa_name)
            calc_value = confidence * chosen_adjratio
            cal_str = f"{confidence} * {chosen_adjratio} = {round(calc_value, 5)}"
            results_str.append(cal_str)
            result.append(calc_value)
            result_confidence.append(confidence)

    # --- 聚合计算逻辑 (FrameSA 始终参与) ---
    safe_agg_value_from_sa = round(SafeAgg_adjratio_start, 5)

    # 聚合计算 (包含所有符合条件的SA和FrameSA)
    print("\n--- 聚合计算 ---")
    result_sum = sum(result) + framesa_adjratio
    confidence_sum = sum(result_confidence) + Frame_confidence
    contributing_sas = name_list
    contributing_sas_all_names = contributing_sas + ['FrameSA']
    
    if confidence_sum == 0:
        calculated_agg_ratio = 0
        print("警告: 聚合 confidence 总和为 0")
    else:
        calculated_agg_ratio = result_sum / confidence_sum

    str_1 = f"adjratio({' + '.join(map(str, contributing_sas_all_names))})/confidence({' + '.join(map(str, contributing_sas_all_names))})"
    res_str = f"{str_1}=\n({' + '.join(map(lambda x: str(round(float(x), 5)), result))} + {framesa_adjratio}) / ({' + '.join(map(lambda x: str(round(float(x), 5)), result_confidence))} + {round(Frame_confidence, 5)}) = {safe_agg_value_from_sa}"

    # 获取ShortAgg和SafeAgg的adjratio值
    short = ShortAgg_adjratio_start
    safe = SafeAgg_adjratio_start

    print(f"ShortAgg AdjRatio Start: {short}, SafeAgg AdjRatio Start (Reported): {safe}")
    
    # DRC Gain Calculation
    if short == 0:
        adrc_gain = 0
        print("警告: ShortAgg AdjRatio 为 0，DRC Gain 设为 0")
    else:
        adrc_gain = safe / short
        adrc_gain = round(adrc_gain, 2)
        
    adrc_gain_str = f"{safe} / {short} = {adrc_gain}"
    framesa_adjratio_str = f"{Frame_adjratio_start} * {Frame_confidence} = {framesa_adjratio}"

    # Extract lux and sat values using the passed root
    lux_values = extract_lux_values(root)
    sat_values = extract_sat_values(root)

    # 创建包含所有必需和有效可选SA的列表用于保存结果
    final_sa_values_for_xml = []
    all_sa_names_in_order = sa_order

    for sa_name in all_sa_names_in_order:
        sa_data = sa_values_dict.get(sa_name)
        if sa_data is not None and isinstance(sa_data, dict):
             final_sa_values_for_xml.append(sa_data)

    save_results_to_xml(
        root,
        lux_values,
        sat_values,
        final_sa_values_for_xml,
        framesa_adjratio_str,
        res_str,
        adrc_gain_str,
        file_name_without_ext,
        file_path,
        short,
        safe,
    )


def save_results_to_xml(
    root, # Add root parameter
    lux_values,
    sat_values,
    sa_values,
    framesa_adjratio_str,
    res_str,
    adrc_gain_str,
    file_name_without_ext,
    file_path,
    short,
    safe,
):
    try:
        lux_index, ava_luma, fps = lux_values
        sat_ratio, dark_ratio = sat_values

        output_root = ET.Element("Analyzer") # Create a new root for the output XML

        # 减少重复的元素创建模式，使用函数
        def add_element(parent, name, value):
            elem = ET.SubElement(parent, name)
            elem.text = saxutils.escape(str(value))
            return elem

        # 添加基本信息
        add_element(output_root, "lux_index", lux_index)
        add_element(output_root, "ava_luma", ava_luma)
        add_element(output_root, "fps", fps)
        add_element(output_root, "sat_ratio", sat_ratio)
        add_element(output_root, "dark_ratio", dark_ratio)

        # 统一处理所有单值元素的提取和添加
        for xpath_key, tag_name in SINGLE_VALUE_CONFIG:
            elements = XPATHS[xpath_key](root)
            if elements and len(elements) > 0 and elements[0].text:
                add_element(output_root, tag_name, elements[0].text)

        # 从配置文件加载SA顺序
        _, _, sa_order, agg_sas = load_sa_config()

        # 添加SA信息
        sa_elem = ET.SubElement(output_root, "SA") # Append to the new root

        # 创建SA值的字典，方便查找
        sa_dict = {}
        for sa_value in sa_values:
            if isinstance(sa_value, dict):
                sa_dict[sa_value["name"]] = sa_value

        # 打印字典中所有的SA名称
        # print(f"sa_dict中的所有SA: {', '.join(sa_dict.keys())}")

        # 按照定义的顺序添加SA
        for sa_name in sa_order:
            if sa_name in sa_dict:
                sa_value = sa_dict[sa_name]
                try:
                    # 使用模板创建SA元素
                    sa_item = copy.deepcopy(get_sa_template())
                    sa_item.tag = sa_value["name"]  # SA_name from dictionary

                    # 使用配置字典和键名来填充模板数据
                    for tag, key in SA_TEMPLATE_MAP.items():
                        sa_item.find(tag).text = saxutils.escape(str(sa_value[key]))

                    # 处理操作符
                    step_elem = sa_item.find("step")
                    operators_name = sa_value["operators_name"]
                    calculations = sa_value["calculations"]
                    operators_num = sa_value["operators_num"]
                    operators_method = sa_value["operators_method"]
                    if operators_name and calculations and operators_num and operators_method:
                        for op_name, calc, nums, method in zip(
                            operators_name, calculations, operators_num, operators_method
                        ):
                            op = copy.deepcopy(OPERATOR_TEMPLATE)
                            # 修改标签名称处理逻辑
                            op_tag = op_name
                            if str(op_name)[0].isdigit():
                                op_tag = f"op_{op_name}"
                            # 移除非法字符
                            op_tag = ''.join(c for c in op_tag if c.isalnum() or c in '_-')
                            op.tag = op_tag
                            op.find("operators_num").text = saxutils.escape(
                                ", ".join(map(str, nums))
                            )
                            op.find("operators_method").text = saxutils.escape(str(method))
                            op.text = saxutils.escape(str(calc))
                            step_elem.append(op)

                    sa_elem.append(sa_item)

                except Exception as e:
                    print(f"Warning: Error processing SA {sa_name}: {str(e)}")
                    continue

        # 添加计算结果
        frame_sa_elem = ET.SubElement(output_root, "FrameSA") # Append to the new root
        frame_sa_elem.text = str(framesa_adjratio_str)

        safe_agg_sa_adj_ratio_elem = ET.SubElement(output_root, "SafeAggSAAdjRatio") # Append to the new root
        safe_agg_sa_adj_ratio_elem.text = saxutils.escape(str(res_str))

        drc_gain_elem = ET.SubElement(output_root, "DRCgain") # Append to the new root
        drc_gain_elem.text = saxutils.escape(str(adrc_gain_str))

        short_elem = ET.SubElement(output_root, "Short") # Append to the new root
        short_elem.text = saxutils.escape(str(short))

        safe_elem = ET.SubElement(output_root, "Safe") # Append to the new root
        safe_elem.text = saxutils.escape(str(safe))

        # 从parsed_root中提取AWB SA描述并添加到输出XML - Use the passed root
        awb_descriptions = extract_awb_sa_descriptions(root)
        if awb_descriptions:
            awb_sa_elem = ET.SubElement(output_root, "awb_sa") # Append to the new root

            # 检查Face Assist数据 - Use the passed root
            face_assist_data = XPATHS["assist_data"](root)
            if (
                face_assist_data
                and len(face_assist_data) > 0
                and face_assist_data[0].text
            ):
                try:
                    face_assist_value = float(face_assist_data[0].text)
                    if face_assist_value != 0:
                        # 如果Face Assist数值不为零，添加FACE Assist到awb_sa中
                        awb_descriptions.append("FACE Assist")
                except (ValueError, TypeError):
                    pass  # 如果转换失败，则不添加FACE Assist

            awb_sa_elem.text = saxutils.escape(",".join(awb_descriptions))

        # 修改channel数据的写入方式 - Use the passed root
        channel_values = extract_channel_values(root)
        if channel_values:
            for channel_key, values in channel_values.items():
                channel_elem = ET.SubElement(output_root, channel_key) # Append to the new root
                # 将所有值转换为字符串并用逗号连接
                channel_elem.text = ",".join(map(str, values))

        # 使用内存写入优化写入速度
        buffer = BytesIO()
        tree = ET.ElementTree(output_root) # Use the new root
        tree.write(buffer, encoding="utf-8", pretty_print=True, xml_declaration=True)

        # 一次性写入文件
        output_file = os.path.join(
            os.path.dirname(file_path), f"{file_name_without_ext}_new.xml"
        )
        with open(output_file, "wb") as f:
            f.write(buffer.getvalue())

        print(f"Saved result to: {output_file}")

    except Exception as e:
        print(f"Error in save_results_to_xml: {str(e)}")
        raise


def parse_main(folder_path, log_callback=None):
    start_time = time.time()
    processed_files = 0

    # 从配置文件加载SA配置
    required_sas, optional_sas, sa_order, agg_sas = load_sa_config()

    # 获取需要处理的文件列表 (使用集合操作优化)
    all_files = set(os.listdir(folder_path))
    
    # 找出所有XML文件和_new.xml文件
    xml_files = {f for f in all_files if f.endswith(".xml") and not f.endswith("_new.xml")}
    new_xml_files = {f for f in all_files if f.endswith("_new.xml")}
    
    # 提取基本文件名
    xml_basenames = {os.path.splitext(f)[0] for f in xml_files}
    processed_basenames = {os.path.splitext(f)[0][:-4] if os.path.splitext(f)[0].endswith("_new") 
                          else os.path.splitext(f)[0] for f in new_xml_files}
    
    # 找出需要处理的文件
    to_process_basenames = xml_basenames - processed_basenames
    file_list = [f for f in xml_files if os.path.splitext(f)[0] in to_process_basenames]
    
    total_files = len(file_list)
    
    # 打印调试信息
    print(f"找到 {total_files} 个需要处理的XML文件")
    if total_files == 0:
        print("警告: 没有找到需要处理的XML文件，请检查文件夹路径和文件名格式")

    # 分批处理文件，减少内存占用
    batch_size = 100  # 根据系统性能调整批处理大小

    for batch_start in range(0, len(file_list), batch_size):
        batch_end = min(batch_start + batch_size, len(file_list))
        batch = file_list[batch_start:batch_end]

        # 使用进程池替代线程池来绕过GIL，并设置8个工作进程
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(
                    process_file,
                    os.path.join(folder_path, filename),
                    folder_path,
                ): filename
                for filename in batch
            }

            for future in concurrent.futures.as_completed(futures):
                filename = futures[future]
                try:
                    result, messages = future.result()
                    if log_callback:
                        for msg in messages:
                            log_callback(msg)
                    if result:
                        processed_files += 1
                except Exception as e:
                    message = f"Error processing file {filename}: {str(e)}"
                    print(message)
                    if log_callback:
                        log_callback(message)

        # 在批次之间强制垃圾回收
        gc.collect()
    end_time = time.time()
    total_time = end_time - start_time
    speed = processed_files / total_time if total_time > 0 else 0

    print(f"\n处理完成 | 总文件: {total_files} | 成功处理: {processed_files}")
    print(f"总耗时: {total_time:.2f}秒 | 平均速度: {speed:.2f} 文件/秒")

    if log_callback:
        log_callback(
            f"\n处理完成 | 总文件: {total_files} | 成功处理: {processed_files}"
        )
        log_callback(f"总耗时: {total_time:.2f}秒 | 平均速度: {speed:.2f} 文件/秒")


def parse_single_main(image_path, log_callback=None):
    """
    处理与指定图片同名的XML文件
    
    Args:
        image_path: 图片文件路径
        log_callback: 日志回调函数
    """
    start_time = time.time()
    processed_files = 0

    if not os.path.isfile(image_path):
        msg = f"错误：图片文件不存在 {image_path}"
        print(msg)
        if log_callback:
            log_callback(msg)
        return
    
    # 获取图片所在文件夹和文件名（不含扩展名）
    folder_path = os.path.dirname(image_path)
    file_name_without_ext = os.path.splitext(os.path.basename(image_path))[0]
    
    # 构建同名XML文件路径
    xml_file_path = os.path.join(folder_path, f"{file_name_without_ext}.xml")
    
    if not os.path.isfile(xml_file_path):
        msg = f"错误：对应的XML文件不存在 {xml_file_path}"
        print(msg)
        if log_callback:
            log_callback(msg)
        return
    
    try:
        result, messages = process_file(xml_file_path, folder_path)
        if log_callback:
            for msg in messages:
                log_callback(msg)
        if result:
            processed_files = 1
    except Exception as e:
        message = f"处理文件时出错 {xml_file_path}: {str(e)}"
        print(message)
        if log_callback:
            log_callback(message)

    end_time = time.time()
    total_time = end_time - start_time
    speed = processed_files / total_time if total_time > 0 else 0

    print(f"\n处理完成 | 总文件: 1 | 成功处理: {processed_files}")
    print(f"总耗时: {total_time:.2f}秒 | 平均速度: {speed:.2f} 文件/秒")

    if log_callback:
        log_callback(
            f"\n处理完成 | 总文件: 1 | 成功处理: {processed_files}"
        )
        log_callback(f"总耗时: {total_time:.2f}秒 | 平均速度: {speed:.2f} 文件/秒")


def process_file(filename, folder_path):
    messages = []
    if os.path.isdir(filename):
        return False, messages

    file_name_without_ext = os.path.splitext(os.path.basename(filename))[0]

    message = f"Processing file: {filename}"
    print(message)
    messages.append(message)

    try:
        # 从配置文件加载SA配置
        required_sas, optional_sas, sa_order, agg_sas = load_sa_config()

        # 减少在内存中保存的完整XML树
        root = None
        try:
            root = parse_xml(filename)

        except Exception as e:
            message = f"Error: Could not parse XML file {filename}: {str(e)}"
            print(message)
            messages.append(message)
            return False, messages

        # --- 优化点：预处理所有SA，构建名称到节点的映射 ---
        general_sas = XPATHS["general_sas"](root)
        sa_nodes_map = {
            XPATHS["analyzer_name"](sa)[0].text: sa
            for sa in general_sas
            if XPATHS["analyzer_name"](sa) and XPATHS["analyzer_name"](sa)[0].text
        }

        sa_values = {}
        missing_required_sa = False

        # --- 处理 FrameSA 或 EVFrameSA 的备选逻辑 ---
        frame_sa_data = extract_SA_values(sa_nodes_map, "FrameSA")
        if frame_sa_data:
            sa_values["FrameSA"] = frame_sa_data
            message = f"找到 FrameSA"
            print(message)
            messages.append(message)
        else:
            # 如果 FrameSA 未找到，尝试查找 EVFrameSA
            evframe_sa_data = extract_SA_values(sa_nodes_map, "EVFrameSA")
            if evframe_sa_data:
                sa_values["FrameSA"] = evframe_sa_data
                message = f"未找到 FrameSA，使用 EVFrameSA 作为替代"
                print(message)
                messages.append(message)
            else:
                # 如果 FrameSA 和 EVFrameSA 都未找到
                message = f"Error: 必需的 SA FrameSA 或 EVFrameSA 未找到"
                print(message)
                missing_required_sa = True
                messages.append(message)

        if missing_required_sa:
            root = None
            gc.collect()
            return False, messages
        # --- 结束 FrameSA 或 EVFrameSA 的备选逻辑 ---


        # 检查必需的SAs (跳过已处理的 FrameSA)
        for sa_name in required_sas:
            if sa_name == "FrameSA": # FrameSA 已在上面处理
                continue
            sa_value = extract_SA_values(sa_nodes_map, sa_name)
            if sa_value is None:
                message = f"Error: Required SA {sa_name} not found"
                print(message)
                missing_required_sa = True
                break
            sa_values[sa_name] = sa_value

        if missing_required_sa:
            # Clear root reference to potentially free memory sooner
            root = None
            gc.collect()
            return False, messages

        # 检查可选的SAs - 如果不存在则使用None值
        for sa_name in optional_sas:
            sa_value = extract_SA_values(sa_nodes_map, sa_name)
            sa_values[sa_name] = sa_value  # 如果不存在就是None
            # if sa_name == "FaceDarkSA":
            #     print(f"FaceDarkSA提取结果: {sa_value is not None}")  # 调试信息

        # 确保所有必需的值都存在后再调用计算函数
        if all(key in sa_values for key in required_sas):
            try:
                # 创建参数字典
                sa_args = {
                    "root": root, # Pass the root element
                    "file_name_without_ext": file_name_without_ext,
                    "file_path": filename,
                }

                # 添加所有SA参数
                for sa_name in required_sas + optional_sas:
                    sa_args[f"{sa_name}_values"] = sa_values.get(sa_name)

                # 检查必要参数是否齐全
                missing_args = [arg for arg in ["root", "file_name_without_ext", "file_path"] if arg not in sa_args]
                if missing_args:
                    raise ValueError(f"缺少必要参数: {', '.join(missing_args)}")

                # 调用函数
                calculate_safe_exp_values(**sa_args)
            except Exception as e:
                message = f"Error in calculate_safe_exp_values: {str(e)}"
                print(message)
                # Clear root reference on error
                root = None
                gc.collect()
                return False, messages
        else:
             # This case should ideally be caught by missing_required_sa check,
             # but added for robustness
             message = f"Error: Not all required SAs were found after extraction for file {filename}"
             print(message)
             # Clear root reference on error
             root = None
             gc.collect()
             return False, messages


        # Clear root reference after successful processing
        root = None
        gc.collect()

        return True, messages  # 处理成功
    except Exception as e:
        message = f"Error processing file {filename}: {str(e)}"
        print(message)
        messages.append(message)
        # Ensure root is cleared even for unexpected errors
        root = None
        gc.collect()
        return False, messages


def extract_channel_values(root):
    """提取Index为0和1的Channels_List中Channel_Data的Value_Grid值"""
    try:
        channel_data = {}
        # 配置信息：索引 -> (新名称, 数量限制)
        channel_configs = {
            "0": ("channel_0_gridRGratio", 256),
            "1": ("channel_1_gridBGratio", 255),
        }

        # 一次性找到所有Channels_List节点
        all_lists = XPATHS["all_channels_lists"](root)

        for node in all_lists:
            index = node.get("Index")
            if index in channel_configs:
                name, limit = channel_configs[index]
                
                channel_data_node = XPATHS["channel_data"](node)
                if channel_data_node:
                    value_grids = XPATHS["value_grid"](channel_data_node[0])
                    # 使用列表推导式和切片来高效地提取数据
                    values = [float(grid.text) for grid in value_grids[:limit]]
                    channel_data[name] = values
        
        return channel_data

    except Exception as e:
        print(f"Error extracting channel values: {str(e)}")
        return None


def extract_awb_sa_descriptions(root):
    """
    遍历AWB_SAGen1Data中所有SA_Description节点，打印非空的text值

    Args:
        root: XML根节点

    Returns:
        包含所有非空SA_Description的列表
    """
    # 使用一个更直接的XPath来获取所有描述节点
    descriptions = [
        desc.text.strip()
        for desc in XPATHS["awb_descriptions_direct"](root)
        if desc.text and desc.text.strip()
    ]
    
    if descriptions:
        print(f"找到 {len(descriptions)} 个AWB SA Descriptions: {', '.join(descriptions)}")
    else:
        print("未找到非空的SA_Description")
        
    return descriptions


def load_sa_config(config_file=SA_CONFIG_FILE):
    """
    从配置文件中读取SA相关的配置
    
    Args:
        config_file: 配置文件路径，默认为SA_CONFIG_FILE
        
    Returns:
        tuple: (required_sas, optional_sas, sa_order, agg_sas)
    """
    config = configparser.ConfigParser()
    try:
        # 显式指定使用UTF-8编码读取配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            config.read_file(f)
        
        # 读取并分割配置项
        required_sas = config['SA_CONFIG']['required_sas'].strip().split(',')
        optional_sas = config['SA_CONFIG']['optional_sas'].strip().split(',')
        sa_order = config['SA_CONFIG']['sa_order'].strip().split(',')
        
        # 读取参与SafeAggSAAdjRatio计算的SA列表
        agg_sas = config['SA_CONFIG']['agg_sas'].strip().split(',')
        
        return required_sas, optional_sas, sa_order, agg_sas
    except Exception as e:
        print(f"Error reading config file {config_file}: {str(e)}")
        # 返回默认值
        return (
            ["FrameSA", "SatPrevSA", "DarkPrevSA", "BrightenImgSA", "YHistSA", "SafeAggSA", "ShortAggSA", "LongAggSA"],
            ["FaceSA", "ExtremeColorSA", "ShortSatPrevSA", "LongDarkPrevSA", "ADRCCapSA", "TouchSA", "FaceDarkSA", "IlluminanceSA", "AFBrktFlagSA"],
            ["FrameSA", "SatPrevSA", "DarkPrevSA", "BrightenImgSA", "FaceSA", "ExtremeColorSA", "ShortSatPrevSA", 
             "LongDarkPrevSA", "YHistSA", "TouchSA", "FaceDarkSA", "IlluminanceSA", "AFBrktFlagSA", "ADRCCapSA", "SafeAggSA", "ShortAggSA", "LongAggSA"],
            ["SatPrevSA", "DarkPrevSA", "BrightenImgSA", "FaceSA", "ExtremeColorSA", "FaceDarkSA"]
        )


if __name__ == "__main__":
    file_path = r"D:\Tuning\O19\0_pic\02_IN_pic\2025.6.18自测图\O19_改后"
    parse_main(file_path)