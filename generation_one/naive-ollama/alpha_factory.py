"""
Alpha 表达式工厂

从 machine_lib.py 拆分出来，包含：
- 各种 Alpha 表达式生成方法
- 时序操作、分组操作、向量操作等工厂方法
"""
from typing import List
from itertools import product

# 操作符定义
ARSENAL_OPS = [
    "ts_moment", "ts_entropy", "ts_min_max_cps", "ts_min_max_diff",
    "inst_tvr", "sigmoid", "ts_decay_exp_window", "ts_percentage",
    "vector_neut", "vector_proj", "signed_power"
]

GROUP_OPS = [
    "group_rank", "group_sum", "group_max", "group_mean",
    "group_median", "group_min", "group_std_dev"
]

TWIN_FIELD_OPS = [
    "ts_corr", "ts_covariance", "ts_co_kurtosis",
    "ts_co_skewness", "ts_theilsen"
]


class AlphaFactory:
    """Alpha 表达式工厂类

    提供各种 Alpha 表达式生成方法
    """

    def __init__(self):
        self.basic_ops = [
            "log", "sqrt", "reverse", "inverse", "rank", "zscore",
            "log_diff", "s_log_1p", "fraction", "quantile",
            "normalize", "scale_down"
        ]
        self.ts_ops = [
            "ts_rank", "ts_zscore", "ts_delta", "ts_sum", "ts_product",
            "ts_ir", "ts_std_dev", "ts_mean", "ts_arg_min", "ts_arg_max",
            "ts_min_diff", "ts_max_diff", "ts_returns", "ts_scale",
            "ts_skewness", "ts_kurtosis", "ts_quantile"
        ]
        self.arsenal = ARSENAL_OPS
        self.group_ops = GROUP_OPS
        self.twin_field_ops = TWIN_FIELD_OPS
        self.ops_set = self.basic_ops + self.ts_ops + self.arsenal + self.group_ops

    def get_vec_fields(self, fields: List[str]) -> List[str]:
        """生成向量字段操作"""
        vec_ops = [
            "vec_avg", "vec_sum", "vec_ir", "vec_max", "vec_count",
            "vec_skewness", "vec_stddev", "vec_choose"
        ]
        vec_fields = []

        for field in fields:
            for vec_op in vec_ops:
                if vec_op == "vec_choose":
                    vec_fields.append(f"{vec_op}({field}, nth=-1)")
                    vec_fields.append(f"{vec_op}({field}, nth=0)")
                else:
                    vec_fields.append(f"{vec_op}({field})")

        return vec_fields

    def ts_factory(self, op: str, field: str) -> List[str]:
        """时序操作工厂"""
        output = []
        days = [5, 22, 66, 120, 240]

        for day in days:
            alpha = f"{op}({field}, {day})"
            output.append(alpha)

        return output

    def ts_comp_factory(self, op: str, field: str, factor: str, paras: List) -> List[str]:
        """带参数的时序操作工厂"""
        output = []
        l1 = [5, 22, 66, 240]
        comb = list(product(l1, paras))

        for day, para in comb:
            if isinstance(para, float):
                alpha = f"{op}({field}, {day}, {factor}={para:.1f})"
            elif isinstance(para, int):
                alpha = f"{op}({field}, {day}, {factor}={para})"
            output.append(alpha)

        return output

    def twin_field_factory(self, op: str, field: str, fields: List[str]) -> List[str]:
        """双字段操作工厂"""
        output = []
        days = [5, 22, 66, 240]
        outset = list(set(fields) - {field})

        for day in days:
            for counterpart in outset:
                alpha = f"{op}({field}, {counterpart}, {day})"
                output.append(alpha)

        return output

    def vector_factory(self, op: str, field: str) -> List[str]:
        """向量操作工厂"""
        output = []
        vectors = ["cap"]

        for vector in vectors:
            alpha = f"{op}({field}, {vector})"
            output.append(alpha)

        return output

    def group_factory(self, op: str, field: str, region: str) -> List[str]:
        """分组操作工厂"""
        output = []

        # 基础分组
        groups = ["market", "sector", "industry", "subindustry"]

        # 按地区添加特定分组
        region_groups = self._get_region_groups(region)
        groups.extend(region_groups)

        for group in groups:
            if op.startswith("group_vector"):
                alpha = f"{op}({field}, cap, densify({group}))"
            elif op.startswith("group_percentage"):
                alpha = f"{op}({field}, densify({group}), percentage=0.5)"
            else:
                alpha = f"{op}({field}, densify({group}))"
            output.append(alpha)

        return output

    def _get_region_groups(self, region: str) -> List[str]:
        """获取地区特定的分组字段"""
        # USA 分组
        usa_groups = [
            'sta1_top3000c50', 'sta1_allc20', 'sta1_allc10', 'sta1_top3000c20', 'sta1_allc5',
            'sta2_top3000_fact3_c50', 'sta2_top3000_fact4_c20', 'sta2_top3000_fact4_c10',
            'sta3_2_sector', 'sta3_3_sector', 'sta3_news_sector', 'sta3_peer_sector',
            'pv13_h_min2_3000_sector', 'pv13_r2_min20_3000_sector'
        ]

        # CHN 分组
        chn_groups = [
            'pv13_h_min2_sector', 'pv13_di_6l', 'pv13_rcsed_6l',
            'sta1_top3000c30', 'sta1_top3000c20', 'sta1_top3000c10'
        ]

        # EUR 分组
        eur_groups = [
            'pv13_5_sector', 'pv13_2_sector', 'pv13_v3_3l_scibr',
            'sta1_allc10', 'sta1_allc2', 'sta1_top1200c2'
        ]

        # GLB 分组
        glb_groups = [
            'pv13_2_sector', 'pv13_10_sector', 'pv13_3l_scibr',
            'sta3_2_sector', 'sta3_3_sector', 'sta3_news_sector'
        ]

        region_map = {
            'usa': usa_groups,
            'chn': chn_groups,
            'eur': eur_groups,
            'glb': glb_groups
        }

        return region_map.get(region.lower(), [])

    def get_first_order(self, vec_fields: List[str], ops_set: List[str] = None) -> List[str]:
        """生成一阶 Alpha 表达式"""
        if ops_set is None:
            ops_set = self.ops_set

        alpha_set = []
        for field in vec_fields:
            alpha_set.append(field)
            for op in ops_set:
                if op == "ts_percentage":
                    alpha_set.extend(self.ts_comp_factory(op, field, "percentage", [0.5]))
                elif op == "ts_decay_exp_window":
                    alpha_set.extend(self.ts_comp_factory(op, field, "factor", [0.5]))
                elif op == "ts_moment":
                    alpha_set.extend(self.ts_comp_factory(op, field, "k", [2, 3, 4]))
                elif op == "ts_entropy":
                    alpha_set.extend(self.ts_comp_factory(op, field, "buckets", [10]))
                elif op in self.twin_field_ops:
                    alpha_set.extend(self.twin_field_factory(op, field, vec_fields))
                elif op.startswith("ts_") or op == "inst_tvr":
                    alpha_set.extend(self.ts_factory(op, field))
                elif op.startswith("group_"):
                    alpha_set.extend(self.group_factory(op, field, "usa"))
                elif op.startswith("vector"):
                    alpha_set.extend(self.vector_factory(op, field))
                elif op == "signed_power":
                    alpha = f"{op}({field}, 2)"
                    alpha_set.append(alpha)
                else:
                    alpha = f"{op}({field})"
                    alpha_set.append(alpha)

        return alpha_set

    def get_ts_second_order(self, first_order: List[str], ts_ops: List[str] = None) -> List[str]:
        """生成二阶时序 Alpha"""
        if ts_ops is None:
            ts_ops = self.ts_ops

        second_order = []
        for fo in first_order:
            for ts_op in ts_ops:
                second_order.extend(self.ts_factory(ts_op, fo))

        return second_order

    def get_group_second_order(self, first_order: List[str], group_ops: List[str] = None, region: str = "usa") -> List[str]:
        """生成二阶分组 Alpha"""
        if group_ops is None:
            group_ops = self.group_ops

        second_order = []
        for fo in first_order:
            for group_op in group_ops:
                second_order.extend(self.group_factory(group_op, fo, region))

        return second_order

    def process_datafields(self, df, data_type: str) -> List[str]:
        """处理数据字段

        Args:
            df: 数据字段 DataFrame
            data_type: 'matrix' 或 'vector'

        Returns:
            处理后的字段列表
        """
        if data_type == "matrix":
            datafields = df[df['type'] == "MATRIX"]["id"].tolist()
        elif data_type == "vector":
            datafields = self.get_vec_fields(df[df['type'] == "VECTOR"]["id"].tolist())
        else:
            datafields = []

        tb_fields = []
        for field in datafields:
            tb_fields.append(f"winsorize(ts_backfill({field}, 120), std=4)")

        return tb_fields

    def load_task_pool(self, alpha_list: List, batch_size: int = 10, concurrent_batches: int = 10) -> List:
        """将 Alpha 列表分割为批次池"""
        pools = []
        current_pool = []
        current_batch = []

        for alpha in alpha_list:
            current_batch.append(alpha)

            if len(current_batch) >= batch_size:
                current_pool.append(current_batch)
                current_batch = []

                if len(current_pool) >= concurrent_batches:
                    pools.append(current_pool)
                    current_pool = []

        if current_batch:
            current_pool.append(current_batch)
        if current_pool:
            pools.append(current_pool)

        return pools
