# tech_screen.py - 技术指标选股工具
# 基于 MCP full 数据结构
# 使用: from tech_screen import screen_stock, parse_tech_table, parse_money_flow

import re
from typing import Dict, Any, Optional, List, Tuple

# ─── 解析 ───────────────────────────────────────────────────────────────────

def parse_tech_table(mcp_full_text: str) -> Dict[str, List]:
    """解析 MCP full 返回的技术指标表格（最近30日）
    
    实际表头: DATE|KDJ.K|KDJ.D|KDJ.J|MA(5)|MA(10)|MA(30)|MA(60)|
              MACD.DIF|MACD.DEA|MACD.HIST|RSI(6)|RSI(12)|RSI(24)|
              BBANDS|ATR|OBV|
    BBANDS 格式: Lower/Middle/Upper (用/分隔)
    """
    result = {
        'dates': [], 'kdj_k': [], 'kdj_d': [], 'kdj_j': [],
        'rsi_6': [], 'rsi_12': [], 'rsi_24': [],
        'macd_dif': [], 'macd_dea': [], 'macd_hist': [],
        'ma5': [], 'ma10': [], 'ma30': [], 'ma60': [],
        'boll_upper': [], 'boll_middle': [], 'boll_lower': [],
        'atr': [], 'obv': [],
    }
    
    # Find table start
    idx = mcp_full_text.find('# 技术指标')
    if idx < 0:
        return result
    
    lines = mcp_full_text[idx:].strip().split('\n')
    if len(lines) < 5:
        return result
    
    # Parse header to find column indices (header is at line 2, data starts at line 4)
    header = lines[2]
    cols = [c.strip().upper() for c in header.split('|')]
    
    # Column mapping (based on actual header order)
    col_map = {}
    for i, c in enumerate(cols):
        if c == 'KDJ.K': col_map['kdj_k'] = i
        elif c == 'KDJ.D': col_map['kdj_d'] = i
        elif c == 'KDJ.J': col_map['kdj_j'] = i
        elif c == 'MA(5)': col_map['ma5'] = i
        elif c == 'MA(10)': col_map['ma10'] = i
        elif c == 'MA(30)': col_map['ma30'] = i
        elif c == 'MA(60)': col_map['ma60'] = i
        elif c == 'MACD.DIF': col_map['macd_dif'] = i
        elif c == 'MACD.DEA': col_map['macd_dea'] = i
        elif c == 'MACD.HIST': col_map['macd_hist'] = i
        elif c == 'RSI(6)': col_map['rsi_6'] = i
        elif c == 'RSI(12)': col_map['rsi_12'] = i
        elif c == 'RSI(24)': col_map['rsi_24'] = i
        elif c == 'BBANDS UPPER': col_map['boll_upper'] = i
        elif c == 'BBANDS MIDDLE': col_map['boll_middle'] = i
        elif c == 'BBANDS LOWER': col_map['boll_lower'] = i
        elif c == 'ATR': col_map['atr'] = i
        elif c == 'OBV': col_map['obv'] = i
        elif c == 'DATE' or c == '日期': col_map['date'] = i
    
    # Parse data rows
    for line in lines[4:]:  # Skip lines[0]=title, [1]=blank, [2]=header, [3]=separator
        if not line.strip() or '---' in line:
            continue
        cells = [c.strip() for c in line.split('|')]
        
        if 'date' in col_map and col_map['date'] < len(cells):
            date_val = cells[col_map['date']].strip()
            if date_val:
                result['dates'].append(date_val)
        
        def get_float(key):
            if key not in col_map: return None
            idx = col_map[key]
            if idx >= len(cells): return None
            val = cells[idx].strip()
            try: return float(val)
            except: return None
        
        result['kdj_k'].append(get_float('kdj_k'))
        result['kdj_d'].append(get_float('kdj_d'))
        result['kdj_j'].append(get_float('kdj_j'))
        result['ma5'].append(get_float('ma5'))
        result['ma10'].append(get_float('ma10'))
        result['ma30'].append(get_float('ma30'))
        result['ma60'].append(get_float('ma60'))
        result['macd_dif'].append(get_float('macd_dif'))
        result['macd_dea'].append(get_float('macd_dea'))
        result['macd_hist'].append(get_float('macd_hist'))
        result['rsi_6'].append(get_float('rsi_6'))
        result['rsi_12'].append(get_float('rsi_12'))
        result['rsi_24'].append(get_float('rsi_24'))
        result['atr'].append(get_float('atr'))
        result['obv'].append(get_float('obv'))
        
        # BBANDS Upper/Middle/Lower are separate columns
        for key in ['boll_upper', 'boll_middle', 'boll_lower']:
            if key in col_map:
                ci = col_map[key]
                if ci < len(cells):
                    try:
                        result[key].append(float(cells[ci].strip()))
                    except:
                        result[key].append(None)
                else:
                    result[key].append(None)
            else:
                result[key].append(None)
    
    return result


