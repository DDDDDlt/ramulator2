import math
from turtle import tilt
import torch.nn as nn
import numpy as np

from typing import List
from mem.mem_instance import MemoryInstance
from pe_array import PE_Array
from ramulator_dram_sim import ramulator_weight_read_group_wise, ramulator_weight_read_not_group_wise, ramulator_input_read, ramulator_output_write

# Stripes accelerator
class Accelerator(PE_Array):
    PR_SCALING = 1.5 # scaling factor to account for post placement and routing

    def __init__(
        self, 
        model_name: str,
        i_prec: int=16, 
        w_prec: int=8, 
        is_bit_serial: bool=False,
        pe_dp_size: int=1,
        pe_energy: float=0, 
        pe_area: float=0,  
        pe_array_dim: List[int]=[],
        init_mem: bool=True,
        context_length: int=256,
        is_generation: bool=False,
        is_mixposit: bool=False,  # per-group size
        # ===== 新增参数（可选，不传就用默认值） =====
        use_scale_overhead_lat: bool = False,  # 是否计入 per-group scale/meta 的 DRAM 额外延迟
        scale_bits: int = 8,                  # scaling factor 精度（默认 INT8）
        meta_bits: int = 2,                   # metadata bits（默认 2）
        group_size: int = 128,                # group size（默认 128）
        worst_case: bool = False,             # 是否考虑最坏情况
    ): 
        super().__init__(model_name, i_prec, w_prec, is_bit_serial, pe_dp_size, pe_energy, pe_area, pe_array_dim, context_length, is_generation, is_mixposit)
        
        self.USE_SCALE_OVERHEAD_LAT = use_scale_overhead_lat
        self.SCALE_BITS = scale_bits
        self.META_BITS = meta_bits
        self.GROUP_SIZE = group_size
        self.WORST_CASE = worst_case
        self.cycle_compute = None
        if init_mem:
            self._init_mem()
            self._check_layer_mem_size()
            self._calc_num_mem_refetch()

    def calc_cycle(self):
        self._calc_compute_cycle()
        self._calc_dram_cycle() 
        total_cycle = 0
        total_cycle_compute = 0
        for name in self.layer_name_list:
            cycle_layer_compute = self._layer_cycle_compute[name]
            cycle_layer_dram    = self._layer_cycle_dram[name]
            total_cycle_compute += cycle_layer_compute
            total_cycle += max(cycle_layer_compute, cycle_layer_dram)
            # print(f"name: {name}, cycle_layer_compute: {cycle_layer_compute}, cycle_layer_dram: {cycle_layer_dram}")
            # if (cycle_layer_compute>cycle_layer_dram):
            #     print("layer name ", name)
            #     print("cycle_layer_compute")
            #     print(cycle_layer_compute)
            #     print("--------------------------------")
            # else:
            #     print("layer name ", name)
            #     print("cycle_layer_dram")
            #     print(cycle_layer_dram)
            #     print("--------------------------------")
        self.cycle_compute = total_cycle_compute
        return total_cycle_compute, total_cycle
    
    def analyze_bottleneck(self):
        """
        分析每层是 memory-bound 还是 compute-bound
        返回统计信息和详细的层级信息
        """
        if not hasattr(self, '_layer_cycle_compute') or not hasattr(self, '_layer_cycle_dram'):
            self.calc_cycle()
        
        memory_bound_layers = []
        compute_bound_layers = []
        layer_details = []
        
        for name in self.layer_name_list:
            cycle_compute = self._layer_cycle_compute[name]
            cycle_dram = self._layer_cycle_dram[name]
            
            # 判断瓶颈类型
            if cycle_dram > cycle_compute:
                bottleneck = 'Memory'
                memory_bound_layers.append(name)
            else:
                bottleneck = 'Compute'
                compute_bound_layers.append(name)
            
            # 计算比例
            ratio = cycle_dram / cycle_compute if cycle_compute > 0 else float('inf')
            
            layer_details.append({
                'name': name,
                'compute_cycles': cycle_compute,
                'dram_cycles': cycle_dram,
                'bottleneck': bottleneck,
                'dram_to_compute_ratio': ratio
            })
        
        stats = {
            'total_layers': len(self.layer_name_list),
            'memory_bound_count': len(memory_bound_layers),
            'compute_bound_count': len(compute_bound_layers),
            'memory_bound_layers': memory_bound_layers,
            'compute_bound_layers': compute_bound_layers,
            'layer_details': layer_details
        }
        
        return stats

    def print_bottleneck_analysis(self, show_details=False):
        """
        打印瓶颈分析结果
        
        Args:
            show_details: 是否显示每层的详细信息
        """
        stats = self.analyze_bottleneck()
        
        print(f"  Bottleneck Analysis:")
        print(f"    Total Layers:         {stats['total_layers']}")
        print(f"    Memory-bound Layers:  {stats['memory_bound_count']} ({stats['memory_bound_count']/stats['total_layers']*100:.1f}%)")
        print(f"    Compute-bound Layers: {stats['compute_bound_count']} ({stats['compute_bound_count']/stats['total_layers']*100:.1f}%)")
        
        if show_details:
            print("  Detailed Layer Analysis:")
            for detail in stats['layer_details']:
                print(f"    Layer: {detail['name']}")
                print(f"      Compute Cycles: {detail['compute_cycles']:,}")
                print(f"      DRAM Cycles:    {detail['dram_cycles']:,}")
                print(f"      Bottleneck:     {detail['bottleneck']}")
                print(f"      DRAM/Compute:   {detail['dram_to_compute_ratio']:.2f}x")
        
        return stats
    
    def _calc_compute_cycle(self):
        self._layer_cycle_compute = {}
        for name in self.layer_name_list:
            w_dim = self.weight_dim[name]
            i_dim = self.input_dim[name]
            o_dim = self.output_dim[name]
            if w_dim is not None:
                tile_layer = self._calc_tile_fc(w_dim, o_dim)
                cycle_layer_compute = tile_layer * self.pe_latency
                self._layer_cycle_compute[name] = cycle_layer_compute
    
    def calc_pe_array_tile(self):
        total_tile = 0
        for name in self.layer_name_list:
            w_dim = self.weight_dim[name]
            o_dim = self.output_dim[name]
            # print(f"name: {name}, w_dim: {w_dim}, o_dim: {o_dim}")
            total_tile += self._calc_tile_fc(w_dim, o_dim)
        return total_tile

    def _calc_tile_fc(self, w_dim, o_dim):
        pe_dp_size = self.pe_dp_size
        num_pe_row = self.pe_array_dim['h']
        num_pe_col = self.pe_array_dim['w']

        # output channel, input channel
        cout, cin = w_dim
        # num token, output channel
        num_token, _ = o_dim

        # tile_in_channel:   number of tiles along input channel
        # tile_cout:  number of tiles along output channel
        tile_in_channel  = math.ceil(cin / pe_dp_size)
        tile_cout        = math.ceil(cout / num_pe_row)
        tile_token       = math.ceil(num_token / num_pe_col)
        
        # print(f"w_dim: {w_dim}, o_dim: {o_dim}")
        # print(f"pe_dp_size: {pe_dp_size}, num_pe_row: {num_pe_row}, num_pe_col: {num_pe_col}")
        # print(f"tile_in_channel: {tile_in_channel}, tile_cout: {tile_cout}, tile_token: {tile_token}")

        total_tile = (tile_in_channel * tile_cout * tile_token)
        return total_tile
    

    def _calc_dram_cycle(self):
        self._layer_cycle_dram = {}
        self._layer_cycle_dram_detail = {}  # 保存详细的周期信息（用于能量计算）
        group_size = self.GROUP_SIZE
        is_group_wise = self.USE_SCALE_OVERHEAD_LAT
        for name in self.layer_name_list:
            # print(name)
            w_dim = self.weight_dim[name]
            o_dim = self.output_dim[name]
            num_dram_fetch_w, num_dram_fetch_i = self._layer_mem_refetch[name]
            w_workload = self._w_mem_required[name] * num_dram_fetch_w
            # print("w_workload", w_workload)
            i_workload = self._i_mem_required[name] * num_dram_fetch_i
            # print("i_workload", i_workload)
            o_workload = self._o_mem_required[name]  # 输出数据不需要重复读取
            # print("o_workload", o_workload)
            col = self.pe_array_dim['w']
            # print("col", col)
            # Ramulator函数现在返回 (cycles, energy_pJ) 元组
            if name in ['attn_qk', 'attn_v']:
                cycle_dram_load_w, energy_dram_load_w = ramulator_input_read(w_workload)
            elif is_group_wise:
                cycle_dram_load_w, energy_dram_load_w = ramulator_weight_read_group_wise(w_workload, group_size, col)
            else:
                cycle_dram_load_w, energy_dram_load_w = ramulator_weight_read_not_group_wise(w_workload)
            cycle_dram_load_i, energy_dram_load_i = ramulator_input_read(i_workload)
            cycle_dram_write_o, energy_dram_write_o = ramulator_output_write(o_workload)
            
            cycle_layer_dram = cycle_dram_load_w + cycle_dram_load_i + cycle_dram_write_o
            self._layer_cycle_dram[name] = cycle_layer_dram
            
            # 保存详细周期信息和能量信息供能量计算使用
            self._layer_cycle_dram_detail[name] = {
                'weight_cycles': cycle_dram_load_w,
                'input_cycles': cycle_dram_load_i,
                'output_cycles': cycle_dram_write_o,
                # 保存Ramulator2计算的实际能量（单位：pJ）
                'weight_energy_pJ': energy_dram_load_w,
                'input_energy_pJ': energy_dram_load_i,
                'output_energy_pJ': energy_dram_write_o
            }
            # print("cycle_dram_load_w", cycle_dram_load_w)
            # print("cycle_dram_load_i", cycle_dram_load_i)
            # print("cycle_dram_write_o", cycle_dram_write_o)
            # print("cycle_layer_dram", cycle_layer_dram)
            # print("--------------------------------")


    # def _calc_dram_cycle(self):
    #     self._layer_cycle_dram = {}
    #     dram_bandwidth = self.dram.rw_bw * 2 # DDR

    #     for name in self.layer_name_list:
    #         i_prec = self.i_prec
    #         if ('attn_qk' in name) or ('attn_v' in name):
    #             w_prec = self.i_prec
    #         else:
    #             w_prec = self.w_prec
    #         w_dim = self.weight_dim[name]
    #         o_dim = self.output_dim[name]
    #         num_dram_fetch_w, num_dram_fetch_i = self._layer_mem_refetch[name]
    #         cycle_dram_load_w = self._w_mem_required[name] * 8 / dram_bandwidth
    #         cycle_dram_load_w *= num_dram_fetch_w
    #         print("cycle_dram_load_w", cycle_dram_load_w)
    #         cycle_dram_load_i = self._i_mem_required[name] * 8 / dram_bandwidth 
    #         cycle_dram_load_i *= num_dram_fetch_i
    #         print("cycle_dram_load_i", cycle_dram_load_i)
    #         cycle_dram_write_o = self._o_mem_required[name] * 8 / dram_bandwidth
    #         print("cycle_dram_write_o", cycle_dram_write_o)
    #         cycle_layer_dram = cycle_dram_load_w + cycle_dram_load_i + cycle_dram_write_o
    #         col = self.pe_array_dim['w']
    #         print("col", col)
    #         print("name", name)
    #         print("cycle_dram_load_w", cycle_dram_load_w)
    #         print("cycle_dram_write_o", cycle_dram_write_o)
    #         print("cycle_dram_load_i", cycle_dram_load_i)
    #         print("cycle_layer_dram", cycle_layer_dram)
    #         print("--------------------------------")
    #         self._layer_cycle_dram[name] = math.ceil(cycle_layer_dram)

    
    def calc_compute_energy(self):
        if self.cycle_compute is None:
            self.cycle_compute, _ = self.calc_cycle()
        compute_energy = self.pe_energy * self.total_pe_count * self.cycle_compute
        # print("total_pe_count", self.total_pe_count)
        # print("cycle_compute", self.cycle_compute) 
        # print("compute_energy", compute_energy)
        return compute_energy
    
    def calc_sram_rd_energy(self):
        w_sram_rd_cost = self.w_sram.r_cost
        i_sram_rd_cost = self.i_sram.r_cost
        num_pe_row = self.pe_array_dim['h']
        num_pe_col = self.pe_array_dim['w']
        if self.cycle_compute is None:
            self.cycle_compute, _ = self.calc_cycle()
        num_cycle_compute = self.cycle_compute
        num_tile = self.calc_pe_array_tile()

        sram_rd_energy = num_tile * (w_sram_rd_cost + i_sram_rd_cost)
        return sram_rd_energy
    
    def calc_sram_wr_energy(self):
        total_energy = 0
        for name in self.layer_name_list:
            w_dim = self.weight_dim[name]
            i_dim = self.input_dim[name]
            o_dim = self.output_dim[name]
            total_energy += self._calc_sram_wr_energy_fc(name, w_dim, i_dim, o_dim, self.w_prec, self.i_prec)
        return total_energy
    
    def _calc_sram_wr_energy_fc(self, layer_name, w_dim, i_dim, o_dim, w_prec, i_prec):
        w_sram_wr_cost = self.w_sram.w_cost_min
        i_sram_wr_cost = self.i_sram.w_cost_min
        w_sram_min_wr_bw = self.w_sram.w_bw_min
        i_sram_min_wr_bw = self.i_sram.w_bw_min
        num_fetch_w, num_fetch_i = self._layer_mem_refetch[layer_name]

        # output channel, weight hidden size
        cout, cin_w = w_dim
        # num token, input hidden size
        _, cin_i = i_dim
        # num token, output channel
        num_token, _ = o_dim

        # write energy, read from DRAM and write to SRAM
        num_w_sram_wr    = math.ceil(cin_w * w_prec / w_sram_min_wr_bw) * cout
        energy_w_sram_wr = num_w_sram_wr * w_sram_wr_cost * num_fetch_w
        num_i_sram_wr    = math.ceil(cin_i * i_prec / i_sram_min_wr_bw) * num_token
        energy_i_sram_wr = num_i_sram_wr * i_sram_wr_cost * num_fetch_i
        num_o_sram_wr    = math.ceil(cout * i_prec / i_sram_min_wr_bw) * num_token
        energy_o_sram_wr = num_o_sram_wr * i_sram_wr_cost

        total_energy = energy_w_sram_wr + energy_i_sram_wr + energy_o_sram_wr
        return total_energy
    
    def calc_dram_energy(self):
        energy = 0
        for name in self.layer_name_list:
            energy += self._calc_dram_energy_fc(name)
        return energy
    
    def _calc_dram_energy_fc(self, layer_name):
        # ==========================================
        # 使用Ramulator2计算的实际DRAM能量
        # ==========================================
        cycle_detail = self._layer_cycle_dram_detail[layer_name]
        
        # 直接使用Ramulator2计算的实际能量（单位：pJ）
        # 这包含了所有实际的DRAM操作能耗：
        # - Background energy (active/precharge state)
        # - Command energy (ACT, PRE, RD, WR, REF等)
        # - 考虑了row buffer miss、bank conflict、refresh等所有开销
        energy_weight = cycle_detail['weight_energy_pJ']
        energy_input  = cycle_detail['input_energy_pJ']
        energy_output = cycle_detail['output_energy_pJ']
        
        total_energy = energy_weight + energy_input + energy_output
        
        # ==========================================
        # 旧的简化能量计算方法（已废弃，保留作为参考）
        # ==========================================
        # # 基于Ramulator仿真周期计算DRAM能量（简化模型）
        # # DDR4-2400 平均功率参数（基于典型workload的功耗特性）
        # # 参考：JEDEC DDR4 spec + Micron power calculator
        # 
        # # DDR4-2400, 2通道, 典型读写混合workload的平均功率
        # # 这是在活跃传输期间的平均功率（不包括idle/standby）
        # # POWER_READ_MW = 800   # mW，读取操作期间的平均功率
        # # POWER_WRITE_MW = 700  # mW，写入操作期间的平均功率
        # 
        # # DDR4-2400频率: 1 GHz
        # # DRAM_FREQ_MHZ = 1
        # 
        # # 每周期的能量 (pJ) = 功率(mW) / 频率(MHz) = 功率(pJ/ns) 
        # ENERGY_PER_CYCLE_READ = 1000   # pJ/cycle
        # ENERGY_PER_CYCLE_WRITE = 900 # pJ/cycle
        # 
        # # 获取该层的Ramulator仿真周期（包含所有实际开销）
        # cycle_detail = self._layer_cycle_dram_detail[layer_name]
        # 
        # # 基于实际周期计算能量
        # # 这里的周期数已经包含了row buffer miss、bank conflict、refresh等所有开销
        # energy_weight = cycle_detail['weight_cycles'] * ENERGY_PER_CYCLE_READ
        # energy_input  = cycle_detail['input_cycles'] * ENERGY_PER_CYCLE_READ
        # energy_output = cycle_detail['output_cycles'] * ENERGY_PER_CYCLE_WRITE
        # 
        # total_energy = energy_weight + energy_input + energy_output
        
        return total_energy
    
    def _check_layer_mem_size(self):
        self._w_mem_required = {}
        self._i_mem_required = {}
        self._o_mem_required = {}   

        for layer_idx, name in enumerate(self.layer_name_list):
            i_prec = self.i_prec
            if ('attn_qk' in name) or ('attn_v' in name):
                w_prec = self.i_prec
                # print(name,"+++++++++++++++++++++++++++++++")
            else:
                w_prec = self.w_prec

            w_dim = self.weight_dim[name]
            i_dim = self.input_dim[name]
            o_dim = self.output_dim[name]

            # output channel, weight hidden size
            cout, cin_w = w_dim
            # num token, input hidden size
            _, cin_i = i_dim
            # num token, output channel
            num_token, _ = o_dim

            self._w_mem_required[name] = math.ceil(cin_w * w_prec / 8) * cout
            self._i_mem_required[name] = math.ceil(cin_i * i_prec / 8) * num_token
            self._o_mem_required[name] = math.ceil(cout * i_prec / 8) * num_token

    def _calc_num_mem_refetch(self):
        # If the on-chip buffer size is not big enough, 
        # we need to refetch input tiles or weight tiles from DRAM
        self._layer_mem_refetch = {}
        size_sram_w   = self.w_sram.size / 8
        size_sram_i   = self.i_sram.size / 8
        for name in self.layer_name_list:
            w_dim = self.weight_dim[name]
            if w_dim is not None:
                w_mem_required = self._w_mem_required[name]
                i_mem_required = self._i_mem_required[name]
                if ( w_mem_required > size_sram_w ) and ( i_mem_required > size_sram_i ):
                    # need DRAM refetch
                    num_refetch_input  = math.ceil(w_mem_required / size_sram_w)
                    num_refetch_weight = math.ceil(i_mem_required / size_sram_i)
                    total_fetch_weight = num_refetch_weight * w_mem_required
                    total_fetch_input  = num_refetch_input * i_mem_required
                    #print(f'{name}, Need DRAM refetch ...')
                    #print(f'w_dim: {w_dim}, i_dim: {i_dim}')
                    if ( total_fetch_weight + i_mem_required ) < ( total_fetch_input + w_mem_required ):
                        #print(f'Refetch weight for {num_refetch_weight} times ...')
                        # refetch all weight for every input tile
                        self._layer_mem_refetch[name] = (num_refetch_weight, 1)
                        # print(f'Refetch weight for {num_refetch_weight} times ...')
                    else:
                        #print(f'Refetch input for {num_refetch_input} times ...\n\n')
                        # refetch all input for every weight tile
                        self._layer_mem_refetch[name] = (1, num_refetch_input)
                        # print(f'Refetch input for {num_refetch_input} times ...')
                else:
                    # no need refetch
                    self._layer_mem_refetch[name] = (1, 1)

    def _init_mem(self):
        if self.is_bit_serial:
            w_bandwidth = self.pe_dp_size * math.ceil(self.w_prec / 4) * 4 * self.pe_array_dim['h'] / 2
        else:
            w_bandwidth = self.pe_dp_size * math.ceil(self.w_prec / 4) * 4 * self.pe_array_dim['h']
        w_sram_bank = 8
        w_sram_config = {
            'technology': 0.022,
            'mem_type': 'ram', 
            'size': 512 * 1024*8,
            # 'size': 32 * 64 * 8,
            'bank_count': w_sram_bank, 
            'rw_bw': w_bandwidth, 
            'r_port': 1, 
            'w_port': 1, 
            'rw_port': 0,
        }
        self.w_sram = MemoryInstance(
            w_sram_config, r_cost=0, w_cost=0, latency=1, 
            min_r_granularity=None, min_w_granularity=64, 
            get_cost_from_cacti=True
        )
        
        if self.is_bit_serial:
            i_bandwidth = self.pe_dp_size * self.i_prec * self.pe_array_dim['w'] / 2
        else:
            i_bandwidth = self.pe_dp_size * self.i_prec * self.pe_array_dim['w']
        i_sram_bank = 8
        i_sram_config = {
            'technology': 0.022,
            'mem_type': 'ram', 
            'size': 512 * 1024*8,
            # 'size': 128 * 256* 8, 
            'bank_count': i_sram_bank, 
            'rw_bw': i_bandwidth,
            'r_port': 1, 
            'w_port': 1, 
            'rw_port': 0,
        }
        self.i_sram = MemoryInstance(
            i_sram_config, r_cost=0, w_cost=0, latency=1, 
            min_r_granularity=64, min_w_granularity=64, 
            get_cost_from_cacti=True
        )


        # # ========== DRAM配置 ==========
        # # 有效带宽（考虑Ramulator仿真的实际开销）
        # dram_rw_bw = 64  # bits/cycle，约为理论带宽的50%

        # dram_config = {
        #     'technology': 0.028,
        #     'mem_type': 'dram', 
        #     'size': 1e9 * 8, 
        #     'bank_count': 1, 
        #     'rw_bw': dram_rw_bw,
        #     'r_port': 0, 
        #     'w_port': 0, 
        #     'rw_port': 1,
        # }

        # # DDR4-2400 每次64B访问的实际能量（基于Micron datasheet）
        # # 注意：这个能量是物理特性，不随带宽变化
        # dram_rd_cost = 1200/2  # pJ per 64-byte read
        # dram_wr_cost = 1000/2  # pJ per 64-byte write

        # self.dram = MemoryInstance(
        #     dram_config, 
        #     r_cost=dram_rd_cost,  # ← 固定值
        #     w_cost=dram_wr_cost,  # ← 固定值
        #     latency=1, 
        #     min_r_granularity=dram_rw_bw, 
        #     min_w_granularity=dram_rw_bw, 
        #     get_cost_from_cacti=False
        # )
                
        # dram_rw_bw = 64
        # dram_config = {
        #     'technology': 0.028,
        #     'mem_type': 'dram', 
        #     'size': 1e9 * 8, 
        #     'bank_count': 1, 
        #     'rw_bw': dram_rw_bw,
        #     'r_port': 0, 
        #     'w_port': 0, 
        #     'rw_port': 1,
        # }
        # wr_cost = dram_rw_bw / 64 * 1200
        # # rd_cost = 2400  # pJ (更准确的 DDR4-2400 读能量)
        # # wr_cost = 2400  # pJ (更准确的 DDR4-2400 写能量)
        # self.dram = MemoryInstance(
        #     dram_config, r_cost=wr_cost, w_cost=wr_cost, latency=1, 
        #     min_r_granularity=dram_rw_bw, min_w_granularity=dram_rw_bw, 
        #     get_cost_from_cacti=False
        # )