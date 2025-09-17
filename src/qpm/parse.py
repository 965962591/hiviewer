# -*- coding: utf-8 -*-

import os
import gc
import copy
import time
import argparse
import configparser
import concurrent.futures
import xml.sax.saxutils as saxutils
from io import BytesIO
from pathlib import Path
from lxml import etree as ET
from functools import lru_cache


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
DEFAULT_VALUE_CONFIG = [
    ("awb_cct", "CCT"),
    ("short_gain", "short_gain"),
    ("safe_gain", "safe_gain"),
    ("aec_settled", "aec_settled"),
]

FULL_PARSE_VALUE_CONFIG = [
    ("r_g_ratio", "R_G_Ratio"),
    ("b_g_ratio", "B_G_Ratio"),
    ("long_gain", "long_gain"),
    ("r_gain", "r_gain"),
    ("b_gain", "b_gain"),
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
    使用优化的解析器解析XML文件。

    Args:
        file_path: XML文件路径

    Returns:
        lxml.etree._Element: 解析后的XML根节点
    """
    try:
        # 配置一个高性能、安全的解析器
        parser = ET.XMLParser(
            recover=True, 
            remove_blank_text=True, 
            remove_comments=True, 
            ns_clean=True,  # 替代手动字符串替换来处理命名空间
            no_network=True # 禁用网络访问
        )
        
        # ET.parse() is highly optimized and reads the file incrementally,
        # avoiding issues with mmap and fromstring.
        tree = ET.parse(file_path, parser=parser)
        
        return tree.getroot()
    except Exception as e:
        print(f"Error parsing XML file {file_path}: {str(e)}")
        raise


def extract_values(root, path):
    element = root.find(path)
    return [child.text for child in element]


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
    full_parse,  # 确保 full_parse 在 **kwargs 之前
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

    # 合并lux和sat值的提取逻辑，减少函数调用
    lux_node = XPATHS["current_frame"](root)[0]
    lux_values = (
        XPATHS["lux_index"](lux_node)[0].text,
        XPATHS["average_luma"](lux_node)[0].text,
        XPATHS["fps"](lux_node)[0].text
    )
    
    sat_values = (None, None)
    if full_parse:
        try:
            sat_node = XPATHS["aecx_metering"](root)[0]
            sat_values = (
                XPATHS["sat_ratio"](sat_node)[0].text,
                XPATHS["dark_ratio"](sat_node)[0].text
            )
        except (IndexError, AttributeError):
            pass # It is okay if these are not found, sat_values will remain (None, None)

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
        full_parse,
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
    full_parse, # 接收 full_parse
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
        
        # 根据 full_parse 控制 sat_ratio 和 dark_ratio 的添加
        if full_parse:
            if sat_ratio is not None:
                add_element(output_root, "sat_ratio", sat_ratio)
            if dark_ratio is not None:
                add_element(output_root, "dark_ratio", dark_ratio)

        # 始终提取默认字段
        for xpath_key, tag_name in DEFAULT_VALUE_CONFIG:
            elements = XPATHS[xpath_key](root)
            if elements and len(elements) > 0 and elements[0].text:
                add_element(output_root, tag_name, elements[0].text)
        
        # 如果是 full_parse，则提取额外的字段
        if full_parse:
            for xpath_key, tag_name in FULL_PARSE_VALUE_CONFIG:
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

        # [INLINE] 合并 extract_awb_sa_descriptions 逻辑
        if full_parse:
            awb_descriptions = [
                desc.text.strip()
                for desc in XPATHS["awb_descriptions_direct"](root)
                if desc.text and desc.text.strip()
            ]
            if awb_descriptions:
                print(f"找到 {len(awb_descriptions)} 个AWB SA Descriptions: {', '.join(awb_descriptions)}")
                awb_sa_elem = ET.SubElement(output_root, "awb_sa") # Append to the new root
                # 检查Face Assist数据
                face_assist_data = XPATHS["assist_data"](root)
                if face_assist_data and face_assist_data[0].text:
                    try:
                        if float(face_assist_data[0].text) != 0:
                            awb_descriptions.append("FACE Assist")
                    except (ValueError, TypeError):
                        pass
                awb_sa_elem.text = saxutils.escape(",".join(awb_descriptions))
            else:
                 print("未找到非空的SA_Description")


        # [INLINE] 合并 extract_channel_values 逻辑,并根据full_parse判断
        if full_parse:
            channel_configs = {
                "0": ("channel_0_gridRGratio", 256),
                "1": ("channel_1_gridBGratio", 255),
            }
            all_lists = XPATHS["all_channels_lists"](root)
            for node in all_lists:
                index = node.get("Index")
                if index in channel_configs:
                    name, limit = channel_configs[index]
                    channel_data_node = XPATHS["channel_data"](node)
                    if channel_data_node:
                        value_grids = XPATHS["value_grid"](channel_data_node[0])
                        values = [float(grid.text) for grid in value_grids[:limit]]
                        channel_elem = ET.SubElement(output_root, name)
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


def get_process_counts():
    # 获取配置文件
    if (config_path := Path(__file__).parent.parent.parent / "config" / "parse.ini").exists():
        print(f"已存在config_path: {config_path}")
    config_dir = config_path.parent
    config_dir.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    if not config_path.exists():
        # Defaults, 默认不进行完整解析
        parse_processes = 8
        batch_size = 50
        full_parse = False
        config["settings"] = {
            "parse_processes": str(parse_processes),
            "batch_size": str(batch_size),
            "full_parse": str(full_parse)
        }
        with open(config_path, "w", encoding="utf-8") as f:
            config.write(f)

    config.read(config_path, encoding="utf-8")
    parse_processes = config.getint("settings", "parse_processes", fallback=8)
    batch_size = config.getint("settings", "batch_size", fallback=50)
    full_parse = config.getboolean("settings", "full_parse", fallback=False)

    return parse_processes, batch_size, full_parse


def parse_main(folder_path, log_callback=None):
    start_time = time.time()
    processed_files = 0

    parse_processes, batch_size, full_parse = get_process_counts()
    print(f"初始配置 - parse_processes: {parse_processes}, batch_size: {batch_size}, full_parse: {full_parse}")

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
    
    # 如果图片数量小于配置的进程数，则使用图片数量作为进程数
    if total_files > 0 and total_files < parse_processes:
        parse_processes = total_files
        print(f"调整进程数：图片数量({total_files}) < 配置进程数，使用图片数量作为进程数")
    
    # 打印调试信息
    print(f"找到 {total_files} 个需要处理的XML文件，将使用 {parse_processes} 个进程处理")
    if total_files == 0:
        print("警告: 没有找到需要处理的XML文件，请检查文件夹路径和文件名格式")


    for batch_start in range(0, len(file_list), batch_size):
        batch_end = min(batch_start + batch_size, len(file_list))
        batch = file_list[batch_start:batch_end]

        # 使用进程池替代线程池来绕过GIL，并设置8个工作进程
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=parse_processes
        ) as executor:
            futures = {
                executor.submit(
                    process_file,
                    os.path.join(folder_path, filename),
                    folder_path,
                    full_parse,  # 传递 full_parse 参数
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
        _, _, full_parse = get_process_counts() # 获取 full_parse 配置
        result, messages = process_file(xml_file_path, folder_path, full_parse)
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


def process_file(filename, folder_path, full_parse=False):
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
        frame_sa_name_to_use = None
        found_frame_sa_source_name = None

        # 1. 寻找以 "FrameSA" 开头的 SA
        for sa_name in sa_nodes_map.keys():
            if sa_name.startswith("FrameSA"):
                frame_sa_name_to_use = sa_name
                break
        
        frame_sa_data = None
        if frame_sa_name_to_use:
            frame_sa_data = extract_SA_values(sa_nodes_map, frame_sa_name_to_use)
            if frame_sa_data:
                found_frame_sa_source_name = frame_sa_name_to_use
        
        # 2. 如果找不到以 "FrameSA" 开头的，则尝试 "EVFrameSA"
        if not frame_sa_data:
            evframe_sa_data = extract_SA_values(sa_nodes_map, "EVFrameSA")
            if evframe_sa_data:
                frame_sa_data = evframe_sa_data
                found_frame_sa_source_name = "EVFrameSA"

        if frame_sa_data:
            # 强制将名称设置为 "FrameSA" 以便后续处理能统一找到它
            frame_sa_data["name"] = "FrameSA"
            sa_values["FrameSA"] = frame_sa_data
            message = f"找到 {found_frame_sa_source_name}，作为 FrameSA 处理"
            print(message)
            messages.append(message)
        else:
            # 如果 FrameSA, 以其开头的, 和 EVFrameSA 都未找到
            message = f"Error: 必需的 SA 'FrameSA' (或以其开头的变体) 或 'EVFrameSA' 未找到"
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
                    "root": root,
                    "file_name_without_ext": file_name_without_ext,
                    "file_path": filename,
                    "full_parse": full_parse, # 直接将 full_parse 添加到字典中
                }

                # 添加所有SA参数
                for sa_name in required_sas + optional_sas:
                    sa_args[f"{sa_name}_values"] = sa_values.get(sa_name)

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


def load_sa_config(config_file='SA.ini'):
    """
    从配置文件中读取SA相关的配置
    
    Args:
        config_file: 配置文件路径，默认为'SA.ini'
        
    Returns:
        tuple: (required_sas, optional_sas, sa_order, agg_sas)
    """
    try:
        if config_file == 'SA.ini':
            config_file = (Path(__file__).parent.parent.parent / "config" / "SA.ini").as_posix()

        # 显式指定使用UTF-8编码读取配置文件
        config = configparser.ConfigParser()
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
    parser = argparse.ArgumentParser(description="处理指定文件夹或单个文件对应的XML数据。")
    parser.add_argument("path", help="要处理的文件夹路径或单个文件的路径。")
    args = parser.parse_args()

    input_path = args.path

    if os.path.isdir(input_path):
        parse_main(input_path)
    elif os.path.isfile(input_path):
        parse_single_main(input_path)
    else:
        print(f"错误：提供的路径 '{input_path}' 不是一个有效的文件夹或文件。")