def parse_money_flow(text: str) -> Dict[str, float]:
    """解析资金流向字段"""
    result = {}
    patterns = [
        (r'主力\s+流入:\s*([\d.]+)亿,\s*占比:\s*([\d.]+)%', '主力'),
        (r'超大单\s+流入:\s*([\d.]+)亿,\s*占比:\s*([\d.]+)%', '超大单'),
        (r'大单\s+流入:\s*([\d.]+)亿,\s*占比:\s*([\d.]+)%', '大单'),
        (r'中单\s+流出:\s*([\d.]+)亿,\s*占比:\s*([\d.]+)%', '中单'),
        (r'小单\s+流出:\s*([\d.]+)亿,\s*占比:\s*([\d.]+)%', '小单'),
        (r'中单\s+流入:\s*([\d.]+)亿,\s*占比:\s*([\d.]+)%', '中单'),
        (r'小单\s+流入:\s*([\d.]+)亿,\s*占比:\s*([\d.]+)%', '小单'),
    ]
    for pattern, key in patterns:
        m = re.search(pattern, text)
        if m:
            if '流出' in pattern:
                result[f'{key}_流出_亿'] = float(m.group(1))
            else:
                result[f'{key}_流入_亿'] = float(m.group(1))
            result[f'{key}_占比'] = float(m.group(2))
    main_in = result.get('主力_流入_亿', 0)
    retail_out = result.get('中单_流出_亿', 0) + result.get('小单_流出_亿', 0)
    result['主力净流入_亿'] = round(main_in - retail_out, 3)
    return result


# ─── 检测函数 ────────────────────────────────────────────────────────────────

def detect_kdj_cross(tech: Dict) -> Dict:
    """KDJ 金叉/死叉检测"""
    k = tech.get('kdj_k', []); d = tech.get('kdj_d', [])
    if len(k) < 2 or len(d) < 2: return {'signal': 'insufficient_data'}
    k0,k1 = k[0],k[1]; d0,d1 = d[0],d[1]
    if None in [k0,k1,d0,d1]: return {'signal': 'data_error'}
    if k1 <= d1 and k0 > d0:
        strength = 'strong' if k0 < 20 else 'moderate' if k0 < 40 else 'weak'
        return {'signal':'golden_cross','k':k0,'d':d0,'k_prev':k1,'d_prev':d1,
                'strength':strength,'desc':f'KDJ金叉 K={k0:.1f} D={d0:.1f}'}
    elif k1 >= d1 and k0 < d0:
        return {'signal':'death_cross','k':k0,'d':d0,'k_prev':k1,'d_prev':d1,
                'desc':f'KDJ死叉 K={k0:.1f} D={d0:.1f}'}
    return {'signal':'none','k':k0,'d':d0,'desc':f'无交叉 K={k0:.1f} D={d0:.1f}'}


def detect_rsi_oversold(tech: Dict, threshold: float = 30) -> Dict:
    """RSI 超卖检测"""
    r6 = tech['rsi_6'][0] if tech.get('rsi_6') else None
    r12 = tech['rsi_12'][0] if tech.get('rsi_12') else None
    if r6 is None or r12 is None: return {'signal': 'data_error'}
    oversold = r6 < threshold and r12 < threshold
    return {'signal': oversold, 'rsi_6': r6, 'rsi_12': r12,
            'desc': f'RSI6={r6:.1f} RSI12={r12:.1f}'}


def detect_macd_cross(tech: Dict) -> Dict:
    """MACD 金叉/死叉检测"""
    dif = tech.get('macd_dif', []); dea = tech.get('macd_dea', [])
    if len(dif) < 2 or len(dea) < 2: return {'signal': 'insufficient_data'}
    d0,d1 = dif[0],dif[1]; de0,de1 = dea[0],dea[1]
    if None in [d0,d1,de0,de1]: return {'signal': 'data_error'}
    if d1 <= de1 and d0 > de0:
        return {'signal':'golden_cross','dif':d0,'dea':de0,
                'desc':f'MACD金叉 DIF={d0:.3f} DEA={de0:.3f}'}
    elif d1 >= de1 and d0 < de0:
        return {'signal':'death_cross','dif':d0,'dea':de0,
                'desc':f'MACD死叉 DIF={d0:.3f} DEA={de0:.3f}'}
    return {'signal':'none','dif':d0,'dea':de0,'desc':f'DIF={d0:.3f} DEA={de0:.3f}'}


def detect_ma_alignment(tech: Dict) -> Dict:
    """MA 均线多头/空头排列"""
    for key in ['ma5','ma10','ma30','ma60']:
        if not tech.get(key): return {'signal': 'insufficient_data'}
    m5,m10,m30,m60 = tech['ma5'][0],tech['ma10'][0],tech['ma30'][0],tech['ma60'][0]
    if None in [m5,m10,m30,m60]: return {'signal': 'data_error'}
    if m5 > m10 > m30 > m60:
        return {'signal':'bullish','m5':m5,'m10':m10,'m30':m30,'m60':m60,
                'desc':f'多头 MA5={m5:.2f}>MA10={m10:.2f}>MA30={m30:.2f}>MA60={m60:.2f}'}
    elif m5 < m10 < m30 < m60:
        return {'signal':'bearish','m5':m5,'m10':m10,'m30':m30,'m60':m60,
                'desc':f'空头 MA5={m5:.2f}<MA10={m10:.2f}<MA30={m30:.2f}<MA60={m60:.2f}'}
    return {'signal':'mixed','desc':f'混乱 MA5={m5:.2f} MA10={m10:.2f} MA30={m30:.2f} MA60={m60:.2f}'}


def detect_money_flow_strength(mf: Dict) -> Dict:
    """资金流向强度检测"""
    main_pct = mf.get('主力_占比', 0)
    net_inflow = mf.get('主力净流入_亿', 0)
    if main_pct >= 20:
        strength = 'strong'
    elif main_pct >= 10:
        strength = 'moderate'
    elif main_pct >= 5:
        strength = 'weak'
    else:
        strength = 'negligible'
    return {
        'strength': strength,
        'main_pct': main_pct,
        'net_inflow_亿': net_inflow,
        'desc': f'主力占比{main_pct:.1f}% 净流入{net_inflow:.2f}亿'
    }


# ─── 选股评分 ────────────────────────────────────────────────────────────────

def screen_stock(mcp_full_text: str, money_flow_text: str = "") -> Dict:
    """综合选股评分（0-100分）
    
    评分规则:
    - KDJ 金叉（超卖区）: +30分
    - KDJ 金叉（中部）: +15分
    - RSI 超卖: +15分
    - MACD 金叉: +15分
    - MA 均线多头: +20分
    - 资金主力占比>20%: +10分
    - KDJ 死叉: -20分
    - MA 均线空头: -15分
    """
    tech = parse_tech_table(mcp_full_text)
    mf = parse_money_flow(money_flow_text) if money_flow_text else {}
    kdj = detect_kdj_cross(tech)
    rsi = detect_rsi_oversold(tech)
    macd = detect_macd_cross(tech)
    ma = detect_ma_alignment(tech)
    money = detect_money_flow_strength(mf) if mf else {}
    
    score = 50  # 基础分
    
    # KDJ
    if kdj.get('signal') == 'golden_cross':
        if kdj.get('strength') == 'strong': score += 30
        elif kdj.get('strength') == 'moderate': score += 15
        else: score += 5
    elif kdj.get('signal') == 'death_cross': score -= 20
    
    # RSI
    if rsi.get('signal') == True: score += 15
    
    # MACD
    if macd.get('signal') == 'golden_cross': score += 15
    elif macd.get('signal') == 'death_cross': score -= 10
    
    # MA
    if ma.get('signal') == 'bullish': score += 20
    elif ma.get('signal') == 'bearish': score -= 15
    
    # 资金
    if money.get('strength') == 'strong': score += 10
    elif money.get('strength') == 'moderate': score += 5
    
    # 推荐
    if score >= 80: rec = 'buy'
    elif score >= 65: rec = 'watch'
    elif score <= 30: rec = 'sell'
    else: rec = 'neutral'
    
    return {
        'kdj': kdj, 'rsi': rsi, 'macd': macd,
        'ma': ma, 'money': money,
        'score': max(0, min(100, score)),
        'recommendation': rec,
    }


# ─── 批量扫描 ───────────────────────────────────────────────────────────────

def batch_screen(codes: List[str]) -> List[Dict]:
    """批量扫描多只股票（只支持沪市）
    
    codes: [code_str, ...]  例如 ['605365', '688197']
    """
    from mcp_utils import mcp_full, normalize_symbol
    results = []
    for code in codes:
        norm = normalize_symbol(code)
        text = mcp_full(norm) if norm else None
        if text:
            r = screen_stock(text, text)
            r['code'] = code
            results.append(r)
            kdj_d = r.get('kdj', {}).get('desc', '?')[:25]
            print(f"{code}: score={r['score']} rec={r['recommendation']} kdj={kdj_d}")
        else:
            print(f"{code}: 无数据")
    return results


# ─── 测试 ────────────────────────────────────────────────────────────────────


def detect_rsi_divergence(tech: Dict, lookback: int = 20) -> Dict:
    """检测 RSI 底背离（价格创新低但 RSI 走强）
    
    底背离: 价格创 N 日新低，但 RSI 没有创新低
    顶背离: 价格创 N 日新高，但 RSI 没有创新高
    
    返回: {
        'signal': 'bullish_divergence' | 'bearish_divergence' | 'none',
        'price_low_idx': int,  # 价格新低位置
        'rsi_low_idx': int,     # RSI 最低点位置
        'description': str,
    }
    """
    prices = tech.get('ma5', [])  # Use MA5 as price proxy
    rsi6 = tech.get('rsi_6', [])
    rsi12 = tech.get('rsi_12', [])
    
    n = min(lookback, len(prices), len(rsi6), len(rsi12))
    if n < 5:
        return {'signal': 'insufficient_data'}
    
    p = prices[:n]
    r = rsi6[:n]  # Use RSI(6)
    
    # Find price lowest point index
    price_min = min(p)
    price_min_idx = p.index(price_min)
    
    # Find RSI at that period
    rsi_at_price_low = r[price_min_idx]
    
    # Find RSI lowest point
    rsi_min = min(r)
    rsi_min_idx = r.index(rsi_min)
    
    # Check if RSI made a higher low while price made a lower low
    # Find if there was an earlier period where price was lower
    if price_min_idx > 0 and price_min_idx < n - 1:
        # Compare RSI at price low vs RSI at earlier low
        # For a bullish divergence: price makes new low, RSI doesn't
        # Find previous significant low
        prev_price_low = min(p[:price_min_idx]) if price_min_idx > 0 else float('inf')
        prev_rsi_at_low = min(r[:price_min_idx]) if price_min_idx > 0 else 0
        
        if prev_rsi_at_low > rsi_at_price_low and rsi_at_price_low < 40:
            return {
                'signal': 'bullish_divergence',
                'price_low_idx': price_min_idx,
                'rsi_low_idx': rsi_min_idx,
                'description': f'RSI底背离: 价格新低={price_min:.2f} RSI={rsi_at_price_low:.1f} 但前期RSI={prev_rsi_at_low:.1f}',
            }
    
    # No clear divergence
    return {
        'signal': 'none',
        'price_low_idx': price_min_idx,
        'rsi_low_idx': rsi_min_idx,
        'description': f'无背离: 价格新低={price_min:.2f} RSI={rsi_at_price_low:.1f}',
    }




def detect_macd_divergence(tech: Dict, lookback: int = 20) -> Dict:
    """检测 MACD 底背离"""
    prices = tech.get('ma5', [])
    dif = tech.get('macd_dif', [])
    n = min(lookback, len(prices), len(dif))
    if n < 5:
        return {'signal': 'insufficient_data'}
    p = prices[:n]
    d = dif[:n]
    price_min = min(p)
    price_min_idx = p.index(price_min)
    dif_at_low = d[price_min_idx]
    if price_min_idx > 1 and dif_at_low is not None:
        prev_vals = [x for x in d[:price_min_idx] if x is not None]
        if prev_vals:
            prev_low = min(prev_vals)
            if dif_at_low > prev_low and dif_at_low < 0:
                return {'signal': 'bullish_divergence', 'price_low': price_min, 'dif_at_low': dif_at_low,
                        'description': 'MACD底背离'}
    return {'signal': 'none', 'price_low': price_min, 'dif_at_low': dif_at_low, 'description': '无背离'}




def calc_stop_loss(price: float, atr: float, boll_lower: float, cost: float,
                   atr_mult: float = 2.0, max_loss_pct: float = 0.15) -> Dict:
    atr_stop = price - atr_mult * atr if atr else None
    boll_stop = boll_lower
    cost_stop = cost * (1 - max_loss_pct)
    stops = [s for s in [atr_stop, boll_stop, cost_stop] if s is not None]
    recommended = min(stops) if stops else cost_stop
    return {
        'atr_stop': round(atr_stop, 2) if atr_stop else None,
        'boll_stop': round(boll_stop, 2) if boll_stop else None,
        'cost_stop': round(cost_stop, 2),
        'recommended': round(recommended, 2),
    }


if __name__ == '__main__':
    import sys; sys.path.insert(0, 'scripts')
    from mcp_utils import mcp_full, normalize_symbol
    code = '605365'
    text = mcp_full(normalize_symbol(code))
    if text:
        r = screen_stock(text, text)
        print(f"\n{'='*50}")
        print(f"股票: {code}")
        print(f"评分: {r['score']} | 推荐: {r['recommendation']}")
        print(f"KDJ: {r['kdj'].get('desc')}")
        print(f"RSI: {r['rsi'].get('desc')}")
        print(f"MACD: {r['macd'].get('desc')}")
        print(f"均线: {r['ma'].get('desc')}")
        print(f"资金: {r['money'].get('desc')}")
    else:
        print("无数据")
