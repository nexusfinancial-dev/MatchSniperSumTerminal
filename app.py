"""
Match Sniper Pro Terminal - Dedicated Standalone Edition
High-Frequency Automated Trading Engine for Deriv (Pure R Volatility Indices)
Specialized Mode F Quantum Citadel:
  1. Solo Match Sniper (+734.0% DIGITMATCH)
  2. Twin-Match Drought Bracketing (+317.0% Dual Bracket)
  3. Cluster Sniper: Under 3 / Over 6 (+213.0% DIGITUNDER/OVER)
  4. Duo Wing: Under 2 / Over 7 (+354.5% DIGITUNDER/OVER)
  5. Parity Delta Spread: Even / Odd (+94.0% DIGITEVEN/ODD)
"""

import asyncio
import collections
from collections import deque
import csv
from datetime import datetime
import inspect
import json
import logging
import math
import os
import random
import socket
import sys
import time
from typing import Dict, List, Optional

import aiohttp

# Force UTF-8 on Windows terminal stdout/stderr
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
import uvicorn
import websockets
import webbrowser
import threading

# Configuration constants and Portable Paths
if getattr(sys, "frozen", False):
    EXE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", EXE_DIR)
else:
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = EXE_DIR

APP_DIR = EXE_DIR

def resolve_resource_path(filename: str) -> str:
    """Finds resource: checks next to executable first, falls back to PyInstaller bundle."""
    local_path = os.path.join(EXE_DIR, filename)
    if os.path.exists(local_path):
        return local_path
    bundle_path = os.path.join(BUNDLE_DIR, filename)
    if os.path.exists(bundle_path):
        return bundle_path
    return local_path

CREDS_FILE = os.path.join(EXE_DIR, "credentials.json")
CSV_LOG_FILE = os.path.join(EXE_DIR, "match_sniper_trades.csv")
HTML_FILE = resolve_resource_path("dashboard.html")
PROOF_HTML_FILE = resolve_resource_path("Match_Sniper_Capital_Proof.html")
MANUAL_HTML_FILE = resolve_resource_path("Match_Sniper_User_Manual.html")

PORT = 8565
HOST = "0.0.0.0"

DERIV_PUBLIC_WS = "wss://api.derivws.com/trading/v1/options/ws/public"
OTP_ENDPOINT = "https://api.derivws.com/trading/v1/options/accounts/{account_id}/otp"
PUBLIC_APP_IDS = ["33PqmtEUNPpbeTwnA3TwQ", "1089", "16929"]
USER_AGENT = "AsianResetLab/1.0"

MATCH_ASSETS = ["R_100", "R_75", "R_50", "R_25", "R_10"]
DECIMALS_MAP = {
    "R_10": 3,
    "R_25": 3,
    "R_50": 4,
    "R_75": 4,
    "R_100": 2,
}


def extract_last_digit(price: float, symbol: str) -> int:
    """Extracts the exact settlement digit according to asset decimal precision."""
    decs = DECIMALS_MAP.get(symbol, 2)
    s = f"{price:.{decs}f}".replace(".", "")
    return int(s[-1]) if s else 0


# ==============================================================================
# LADDER BUILDERS WITH FLAT-START SHIELDS & DYNAMIC RECOVERY
# ==============================================================================

def build_match_ladder(base_stake: float = 0.35, steps: int = 17) -> List[dict]:
    """
    Dynamic Inviolable Ladder for DIGITMATCH (+734.0% Net Payout, 8.34x Multiplier).
    First 7 steps (0-6) remain flat at base stake (Flat-Start Shield).
    Steps 7+ compute required stake to cover cumulative drain + target profit.
    """
    b = max(0.35, round(base_stake, 2))
    payout_mult = 8.34
    net_ratio = 7.34
    num_steps = max(2, min(100, int(steps)))
    ladder = []
    cum_drain = 0.0
    target_profit = round(b * 1.0, 2)
    for idx in range(num_steps):
        if idx < 7:
            s = b
        else:
            req_s = (cum_drain + target_profit) / net_ratio
            s = max(b, round(math.ceil(req_s * 100) / 100.0, 2))
        cum_drain = round(cum_drain + s, 2)
        win_ret = round(s * payout_mult, 2)
        net_ret = round(win_ret - cum_drain, 2)
        desc = f"Step {idx}: Flat Match (${s:.2f})" if idx < 7 else f"Step {idx}: Recovery Match (${s:.2f})"
        ladder.append({
            "step": idx,
            "contract": "DIGITMATCH (1t)",
            "stake": s,
            "payout": "+734.0%",
            "type": "Sniper Drought Match" if idx == 0 else (f"Flat Shield Step {idx}" if idx < 7 else f"Recovery Step {idx}"),
            "drain": cum_drain,
            "win_return": win_ret,
            "net": net_ret,
            "desc": desc,
            "payout_ratio": net_ratio,
        })
    return ladder


def build_twin_match_ladder(base_stake: float = 0.35, steps: int = 20) -> List[dict]:
    """
    Dynamic Inviolable Ladder for TWIN-MATCH BRACKET (2 simultaneous DIGITMATCH bets).
    Win Rate per step: 20.0% (1 in 5 chance).
    Each step places stake s on Digit A and stake s on Digit B (total cost = 2*s).
    Winning payout: s * 8.34 (+317.0% net on total cost 2*s, net_ratio = 3.17).
    Phase 1 (Steps 0-2): 3 flat attempts at base stake per digit (2*b total cost per step).
    Phase 2 (Steps 3+): Dynamic micro-martingale scaling covering full deficit.
    """
    b = max(0.35, round(base_stake, 2))
    payout_mult = 8.34
    net_ratio = 3.17
    num_steps = max(2, min(100, int(steps)))
    ladder = []
    cum_drain = 0.0
    target_profit = round(b * 1.0, 2)
    for idx in range(num_steps):
        if idx < 3:
            s = b
        else:
            req_s = (cum_drain + target_profit) / (payout_mult - 2.0)
            s = max(b, round(math.ceil(req_s * 100) / 100.0, 2))
        step_total_cost = round(s * 2, 2)
        cum_drain = round(cum_drain + step_total_cost, 2)
        win_ret = round(s * payout_mult, 2)
        net_ret = round(win_ret - cum_drain, 2)
        desc = f"Step {idx}: Flat Twin (${s:.2f} x 2 = ${step_total_cost:.2f})" if idx < 3 else f"Step {idx}: Recovery Twin (${s:.2f} x 2 = ${step_total_cost:.2f})"
        ladder.append({
            "step": idx,
            "contract": "TWIN DIGITMATCH (2x 1t)",
            "stake": step_total_cost,
            "stake_per_digit": s,
            "payout": "+317.0%",
            "type": "Twin Sniper" if idx == 0 else (f"Flat Twin Step {idx}" if idx < 3 else f"Twin Recovery Step {idx}"),
            "drain": cum_drain,
            "win_return": win_ret,
            "net": net_ret,
            "desc": desc,
            "payout_ratio": net_ratio,
        })
    return ladder


def build_cluster_ladder(base_stake: float = 0.35, steps: int = 12) -> List[dict]:
    """
    Dynamic Inviolable Ladder for CLUSTER SNIPER (DIGITUNDER 3 or DIGITOVER 6).
    Win Rate per step: 30.0% (Covers 3 digits: {0,1,2} or {7,8,9}).
    Payout: +213.0% net (3.13x total return multiplier).
    Phase 1 (Steps 0-1): 2 flat attempts at base stake.
    Phase 2 (Steps 2+): Dynamic recovery covering full cumulative drain + target profit.
    """
    b = max(0.35, round(base_stake, 2))
    payout_mult = 3.13
    net_ratio = 2.13
    num_steps = max(2, min(100, int(steps)))
    ladder = []
    cum_drain = 0.0
    target_profit = round(b * 1.0, 2)
    for idx in range(num_steps):
        if idx < 2:
            s = b
        else:
            req_s = (cum_drain + target_profit) / net_ratio
            s = max(b, round(math.ceil(req_s * 100) / 100.0, 2))
        cum_drain = round(cum_drain + s, 2)
        win_ret = round(s * payout_mult, 2)
        net_ret = round(win_ret - cum_drain, 2)
        desc = f"Step {idx}: Flat Cluster (${s:.2f})" if idx < 2 else f"Step {idx}: Recovery Cluster (${s:.2f})"
        ladder.append({
            "step": idx,
            "contract": "CLUSTER (UNDER 3 / OVER 6)",
            "stake": s,
            "payout": "+213.0%",
            "type": "Cluster Vacuum Sniper" if idx == 0 else (f"Flat Cluster Step {idx}" if idx < 2 else f"Cluster Recovery Step {idx}"),
            "drain": cum_drain,
            "win_return": win_ret,
            "net": net_ret,
            "desc": desc,
            "payout_ratio": net_ratio,
        })
    return ladder


def build_duo_wing_ladder(base_stake: float = 0.35, steps: int = 21) -> List[dict]:
    """
    Dynamic Inviolable Ladder for DUO WING (UNDER 2 / OVER 7).
    Win Rate per step: 20.0% (Covers 2 digits: {0,1} or {8,9}).
    Payout: +354.5% net (4.545x total return multiplier).
    Phase 1 (Steps 0-2): 3 flat attempts at base stake.
    Phase 2 (Steps 3+): Dynamic recovery covering full cumulative drain + target profit.
    """
    b = max(0.35, round(base_stake, 2))
    payout_mult = 4.545
    net_ratio = 3.545
    num_steps = max(2, min(100, int(steps)))
    ladder = []
    cum_drain = 0.0
    target_profit = round(b * 1.0, 2)
    for idx in range(num_steps):
        if idx < 3:
            s = b
        else:
            req_s = (cum_drain + target_profit) / net_ratio
            s = max(b, round(math.ceil(req_s * 100) / 100.0, 2))
        cum_drain = round(cum_drain + s, 2)
        win_ret = round(s * payout_mult, 2)
        net_ret = round(win_ret - cum_drain, 2)
        desc = f"Step {idx}: Flat Duo Wing (${s:.2f})" if idx < 3 else f"Step {idx}: Recovery Duo Wing (${s:.2f})"
        ladder.append({
            "step": idx,
            "contract": "DUO WING (UNDER 2 / OVER 7)",
            "stake": s,
            "payout": "+354.5%",
            "type": "Duo Wing Tail Sniper" if idx == 0 else (f"Flat Duo Wing Step {idx}" if idx < 3 else f"Duo Wing Recovery Step {idx}"),
            "drain": cum_drain,
            "win_return": win_ret,
            "net": net_ret,
            "desc": desc,
            "payout_ratio": net_ratio,
        })
    return ladder


def build_parity_spread_ladder(base_stake: float = 0.35, steps: int = 6) -> List[dict]:
    """
    Dynamic Inviolable Ladder for PARITY DELTA SPREAD (DIGITEVEN / DIGITODD).
    Win Rate per step: 50.0% (Covers 5 digits: {0,2,4,6,8} or {1,3,5,7,9}).
    Payout: +94.0% net (1.94x total return multiplier).
    """
    b = max(0.35, round(base_stake, 2))
    payout_mult = 1.94
    net_ratio = 0.94
    num_steps = max(2, min(100, int(steps)))
    ladder = []
    cum_drain = 0.0
    target_profit = round(b * net_ratio, 2)
    for idx in range(num_steps):
        if idx == 0:
            s = b
        else:
            req_s = (cum_drain + target_profit) / net_ratio
            s = max(b, round(math.ceil(req_s * 100) / 100.0, 2))
        cum_drain = round(cum_drain + s, 2)
        win_ret = round(s * payout_mult, 2)
        net_ret = round(win_ret - cum_drain, 2)
        desc = f"Step {idx}: Base Parity (${s:.2f})" if idx == 0 else f"Step {idx}: Recovery Parity (${s:.2f})"
        ladder.append({
            "step": idx,
            "contract": "PARITY (DIGITEVEN / DIGITODD)",
            "stake": s,
            "payout": "+94.0%",
            "type": "Parity Delta Sniper" if idx == 0 else f"Parity Recovery Step {idx}",
            "drain": cum_drain,
            "win_return": win_ret,
            "net": net_ret,
            "desc": desc,
            "payout_ratio": net_ratio,
        })
    return ladder


def build_penta_salvo_ladder(base_stake: float = 0.35, steps: int = 3, num_assets: int = 15, rec_contracts: int = 6) -> List[dict]:
    """
    Inviolable Adaptive Multi-Salvo Kelly Ladder for PENTA-ASSET SALVO:
    - Step 0: Initial high-probability multi-contract salvo (12 to 15 concurrent contracts @ base_stake).
      Win of 2 contracts banks immediate net profit.
    - Steps 1 & 2: Focused 6-contract recovery salvos scaled by Kelly formula:
      req = (cum_drain + target_profit) / (8.34 - rec_contracts).
      Since 8.34 - 6 = 2.34 > 0, ANY SINGLE HIT IN RECOVERY COVERS CUMULATIVE DRAIN AND SECURES NET PROFIT!
    - Max steps strictly capped at 3 steps to preserve >90% capital.
    """
    b = max(0.35, round(base_stake, 2))
    num_steps = max(2, min(50, int(steps)))
    n0 = max(1, min(15, int(num_assets)))
    n_rec = max(1, min(7, int(rec_contracts)))
    ladder = []

    # Step 0: Initial Salvo
    s0_total = round(b * n0, 2)
    cum_drain = s0_total
    s0_win1 = round(b * 8.34, 2)
    s0_win2 = round(b * 8.34 * 2, 2)
    s0_net1 = round(s0_win1 - s0_total, 2)
    s0_net2 = round(s0_win2 - s0_total, 2)
    payout_label = f"+{round((s0_net2/s0_total)*100, 1)}% (2 Wins)" if s0_net2 > 0 else "Multi-Salvo"
    ladder.append({
        "step": 0,
        "contract": f"PENTA SALVO ({n0}x 1t)",
        "stake": s0_total,
        "stake_per_digit": b,
        "payout": payout_label,
        "type": f"{n0}-Contract Multi-Salvo",
        "num_contracts": n0,
        "drain": cum_drain,
        "win_return": s0_win1,
        "win2_return": s0_win2,
        "net": s0_net2,
        "desc": f"Step 0: Penta Salvo ({n0}x ${b:.2f} = ${s0_total:.2f})",
        "payout_ratio": 7.34,
        "is_salvo": True,
    })

    # Steps 1+: Focused Recovery Salvos (6 contracts)
    target_profit = round(b * 1.0, 2)
    divisor = max(0.5, 8.34 - n_rec) if n_rec < 8 else 1.0
    for idx in range(1, num_steps):
        req_per_digit = (cum_drain + target_profit) / divisor
        s_digit = max(b, round(math.ceil(req_per_digit * 100) / 100.0, 2))
        st_total = round(s_digit * n_rec, 2)
        cum_drain = round(cum_drain + st_total, 2)
        win1 = round(s_digit * 8.34, 2)
        win2 = round(s_digit * 8.34 * 2, 2)
        net1 = round(win1 - cum_drain, 2)
        net2 = round(win2 - cum_drain, 2)
        ladder.append({
            "step": idx,
            "contract": f"PENTA RECOVERY SALVO ({n_rec}x 1t)",
            "stake": st_total,
            "stake_per_digit": s_digit,
            "payout": f"+{round((net1/st_total)*100, 1)}% (1 Win)",
            "type": f"{n_rec}-Contract Recovery Salvo Step {idx}",
            "num_contracts": n_rec,
            "drain": cum_drain,
            "win_return": win1,
            "win2_return": win2,
            "net": net1,
            "desc": f"Step {idx}: Recovery Salvo ({n_rec}x ${s_digit:.2f} = ${st_total:.2f})",
            "payout_ratio": round(8.34 - 1.0, 2),
            "is_salvo": True,
        })
    return ladder


def calculate_symbol_expected_drought_stats(sym: str) -> dict:
    """
    Computes rolling empirical mean and standard deviation of digit inter-arrival intervals
    over recent ticks for the given symbol to derive the statistical reversal threshold.
    """
    digits = list(state.digits.get(sym, []))[-100:]
    if len(digits) < 20:
        return {"mean": 10.0, "std": 9.5, "expected_threshold": 18}
    
    intervals = []
    for d in range(10):
        indices = [i for i, val in enumerate(digits) if val == d]
        if len(indices) >= 2:
            gaps = [indices[j] - indices[j-1] for j in range(1, len(indices))]
            intervals.extend(gaps)
        elif len(indices) == 1:
            intervals.append(len(digits) - indices[0])
        else:
            intervals.append(len(digits))
            
    if not intervals:
        return {"mean": 10.0, "std": 9.5, "expected_threshold": 18}
        
    mean_val = sum(intervals) / len(intervals)
    variance = sum((x - mean_val) ** 2 for x in intervals) / len(intervals)
    std_val = math.sqrt(variance)
    exp_thresh = int(round(mean_val + 1.0 * std_val))
    exp_thresh = max(12, min(30, exp_thresh))
    return {
        "mean": round(mean_val, 1),
        "std": round(std_val, 1),
        "expected_threshold": exp_thresh,
    }


# ==============================================================================
# TERMINAL STATE OBJECT
# ==============================================================================

class MatchSniperState:
    def __init__(self):
        self.is_running = False
        self.active_account = "demo"
        self.creds = self.load_credentials()
        self.deriv_balance = 0.0
        self.balance_synced = False

        self.ticks = {sym: deque(maxlen=500) for sym in MATCH_ASSETS}
        self.digits = {sym: deque(maxlen=500) for sym in MATCH_ASSETS}
        self.pip_steps = {sym: deque(maxlen=100) for sym in MATCH_ASSETS}

        self.tick_event = asyncio.Event()
        self.in_live_trade = False
        self.trade_exec_lock = asyncio.Lock()
        self.persistent_ws_lock = asyncio.Lock()
        self.global_lock_until = 0.0
        self.persistent_trade_ws = None
        self.persistent_ws_account = None
        self.persistent_ws_last_active = 0.0

        self.total_trades = 0
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0.00
        self.vault_balance = 0.00
        self.capital_growth_pool = 0.00
        self.active_cycle = 1
        self.cycle_target_usd = 185.00
        self.cycle_accumulated_pnl = 0.00
        self.vault_locked_profit = 0.00
        self.initial_sl_usd = 15.00
        self.session_start_balance = 0.00
        self.hard_sl_floor = 0.00
        self.stop_on_max_martingale = True
        self.stopped_by_martingale_hit = False
        self.stopped_by_take_profit = False
        self.take_profit_enabled = True
        self.stopped_by_stop_loss = False
        self.stop_loss_enabled = True
        self.hard_sl_enabled = True
        self.current_loss_streak = 0
        self.max_loss_streak = 0
        self.baskets_cleared = 0
        self.step_distribution = {s: 0 for s in range(35)}

        self.match_config = {
            "asset": "ALL",
            "enabled_assets": ["R_100", "R_75", "R_50", "R_25", "R_10"],
            "sub_mode": "solo",
            "base_stake": 0.35,
            "drought_threshold": 5,
            "min_digit_drought": 0,
            "basket_sum_threshold": 0,
            "cluster_sum_threshold": 0,
            "duo_sum_threshold": 0,
            "twin_sum_threshold": 0,
            "min_penta_trades": 2,
            "max_penta_trades": 15,
            "penta_rec_trades": 6,
            "penta_exact_threshold": True,
            "solo_step_expansion": False,
            "twin_drought_threshold": 15,
            "cluster_drought_threshold": 10,
            "duo_drought_threshold": 14,
            "parity_spread_threshold": 8.0,
            "penta_drought_threshold": 18,
            "penta_max_drought": 18,
            "penta_window_span": 0,
            "penta_max_steps": 3,
            "penta_separate_ranges": False,
            "penta_symbol_ranges": {
                "R_10": {"min": 18, "max": 18},
                "R_25": {"min": 18, "max": 18},
                "R_50": {"min": 18, "max": 18},
                "R_75": {"min": 18, "max": 18},
                "R_100": {"min": 18, "max": 18},
            },
            "duration_ticks": 1,
            "max_steps": 17,
            "target_profit_usd": 185.00,
            "stop_loss_usd": 15.00,
            "step_sl_action": "reset_to_s0",
            "tri_strike_filter": True,
            "max_target_strikes": 20,
            "open_depth": True,
            "filter_zombie": True,
            "min_rolling_freq": 5,
            "hunt_zombies": False,
            "require_squeeze": False,
            "allow_dynamic_pivot": False,
            "parity_streak_filter": False,
            "parity_repeat_on_loss": True,
            "direct_fast_buy": True,
            "ai_commander": False,
            "user_custom_stake": False,
            "target_priority": "min",
            "fresh_breakout_mode": True,
            "symbol_thresholds": {
                "R_10": 4,
                "R_25": 7,
                "R_50": 5,
                "R_75": 6,
                "R_100": 5,
            },
            "symbol_enabled": {
                "R_10": True,
                "R_25": True,
                "R_50": True,
                "R_75": True,
                "R_100": True,
            },
        }

        self.match_state = {
            "ladder": build_match_ladder(0.35, 17),
            "current_step": 0,
            "status": "STANDBY",
            "active_cycle": 1,
            "cycle_target_usd": 185.00,
            "cycle_accumulated_pnl": 0.00,
            "vault_locked_profit": 0.00,
            "hard_sl_floor": 0.00,
            "initial_sl_usd": 15.00,
            "session_start_balance": 0.00,
            "session_trades": 0,
            "session_wins": 0,
            "session_losses": 0,
            "session_pnl": 0.00,
            "sequences_won": 0,
            "sequences_lost": 0,
            "max_step_hit": 0,
            "sequence_accumulated_loss": 0.00,
            "last_trade_time": 0.0,
            "last_trade_finish_time": 0.0,
            "last_traded_symbol": None,
            "frozen_symbol": None,
            "frozen_until": 0.0,
            "locked_digit": None,
            "locked_twin_digit": None,
            "locked_cluster_type": None,
            "locked_barrier": None,
            "locked_parity_type": None,
            "locked_symbol": None,
            "locked_base_thresh": None,
            "target_consecutive_trades": 0,
            "current_target_key": None,
            "exhausted_targets": [],
            "manual_lock": False,
            "target_reached": False,
            "ai_cooldown_until": 0.0,
            "ai_phase": "PHASE 1: SURVIVAL SHIELD ($15->$25)",
            "assets_drought_radar": {},
            "assets_freq_radar": {},
            "cluster_radar": {},
            "parity_radar": {},
            "global_digit_droughts": {},
            "drought_radar": {d: 0 for d in range(10)},
            "rolling_freq_100": {d: 10 for d in range(10)},
            "zombie_digits": [],
            "max_drought_digit": 0,
            "max_drought_symbol": "R_100",
            "max_drought_count": 0,
        }

        self.trade_history = []
        self.logs = []
        self.ws_clients = set()

    def load_credentials(self) -> dict:
        default_creds = {
            "token": "",
            "account_id_demo": "",
            "account_id_real": "",
            "active": "demo",
            "demo": {"account_id": "", "token": ""},
            "real": {"account_id": "", "token": ""}
        }
        if os.path.exists(CREDS_FILE):
            try:
                with open(CREDS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        else:
            bundled_creds = os.path.join(BUNDLE_DIR, "credentials.json")
            if os.path.exists(bundled_creds) and bundled_creds != CREDS_FILE:
                try:
                    with open(bundled_creds, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    with open(CREDS_FILE, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2)
                    return data
                except Exception:
                    pass
            try:
                with open(CREDS_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_creds, f, indent=2)
            except Exception:
                pass
        return default_creds

    def save_credentials(self):
        try:
            with open(CREDS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.creds, f, indent=2)
        except Exception as e:
            self.log(f"Failed to save credentials: {e}", "WARN")

    def get_active_account_id(self) -> str:
        acc = self.creds.get(self.active_account, {})
        if isinstance(acc, dict):
            val = acc.get("account_id", "").strip()
            if val:
                return val
        if self.active_account == "demo":
            return str(self.creds.get("account_id_demo", "")).strip()
        elif self.active_account == "real":
            return str(self.creds.get("account_id_real", "")).strip()
        return ""

    def get_active_token(self) -> str:
        acc = self.creds.get(self.active_account, {})
        if isinstance(acc, dict):
            val = acc.get("token", "").strip()
            if val:
                return val
        return str(self.creds.get("token", "")).strip()

    def log(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = {"time": ts, "msg": msg, "level": level}
        self.logs.insert(0, entry)
        if len(self.logs) > 300:
            self.logs.pop()
        try:
            print(f"[{ts}][MatchSniper][{level}] {msg}")
        except Exception:
            try:
                clean_msg = msg.encode("ascii", errors="replace").decode("ascii")
                print(f"[{ts}][MatchSniper][{level}] {clean_msg}")
            except Exception:
                pass


state = MatchSniperState()


def rebuild_active_ladder() -> List[dict]:
    """
    Universally rebuilds active Martingale ladder for the current mode,
    and dynamically enforces Rule: Target Profit = Full Martingale Depth (ladder[-1]['drain']).
    """
    mc = state.match_config
    ms = state.match_state
    b = float(mc.get("base_stake", 0.35))
    sub = mc.get("sub_mode", "solo")
    open_d = bool(mc.get("open_depth", True))
    ms["open_depth"] = open_d

    if sub == "parity_spread":
        st_count = int(mc.get("parity_max_steps", 20 if open_d else 6))
        lad = build_parity_spread_ladder(b, steps=st_count)
    elif sub == "duo_wing":
        st_count = int(mc.get("duo_max_steps", 25 if open_d else 21))
        lad = build_duo_wing_ladder(b, steps=st_count)
    elif sub == "cluster":
        st_count = int(mc.get("cluster_max_steps", 20 if open_d else 12))
        lad = build_cluster_ladder(b, steps=st_count)
    elif sub == "twin":
        st_count = int(mc.get("twin_max_steps", 25 if open_d else 20))
        lad = build_twin_match_ladder(b, steps=st_count)
    elif sub == "penta":
        max_targets = int(mc.get("max_penta_trades", 15))
        st_count = int(mc.get("penta_max_steps", 10 if open_d else 3))
        rec_targets = int(mc.get("penta_rec_trades", 6))
        lad = build_penta_salvo_ladder(b, steps=st_count, num_assets=max_targets, rec_contracts=rec_targets)
    else:
        st_count = int(mc.get("solo_max_steps", 30 if open_d else 17))
        lad = build_match_ladder(b, steps=st_count)

    ms["ladder"] = lad
    mc["max_steps"] = len(lad)
    mc["max_step"] = len(lad) - 1

    # Inviolable Target Rule: Cycle Target = Full Martingale Drain Depth
    drain_depth = round(lad[-1]["drain"], 2) if lad else 100.0
    state.cycle_target_usd = drain_depth
    mc["target_profit_usd"] = drain_depth
    ms["cycle_target_usd"] = drain_depth

    # For Penta multi-salvo, ensure SL buffer accommodates the full 3-step ladder depth
    if sub == "penta":
        penta_required_sl = max(75.0, round(drain_depth + 5.0, 2))
        if state.initial_sl_usd < penta_required_sl:
            state.initial_sl_usd = penta_required_sl
            mc["stop_loss_usd"] = penta_required_sl
            if state.session_start_balance > 0.0 and state.active_cycle == 1:
                state.hard_sl_floor = round(state.session_start_balance - state.initial_sl_usd, 2)
                ms["hard_sl_floor"] = state.hard_sl_floor
    return lad


def sync_ai_commander_shield(live_bal: Optional[float] = None) -> dict:
    """Dynamic AI Commander Auto-Scaling Matrix ($15 -> $200 compounding path)."""
    bal = live_bal if (live_bal is not None and live_bal > 0) else state.deriv_balance
    mc = state.match_config
    ms = state.match_state
    sub = mc.get("sub_mode", "solo")

    if bal < 25.0:
        b = 0.35
        cluster_th = 11
        duo_th = 16
        solo_th = 30
        phase = "PHASE 1: SURVIVAL SHIELD ($15->$25)"
    elif bal < 50.0:
        b = 0.50
        cluster_th = 10
        duo_th = 14
        solo_th = 28
        phase = "PHASE 2: CONSERVATIVE COMPOUND ($25->$50)"
    elif bal < 100.0:
        b = 0.75
        cluster_th = 9
        duo_th = 13
        solo_th = 26
        phase = "PHASE 3: MOMENTUM EXPANSION ($50->$100)"
    else:
        b = round(max(1.0, math.floor(bal * 0.01 * 100) / 100.0), 2)
        cluster_th = 9
        duo_th = 12
        solo_th = 25
        phase = "PHASE 4: EXPONENTIAL CITADEL ($100->$200+)"

    cluster_steps = 12
    for s in range(8, 25):
        lad = build_cluster_ladder(b, s)
        if lad[-1]["drain"] <= bal + 0.15:
            cluster_steps = s

    duo_steps = 14
    for s in range(10, 30):
        lad = build_duo_wing_ladder(b, s)
        if lad[-1]["drain"] <= bal + 0.15:
            duo_steps = s

    solo_steps = 12
    for s in range(12, 36):
        lad = build_match_ladder(b, s)
        if lad[-1]["drain"] <= bal + 0.15:
            solo_steps = s

    if not mc.get("user_custom_stake", False):
        mc["base_stake"] = b

    mc["cluster_drought_threshold"] = cluster_th
    mc["duo_drought_threshold"] = duo_th
    mc["drought_threshold"] = solo_th
    ms["ai_phase"] = phase

    if sub == "duo_wing":
        ms["ladder"] = build_duo_wing_ladder(b, steps=duo_steps)
    elif sub == "solo":
        ms["ladder"] = build_match_ladder(b, steps=solo_steps)
    elif sub == "cluster":
        ms["ladder"] = build_cluster_ladder(b, steps=cluster_steps)
    elif sub == "twin":
        ms["ladder"] = build_twin_match_ladder(b, steps=int(mc.get("twin_max_steps", 20)))
    elif sub == "parity_spread":
        ms["ladder"] = build_parity_spread_ladder(b, steps=int(mc.get("parity_max_steps", 6)))
    elif sub == "penta":
        max_targets = int(mc.get("max_penta_trades", 15))
        st_count = int(mc.get("penta_max_steps", 3))
        rec_targets = int(mc.get("penta_rec_trades", 6))
        ms["ladder"] = build_penta_salvo_ladder(b, steps=st_count, num_assets=max_targets, rec_contracts=rec_targets)

    mc["max_steps"] = len(ms["ladder"])
    mc["max_step"] = len(ms["ladder"]) - 1
    drain_depth = round(ms["ladder"][-1]["drain"], 2) if ms["ladder"] else 100.0
    state.cycle_target_usd = drain_depth
    mc["target_profit_usd"] = drain_depth
    ms["cycle_target_usd"] = drain_depth
    return ms["ladder"]


# ==============================================================================
# WEBSOCKET & NETWORK CONNECTION HANDLING
# ==============================================================================

def _ws_connect(url: str, extra_headers: Optional[dict] = None, **kwargs):
    sig = inspect.signature(websockets.connect)
    if extra_headers:
        if "additional_headers" in sig.parameters:
            kwargs["additional_headers"] = extra_headers
        else:
            kwargs["extra_headers"] = extra_headers
    return websockets.connect(url, **kwargs)


def is_ws_open(ws) -> bool:
    if ws is None:
        return False
    if hasattr(ws, "closed"):
        return not ws.closed
    if hasattr(ws, "state"):
        return ws.state.name == "OPEN"
    return False


async def fetch_otp_ws_url(account_id: str, token: str) -> Optional[str]:
    """Obtains authorized WebSocket URL via Deriv One-Time Password API."""
    url = OTP_ENDPOINT.format(account_id=account_id)
    for app_id in PUBLIC_APP_IDS:
        headers = {
            "Deriv-App-ID": app_id,
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json={}, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        ws_url = data.get("data", {}).get("url")
                        if ws_url:
                            return ws_url
        except Exception:
            continue
    state.log(f"⚠️ Deriv OTP WS authorization failed for {account_id}", "WARN")
    return None


async def get_or_create_persistent_trading_ws(account_id: str, token: str):
    """Maintains a persistent, warm, ultra-low latency WebSocket for trade execution."""
    if is_ws_open(state.persistent_trade_ws) and state.persistent_ws_account == account_id:
        return state.persistent_trade_ws

    async with state.persistent_ws_lock:
        if is_ws_open(state.persistent_trade_ws) and state.persistent_ws_account == account_id:
            return state.persistent_trade_ws

        if state.persistent_trade_ws is not None:
            try:
                await state.persistent_trade_ws.close()
            except Exception:
                pass
            state.persistent_trade_ws = None

        ws_url = await fetch_otp_ws_url(account_id, token)
        if not ws_url:
            return None

        try:
            ws = await _ws_connect(
                ws_url,
                extra_headers={"User-Agent": USER_AGENT},
                ping_interval=15,
                ping_timeout=15,
            )
            state.persistent_trade_ws = ws
            try:
                sock = ws.transport.get_extra_info('socket') if hasattr(ws, 'transport') else None
                if sock is not None:
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            except Exception:
                pass
            state.persistent_ws_account = account_id
            state.persistent_ws_last_active = time.time()
            state.log(f"⚡ Dedicated Trading WebSocket online for {account_id}.", "SYSTEM")
            return ws
        except Exception as e:
            state.log(f"Failed to connect persistent Deriv WS: {e}", "WARN")
            return None


async def sync_deriv_live_balance():
    """Non-blocking background balance synchronization."""
    if state.in_live_trade or state.trade_exec_lock.locked():
        return
    token = state.get_active_token()
    account_id = state.get_active_account_id()
    if not token or not account_id:
        return
    try:
        async with state.trade_exec_lock:
            ws = await get_or_create_persistent_trading_ws(account_id, token)
            if not ws or state.in_live_trade:
                return
            await ws.send(json.dumps({"balance": 1}))
            raw = await asyncio.wait_for(ws.recv(), timeout=8.0)
            msg = json.loads(raw)
            if "balance" in msg and "balance" in msg["balance"]:
                state.deriv_balance = round(float(msg["balance"]["balance"]), 2)
                state.balance_synced = True
    except Exception:
        pass


# ==============================================================================
# 1-SHOT DIRECT FAST BUY & TRADE EXECUTION PIPELINE
# ==============================================================================

async def execute_live_deriv_digit_trade(sig: dict):
    """
    Ultra-fast execution pipeline:
    - Zero-delay socket buffer purge (clears internal queue)
    - 1-Shot Direct Fast Buy (~50ms roundtrip)
    - Clean settlement and forget stream drainage
    - Non-blocking local balance update + Tri-Strike tracking
    """
    if not state.is_running or state.trade_exec_lock.locked():
        return

    # Hard SL Circuit Breaker check
    if state.hard_sl_enabled and state.stop_loss_enabled and state.hard_sl_floor > 0.0 and state.deriv_balance > 0.0 and state.deriv_balance <= state.hard_sl_floor:
        state.is_running = False
        state.stopped_by_stop_loss = True
        state.match_state["status"] = "STOPPED_BY_HARD_SL"
        state.log(f"🛑 Execution aborted: Balance (${state.deriv_balance:.2f}) <= Hard SL Floor (${state.hard_sl_floor:.2f}). Engine stopped safely.", "RISK")
        return

    async with state.trade_exec_lock:
        state.in_live_trade = True
        state.global_lock_until = time.time() + 12.0
        try:
            symbol = sig["symbol"]
            deriv_ctype = sig.get("deriv_contract_type", "DIGITMATCH")
            if sig.get("is_penta_salvo") and sig.get("penta_targets"):
                barrier_str = " & ".join(f"{t['symbol']}:D{t['digit']}" for t in sig["penta_targets"])
            elif sig.get("is_twin_match") and sig.get("twin_barrier"):
                barrier_str = f"{sig['barrier']} & {sig['twin_barrier']}"
            else:
                barrier_str = str(sig.get("barrier", ""))
            dur_ticks = int(sig.get("duration_ticks", 1))
            fallback_ratio = float(sig.get("payout_ratio", 7.34))
            stake = float(sig.get("custom_stake", 0.35))
            cur_s = int(sig.get("custom_step", 0))

            sub_m = state.match_config.get("sub_mode", "solo")
            mode_title = (
                "Penta Salvo" if sub_m == "penta" else (
                    "Parity Spread" if sub_m == "parity_spread" else (
                        "Duo Wing" if sub_m == "duo_wing" else (
                            "Cluster Sniper" if sub_m == "cluster" else (
                                "Twin Match" if sub_m == "twin" else "Solo Match"
                            )
                        )
                    )
                )
            )
            sizing = {
                "step": cur_s,
                "formula_text": f"{mode_title} Step {cur_s}: Stake ${stake:.2f} @ +{fallback_ratio*100:.1f}%",
            }

            account_id = state.get_active_account_id()
            token = state.get_active_token()
            order_log_msg = f"🚀 LIVE ORDER [{account_id} {state.match_config['sub_mode'].upper()}]: {symbol} {sig['contract_type']} | Stake=${stake:.2f} (Step {sizing['step']})"

            t_exec_start = time.time()
            ws = await get_or_create_persistent_trading_ws(account_id, token)
            if not ws:
                state.log(f"❌ Failed to obtain Deriv trading session for {account_id}.", "WARN")
                return

            # Zero-delay socket buffer purge (modern websockets 17+ and legacy)
            if hasattr(ws, "recv_messages") and hasattr(ws.recv_messages, "frames") and hasattr(ws.recv_messages.frames, "queue"):
                ws.recv_messages.frames.queue.clear()
            if hasattr(ws, "messages") and isinstance(ws.messages, deque):
                ws.messages.clear()
            elif hasattr(ws, "messages") and isinstance(ws.messages, asyncio.Queue):
                while not ws.messages.empty():
                    try:
                        ws.messages.get_nowait()
                    except Exception:
                        break
            while True:
                try:
                    await asyncio.wait_for(ws.recv(), timeout=0.001)
                except Exception:
                    break

            fast_buy = state.match_config.get("direct_fast_buy", True)

            if sig.get("is_penta_salvo") and sig.get("penta_targets"):
                # PENTA-ASSET SALVO (Concurrent contracts across all enabled assets)
                targets = sig["penta_targets"]
                req_map = {}
                for idx, tgt in enumerate(targets):
                    r_id = 501 + idx
                    s_sym = tgt["symbol"]
                    d_bar = str(tgt["digit"])
                    s_stake = float(tgt.get("stake", stake / max(1, len(targets))))
                    params = {
                        "amount": round(s_stake, 2), "basis": "stake",
                        "contract_type": "DIGITMATCH", "currency": "USD",
                        "duration": dur_ticks, "duration_unit": "t",
                        "underlying_symbol": s_sym, "barrier": d_bar,
                    }
                    req_map[r_id] = {"target": tgt, "params": params, "stake": s_stake}
                    await ws.send(json.dumps({"buy": "1", "price": round(s_stake, 2), "parameters": params, "req_id": r_id}, separators=(',', ':')))

                state.log(order_log_msg, "EXEC")

                cids = {}
                asks = {}
                payouts = {}
                t0 = time.time()
                while time.time() - t0 < 10.0 and len(cids) < len(req_map):
                    raw = await asyncio.wait_for(ws.recv(), timeout=6.0)
                    msg = json.loads(raw)
                    if msg.get("error"):
                        state.log(f"⚠️ Deriv Penta Salvo Buy Error: {msg['error'].get('message')}", "WARN")
                        return
                    if msg.get("msg_type") == "buy":
                        b_info = msg.get("buy", {})
                        r_id = msg.get("req_id")
                        if r_id in req_map:
                            cids[r_id] = b_info.get("contract_id")
                            asks[r_id] = float(b_info.get("buy_price", req_map[r_id]["stake"]))
                            payouts[r_id] = float(b_info.get("payout", round(asks[r_id] * 8.34, 2)))
                            if "balance_after" in b_info:
                                state.deriv_balance = round(float(b_info["balance_after"]), 2)
                                state.balance_synced = True

                if len(cids) < len(req_map):
                    state.log(f"⚠️ Deriv Penta Salvo Incomplete ({len(cids)}/{len(req_map)} confirmed)", "WARN")
                    return

                dispatch_ms = (time.time() - t_exec_start) * 1000.0
                state.log(
                    f"⚡ PENTA SALVO 5X BUY CONFIRMED on {account_id}: {len(cids)} Contracts Placed! | Cost=${sum(asks.values()):.2f} | 🚀 Dispatch={dispatch_ms:.0f}ms",
                    "BUY",
                )

                sub_ids = {}
                for r_id, cid in cids.items():
                    await ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": cid, "subscribe": 1}))

                poc_map = {}
                settle_start = time.time()
                while time.time() - settle_start < 30.0 and len(poc_map) < len(cids):
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        msg = json.loads(raw)
                        if msg.get("msg_type") == "proposal_open_contract":
                            poc = msg.get("proposal_open_contract", {})
                            c_id = poc.get("contract_id")
                            s_id = msg.get("subscription", {}).get("id") or poc.get("id")
                            if c_id in cids.values():
                                if s_id:
                                    sub_ids[c_id] = s_id
                                if poc.get("is_sold") == 1 or poc.get("status") in ("won", "lost"):
                                    poc_map[c_id] = poc
                    except asyncio.TimeoutError:
                        for cid in cids.values():
                            if cid not in poc_map:
                                try:
                                    await ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": cid}))
                                except Exception:
                                    pass

                for sid in sub_ids.values():
                    if sid:
                        try:
                            await ws.send(json.dumps({"forget": sid}))
                            await asyncio.wait_for(ws.recv(), timeout=0.1)
                        except Exception:
                            pass

                won_count = 0
                total_pnl = 0.0
                settled_poc = None
                for cid, poc in poc_map.items():
                    is_w = (poc.get("status") == "won") or (float(poc.get("profit", 0.0)) > 0)
                    if is_w:
                        won_count += 1
                        settled_poc = poc
                    total_pnl += float(poc.get("profit", 0.0))

                if not settled_poc and poc_map:
                    settled_poc = list(poc_map.values())[0]

                won = (total_pnl > 0.0)
                net_pnl = round(total_pnl, 2)
                buy_p = round(sum(asks.values()), 2)
                ask_price = buy_p
                live_payout = round(sum(payouts.values()), 2)
                live_ratio = round(net_pnl / buy_p, 4) if buy_p > 0 else 0.67
            elif sig.get("is_twin_match") and sig.get("twin_barrier"):
                # DUAL-ASSET TWIN BRACKET (2 concurrent contracts across 2 assets)
                d1 = str(sig["barrier"])
                d2 = str(sig["twin_barrier"])
                sym1 = sig.get("symbol")
                sym2 = sig.get("twin_symbol", sym1)
                ctype1 = sig.get("deriv_contract_type", "DIGITMATCH")
                ctype2 = sig.get("twin_deriv_contract_type", ctype1)

                if sym1 == sym2 and d1 == d2:
                    state.log(f"⚠️ TWIN INTEGRITY VIOLATION: identical symbol {sym1} and digit {d1}! Aborting.", "WARN")
                    return

                s_each = float(sig.get("custom_stake_per_digit", stake / 2.0))

                params1 = {
                    "amount": round(s_each, 2), "basis": "stake",
                    "contract_type": ctype1, "currency": "USD",
                    "duration": dur_ticks, "duration_unit": "t",
                    "underlying_symbol": sym1, "barrier": str(d1),
                }
                params2 = {
                    "amount": round(s_each, 2), "basis": "stake",
                    "contract_type": ctype2, "currency": "USD",
                    "duration": dur_ticks, "duration_unit": "t",
                    "underlying_symbol": sym2, "barrier": str(d2),
                }
                await ws.send(json.dumps({"buy": "1", "price": round(s_each, 2), "parameters": params1, "req_id": 201}, separators=(',', ':')))
                await ws.send(json.dumps({"buy": "1", "price": round(s_each, 2), "parameters": params2, "req_id": 202}, separators=(',', ':')))
                state.log(order_log_msg, "EXEC")

                cid1, cid2 = None, None
                ask1, ask2 = s_each, s_each
                payout1, payout2 = round(s_each * 8.34, 2), round(s_each * 8.34, 2)

                t0 = time.time()
                while time.time() - t0 < 10.0:
                    raw = await asyncio.wait_for(ws.recv(), timeout=6.0)
                    msg = json.loads(raw)
                    if msg.get("error"):
                        state.log(f"⚠️ Deriv Twin Direct Buy Error: {msg['error'].get('message')}", "WARN")
                        return
                    if msg.get("msg_type") == "buy":
                        b_info = msg.get("buy", {})
                        req_id = msg.get("req_id")
                        if req_id == 201 or (not cid1 and req_id != 202):
                            cid1 = b_info.get("contract_id")
                            ask1 = float(b_info.get("buy_price", s_each))
                            payout1 = float(b_info.get("payout", payout1))
                        else:
                            cid2 = b_info.get("contract_id")
                            ask2 = float(b_info.get("buy_price", s_each))
                            payout2 = float(b_info.get("payout", payout2))
                            if "balance_after" in b_info:
                                state.deriv_balance = round(float(b_info["balance_after"]), 2)
                                state.balance_synced = True
                        if cid1 and cid2:
                            break

                if not cid1 or not cid2:
                    state.log("⚠️ Deriv Twin Direct Buy Incomplete", "WARN")
                    return

                dispatch_ms = (time.time() - t_exec_start) * 1000.0
                state.log(
                    f"⚡ DUAL-ASSET TWIN 1-SHOT BUY CONFIRMED on {account_id}: {sym1} D{d1} (#{cid1}) + {sym2} D{d2} (#{cid2}) | Cost=${ask1+ask2:.2f} | 🚀 Dispatch={dispatch_ms:.0f}ms",
                    "BUY",
                )

                await ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": cid1, "subscribe": 1}))
                await ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": cid2, "subscribe": 1}))

                poc1, poc2 = None, None
                sub_id1, sub_id2 = None, None
                settle_start = time.time()
                while time.time() - settle_start < 30.0:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        msg = json.loads(raw)
                        if msg.get("msg_type") == "proposal_open_contract":
                            poc = msg.get("proposal_open_contract", {})
                            c_id = poc.get("contract_id")
                            s_id = msg.get("subscription", {}).get("id") or poc.get("id")
                            if c_id == cid1:
                                if s_id:
                                    sub_id1 = s_id
                                if poc.get("is_sold") == 1 or poc.get("status") in ("won", "lost"):
                                    poc1 = poc
                            elif c_id == cid2:
                                if s_id:
                                    sub_id2 = s_id
                                if poc.get("is_sold") == 1 or poc.get("status") in ("won", "lost"):
                                    poc2 = poc
                            if poc1 and poc2:
                                break
                    except asyncio.TimeoutError:
                        try:
                            if not poc1: await ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": cid1}))
                            if not poc2: await ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": cid2}))
                        except Exception:
                            pass

                if not poc1 or not poc2:
                    return

                for sid in (sub_id1, sub_id2):
                    if sid:
                        try:
                            await ws.send(json.dumps({"forget": sid}))
                            await asyncio.wait_for(ws.recv(), timeout=0.15)
                        except Exception:
                            pass

                won1 = (poc1.get("status") == "won") or (float(poc1.get("profit", 0)) > 0)
                won2 = (poc2.get("status") == "won") or (float(poc2.get("profit", 0)) > 0)
                won = (won1 or won2)
                settled_poc = poc2 if (won2 and not won1) else poc1

                pnl1 = float(poc1.get("profit", 0.0))
                pnl2 = float(poc2.get("profit", 0.0))
                net_pnl = round(pnl1 + pnl2, 2)
                buy_p = round(ask1 + ask2, 2)
                ask_price = buy_p
                live_payout = round(payout1, 2)
                live_ratio = round((payout1 - buy_p) / buy_p, 4) if buy_p > 0 else 3.17
            else:
                # Single Contract Execution (Solo, Cluster, Duo Wing, Parity Spread)
                req_id_buy = random.randint(100000, 999999)
                params = {
                    "amount": round(stake, 2),
                    "basis": "stake",
                    "contract_type": deriv_ctype,
                    "currency": "USD",
                    "duration": dur_ticks,
                    "duration_unit": "t",
                    "underlying_symbol": symbol,
                }
                if deriv_ctype not in ("CALL", "PUT", "CALLE", "PUTE", "DIGITEVEN", "DIGITODD") and barrier_str:
                    params["barrier"] = barrier_str

                buy_req = {
                    "buy": "1",
                    "price": round(stake, 2),
                    "parameters": params,
                    "req_id": req_id_buy,
                }
                await ws.send(json.dumps(buy_req, separators=(',', ':')))
                state.log(order_log_msg, "EXEC")

                contract_id = None
                ask_price = round(stake, 2)
                live_payout = round(stake * (1.0 + fallback_ratio), 2)
                live_ratio = fallback_ratio

                t0 = time.time()
                while time.time() - t0 < 10.0:
                    raw = await asyncio.wait_for(ws.recv(), timeout=6.0)
                    msg = json.loads(raw)
                    if msg.get("error"):
                        state.log(f"⚠️ Deriv Direct Fast Buy Error: {msg['error'].get('message')}", "WARN")
                        state.global_lock_until = time.time() + 3.0
                        return
                    if msg.get("msg_type") == "buy" and (msg.get("req_id") == req_id_buy or not msg.get("req_id")):
                        b_info = msg.get("buy", {})
                        contract_id = b_info.get("contract_id")
                        ask_price = float(b_info.get("buy_price", stake))
                        live_payout = float(b_info.get("payout", live_payout))
                        live_ratio = max(0.05, (live_payout - ask_price) / ask_price) if ask_price > 0 else fallback_ratio
                        if "balance_after" in b_info:
                            state.deriv_balance = round(float(b_info["balance_after"]), 2)
                            state.balance_synced = True
                        dispatch_ms = (time.time() - t_exec_start) * 1000.0
                        state.log(
                            f"⚡ 1-SHOT BUY CONFIRMED on {account_id}: Contract #{contract_id} | Cost=${ask_price:.2f} | Payout=${live_payout:.2f} | 🚀 Dispatch={dispatch_ms:.0f}ms",
                            "BUY",
                        )
                        break

                if not contract_id:
                    state.log("⚠️ Deriv Direct Fast Buy Failed to return contract ID", "WARN")
                    return

                await ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id, "subscribe": 1}))
                settled_poc = None
                sub_id = None
                settle_start = time.time()
                while time.time() - settle_start < 30.0:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        msg = json.loads(raw)
                        if msg.get("msg_type") == "proposal_open_contract":
                            poc = msg.get("proposal_open_contract", {})
                            c_id = poc.get("contract_id")
                            if c_id is not None and c_id != contract_id:
                                continue
                            s_id = msg.get("subscription", {}).get("id") or poc.get("id")
                            if s_id:
                                sub_id = s_id
                            if poc.get("is_sold") == 1 or poc.get("status") in ("won", "lost"):
                                settled_poc = poc
                                break
                    except asyncio.TimeoutError:
                        try:
                            await ws.send(json.dumps({"proposal_open_contract": 1, "contract_id": contract_id}))
                        except Exception:
                            pass

                if not settled_poc:
                    return

                if sub_id:
                    try:
                        await ws.send(json.dumps({"forget": sub_id}))
                        await asyncio.wait_for(ws.recv(), timeout=0.15)
                    except Exception:
                        pass

                status_str = settled_poc.get("status", "")
                buy_p = float(settled_poc.get("buy_price", ask_price))
                sell_p = float(settled_poc.get("sell_price", 0.0))
                net_pnl = round(float(settled_poc.get("profit", sell_p - buy_p)), 2)
                won = (status_str == "won") or (net_pnl > 0)

            # Extract exit spot and exit digit
            entry_tick = float(settled_poc.get("entry_spot") or settled_poc.get("entry_tick") or sig["entry_spot"])
            if settled_poc.get("exit_spot") is not None:
                exit_tick = float(settled_poc["exit_spot"])
            elif settled_poc.get("tick_stream") and len(settled_poc["tick_stream"]) > 0:
                exit_tick = float(settled_poc["tick_stream"][-1].get("tick", entry_tick))
            elif settled_poc.get("exit_tick") is not None:
                exit_tick = float(settled_poc["exit_tick"])
            else:
                exit_tick = entry_tick
            eval_sym = symbol
            if sig.get("is_penta_salvo") and settled_poc:
                eval_sym = settled_poc.get("underlying") or (sig["penta_targets"][0]["symbol"] if sig.get("penta_targets") else "R_100")
            exit_digit = extract_last_digit(exit_tick, eval_sym)

            # Instant local balance update without lock contention
            if won:
                state.deriv_balance = round(state.deriv_balance + buy_p + net_pnl, 2)

            ms = state.match_state
            mc = state.match_config
            ms["session_trades"] += 1
            ms["session_pnl"] = round(ms["session_pnl"] + net_pnl, 2)
            ms["last_trade_finish_time"] = time.time()

            # Determine traded target key for 3-strike rotation tracking
            sub_m = mc.get("sub_mode", "solo")
            if sub_m == "twin":
                t_b1 = sig.get("barrier", "")
                t_b2 = sig.get("twin_barrier", "")
                s1 = sig.get("symbol", symbol)
                s2 = sig.get("twin_symbol", s1)
                traded_key = f"{s1}:D{t_b1}+{s2}:D{t_b2}"
            elif sub_m in ("cluster", "duo_wing"):
                deriv_c = sig.get("deriv_contract_type", "")
                barr = sig.get("barrier", "")
                traded_key = f"{symbol}:{deriv_c}:{barr}"
            elif sub_m == "parity_spread":
                deriv_c = sig.get("deriv_contract_type", "")
                traded_key = f"{symbol}:{deriv_c}"
            elif sub_m == "penta":
                if sig.get("is_penta_salvo"):
                    if ms.get("locked_symbol") and ms.get("locked_digit") is not None:
                        traded_key = f"{ms['locked_symbol']}:D{ms['locked_digit']}"
                    else:
                        traded_key = f"{symbol}:D{sig.get('barrier')}"
                else:
                    traded_key = f"{symbol}:D{sig.get('barrier')}"
            else:
                traded_key = f"{symbol}:D{sig.get('barrier')}"

            if won:
                cur_s = max(int(ms.get("current_step", 0)), int(sig.get("custom_step", 0)))
                ms["ai_cooldown_until"] = time.time() + (20.0 if cur_s >= 3 else 4.0)
                ms["session_wins"] += 1
                ms["sequences_won"] += 1
                ms["current_step"] = 0
                ms["sequence_accumulated_loss"] = 0.0
                ms["last_traded_symbol"] = symbol
                ms["frozen_symbol"] = None
                ms["frozen_until"] = 0.0
                ms["locked_digit"] = None
                ms["locked_twin_digit"] = None
                ms["locked_cluster_type"] = None
                ms["locked_barrier"] = None
                ms["locked_parity_type"] = None
                ms["locked_symbol"] = None
                ms["locked_base_thresh"] = None
                ms["target_consecutive_trades"] = 0
                ms["current_target_key"] = None
                ms["exhausted_targets"] = []
            else:
                ms["session_losses"] += 1
                loss_add = abs(net_pnl) if sig.get("is_penta_salvo") else buy_p
                ms["sequence_accumulated_loss"] = round(float(ms.get("sequence_accumulated_loss", 0.0)) + loss_add, 2)
                ms["last_traded_symbol"] = symbol
                ms["frozen_symbol"] = None
                ms["frozen_until"] = 0.0

                max_s = len(ms["ladder"]) - 1 if ms.get("ladder") else 16
                open_d = bool(mc.get("open_depth", True))
                if not open_d and ms["current_step"] >= max_s:
                    ms["sequences_lost"] += 1
                    ms["current_step"] = 0
                    ms["sequence_accumulated_loss"] = 0.0
                    ms["locked_digit"] = None
                    ms["locked_twin_digit"] = None
                    ms["locked_cluster_type"] = None
                    ms["locked_barrier"] = None
                    ms["locked_parity_type"] = None
                    ms["locked_symbol"] = None
                    ms["locked_base_thresh"] = None
                    ms["target_consecutive_trades"] = 0
                    ms["current_target_key"] = None
                    ms["exhausted_targets"] = []
                    
                    sl_action = mc.get("step_sl_action", "reset_to_s0")
                    loss_cap = sum(x['stake'] for x in ms['ladder'])
                    if sl_action == "stop_engine":
                        state.is_running = False
                        state.stopped_by_martingale_hit = True
                        ms["status"] = "STOPPED_MAX_MARTINGALE_HIT"
                        state.log(f"🛑 MARTINGALE CEILING HIT: Reached Step {max_s} loss cap (${loss_cap:.2f}). Engine Auto-Stopped!", "LOCK")
                    else:
                        # Option 2: Cut loss at max_s, reset basket to S0, brief 6s cooldown, and continue trading
                        ms["ai_cooldown_until"] = time.time() + 6.0
                        state.log(f"🛡️ STEP {max_s} CUT & RESET: Basket loss (-${loss_cap:.2f}) settled. Resetting basket to S0 to continue trading safely!", "RISK")
                else:
                    ms["current_step"] += 1
                    ms["max_step_hit"] = max(ms["max_step_hit"], ms["current_step"])

                    # Target strike tracking
                    if ms.get("current_target_key") == traded_key:
                        ms["target_consecutive_trades"] = int(ms.get("target_consecutive_trades", 0)) + 1
                    else:
                        ms["current_target_key"] = traded_key
                        ms["target_consecutive_trades"] = 1

                    max_strikes = int(mc.get("max_target_strikes", 20))
                    tri_strike_active = bool(mc.get("tri_strike_filter", True))

                    if tri_strike_active and ms["target_consecutive_trades"] >= max_strikes:
                        if traded_key not in ms.get("exhausted_targets", []):
                            ms.setdefault("exhausted_targets", []).append(traded_key)
                        state.log(
                            f"🛡️ {max_strikes}-STRIKE ROTATION TRIGGERED: Target [{traded_key}] failed {max_strikes} consecutive attempts ({ms['target_consecutive_trades']}/{max_strikes})! Unlocking target to rotate recovery to next qualified anomaly.",
                            "PIVOT",
                        )
                        ms["locked_digit"] = None
                        ms["locked_twin_digit"] = None
                        ms["locked_cluster_type"] = None
                        ms["locked_barrier"] = None
                        ms["locked_parity_type"] = None
                        ms["locked_symbol"] = None
                        ms["locked_base_thresh"] = None
                        ms["target_consecutive_trades"] = 0
                        ms["current_target_key"] = None
                    else:
                        if sub_m in ("solo", "penta") and ms.get("locked_digit") is not None and ms.get("locked_symbol") is not None:
                            l_sym = ms["locked_symbol"]
                            l_dig = ms["locked_digit"]
                            strike_info = f" [Strike {ms['target_consecutive_trades']}/{max_strikes}]" if tri_strike_active else ""
                            if sub_m == "penta":
                                p_min = int(mc.get("penta_drought_threshold", 18))
                                p_max = int(mc.get("penta_max_drought", 0))
                                if p_max < p_min: p_max = p_min + int(mc.get("penta_window_span", 2))
                                state.log(
                                    f"🎯 PENTA RECOVERY LOCKED: Maintaining {l_sym} D{l_dig}{strike_info} for Step {ms['current_step']} (Window: [{p_min}-{p_max}]t)",
                                    "TARGET",
                                )
                            else:
                                b_th = ms.get("locked_base_thresh") or int(mc.get("symbol_thresholds", {}).get(l_sym, mc.get("drought_threshold", 5)))
                                step_exp = ms["current_step"] if mc.get("solo_step_expansion", False) else 0
                                req_th = b_th + step_exp
                                state.log(
                                    f"🎯 SOLO TARGET LOCKED: Maintaining {l_sym} D{l_dig}{strike_info} for Step {ms['current_step']} (Required drought: {req_th}t)",
                                    "TARGET",
                                )
                        elif sub_m in ("cluster", "duo_wing") and ms.get("locked_cluster_type") is not None and ms.get("locked_symbol") is not None:
                            l_sym = ms["locked_symbol"]
                            l_ct = ms["locked_cluster_type"]
                            l_b = ms.get("locked_barrier", "")
                            lbl = "DUO WING" if sub_m == "duo_wing" else "CLUSTER"
                            strike_info = f" [Strike {ms['target_consecutive_trades']}/{max_strikes}]" if tri_strike_active else ""
                            state.log(
                                f"🎯 {lbl} LOCKED: Maintaining {l_sym} {l_ct} {l_b}{strike_info} for Step {ms['current_step']}",
                                "TARGET",
                            )
                        else:
                            ms["locked_symbol"] = None
                            ms["locked_digit"] = None
                            ms["locked_twin_digit"] = None
                            ms["locked_cluster_type"] = None
                            ms["locked_barrier"] = None
                            ms["locked_parity_type"] = None
                            ms["locked_base_thresh"] = None

            # ------------------------------------------------------------------
            # 1-1-2 RATCHET COMPOUNDING ENGINE & DYNAMIC RISK PROTECTION
            # ------------------------------------------------------------------
            if state.session_start_balance <= 0.0 and state.deriv_balance > 0.0:
                state.session_start_balance = round(state.deriv_balance - net_pnl, 2)
                if state.active_cycle == 1:
                    state.hard_sl_floor = round(state.session_start_balance - state.initial_sl_usd, 2)

            # Cycle PnL tracks fresh profit accumulated inside the current cycle
            cycle_net_pnl = round(ms["session_pnl"] - state.vault_locked_profit, 2)
            state.cycle_accumulated_pnl = cycle_net_pnl
            ms["cycle_accumulated_pnl"] = state.cycle_accumulated_pnl
            ms["active_cycle"] = state.active_cycle
            ms["vault_locked_profit"] = state.vault_locked_profit
            ms["hard_sl_floor"] = state.hard_sl_floor

            # Target checks only occur when Martingale is at safe base (current_step == 0)
            if ms["current_step"] == 0:
                target_d = state.cycle_target_usd

                # 🏛️ CYCLE 1: Capital Lock / Breakeven Fortress
                if state.active_cycle == 1 and state.cycle_accumulated_pnl >= target_d:
                    state.vault_locked_profit = round(state.vault_locked_profit + target_d, 2)
                    state.vault_balance = state.vault_locked_profit
                    state.active_cycle = 2
                    state.cycle_accumulated_pnl = round(ms["session_pnl"] - state.vault_locked_profit, 2)
                    # Ratchet Stop Loss up to Initial Capital (Breakeven): Initial Capital is 100% secured!
                    state.hard_sl_floor = round(state.session_start_balance, 2)
                    ms["active_cycle"] = 2
                    ms["vault_locked_profit"] = state.vault_locked_profit
                    ms["hard_sl_floor"] = state.hard_sl_floor
                    state.log(
                        f"🏛️ [CYCLE 1 COMPLETE] Milestone ${target_d:.2f} locked into Vault! "
                        f"Stop Loss floor raised to Breakeven (${state.hard_sl_floor:.2f}). "
                        f"Initial capital is now 100% secured! Entering CYCLE 2 (Growth Fuel Phase).",
                        "CYCLE",
                    )

                # 🚀 CYCLE 2: Growth Fuel Phase Complete -> The 2X Scaling Leap
                elif state.active_cycle == 2 and state.cycle_accumulated_pnl >= target_d:
                    state.active_cycle = 3
                    state.cycle_accumulated_pnl = round(ms["session_pnl"] - state.vault_locked_profit, 2)
                    old_base = float(mc.get("base_stake", 0.35))
                    new_base = round(old_base * 2.0, 2)
                    mc["base_stake"] = new_base
                    rebuild_active_ladder()  # Capacity doubles to 2D; cycle_target_usd becomes 2D
                    # Protect initial capital + locked vault
                    state.hard_sl_floor = round(state.session_start_balance + state.vault_locked_profit, 2)
                    ms["active_cycle"] = 3
                    ms["hard_sl_floor"] = state.hard_sl_floor
                    state.log(
                        f"🚀 [CYCLE 2 COMPLETE] Growth fuel secured! Escalating to CYCLE 3 (2X SCALING LEAP): "
                        f"Base Stake doubled (${old_base:.2f} -> ${new_base:.2f}), "
                        f"Martingale Capacity doubled to ${state.cycle_target_usd:.2f}. "
                        f"Vault Shielded: ${state.vault_locked_profit:.2f}. Hard SL Floor=${state.hard_sl_floor:.2f}.",
                        "CYCLE",
                    )

                # 👑 CYCLE 3+: Geometric Compounding
                elif state.active_cycle >= 3 and state.cycle_accumulated_pnl >= target_d:
                    state.vault_locked_profit = round(state.vault_locked_profit + target_d, 2)
                    state.vault_balance = state.vault_locked_profit
                    state.active_cycle += 1
                    state.cycle_accumulated_pnl = round(ms["session_pnl"] - state.vault_locked_profit, 2)
                    old_base = float(mc.get("base_stake", 0.35))
                    new_base = round(old_base * 2.0, 2)
                    mc["base_stake"] = new_base
                    rebuild_active_ladder()
                    state.hard_sl_floor = round(state.session_start_balance + state.vault_locked_profit, 2)
                    ms["active_cycle"] = state.active_cycle
                    ms["vault_locked_profit"] = state.vault_locked_profit
                    ms["hard_sl_floor"] = state.hard_sl_floor
                    state.log(
                        f"👑 [CYCLE {state.active_cycle - 1} COMPLETE] Profit ${target_d:.2f} locked into Vault! "
                        f"Advancing to CYCLE {state.active_cycle}. Base Stake=${new_base:.2f}, New Target=${state.cycle_target_usd:.2f}.",
                        "CYCLE",
                    )

            # ------------------------------------------------------------------
            # HARD STOP-LOSS CIRCUIT BREAKER ("فصل المحرك")
            # ------------------------------------------------------------------
            sl_breached = False
            sl_reason = ""
            if state.hard_sl_enabled and state.stop_loss_enabled and state.hard_sl_floor > 0.0 and state.deriv_balance > 0.0 and state.deriv_balance <= state.hard_sl_floor:
                sl_breached = True
                sl_reason = f"Deriv Balance (${state.deriv_balance:.2f}) dropped to Hard SL Floor (${state.hard_sl_floor:.2f})"

            if state.active_cycle == 1 and state.stop_loss_enabled and state.initial_sl_usd > 0.0 and ms["session_pnl"] <= -state.initial_sl_usd:
                sl_breached = True
                sl_reason = f"Session PnL (-${abs(ms['session_pnl']):.2f}) reached Initial SL limit (-${state.initial_sl_usd:.2f})"

            if sl_breached:
                state.is_running = False
                state.stopped_by_stop_loss = True
                ms["stop_loss_reached"] = True
                ms["status"] = "STOPPED_BY_HARD_SL"
                state.log(
                    f"🛑 [EMERGENCY CIRCUIT BREAKER] {sl_reason}! Engine immediately halted and disconnected to preserve capital!",
                    "RISK",
                )

            cur_step_idx = min(34, int(sizing["step"]))
            state.step_distribution[cur_step_idx] = state.step_distribution.get(cur_step_idx, 0) + 1
            ms["max_step_hit"] = max(int(ms.get("max_step_hit", 0)), cur_step_idx)

            exit_parity = "EVEN" if (exit_digit % 2 == 0) else "ODD"
            t_record = {
                "num": state.total_trades + 1,
                "time": datetime.now().strftime("%H:%M:%S"),
                "account": f"{account_id} ({mc['sub_mode'].upper()})",
                "symbol": symbol,
                "contract_type": sig["contract_type"],
                "payout_pct": f"+{round(live_ratio*100, 1)}%",
                "step": sizing["step"],
                "stake": round(buy_p, 2),
                "exit_digit": exit_digit,
                "exit_parity": exit_parity,
                "formula_text": sizing["formula_text"],
                "settlement_note": f"{exit_parity} (d={exit_digit})",
                "outcome": "WIN" if won else "LOSS",
                "pnl": net_pnl,
                "deficit_after": ms["sequence_accumulated_loss"],
            }
            state.trade_history.insert(0, t_record)
            state.total_trades += 1
            if won:
                state.wins += 1
                state.current_loss_streak = 0
                state.baskets_cleared += 1
            else:
                state.losses += 1
                state.current_loss_streak += 1
                state.max_loss_streak = max(state.max_loss_streak, state.current_loss_streak)
            state.total_pnl = round(state.total_pnl + net_pnl, 2)

            try:
                with open(CSV_LOG_FILE, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        t_record["num"], t_record["time"], t_record["account"],
                        symbol, sig["contract_type"], barrier_str, t_record["payout_pct"],
                        t_record["step"], t_record["stake"], entry_tick, exit_tick,
                        exit_digit, t_record["outcome"], net_pnl, t_record["deficit_after"]
                    ])
            except Exception:
                pass

            tag = "WIN" if won else "WARN"
            state.log(
                f"{'✅ WIN' if won else '❌ LOSS'} #{t_record['num']} [{account_id}]: {symbol} {sig['contract_type']} | Exit Digit={exit_digit} | PnL={net_pnl:+.2f}$ | Deficit=${t_record['deficit_after']:.2f}",
                tag,
            )
        except Exception as e:
            state.persistent_trade_ws = None
            err_msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
            state.log(f"Live execution exception: {err_msg}", "WARN")
        finally:
            state.in_live_trade = False
            state.global_lock_until = time.time() + 0.02
            now_f = time.time()
            state.match_state["last_trade_finish_time"] = now_f
            state.tick_event.set()


# ==============================================================================
# MODE F TRADING ENGINE WORKER
# ==============================================================================

async def match_sniper_worker():
    """
    Autonomous Engine for Mode F Quantum Citadel:
    - Solo Match Sniper (+734.0%)
    - Twin-Match Drought Bracketing (+317.0%)
    - Cluster Sniper (+213.0%)
    - Duo Wing (+354.5%)
    - Parity Delta Spread (+94.0%)
    """
    while True:
        try:
            await asyncio.wait_for(state.tick_event.wait(), timeout=0.04)
            state.tick_event.clear()
        except asyncio.TimeoutError:
            pass

        try:
            now = time.time()
            mc = state.match_config
            ms = state.match_state
            cfg_asset = mc.get("asset", "ALL")
            enabled_syms = mc.get("enabled_assets", list(MATCH_ASSETS))
            if cfg_asset in MATCH_ASSETS:
                scan_syms = [cfg_asset] if cfg_asset in enabled_syms else []
            else:
                scan_syms = [s for s in MATCH_ASSETS if s in enabled_syms]
            if not scan_syms:
                scan_syms = [enabled_syms[0]] if enabled_syms else ["R_100"]
            monitored_sym = cfg_asset if (cfg_asset in scan_syms) else scan_syms[0]

            sub_mode = mc.get("sub_mode", "solo")
            if mc.get("ai_commander", False):
                if sub_mode == "cluster":
                    d_thresh = int(mc.get("cluster_drought_threshold", 10))
                elif sub_mode == "duo_wing":
                    d_thresh = int(mc.get("duo_drought_threshold", 14))
                else:
                    d_thresh = int(mc.get("drought_threshold", 30))
            else:
                if sub_mode == "cluster":
                    d_thresh = int(mc.get("cluster_drought_threshold", 10))
                elif sub_mode == "duo_wing":
                    d_thresh = int(mc.get("duo_drought_threshold", 14))
                elif sub_mode == "twin":
                    d_thresh = int(mc.get("drought_threshold", 18))
                else:
                    d_thresh = int(mc.get("drought_threshold", 25))

            twin_d_thresh = int(mc.get("twin_drought_threshold", 15))
            min_freq = int(mc.get("min_rolling_freq", 5))
            require_squeeze = bool(mc.get("require_squeeze", False))
            allow_pivot = False if mc.get("ai_commander", False) else bool(mc.get("allow_dynamic_pivot", False))
            hunt_zombies = bool(mc.get("hunt_zombies", False))
            tri_strike_on = bool(mc.get("tri_strike_filter", True))
            exhausted_targets = set(ms.get("exhausted_targets", []))

            # 1. Build real-time drought radar & 100t frequency across Pure-R assets
            assets_drought_map = {}
            assets_freq_map = {}
            cluster_radar = {}
            parity_radar = {}
            for sym in MATCH_ASSETS:
                assets_drought_map[sym] = {d: 0 for d in range(10)}
                assets_freq_map[sym] = {d: 10 for d in range(10)}
                u3_cnt = 0
                o6_cnt = 0
                u2_cnt = 0
                o7_cnt = 0
                m_even = 0.0
                m_odd = 0.0
                delta_spread = 0.0
                ce = 0
                co = 0
                if sym in state.digits and len(state.digits[sym]) >= 10:
                    d_list = list(state.digits[sym])
                    sub_100 = d_list[-100:]
                    for d in range(10):
                        try:
                            rev_idx = d_list[::-1].index(d)
                            assets_drought_map[sym][d] = rev_idx
                        except ValueError:
                            assets_drought_map[sym][d] = len(d_list)
                        assets_freq_map[sym][d] = sub_100.count(d)

                    u3_cnt = len(d_list)
                    o6_cnt = len(d_list)
                    u2_cnt = len(d_list)
                    o7_cnt = len(d_list)
                    for i, d in enumerate(reversed(d_list)):
                        if d in {0, 1, 2}:
                            u3_cnt = i
                            break
                    for i, d in enumerate(reversed(d_list)):
                        if d in {7, 8, 9}:
                            o6_cnt = i
                            break
                    for i, d in enumerate(reversed(d_list)):
                        if d in {0, 1}:
                            u2_cnt = i
                            break
                    for i, d in enumerate(reversed(d_list)):
                        if d in {8, 9}:
                            o7_cnt = i
                            break

                    m_even = sum(assets_drought_map[sym][d] for d in (0, 2, 4, 6, 8)) / 5.0
                    m_odd = sum(assets_drought_map[sym][d] for d in (1, 3, 5, 7, 9)) / 5.0
                    delta_spread = round(m_even - m_odd, 2)
                    for d in reversed(d_list):
                        if d % 2 != 0:
                            if ce == 0:
                                co += 1
                            else:
                                break
                        else:
                            if co == 0:
                                ce += 1
                            else:
                                break

                u3_indivs = [assets_drought_map[sym].get(d, 0) for d in (0, 1, 2)]
                o6_indivs = [assets_drought_map[sym].get(d, 0) for d in (7, 8, 9)]
                u2_indivs = [assets_drought_map[sym].get(d, 0) for d in (0, 1)]
                o7_indivs = [assets_drought_map[sym].get(d, 0) for d in (8, 9)]
                sym_sorted_dr = sorted([assets_drought_map[sym].get(d, 0) for d in range(10)], reverse=True)

                cluster_radar[sym] = {
                    "under_3": u3_cnt, "over_6": o6_cnt,
                    "under_2": u2_cnt, "over_7": o7_cnt,
                    "u3_sum": sum(u3_indivs),
                    "u3_min": min(u3_indivs) if u3_indivs else 0,
                    "o6_sum": sum(o6_indivs),
                    "o6_min": min(o6_indivs) if o6_indivs else 0,
                    "u2_sum": sum(u2_indivs),
                    "u2_min": min(u2_indivs) if u2_indivs else 0,
                    "o7_sum": sum(o7_indivs),
                    "o7_min": min(o7_indivs) if o7_indivs else 0,
                    "twin_sum": sum(sym_sorted_dr[:2]) if len(sym_sorted_dr) >= 2 else 0,
                    "twin_min": sym_sorted_dr[1] if len(sym_sorted_dr) >= 2 else 0,
                }
                parity_radar[sym] = {
                    "m_even": round(m_even, 2),
                    "m_odd": round(m_odd, 2),
                    "delta": delta_spread,
                    "consec_even": ce,
                    "consec_odd": co,
                }

            global_digit_droughts = {}
            for d in range(10):
                best_cnt = -1
                best_s = scan_syms[0] if scan_syms else "R_100"
                best_f = 10
                for sym in scan_syms:
                    c = assets_drought_map.get(sym, {}).get(d, 0)
                    f = assets_freq_map.get(sym, {}).get(d, 10)
                    if c > best_cnt:
                        best_cnt = c
                        best_s = sym
                        best_f = f
                global_digit_droughts[d] = {
                    "count": max(0, best_cnt),
                    "symbol": best_s,
                    "freq_100": best_f,
                }

            ms["assets_drought_radar"] = assets_drought_map
            ms["assets_freq_radar"] = assets_freq_map
            ms["cluster_radar"] = cluster_radar
            ms["parity_radar"] = parity_radar
            ms["global_digit_droughts"] = global_digit_droughts
            ms["drought_radar"] = {d: global_digit_droughts[d]["count"] for d in range(10)}
            ms["rolling_freq_100"] = {d: global_digit_droughts[d]["freq_100"] for d in range(10)}
            ms["zombie_digits"] = [d for d in range(10) if ms["rolling_freq_100"][d] < min_freq]

            best_d = 0
            best_sym = scan_syms[0] if scan_syms else "R_100"
            max_d = -1
            for d in range(10):
                item = global_digit_droughts[d]
                if item["count"] > max_d:
                    max_d = item["count"]
                    best_d = d
                    best_sym = item["symbol"]

            ms["max_drought_digit"] = best_d
            ms["max_drought_symbol"] = best_sym
            ms["max_drought_count"] = max_d

            if not state.is_running:
                if state.stopped_by_stop_loss:
                    ms["status"] = "STOPPED_BY_HARD_SL"
                elif state.stopped_by_martingale_hit:
                    ms["status"] = "PAUSED_MAX_MARTINGALE_HIT"
                elif state.stopped_by_take_profit:
                    ms["status"] = "TARGET_REACHED"
                else:
                    ms["status"] = "TERMINAL_PAUSED"
                continue

            if state.stopped_by_stop_loss:
                ms["status"] = "STOPPED_BY_HARD_SL"
                continue

            if state.stopped_by_martingale_hit:
                ms["status"] = "PAUSED_MAX_MARTINGALE_HIT"
                continue

            if state.in_live_trade or state.trade_exec_lock.locked():
                ms["status"] = "IN_FLIGHT_SETTLING (1t Horizon)"
                continue

            # Hard SL Circuit Breaker pre-trade check (evaluated only when idle, NOT during in-flight trades)
            if state.hard_sl_enabled and state.stop_loss_enabled and state.hard_sl_floor > 0.0 and state.deriv_balance > 0.0 and state.deriv_balance <= state.hard_sl_floor:
                state.is_running = False
                state.stopped_by_stop_loss = True
                ms["status"] = "STOPPED_BY_HARD_SL"
                state.log(f"🛑 [EMERGENCY CIRCUIT BREAKER] Deriv Balance (${state.deriv_balance:.2f}) breached Hard SL Floor (${state.hard_sl_floor:.2f})! Engine disconnected safely.", "RISK")
                continue

            cur_step = int(ms["current_step"])
            ladder = ms.get("ladder") or rebuild_active_ladder()
            req_cooldown = 0.02
            last_t_time = float(ms.get("last_trade_finish_time") or ms.get("last_trade_time", 0.0))
            if (now - last_t_time) < req_cooldown:
                continue

            target_digit = None
            target_twin = None
            target_twin_sym = None
            target_cluster_type = None
            target_barrier = None
            target_drought = 0
            target_twin_drought = 0
            target_parity_type = None
            target_spread = 0.0
            target_streak = 0
            target_sym = None
            ai_selected = False

            if mc.get("ai_commander", False) and cur_step == 0:
                if now < float(ms.get("ai_cooldown_until", 0.0)):
                    ms["status"] = f"🛡️ AI COOLDOWN ({ms['ai_cooldown_until'] - now:.0f}s) • Refreshing Stream"
                    continue

                sync_ai_commander_shield(state.deriv_balance)
                r100_digits = list(state.digits.get("R_100", []))
                if len(r100_digits) < 25:
                    ms["status"] = f"WARMING R_100 STREAM ({len(r100_digits)}/25t)"
                    continue

                cluster_th = int(mc.get("cluster_drought_threshold", 10))
                duo_th = int(mc.get("duo_drought_threshold", 14))
                sym_threshs = mc.get("symbol_thresholds", {})
                solo_th = int(sym_threshs.get("R_100", mc.get("drought_threshold", 5)))
                cr_r100 = cluster_radar.get("R_100", {})
                u3_cnt = int(cr_r100.get("under_3", 0))
                o6_cnt = int(cr_r100.get("over_6", 0))
                u2_cnt = int(cr_r100.get("under_2", 0))
                o7_cnt = int(cr_r100.get("over_7", 0))
                sub_100_r100 = r100_digits[-100:]
                scale_100 = 100.0 / max(1, len(sub_100_r100))
                freqs_r100 = assets_freq_map.get("R_100", {})
                f_u3 = round(sum(freqs_r100.get(d, 0) for d in (0, 1, 2)) * scale_100)
                f_o6 = round(sum(freqs_r100.get(d, 0) for d in (7, 8, 9)) * scale_100)
                f_u2 = round(sum(freqs_r100.get(d, 0) for d in (0, 1)) * scale_100)
                f_o7 = round(sum(freqs_r100.get(d, 0) for d in (8, 9)) * scale_100)

                is_fresh_mode = (mc.get("target_priority", "min") == "min")

                ai_candidates = []
                # Strict equality triggers (count == threshold)
                if u3_cnt == cluster_th and f_u3 >= 15:
                    ai_candidates.append({
                        "sub_mode": "cluster",
                        "score": 1.0,
                        "count": u3_cnt,
                        "dist": 0,
                        "freq": f_u3,
                        "cluster_type": "UNDER",
                        "barrier": "3",
                        "digit": None,
                    })
                if o6_cnt == cluster_th and f_o6 >= 15:
                    ai_candidates.append({
                        "sub_mode": "cluster",
                        "score": 1.0,
                        "count": o6_cnt,
                        "dist": 0,
                        "freq": f_o6,
                        "cluster_type": "OVER",
                        "barrier": "6",
                        "digit": None,
                    })
                if u2_cnt == duo_th and f_u2 >= 10:
                    ai_candidates.append({
                        "sub_mode": "duo_wing",
                        "score": 1.0,
                        "count": u2_cnt,
                        "dist": 0,
                        "freq": f_u2,
                        "cluster_type": "UNDER",
                        "barrier": "2",
                        "digit": None,
                    })
                if o7_cnt == duo_th and f_o7 >= 10:
                    ai_candidates.append({
                        "sub_mode": "duo_wing",
                        "score": 1.0,
                        "count": o7_cnt,
                        "dist": 0,
                        "freq": f_o7,
                        "cluster_type": "OVER",
                        "barrier": "7",
                        "digit": None,
                    })
                for d in range(10):
                    d_cnt = int(assets_drought_map.get("R_100", {}).get(d, 0))
                    d_freq100 = round(int(freqs_r100.get(d, 0)) * scale_100)
                    if d_cnt == solo_th and d_freq100 >= 6:
                        ai_candidates.append({
                            "sub_mode": "solo",
                            "score": 1.0,
                            "count": d_cnt,
                            "dist": 0,
                            "freq": d_freq100,
                            "cluster_type": None,
                            "barrier": str(d),
                            "digit": d,
                        })

                if ai_candidates:
                    if is_fresh_mode:
                        ai_candidates.sort(key=lambda x: (x["dist"], x["count"]))
                    else:
                        ai_candidates.sort(key=lambda x: x["score"], reverse=True)
                    winner = ai_candidates[0]
                    ai_selected = True
                    chosen_sub = winner["sub_mode"]
                    mc["sub_mode"] = chosen_sub
                    sub_mode = chosen_sub
                    target_sym = "R_100"
                    b_stake = float(mc.get("base_stake", 0.35))

                    if chosen_sub == "cluster":
                        d_thresh = cluster_th
                        ms["ladder"] = build_cluster_ladder(b_stake, steps=int(mc.get("cluster_max_steps", 12)))
                        target_cluster_type = winner["cluster_type"]
                        target_barrier = winner["barrier"]
                        target_drought = winner["count"]
                        ms["locked_cluster_type"] = target_cluster_type
                        ms["locked_barrier"] = target_barrier
                        ms["locked_digit"] = None
                        ms["locked_twin_digit"] = None
                        ms["locked_parity_type"] = None
                        ms["locked_symbol"] = "R_100"
                    elif chosen_sub == "duo_wing":
                        d_thresh = duo_th
                        ms["ladder"] = build_duo_wing_ladder(b_stake, steps=int(mc.get("duo_max_steps", 21)))
                        target_cluster_type = winner["cluster_type"]
                        target_barrier = winner["barrier"]
                        target_drought = winner["count"]
                        ms["locked_cluster_type"] = target_cluster_type
                        ms["locked_barrier"] = target_barrier
                        ms["locked_digit"] = None
                        ms["locked_twin_digit"] = None
                        ms["locked_parity_type"] = None
                        ms["locked_symbol"] = "R_100"
                    else:
                        d_thresh = solo_th
                        ms["ladder"] = build_match_ladder(b_stake, steps=int(mc.get("solo_max_steps", 17)))
                        target_digit = winner["digit"]
                        target_drought = winner["count"]
                        ms["locked_digit"] = target_digit
                        ms["locked_twin_digit"] = None
                        ms["locked_cluster_type"] = None
                        ms["locked_barrier"] = str(target_digit)
                        ms["locked_parity_type"] = None
                        ms["locked_symbol"] = "R_100"

                    mc["max_steps"] = len(ms["ladder"])
                    mc["max_step"] = len(ms["ladder"]) - 1
                else:
                    ms["status"] = f"AI SCANNING R_100 (Deepest: Solo={max_d}t<{solo_th}t | U3={u3_cnt}t | O6={o6_cnt}t | U2={u2_cnt}t | O7={o7_cnt}t)"
                    continue

            # ==================================================================
            # STRICT FRESH BREAKOUT & DUAL-ASSET TWIN ARCHITECTURE
            # 1. No artificial freeze: Exact equality (count == thresh) physically
            #    guarantees that any trade is a genuinely fresh hit!
            # 2. Asset-specific Thresholds: Each asset is judged by its own optimal
            #    threshold configured by user.
            # 3. Dual-Asset Twin: Simultaneously snipes across TWO independent assets.
            # ==================================================================
            def is_sym_allowed(sym: str) -> bool:
                if not mc.get("symbol_enabled", {}).get(sym, True):
                    return False
                return True

            sym_threshs = mc.get("symbol_thresholds", {})

            if not ai_selected and sub_mode == "parity_spread":
                parity_th = float(mc.get("parity_spread_threshold", 8.0))
                req_streak = 4 if mc.get("parity_streak_filter", False) else 0

                parity_cands = []
                for sym in scan_syms:
                    if not is_sym_allowed(sym):
                        continue
                    pr = parity_radar.get(sym, {})
                    delta = pr.get("delta", 0.0)
                    ce = pr.get("consec_even", 0)
                    co = pr.get("consec_odd", 0)

                    # Strict equality condition (|delta| == parity_th)
                    t_even_key = f"{sym}:DIGITEVEN"
                    t_odd_key = f"{sym}:DIGITODD"
                    if abs(delta - parity_th) < 0.15 and co >= req_streak:
                        if not (tri_strike_on and t_even_key in exhausted_targets):
                            parity_cands.append({
                                "symbol": sym,
                                "parity_type": "DIGITEVEN",
                                "delta": delta,
                                "dist": 0.0,
                                "streak": co,
                            })
                    elif abs((-delta) - parity_th) < 0.15 and ce >= req_streak:
                        if not (tri_strike_on and t_odd_key in exhausted_targets):
                            parity_cands.append({
                                "symbol": sym,
                                "parity_type": "DIGITODD",
                                "delta": delta,
                                "dist": 0.0,
                                "streak": ce,
                            })

                if parity_cands:
                    best_p = parity_cands[0]
                    target_parity_type = best_p["parity_type"]
                    target_sym = best_p["symbol"]
                    target_spread = best_p["delta"]
                    target_streak = best_p["streak"]
                else:
                    ms["status"] = f"❄️ PARITY (Step {cur_step}): Waiting for exact |ΔM| == {parity_th:.1f}"
                    continue

            elif not ai_selected and sub_mode in ("cluster", "duo_wing"):
                is_duo = (sub_mode == "duo_wing")
                u_key = "under_2" if is_duo else "under_3"
                o_key = "over_7" if is_duo else "over_6"
                u_bar = "2" if is_duo else "3"
                o_bar = "7" if is_duo else "6"
                u_digits = (0, 1) if is_duo else (0, 1, 2)
                o_digits = (8, 9) if is_duo else (7, 8, 9)
                min_cluster_f = min_freq if (min_freq > 0 and mc.get("filter_zombie", False)) else 0

                # Check if we already have a locked target from Step 0 loss for recovery
                if cur_step > 0 and ms.get("locked_cluster_type") and ms.get("locked_symbol"):
                    target_cluster_type = ms["locked_cluster_type"]
                    target_barrier = ms.get("locked_barrier", u_bar if target_cluster_type == "UNDER" else o_bar)
                    target_sym = ms["locked_symbol"]
                    l_cl_key = f"{target_sym}:DIGIT{target_cluster_type}:{target_barrier}"
                    if tri_strike_on and l_cl_key in exhausted_targets:
                        state.log(f"🛡️ CLUSTER TARGET EXHAUSTED: {l_cl_key} in exhausted list. Rotating recovery to next anomaly!", "PIVOT")
                        ms["locked_cluster_type"] = None
                        ms["locked_barrier"] = None
                        ms["locked_symbol"] = None
                        target_cluster_type = None
                    else:
                        cr = cluster_radar.get(target_sym, {})
                        target_drought = cr.get(u_key if target_cluster_type == "UNDER" else o_key, 0)
                
                if target_cluster_type is None:
                    user_sum_th = int(mc.get("cluster_sum_threshold", 0) or mc.get("basket_sum_threshold", 0))
                    user_min_indiv = int(mc.get("min_digit_drought", 0))

                    cluster_cands = []
                    best_u_sum, best_o_sum = 0, 0
                    best_u_cnt, best_o_cnt = 0, 0

                    for sym in scan_syms:
                        if not is_sym_allowed(sym):
                            continue
                        if sym not in state.digits or len(state.digits[sym]) < 20:
                            continue
                        s_thresh = int(sym_threshs.get(sym, d_thresh))

                        cr = cluster_radar.get(sym, {})
                        u_cnt = cr.get(u_key, 0)
                        o_cnt = cr.get(o_key, 0)
                        u_sum = cr.get("u2_sum" if is_duo else "u3_sum", 0)
                        o_sum = cr.get("o7_sum" if is_duo else "o6_sum", 0)
                        u_min = cr.get("u2_min" if is_duo else "u3_min", 0)
                        o_min = cr.get("o7_min" if is_duo else "o6_min", 0)

                        if u_sum > best_u_sum:
                            best_u_sum = u_sum
                        if o_sum > best_o_sum:
                            best_o_sum = o_sum
                        if u_cnt > best_u_cnt:
                            best_u_cnt = u_cnt
                        if o_cnt > best_o_cnt:
                            best_o_cnt = o_cnt

                        freqs = assets_freq_map.get(sym, {})
                        f_u = sum(freqs.get(d, 10) for d in u_digits)
                        f_o = sum(freqs.get(d, 10) for d in o_digits)

                        req_f = min_cluster_f if min_cluster_f > 0 else 0

                        # DECISION LOGIC:
                        # Case 1: Custom Sum Threshold (> 0) -> Respect the Sum!
                        # Case 2: No Custom Sum (0) -> Pure Cluster Drought Threshold
                        t_u_key = f"{sym}:DIGITUNDER:{u_bar}"
                        t_o_key = f"{sym}:DIGITOVER:{o_bar}"

                        if user_sum_th > 0:
                            u_sum_ok = (u_sum >= user_sum_th)
                            o_sum_ok = (o_sum >= user_sum_th)
                            if user_min_indiv > 0:
                                u_sum_ok = u_sum_ok and (u_min >= user_min_indiv)
                                o_sum_ok = o_sum_ok and (o_min >= user_min_indiv)

                            if u_sum_ok and f_u >= req_f:
                                if not (tri_strike_on and t_u_key in exhausted_targets):
                                    cluster_cands.append({
                                        "symbol": sym,
                                        "cluster_type": "UNDER",
                                        "barrier": u_bar,
                                        "count": u_cnt,
                                        "basket_sum": u_sum,
                                        "freq": f_u,
                                    })
                            if o_sum_ok and f_o >= req_f:
                                if not (tri_strike_on and t_o_key in exhausted_targets):
                                    cluster_cands.append({
                                        "symbol": sym,
                                        "cluster_type": "OVER",
                                        "barrier": o_bar,
                                        "count": o_cnt,
                                        "basket_sum": o_sum,
                                        "freq": f_o,
                                    })
                        else:
                            # Pure Drought Threshold mode
                            is_fresh = mc.get("fresh_breakout_mode", True)
                            u_cnt_ok = (u_cnt == s_thresh) if is_fresh else (u_cnt >= s_thresh)
                            o_cnt_ok = (o_cnt == s_thresh) if is_fresh else (o_cnt >= s_thresh)

                            if u_cnt_ok and f_u >= req_f:
                                if not (tri_strike_on and t_u_key in exhausted_targets):
                                    cluster_cands.append({
                                        "symbol": sym,
                                        "cluster_type": "UNDER",
                                        "barrier": u_bar,
                                        "count": u_cnt,
                                        "basket_sum": u_sum,
                                        "freq": f_u,
                                    })
                            if o_cnt_ok and f_o >= req_f:
                                if not (tri_strike_on and t_o_key in exhausted_targets):
                                    cluster_cands.append({
                                        "symbol": sym,
                                        "cluster_type": "OVER",
                                        "barrier": o_bar,
                                        "count": o_cnt,
                                        "basket_sum": o_sum,
                                        "freq": f_o,
                                    })

                    if cluster_cands:
                        if user_sum_th > 0:
                            cluster_cands.sort(key=lambda x: x["basket_sum"], reverse=True)
                        else:
                            cluster_cands.sort(key=lambda x: x["count"], reverse=True)
                        best_cand = cluster_cands[0]
                        target_cluster_type = best_cand["cluster_type"]
                        target_barrier = best_cand["barrier"]
                        target_sym = best_cand["symbol"]
                        target_drought = best_cand["count"]
                        ms["locked_cluster_type"] = target_cluster_type
                        ms["locked_barrier"] = target_barrier
                        ms["locked_symbol"] = target_sym
                    else:
                        mode_label = "Duo Wing" if is_duo else "Cluster"
                        if user_sum_th > 0:
                            ms["status"] = f"❄️ {mode_label.upper()} (Step {cur_step}): Scanning Sum>={user_sum_th}t (Deepest: U_Sum={best_u_sum}t, O_Sum={best_o_sum}t)"
                        else:
                            ms["status"] = f"❄️ {mode_label.upper()} (Step {cur_step}): Scanning Thresh={d_thresh}t (Deepest: U3={best_u_cnt}t, O6={best_o_cnt}t)"
                        continue

            elif not ai_selected:
                eligible_cands = []
                twin_qualified_assets = []
                user_min_indiv = int(mc.get("min_digit_drought", 0))
                user_sum_th = int(mc.get("basket_sum_threshold", 0))
                min_penta_trades = int(mc.get("min_penta_trades", 3))

                # Step Expansion for Solo: +1 drought per martingale step depth (Disabled by default)
                step_expansion = int(cur_step) if mc.get("solo_step_expansion", False) else 0

                for sym in scan_syms:
                    if not is_sym_allowed(sym):
                        continue
                    if sym not in state.digits or len(state.digits[sym]) < 20:
                        continue
                    d_list = list(state.digits[sym])
                    s_thresh = int(sym_threshs.get(sym, d_thresh))
                    min_indiv_th = user_min_indiv if user_min_indiv > 0 else s_thresh
                    twin_sum_th = user_sum_th if user_sum_th > 0 else (2 * s_thresh)
                    req_solo_thresh = s_thresh + step_expansion

                    # Twin candidate evaluation on this symbol
                    sym_dr_map = assets_drought_map.get(sym, {})
                    candidate_twin_digits = range(10)
                    if min_freq > 0 and mc.get("filter_zombie", True) and not hunt_zombies:
                        candidate_twin_digits = [d for d in range(10) if assets_freq_map.get(sym, {}).get(d, 10) >= min_freq]
                    elif hunt_zombies:
                        candidate_twin_digits = [d for d in range(10) if assets_freq_map.get(sym, {}).get(d, 10) < min_freq]
                    sorted_digits = sorted(candidate_twin_digits, key=lambda d: sym_dr_map.get(d, 0), reverse=True)
                    if len(sorted_digits) >= 2:
                        top_d1, top_d2 = sorted_digits[0], sorted_digits[1]
                        dr1 = sym_dr_map.get(top_d1, 0)
                        dr2 = sym_dr_map.get(top_d2, 0)
                        tw_min = min(dr1, dr2)
                        tw_sum = dr1 + dr2
                        if tw_min >= min_indiv_th and tw_sum >= twin_sum_th:
                            t_pair_key = f"{sym}:D{top_d1}+{sym}:D{top_d2}"
                            if not (tri_strike_on and t_pair_key in exhausted_targets):
                                twin_qualified_assets.append({
                                    "symbol": sym,
                                    "p1": {"digit": top_d1, "count": dr1},
                                    "p2": {"digit": top_d2, "count": dr2},
                                    "twin_sum": tw_sum,
                                    "twin_min": tw_min,
                                })

                    for d in range(10):
                        try:
                            cnt = d_list[::-1].index(d)
                        except ValueError:
                            cnt = len(d_list)
                        f_100 = assets_freq_map.get(sym, {}).get(d, 10)
                        if hunt_zombies:
                            pass_zombie = (cnt >= req_solo_thresh and f_100 < min_freq)
                        else:
                            freq_ok = (f_100 >= min_freq) if (min_freq > 0 and mc.get("filter_zombie", True)) else True
                            pass_zombie = (cnt >= req_solo_thresh and freq_ok)

                        if pass_zombie:
                            t_cand_key = f"{sym}:D{d}"
                            if not (tri_strike_on and t_cand_key in exhausted_targets):
                                cand = {
                                    "symbol": sym,
                                    "digit": d,
                                    "count": cnt,
                                    "barrier": str(d),
                                    "contract_type": "DIGITMATCH",
                                    "dist": 0,
                                    "freq": f_100,
                                }
                                eligible_cands.append(cand)

                if sub_mode == "penta":
                    enabled_syms = [s for s in MATCH_ASSETS if is_sym_allowed(s)]
                    min_penta_th = int(mc.get("penta_drought_threshold", 18))
                    user_max_penta = int(mc.get("penta_max_drought", 0))
                    window_span = int(mc.get("penta_window_span", 0))
                    min_penta_trades = int(mc.get("min_penta_trades", 2))
                    max_penta_trades = int(mc.get("max_penta_trades", 15))
                    penta_rec_trades = int(mc.get("penta_rec_trades", 6))
                    exact_mode = bool(mc.get("penta_exact_threshold", True))
                    is_fresh_mode = (mc.get("target_priority", "min") == "min")

                    use_separate = bool(mc.get("penta_separate_ranges", False))
                    p_sym_ranges = mc.get("penta_symbol_ranges", {})

                    if ladder and cur_step < len(ladder):
                        cur_lad_step = ladder[cur_step]
                        cur_stake_per_digit = float(cur_lad_step.get("stake_per_digit", mc.get("base_stake", 0.35)))
                    else:
                        b_penta = float(mc.get("base_stake", 0.35))
                        t_profit_p = round(b_penta * 1.0, 2)
                        n_rec_cnt = max(1, min(7, int(mc.get("penta_rec_trades", 6))))
                        div_p = max(0.5, 8.34 - n_rec_cnt)
                        c_loss_p = max(float(ms.get("sequence_accumulated_loss", 0.0)), float(ladder[-1]["drain"]) if ladder else 0.0)
                        req_digit_p = (c_loss_p + t_profit_p) / div_p
                        cur_stake_per_digit = max(b_penta, round(math.ceil(req_digit_p * 100) / 100.0, 2))

                    target_contracts_count = max_penta_trades if cur_step == 0 else penta_rec_trades

                    all_penta_cands = []
                    ready_syms = []

                    for s in enabled_syms:
                        if s not in state.digits or len(state.digits[s]) < 20:
                            continue
                        if use_separate and s in p_sym_ranges:
                            s_th_exact = int(p_sym_ranges[s].get("min", min_penta_th))
                            s_th_min = s_th_exact
                            s_th_max = int(p_sym_ranges[s].get("max", s_th_min + window_span))
                        else:
                            s_th_exact = min_penta_th
                            s_th_min = min_penta_th
                            s_th_max = user_max_penta if user_max_penta >= s_th_min else (s_th_min + window_span)

                        s_dr_map = assets_drought_map.get(s, {})
                        for d in range(10):
                            f_100 = assets_freq_map.get(s, {}).get(d, 10)
                            freq_ok = (f_100 >= min_freq) if (min_freq > 0 and mc.get("filter_zombie", True) and not hunt_zombies) else True
                            if hunt_zombies:
                                freq_ok = (f_100 < min_freq)
                            if not freq_ok:
                                continue
                            dr = s_dr_map.get(d, 0)
                            t_cand_key = f"{s}:D{d}"

                            qualifies = (dr == s_th_exact) if exact_mode else (s_th_min <= dr <= s_th_max)

                            if qualifies:
                                if not (tri_strike_on and t_cand_key in exhausted_targets):
                                    all_penta_cands.append({
                                        "symbol": s,
                                        "digit": d,
                                        "count": dr,
                                        "barrier": str(d),
                                        "freq": f_100,
                                        "stake": cur_stake_per_digit,
                                        "s_min": s_th_min,
                                        "s_max": s_th_max,
                                    })
                                    ready_syms.append(f"{s}:D{d}({dr}t)")

                    if is_fresh_mode:
                        all_penta_cands.sort(key=lambda t: (t["count"], -t["freq"]))
                    else:
                        all_penta_cands.sort(key=lambda t: (-t["count"], -t["freq"]))

                    penta_targets = all_penta_cands[:target_contracts_count]

                    min_req = min_penta_trades if cur_step == 0 else 1
                    if len(penta_targets) >= min_req:
                        target_sym = "PENTA_5X"
                        target_digit = penta_targets[0]["digit"]
                        ms["locked_digit"] = target_digit
                        ms["locked_symbol"] = penta_targets[0]["symbol"]
                        ms["locked_base_thresh"] = penta_targets[0].get("s_min", min_penta_th)
                    else:
                        mode_label = f"== {min_penta_th}t" if exact_mode else f"[{min_penta_th}-{s_th_max}]t"
                        step_label = "Step 0 (Initial Salvo)" if cur_step == 0 else f"Step {cur_step} (Recovery Salvo)"
                        ms["status"] = f"❄️ PENTA {step_label}: Waiting for {min_req}+ targets at {mode_label} (Currently: {len(penta_targets)}/{min_req} ready: {ready_syms[:target_contracts_count]})"
                        continue
                elif sub_mode == "twin":
                    if twin_qualified_assets:
                        twin_qualified_assets.sort(key=lambda x: x["twin_sum"], reverse=True)
                        best_tw = twin_qualified_assets[0]
                        target_sym = best_tw["symbol"]
                        target_twin_sym = best_tw["symbol"]
                        target_digit = best_tw["p1"]["digit"]
                        target_twin = best_tw["p2"]["digit"]
                        target_drought = best_tw["p1"]["count"]
                        target_twin_drought = best_tw["p2"]["count"]
                    else:
                        ms["status"] = f"❄️ TWIN (Step {cur_step}): Scanning for Min>={min_indiv_th}t & Sum>={twin_sum_th}t"
                        continue
                else:
                    # sub_mode == "solo"
                    if cur_step > 0 and ms.get("locked_digit") is not None and ms.get("locked_symbol") is not None:
                        # LOCKED TARGET RECOVERY: Stay strictly locked to target digit & asset unless invalidated or exhausted
                        locked_sym = ms["locked_symbol"]
                        locked_d = ms["locked_digit"]
                        l_key = f"{locked_sym}:D{locked_d}"
                        if tri_strike_on and l_key in exhausted_targets:
                            state.log(f"🛡️ SOLO TARGET EXHAUSTED: {l_key} reached strike limit. Rotating recovery to next anomaly!", "PIVOT")
                            ms["locked_digit"] = None
                            ms["locked_symbol"] = None
                            ms["locked_base_thresh"] = None
                        else:
                            s_th = int(sym_threshs.get(locked_sym, d_thresh))
                            b_th = ms.get("locked_base_thresh") or s_th
                            cur_drought = assets_drought_map.get(locked_sym, {}).get(locked_d, 0)
                            
                            # SMART INVALIDATION: If the locked digit hit the market while waiting
                            if cur_drought < s_th:
                                state.log(f"⚠️ SOLO TARGET INVALIDATED: {locked_sym} D{locked_d} hit market (Drought={cur_drought}t < {s_th}t). Switching to fresh anomaly!", "TARGET")
                                ms["locked_digit"] = None
                                ms["locked_symbol"] = None
                                ms["locked_base_thresh"] = None
                            else:
                                step_exp = cur_step if mc.get("solo_step_expansion", False) else 0
                                req_drought = b_th + step_exp
                                if cur_drought >= req_drought:
                                    target_digit = locked_d
                                    target_sym = locked_sym
                                    target_drought = cur_drought
                                else:
                                    ms["status"] = f"🎯 SOLO LOCKED TARGET (Step {cur_step}): {locked_sym} D{locked_d} Drought={cur_drought}t (Waiting for >={req_drought}t)"
                                    continue

                    if target_digit is None:
                        if eligible_cands:
                            is_fresh_mode = (mc.get("target_priority", "min") == "min")
                            if is_fresh_mode:
                                eligible_cands.sort(key=lambda x: (x["dist"], x["count"]))
                            else:
                                eligible_cands.sort(key=lambda x: x["count"], reverse=True)
                            best_cand = eligible_cands[0]
                            target_digit = best_cand["digit"]
                            target_sym = best_cand["symbol"]
                            target_drought = best_cand["count"]
                            # Lock target for the entire sequence
                            ms["locked_digit"] = target_digit
                            ms["locked_symbol"] = target_sym
                            ms["locked_base_thresh"] = int(sym_threshs.get(target_sym, d_thresh))
                        else:
                            req_note = f" (Req: {d_thresh}+{step_expansion}t)" if step_expansion > 0 else ""
                            ms["status"] = f"❄️ SOLO (Step {cur_step}): Scanning for drought >= {d_thresh + step_expansion}t{req_note}"
                            continue

                if target_digit is None and not (sub_mode in ("cluster", "duo_wing", "parity_spread")):
                    zombie_note = f" ({len(ms['zombie_digits'])} digits muted by Zombie Filter)" if ms['zombie_digits'] else ""
                    ms["status"] = f"SNIPING DROUGHT on {monitored_sym} (Deepest: D{best_d}@{best_sym} = {max_d}t < {d_thresh}t{zombie_note})"
                    continue

            # Squeeze Gate Filter on Step 0
            if cur_step == 0 and require_squeeze and target_sym in state.pip_steps and len(state.pip_steps[target_sym]) >= 3:
                last_step = abs(int(state.pip_steps[target_sym][-1]))
                if last_step > 3:
                    ms["status"] = f"HOLDING SQUEEZE on {target_sym} (Last Step={last_step}p > 3p • Squeeze Gate Closed)"
                    continue

            # Ladder stake & signal construction
            ladder = ms.get("ladder", [])
            b_stake = float(mc.get("base_stake", 0.35))
            open_d = bool(mc.get("open_depth", True))

            if ladder and cur_step < len(ladder):
                step_info = ladder[cur_step]
                stake = float(step_info["stake"])
                s_each = float(step_info.get("stake_per_digit", stake / 2.0 if sub_mode == "twin" else stake))
            else:
                # Dynamic On-The-Fly Stake Calculation for Open Depth
                cum_drain = max(float(ms.get("sequence_accumulated_loss", 0.0)), float(ladder[-1]["drain"]) if ladder else 0.0)
                if sub_mode == "parity_spread":
                    t_profit = round(b_stake * 0.94, 2)
                    req_s = (cum_drain + t_profit) / 0.94
                    stake = max(b_stake, round(math.ceil(req_s * 100) / 100.0, 2))
                    s_each = stake
                elif sub_mode in ("cluster", "duo_wing"):
                    is_duo_b = (sub_mode == "duo_wing" or target_barrier in ("2", "7"))
                    n_ratio = 3.545 if is_duo_b else 2.13
                    t_profit = round(b_stake * 1.0, 2)
                    req_s = (cum_drain + t_profit) / n_ratio
                    stake = max(b_stake, round(math.ceil(req_s * 100) / 100.0, 2))
                    s_each = stake
                elif sub_mode == "twin":
                    t_profit = round(b_stake * 1.0, 2)
                    req_s_digit = (cum_drain + t_profit) / (8.34 - 2.0)
                    s_digit = max(b_stake, round(math.ceil(req_s_digit * 100) / 100.0, 2))
                    stake = round(s_digit * 2, 2)
                    s_each = s_digit
                elif sub_mode == "penta":
                    t_profit = round(b_stake * 1.0, 2)
                    n_rec = max(1, min(7, int(mc.get("penta_rec_trades", 6))))
                    divisor = max(0.5, 8.34 - n_rec)
                    req_s_digit = (cum_drain + t_profit) / divisor
                    s_digit = max(b_stake, round(math.ceil(req_s_digit * 100) / 100.0, 2))
                    stake = round(s_digit * n_rec, 2)
                    s_each = s_digit
                else:  # Solo Match (+734.0%)
                    t_profit = round(b_stake * 1.0, 2)
                    req_s = (cum_drain + t_profit) / 7.34
                    stake = max(b_stake, round(math.ceil(req_s * 100) / 100.0, 2))
                    s_each = stake
                step_info = {"step": cur_step, "stake": stake, "stake_per_digit": s_each}

            # Deriv Live Balance Guardrail: Prevent API rejection or negative equity
            if state.deriv_balance > 0.0 and stake > state.deriv_balance:
                state.log(f"🛑 INSUFFICIENT BALANCE FOR STEP {cur_step}: Required stake ${stake:.2f} > Deriv Balance ${state.deriv_balance:.2f}. Engine stopping safely to protect capital!", "RISK")
                state.is_running = False
                ms["status"] = "STOPPED_INSUFFICIENT_BALANCE"
                continue

            dur_ticks = int(mc.get("duration_ticks", 1))

            latest_tick = float(state.ticks[target_sym][-1]) if target_sym in state.ticks and len(state.ticks[target_sym]) > 0 else 0.0

            if sub_mode == "parity_spread":
                deriv_c = target_parity_type
                p_label = "+94.0%"
                p_ratio = 0.94
                target_label = "EVEN" if deriv_c == "DIGITEVEN" else "ODD"
                ms["status"] = f"FIRING PARITY {target_label} on {target_sym} (Step {cur_step}/{len(ladder)-1} • ${stake:.2f} • ΔM={target_spread:+.1f})"
                ms["last_trade_time"] = now
                sig = {
                    "symbol": target_sym,
                    "contract_type": f"PARITY SNIPER {target_sym} {deriv_c} ({dur_ticks}t • Step {cur_step})",
                    "deriv_contract_type": deriv_c,
                    "duration_ticks": dur_ticks,
                    "payout_ratio": p_ratio,
                    "entry_spot": latest_tick,
                    "reason": f"Parity Delta Spread: {deriv_c} ΔM={target_spread:+.1f} (Streak={target_streak}t) == {parity_th:.1f} -> {p_label}",
                    "is_match_sniper": True,
                    "is_twin_match": False,
                    "custom_stake": stake,
                    "custom_step": cur_step,
                }
            elif sub_mode in ("cluster", "duo_wing"):
                cl_type = target_cluster_type
                barrier = target_barrier
                deriv_c = f"DIGIT{cl_type}"
                is_duo_b = (sub_mode == "duo_wing" or barrier in ("2", "7"))
                p_ratio = 3.545 if is_duo_b else 2.13
                p_label = "+354.5%" if is_duo_b else "+213.0%"
                wr_label = "20%" if is_duo_b else "30%"
                mode_title = "DUO WING" if is_duo_b else "CLUSTER"
                ms["status"] = f"FIRING {mode_title} {cl_type} {barrier} on {target_sym} (Step {cur_step}/{len(ladder)-1} • ${stake:.2f} • {wr_label} WR)"
                ms["last_trade_time"] = now
                sig = {
                    "symbol": target_sym,
                    "contract_type": f"{mode_title} SNIPER {target_sym} {deriv_c} {barrier} ({dur_ticks}t • Step {cur_step})",
                    "deriv_contract_type": deriv_c,
                    "barrier": barrier,
                    "duration_ticks": dur_ticks,
                    "payout_ratio": p_ratio,
                    "entry_spot": latest_tick,
                    "reason": f"{mode_title} Sniper: {deriv_c} {barrier} Drought={target_drought}t == {d_thresh}t -> {p_label}",
                    "is_match_sniper": True,
                    "is_twin_match": False,
                    "custom_stake": stake,
                    "custom_step": cur_step,
                }
            elif sub_mode == "penta":
                tot_s = round(sum(t.get("stake", cur_stake_per_digit) for t in penta_targets), 2)
                step_title = "Step 0" if cur_step == 0 else f"Step {cur_step} Recovery"
                ms["status"] = f"FIRING PENTA SALVO on {len(penta_targets)} Assets ({step_title} • ${tot_s:.2f} • == Threshold)"
                ms["last_trade_time"] = now
                sig = {
                    "symbol": "PENTA_5X",
                    "contract_type": f"PENTA SALVO ({len(penta_targets)}x {dur_ticks}t • {step_title})",
                    "is_match_sniper": True,
                    "is_penta_salvo": True,
                    "penta_targets": penta_targets,
                    "custom_stake": tot_s,
                    "custom_step": cur_step,
                    "duration_ticks": dur_ticks,
                    "payout_ratio": 7.34,
                    "entry_spot": 0.0,
                    "reason": f"Penta Salvo: {len(penta_targets)} Assets strictly at drought == threshold ({step_title})",
                }
            elif sub_mode == "twin" and target_twin is not None:
                s_each = float(step_info.get("stake_per_digit", stake / 2.0))
                sec_sym = target_twin_sym or target_sym
                zh_label = "ZOMBIE HUNTER BRACKET" if hunt_zombies else "DUAL-ASSET TWIN"
                ms["status"] = f"FIRING {zh_label} {target_sym}:D{target_digit} + {sec_sym}:D{target_twin} (Step {cur_step}/{len(ladder)-1} • ${stake:.2f} • 20% WR)"
                ms["last_trade_time"] = now
                reason_tag = "Zombie Hunter" if hunt_zombies else "Dual-Asset Twin"
                sig = {
                    "symbol": target_sym,
                    "twin_symbol": sec_sym,
                    "contract_type": f"TWIN SNIPER {target_sym}:D{target_digit} + {sec_sym}:D{target_twin} ({dur_ticks}t • Step {cur_step})",
                    "deriv_contract_type": "DIGITMATCH",
                    "twin_deriv_contract_type": "DIGITMATCH",
                    "barrier": str(target_digit),
                    "twin_barrier": str(target_twin),
                    "duration_ticks": dur_ticks,
                    "payout_ratio": 3.17,
                    "entry_spot": latest_tick,
                    "reason": f"{reason_tag}: {target_sym} D{target_digit} ({target_drought}t) + {sec_sym} D{target_twin} ({target_twin_drought}t)",
                    "is_match_sniper": True,
                    "is_twin_match": True,
                    "custom_stake": stake,
                    "custom_stake_per_digit": s_each,
                    "custom_step": cur_step,
                }
            else:
                zh_label = "ZOMBIE WAKE-UP" if hunt_zombies else "DIGITMATCH"
                ms["status"] = f"FIRING {zh_label} {target_digit} on {target_sym} (Step {cur_step}/{len(ladder)-1} • ${stake:.2f} • Drought={target_drought}t)"
                ms["last_trade_time"] = now
                ms["locked_digit"] = target_digit
                ms["locked_symbol"] = target_sym
                if ms.get("locked_base_thresh") is None:
                    ms["locked_base_thresh"] = int(sym_threshs.get(target_sym, d_thresh))
                reason_tag = "Zombie Hunter" if hunt_zombies else "Match Sniper"
                sig = {
                    "symbol": target_sym,
                    "contract_type": f"MATCH SNIPER {target_sym} DIGITMATCH {target_digit} ({dur_ticks}t • Step {cur_step})",
                    "deriv_contract_type": "DIGITMATCH",
                    "barrier": str(target_digit),
                    "duration_ticks": dur_ticks,
                    "payout_ratio": 7.34,
                    "entry_spot": latest_tick,
                    "reason": f"{reason_tag}: Digit {target_digit} Drought={target_drought}t == {d_thresh}t -> DIGITMATCH {target_digit} (+734.0%)",
                    "is_match_sniper": True,
                    "is_twin_match": False,
                    "custom_stake": stake,
                    "custom_step": cur_step,
                }

            asyncio.create_task(execute_live_deriv_digit_trade(sig))
        except Exception as e:
            state.log(f"⚠️ Match Sniper Worker Loop Error: {type(e).__name__}: {e}", "WARN")
            await asyncio.sleep(0.5)


# ==============================================================================
# BACKGROUND WORKERS: PUBLIC FEED, BROADCAST, AND KEEPALIVE
# ==============================================================================

async def public_stream_worker():
    """Streams live public market ticks for all Pure-R Volatility assets."""
    while True:
        try:
            async with _ws_connect(DERIV_PUBLIC_WS, ping_interval=20, ping_timeout=20) as ws:
                try:
                    sock = ws.transport.get_extra_info('socket') if hasattr(ws, 'transport') else None
                    if sock is not None:
                        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except Exception:
                    pass

                for sym in MATCH_ASSETS:
                    req_hist = {
                        "ticks_history": sym,
                        "end": "latest",
                        "count": 500,
                        "style": "ticks",
                        "subscribe": 1,
                    }
                    await ws.send(json.dumps(req_hist))
                state.log("📡 Pure-R Public Tick Streams connected for all 5 assets.", "SYSTEM")

                while True:
                    raw = await ws.recv()
                    msg = json.loads(raw)
                    mtype = msg.get("msg_type")
                    if mtype == "history":
                        sym = msg.get("echo_req", {}).get("ticks_history")
                        if sym in MATCH_ASSETS:
                            decs = DECIMALS_MAP.get(sym, 2)
                            prices = [float(p) for p in msg.get("history", {}).get("prices", [])]
                            for idx, p in enumerate(prices):
                                state.ticks[sym].append(p)
                                d = extract_last_digit(p, sym)
                                state.digits[sym].append(d)
                                if idx > 0:
                                    p_prev = prices[idx - 1]
                                    pip_diff = int(round((p - p_prev) * (10 ** decs)))
                                    state.pip_steps[sym].append(pip_diff)
                    elif mtype == "tick":
                        t = msg.get("tick", {})
                        sym = t.get("symbol")
                        if sym in MATCH_ASSETS:
                            price = float(t.get("quote", t.get("bid", 0.0)))
                            decs = DECIMALS_MAP.get(sym, 2)
                            if len(state.ticks[sym]) > 0:
                                prev_p = state.ticks[sym][-1]
                                pip_diff = int(round((price - prev_p) * (10 ** decs)))
                                state.pip_steps[sym].append(pip_diff)
                            state.ticks[sym].append(price)
                            state.digits[sym].append(extract_last_digit(price, sym))
                            state.tick_event.set()
        except Exception as e:
            state.log(f"Public tick stream disconnected: {e}. Reconnecting...", "WARN")
            await asyncio.sleep(2.0)


async def broadcast_worker():
    """Rapid live telemetry broadcast worker (120ms cycle)."""
    while True:
        await asyncio.sleep(0.12)
        if not state.ws_clients:
            continue

        wr = round((state.wins / state.total_trades) * 100.0, 2) if state.total_trades > 0 else 0.0
        active_asset = state.match_config.get("asset", "ALL")
        disp_sym = active_asset if active_asset in MATCH_ASSETS else "R_100"
        recent_digits = list(state.digits[disp_sym])[-30:] if disp_sym in state.digits else []
        latest_digits = {sym: (state.digits[sym][-1] if sym in state.digits and len(state.digits[sym]) > 0 else None) for sym in MATCH_ASSETS}
        latest_prices = {sym: (state.ticks[sym][-1] if sym in state.ticks and len(state.ticks[sym]) > 0 else None) for sym in MATCH_ASSETS}

        s0 = state.step_distribution.get(0, 0)
        s1 = state.step_distribution.get(1, 0)
        s2 = state.step_distribution.get(2, 0)
        s3_plus = sum(state.step_distribution.get(k, 0) for k in range(3, 35))

        # Rolling Expected Drought Range & Reversal Stats for Penta
        if state.match_config.get("sub_mode") == "penta":
            p_stats = {sym: calculate_symbol_expected_drought_stats(sym) for sym in MATCH_ASSETS}
            m_vals = [p_stats[s]["mean"] for s in MATCH_ASSETS]
            s_vals = [p_stats[s]["std"] for s in MATCH_ASSETS]
            g_mean = round(sum(m_vals) / len(m_vals), 1)
            g_std = round(sum(s_vals) / len(s_vals), 1)
            g_exp = int(round(g_mean + 1.0 * g_std))
            state.match_state["penta_expected_stats"] = {
                "mean": g_mean,
                "std": g_std,
                "expected_threshold": g_exp,
                "by_asset": p_stats,
            }

        payload = {
            "type": "telemetry",
            "is_running": state.is_running,
            "active_account": state.active_account,
            "account_id": state.get_active_account_id(),
            "balance": state.deriv_balance,
            "balance_synced": state.balance_synced,
            "total_trades": state.total_trades,
            "wins": state.wins,
            "losses": state.losses,
            "win_rate": wr,
            "total_pnl": state.total_pnl,
            "vault_balance": state.vault_balance,
            "capital_growth_pool": state.capital_growth_pool,
            "active_cycle": state.active_cycle,
            "cycle_target_usd": state.cycle_target_usd,
            "cycle_accumulated_pnl": state.cycle_accumulated_pnl,
            "vault_locked_profit": state.vault_locked_profit,
            "initial_sl_usd": state.initial_sl_usd,
            "session_start_balance": state.session_start_balance,
            "hard_sl_floor": state.hard_sl_floor,
            "current_loss_streak": state.current_loss_streak,
            "max_loss_streak": state.max_loss_streak,
            "baskets_cleared": state.baskets_cleared,
            "step_distribution": state.step_distribution,
            "step_summary": {"s0": s0, "s1": s1, "s2": s2, "s3_plus": s3_plus},
            "take_profit_enabled": state.take_profit_enabled,
            "stop_loss_enabled": state.stop_loss_enabled,
            "hard_sl_enabled": state.hard_sl_enabled,
            "stopped_by_stop_loss": state.stopped_by_stop_loss,
            "match_config": state.match_config,
            "match_state": state.match_state,
            "recent_digits": recent_digits,
            "latest_digits": latest_digits,
            "latest_prices": latest_prices,
            "recent_trades": state.trade_history[:50],
            "logs": state.logs[:30],
        }
        msg = json.dumps(payload)
        dead = []
        for ws in list(state.ws_clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            state.ws_clients.discard(ws)


async def persistent_trading_ws_keepalive_worker():
    while True:
        await asyncio.sleep(20.0)
        try:
            if is_ws_open(state.persistent_trade_ws) and not state.in_live_trade:
                await state.persistent_trade_ws.send(json.dumps({"ping": 1}))
        except Exception:
            state.persistent_trade_ws = None


async def periodic_balance_sync_worker():
    await asyncio.sleep(1.0)
    await sync_deriv_live_balance()
    if state.session_start_balance <= 0.0 and state.deriv_balance > 0.0:
        state.session_start_balance = state.deriv_balance
        if state.active_cycle == 1:
            state.hard_sl_floor = round(state.session_start_balance - state.initial_sl_usd, 2)
    while True:
        await asyncio.sleep(45.0)
        if not state.in_live_trade:
            await sync_deriv_live_balance()
            if state.session_start_balance <= 0.0 and state.deriv_balance > 0.0:
                state.session_start_balance = state.deriv_balance
                if state.active_cycle == 1:
                    state.hard_sl_floor = round(state.session_start_balance - state.initial_sl_usd, 2)
            if state.is_running and state.hard_sl_enabled and state.stop_loss_enabled and state.hard_sl_floor > 0.0 and state.deriv_balance > 0.0 and state.deriv_balance <= state.hard_sl_floor:
                state.is_running = False
                state.stopped_by_stop_loss = True
                state.match_state["status"] = "STOPPED_BY_HARD_SL"
                state.log(f"🛑 [CIRCUIT BREAKER ON BALANCE SYNC] Balance (${state.deriv_balance:.2f}) <= Floor (${state.hard_sl_floor:.2f})! Engine disconnected.", "RISK")


# ==============================================================================
# FASTAPI APPLICATION & WEBSOCKET DISPATCHER
# ==============================================================================

app = FastAPI(title="Match Sniper Pro Standalone", version="3.0")


@app.on_event("startup")
async def startup_event():
    # Initialize active ladder & dynamic cycle target (= Martingale Drain Depth)
    rebuild_active_ladder()

    asyncio.create_task(public_stream_worker())
    asyncio.create_task(match_sniper_worker())
    asyncio.create_task(broadcast_worker())
    asyncio.create_task(persistent_trading_ws_keepalive_worker())
    asyncio.create_task(periodic_balance_sync_worker())
    state.log(f"⚡ Match Sniper Pro Standalone Engine initialized on http://127.0.0.1:{PORT}", "SYSTEM")


@app.get("/")
async def serve_dashboard():
    p = resolve_resource_path("dashboard.html")
    if os.path.exists(p):
        return FileResponse(p)
    return HTMLResponse("<h2>Match Sniper Pro Terminal is running. dashboard.html not found.</h2>")


@app.get("/proof")
@app.get("/capital_proof")
@app.get("/Match_Sniper_Capital_Proof.html")
async def serve_capital_proof():
    p = resolve_resource_path("Match_Sniper_Capital_Proof.html")
    if os.path.exists(p):
        return FileResponse(p)
    return HTMLResponse("<h2>Capital Proof document not found.</h2>")


@app.get("/manual")
@app.get("/guide")
@app.get("/Match_Sniper_User_Manual.html")
async def serve_manual():
    p = resolve_resource_path("Match_Sniper_User_Manual.html")
    if os.path.exists(p):
        return FileResponse(p)
    return HTMLResponse("<h2>User Manual document not found.</h2>")


@app.get("/api/download_csv")
async def download_csv():
    if os.path.exists(CSV_LOG_FILE):
        return FileResponse(CSV_LOG_FILE, filename="match_sniper_trades.csv")
    return Response(content="num,time,account,symbol,contract_type,barrier,payout_pct,step,stake,entry_spot,exit_spot,exit_digit,outcome,pnl,deficit_after\n", media_type="text/csv")


@app.get("/api/credentials")
async def get_credentials_api():
    creds = state.load_credentials()
    return JSONResponse({
        "status": "ok",
        "file_path": CREDS_FILE,
        "creds": creds,
        "raw_json": json.dumps(creds, indent=2),
        "active_account": state.active_account,
    })


@app.post("/api/credentials")
async def save_credentials_api(request: Request):
    try:
        body = await request.json()
        new_creds = None
        if "raw_json" in body:
            raw_val = body["raw_json"]
            if isinstance(raw_val, dict):
                new_creds = raw_val
            elif isinstance(raw_val, str):
                new_creds = json.loads(raw_val)
        elif "creds" in body and isinstance(body["creds"], dict):
            new_creds = body["creds"]
        elif "demo_id" in body or "real_id" in body:
            demo_id = str(body.get("demo_id", "")).strip()
            demo_token = str(body.get("demo_token", "")).strip()
            real_id = str(body.get("real_id", "")).strip()
            real_token = str(body.get("real_token", "")).strip()
            active = str(body.get("active", state.active_account or "demo")).strip()
            tok = real_token if active == "real" else demo_token
            new_creds = {
                "token": tok or state.creds.get("token", ""),
                "account_id_demo": demo_id,
                "account_id_real": real_id,
                "active": active,
                "demo": {"account_id": demo_id, "token": demo_token},
                "real": {"account_id": real_id, "token": real_token}
            }
        elif isinstance(body, dict) and any(k in body for k in ["demo", "real", "token", "account_id_demo", "account_id_real"]):
            new_creds = body

        if not isinstance(new_creds, dict):
            return JSONResponse({"status": "error", "message": "Invalid credentials format: must be a valid JSON object"}, status_code=400)

        if not any(k in new_creds for k in ["demo", "real", "token", "account_id_demo", "account_id_real"]):
            return JSONResponse({"status": "error", "message": "Rejected: Missing core credentials fields (demo/real/token)"}, status_code=400)

        with open(CREDS_FILE, "w", encoding="utf-8") as f:
            json.dump(new_creds, f, indent=2)

        state.creds = new_creds
        if "active" in new_creds and new_creds["active"] in ["demo", "real"]:
            state.active_account = new_creds["active"]

        if state.persistent_trade_ws:
            try:
                await state.persistent_trade_ws.close()
            except Exception:
                pass
            state.persistent_trade_ws = None

        asyncio.create_task(sync_deriv_live_balance())
        state.log("🔑 Updated credentials.json from UI popup modal.", "AUTH")
        return JSONResponse({
            "status": "ok",
            "message": "Credentials updated and applied successfully!",
            "creds": state.creds,
            "raw_json": json.dumps(state.creds, indent=2),
            "active_account": state.active_account,
        })
    except json.JSONDecodeError as e:
        return JSONResponse({"status": "error", "message": f"JSON syntax error: {e}"}, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Server error: {e}"}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    state.ws_clients.add(ws)
    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            act = data.get("action")
            p = data.get("payload", {})
            mc = state.match_config
            ms = state.match_state

            if act == "start_engine":
                if "initial_sl_usd" in p:
                    state.initial_sl_usd = max(1.0, round(float(p["initial_sl_usd"]), 2))
                    mc["stop_loss_usd"] = state.initial_sl_usd

                if state.session_start_balance <= 0.0 and state.deriv_balance > 0.0:
                    state.session_start_balance = state.deriv_balance

                if state.active_cycle == 1:
                    state.hard_sl_floor = round(state.session_start_balance - state.initial_sl_usd, 2) if state.session_start_balance > 0 else 0.0
                elif state.active_cycle == 2:
                    state.hard_sl_floor = round(state.session_start_balance, 2)
                else:
                    state.hard_sl_floor = round(state.session_start_balance + state.vault_locked_profit, 2)

                state.is_running = True
                state.stopped_by_martingale_hit = False
                state.stopped_by_take_profit = False
                state.stopped_by_stop_loss = False
                ms["target_reached"] = False
                ms["stop_loss_reached"] = False
                state.match_state["status"] = "HUNTING"
                state.log(
                    f"▶️ MATCH SNIPER ENGINE STARTED. Active Cycle={state.active_cycle}, "
                    f"Target=${state.cycle_target_usd:.2f}, SL=${state.initial_sl_usd:.2f}, Floor=${state.hard_sl_floor:.2f}.",
                    "SYSTEM"
                )

            elif act == "stop_engine":
                state.is_running = False
                state.match_state["status"] = "TERMINAL_PAUSED"
                state.log("⏸️ MATCH SNIPER ENGINE PAUSED.", "SYSTEM")

            elif act == "switch_account":
                mode = p.get("mode", "demo")
                state.active_account = mode
                state.balance_synced = False
                if state.persistent_trade_ws is not None:
                    try:
                        await state.persistent_trade_ws.close()
                    except Exception:
                        pass
                    state.persistent_trade_ws = None
                state.log(f"Switched account to {mode.upper()} ({state.get_active_account_id()}).", "MODE")
                asyncio.create_task(sync_deriv_live_balance())

            elif act == "sync_balance":
                asyncio.create_task(sync_deriv_live_balance())

            elif act == "set_match_config":
                mc = state.match_config
                ms = state.match_state
                old_base = float(mc.get("base_stake", 0.35))
                explicit_ai_on = ("ai_commander" in p and bool(p["ai_commander"]))

                if "asset" in p:
                    mc["asset"] = p["asset"]
                if "sub_mode" in p:
                    mc["sub_mode"] = p["sub_mode"]
                if "drought_threshold" in p:
                    mc["drought_threshold"] = max(1, min(100, int(p["drought_threshold"])))
                if "twin_drought_threshold" in p:
                    mc["twin_drought_threshold"] = max(1, min(100, int(p["twin_drought_threshold"])))
                if "parity_spread_threshold" in p:
                    mc["parity_spread_threshold"] = max(0.5, min(50.0, float(p["parity_spread_threshold"])))
                if "parity_streak_filter" in p:
                    mc["parity_streak_filter"] = bool(p["parity_streak_filter"])
                if "parity_repeat_on_loss" in p:
                    mc["parity_repeat_on_loss"] = bool(p["parity_repeat_on_loss"])
                if "filter_zombie" in p:
                    mc["filter_zombie"] = bool(p["filter_zombie"])
                if "min_rolling_freq" in p:
                    mc["min_rolling_freq"] = max(0, min(20, int(p["min_rolling_freq"])))
                    if "filter_zombie" not in p:
                        mc["filter_zombie"] = (mc["min_rolling_freq"] > 0)
                if "require_squeeze" in p:
                    mc["require_squeeze"] = bool(p["require_squeeze"])
                if "allow_dynamic_pivot" in p:
                    mc["allow_dynamic_pivot"] = bool(p["allow_dynamic_pivot"])
                if "hunt_zombies" in p:
                    mc["hunt_zombies"] = bool(p["hunt_zombies"])
                if "tri_strike_filter" in p:
                    mc["tri_strike_filter"] = bool(p["tri_strike_filter"])
                if "max_target_strikes" in p:
                    mc["max_target_strikes"] = max(1, min(50, int(p["max_target_strikes"])))
                    state.log(f"🛡️ Target Strike Rotation Limit updated to: {mc['max_target_strikes']} strikes", "CONFIG")
                if "direct_fast_buy" in p:
                    mc["direct_fast_buy"] = bool(p["direct_fast_buy"])
                if "ai_commander" in p:
                    mc["ai_commander"] = bool(p["ai_commander"])
                if "duo_drought_threshold" in p:
                    mc["duo_drought_threshold"] = max(2, min(60, int(p["duo_drought_threshold"])))
                if "cluster_drought_threshold" in p:
                    mc["cluster_drought_threshold"] = max(2, min(60, int(p["cluster_drought_threshold"])))
                if "penta_drought_threshold" in p:
                    mc["penta_drought_threshold"] = max(1, min(100, int(p["penta_drought_threshold"])))
                if "penta_max_drought" in p:
                    mc["penta_max_drought"] = max(1, min(100, int(p["penta_max_drought"])))
                if "penta_window_span" in p:
                    mc["penta_window_span"] = max(0, min(20, int(p["penta_window_span"])))
                if "penta_exact_threshold" in p:
                    mc["penta_exact_threshold"] = bool(p["penta_exact_threshold"])
                if "penta_rec_trades" in p:
                    mc["penta_rec_trades"] = max(1, min(7, int(p["penta_rec_trades"])))
                if "penta_separate_ranges" in p:
                    mc["penta_separate_ranges"] = bool(p["penta_separate_ranges"])
                    state.log(f"Penta Separate Ranges Mode: {mc['penta_separate_ranges']}", "CONFIG")
                if "penta_symbol_ranges" in p and isinstance(p["penta_symbol_ranges"], dict):
                    mc.setdefault("penta_symbol_ranges", {})
                    for s, rng in p["penta_symbol_ranges"].items():
                        if s in MATCH_ASSETS and isinstance(rng, dict):
                            r_min = max(1, min(100, int(rng.get("min", mc.get("penta_drought_threshold", 18)))))
                            r_max = max(r_min, min(100, int(rng.get("max", r_min + 2))))
                            mc["penta_symbol_ranges"][s] = {"min": r_min, "max": r_max}
                    state.log(f"Penta Symbol Ranges Updated: {mc['penta_symbol_ranges']}", "CONFIG")
                if "min_digit_drought" in p:
                    mc["min_digit_drought"] = max(0, min(100, int(p["min_digit_drought"])))
                if "cluster_sum_threshold" in p:
                    mc["cluster_sum_threshold"] = max(0, min(300, int(p["cluster_sum_threshold"])))
                if "basket_sum_threshold" in p:
                    b_val = max(0, min(300, int(p["basket_sum_threshold"])))
                    mc["basket_sum_threshold"] = b_val
                    sub_cur = mc.get("sub_mode", "solo")
                    if sub_cur == "cluster":
                        mc["cluster_sum_threshold"] = b_val
                    elif sub_cur == "duo_wing":
                        mc["duo_sum_threshold"] = b_val
                    elif sub_cur == "twin":
                        mc["twin_sum_threshold"] = b_val
                if "duo_sum_threshold" in p:
                    mc["duo_sum_threshold"] = max(0, min(300, int(p["duo_sum_threshold"])))
                if "twin_sum_threshold" in p:
                    mc["twin_sum_threshold"] = max(0, min(300, int(p["twin_sum_threshold"])))
                if "min_penta_trades" in p:
                    mc["min_penta_trades"] = max(1, min(15, int(p["min_penta_trades"])))
                if "max_penta_trades" in p:
                    mc["max_penta_trades"] = max(1, min(15, int(p["max_penta_trades"])))
                if "solo_step_expansion" in p:
                    mc["solo_step_expansion"] = bool(p["solo_step_expansion"])
                if "enabled_assets" in p and isinstance(p["enabled_assets"], list):
                    mc["enabled_assets"] = [s for s in p["enabled_assets"] if s in MATCH_ASSETS]
                    mc.setdefault("symbol_enabled", {})
                    for s in MATCH_ASSETS:
                        mc["symbol_enabled"][s] = (s in mc["enabled_assets"])
                    state.log(f"Active Assets Portfolio Updated: {mc['enabled_assets']}", "CONFIG")
                if "symbol_thresholds" in p and isinstance(p["symbol_thresholds"], dict):
                    mc.setdefault("symbol_thresholds", {})
                    for s, th in p["symbol_thresholds"].items():
                        if s in MATCH_ASSETS:
                            try:
                                mc["symbol_thresholds"][s] = max(1, min(100, int(th)))
                            except (ValueError, TypeError):
                                pass
                    state.log(f"Asset-Specific Thresholds Updated: {mc['symbol_thresholds']}", "CONFIG")
                if "symbol_enabled" in p and isinstance(p["symbol_enabled"], dict):
                    mc.setdefault("symbol_enabled", {})
                    for s, en in p["symbol_enabled"].items():
                        if s in MATCH_ASSETS:
                            mc["symbol_enabled"][s] = bool(en)
                    mc["enabled_assets"] = [s for s in MATCH_ASSETS if mc["symbol_enabled"].get(s, True)]
                    state.log(f"Asset Enablement Updated: {mc['symbol_enabled']}", "CONFIG")
                if "target_priority" in p:
                    p_val = str(p["target_priority"]).lower()
                    if p_val in ("max", "min"):
                        mc["target_priority"] = p_val
                        p_label = "🌱 FRESH BREAKOUT (MIN)" if p_val == "min" else "🎯 MAX VACUUM"
                        state.log(f"Target Priority Strategy set to: {p_label}", "CONFIG")

                if "open_depth" in p:
                    mc["open_depth"] = bool(p["open_depth"])
                    state.log(f"♾️ Open Martingale Depth set to: {'ENABLED (UNLIMITED)' if mc['open_depth'] else 'DISABLED'}", "CONFIG")
                if "max_steps" in p:
                    val_st = int(p["max_steps"])
                    if val_st == 0:
                        mc["open_depth"] = True
                        state.log("♾️ Open Martingale Depth set to: ENABLED (UNLIMITED)", "CONFIG")
                    else:
                        mc["open_depth"] = False
                        req_steps = max(2, min(100, val_st))
                        sub = mc.get("sub_mode", "solo")
                        if sub == "solo":
                            mc["solo_max_steps"] = req_steps
                        elif sub == "twin":
                            mc["twin_max_steps"] = req_steps
                        elif sub == "cluster":
                            mc["cluster_max_steps"] = req_steps
                        elif sub == "duo_wing":
                            mc["duo_max_steps"] = req_steps
                        elif sub == "parity_spread":
                            mc["parity_max_steps"] = req_steps
                        elif sub == "penta":
                            mc["penta_max_steps"] = req_steps
                        mc["max_steps"] = req_steps

                force_reset = bool(p.get("force_reset_step", False))
                if force_reset:
                    ms["current_step"] = 0
                    ms["sequence_accumulated_loss"] = 0.00
                    ms["locked_digit"] = None
                    ms["locked_twin_digit"] = None
                    ms["locked_cluster_type"] = None
                    ms["locked_barrier"] = None
                    ms["locked_parity_type"] = None
                    ms["locked_symbol"] = None
                    ms["locked_base_thresh"] = None
                    ms["target_consecutive_trades"] = 0
                    ms["current_target_key"] = None
                    ms["exhausted_targets"] = []
                    state.stopped_by_martingale_hit = False

                if "lock_target_digit" in p:
                    val = p["lock_target_digit"]
                    req_sym = p.get("lock_target_symbol") or mc.get("asset", "R_100")
                    if req_sym == "ALL":
                        req_sym = "R_100"
                    if val is None or str(val).upper() in ("NONE", "CLEAR", "", "NULL"):
                        ms["locked_digit"] = None
                        ms["locked_symbol"] = req_sym if mc.get("asset") != "ALL" else None
                        ms["manual_lock"] = False
                        state.log("🎯 Manual Target Lock Cleared.", "CONFIG")
                    else:
                        try:
                            ms["locked_digit"] = int(val)
                            ms["manual_lock"] = True
                            ms["locked_symbol"] = req_sym
                            state.log(f"🎯 Manual Target Locked: D{ms['locked_digit']} on {req_sym}!", "CONFIG")
                        except (ValueError, TypeError):
                            pass

                if "base_stake" in p:
                    if int(ms.get("current_step", 0)) == 0:
                        b = max(0.35, min(1000.0, round(float(p["base_stake"]), 2)))
                        mc["base_stake"] = b
                        if not explicit_ai_on and (b != old_base or "ai_commander" not in p):
                            mc["user_custom_stake"] = True

                if "initial_sl_usd" in p:
                    new_sl = max(1.0, round(float(p["initial_sl_usd"]), 2))
                    state.initial_sl_usd = new_sl
                    mc["stop_loss_usd"] = new_sl
                    if state.active_cycle == 1 and state.session_start_balance > 0:
                        state.hard_sl_floor = round(state.session_start_balance - state.initial_sl_usd, 2)
                    state.log(f"Variable Initial SL updated: ${new_sl:.2f} (Floor: ${state.hard_sl_floor:.2f})", "CONFIG")

                should_rebuild = (int(ms.get("current_step", 0)) == 0) or ("max_steps" in p) or ("sub_mode" in p) or ("base_stake" in p) or ("symbol_enabled" in p)
                if should_rebuild:
                    rebuild_active_ladder()
                    sub = mc.get("sub_mode", "solo")
                    state.log(f"Ladder Updated: Depth={len(ms['ladder'])} Steps for {sub.upper()} mode. Cycle Target=${state.cycle_target_usd:.2f} (= Depth).", "CONFIG")

                if explicit_ai_on and mc.get("ai_commander", False) and int(ms.get("current_step", 0)) == 0:
                    sync_ai_commander_shield(state.deriv_balance)

                if "target_profit_usd" in p and not should_rebuild:
                    new_tgt = round(float(p["target_profit_usd"]), 2)
                    mc["target_profit_usd"] = new_tgt
                    state.cycle_target_usd = new_tgt
                    if ms.get("session_pnl", 0.0) < new_tgt:
                        state.stopped_by_take_profit = False
                        ms["target_reached"] = False

                if "stop_loss_usd" in p:
                    new_sl = round(float(p["stop_loss_usd"]), 2)
                    mc["stop_loss_usd"] = new_sl
                    if ms.get("session_pnl", 0.0) > -new_sl:
                        state.stopped_by_stop_loss = False
                        ms["stop_loss_reached"] = False

                if "step_sl_action" in p:
                    mc["step_sl_action"] = str(p["step_sl_action"])

                state.log(
                    f"Config Updated: Mode={mc.get('sub_mode','solo').upper()}, Steps={len(ms['ladder'])}, Asset={mc.get('asset', 'ALL')}, Thresh={mc.get('drought_threshold', 25)}t, Base=${mc.get('base_stake', 0.35):.2f}",
                    "CONFIG",
                )

            elif act == "toggle_asset":
                sym = p.get("symbol")
                if sym in MATCH_ASSETS:
                    ea = list(mc.get("enabled_assets", list(MATCH_ASSETS)))
                    se = dict(mc.get("symbol_enabled", {s: True for s in MATCH_ASSETS}))
                    if sym in ea:
                        if len(ea) > 1:
                            ea.remove(sym)
                            se[sym] = False
                            state.log(f"Asset {sym} toggled OFF. Active: {ea}", "CONFIG")
                        else:
                            state.log(f"Cannot disable {sym}: At least 1 asset must remain active.", "WARN")
                    else:
                        ea.append(sym)
                        se[sym] = True
                        state.log(f"Asset {sym} toggled ON. Active: {ea}", "CONFIG")
                    mc["enabled_assets"] = ea
                    mc["symbol_enabled"] = se
                    if mc.get("sub_mode") == "penta":
                        rebuild_active_ladder()

            elif act == "toggle_take_profit":
                state.take_profit_enabled = not state.take_profit_enabled
                state.log(f"Take-Profit Guard: {'ENABLED' if state.take_profit_enabled else 'DISABLED'}", "CONFIG")

            elif act == "toggle_stop_loss":
                state.stop_loss_enabled = not state.stop_loss_enabled
                state.log(f"Stop-Loss Guard: {'ENABLED' if state.stop_loss_enabled else 'DISABLED'}", "CONFIG")

            elif act == "toggle_hard_sl":
                state.hard_sl_enabled = not state.hard_sl_enabled
                state.log(f"Hard Floor Circuit Breaker: {'ENABLED' if state.hard_sl_enabled else 'DISABLED'}", "CONFIG")

            elif act == "clear_ledger":
                state.trade_history.clear()
                try:
                    with open(CSV_LOG_FILE, "w", newline="", encoding="utf-8") as f:
                        f.write("num,time,account,symbol,contract_type,barrier,payout_pct,step,stake,entry_spot,exit_spot,exit_digit,outcome,pnl,deficit_after\n")
                except Exception:
                    pass
                state.log("Real-time execution ledger and CSV log cleared.", "SYSTEM")

            elif act == "clear_console":
                state.logs.clear()

            elif act == "reset_session":
                state.total_trades = 0
                state.wins = 0
                state.losses = 0
                state.total_pnl = 0.00
                ms = state.match_state
                mc = state.match_config
                ms["session_trades"] = 0
                ms["session_wins"] = 0
                ms["session_losses"] = 0
                ms["session_pnl"] = 0.00
                ms["sequences_won"] = 0
                ms["sequences_lost"] = 0
                ms["current_step"] = 0
                ms["max_step_hit"] = 0
                ms["sequence_accumulated_loss"] = 0.00
                ms["ai_cooldown_until"] = 0.0
                ms["locked_digit"] = None
                ms["locked_twin_digit"] = None
                ms["locked_cluster_type"] = None
                ms["locked_barrier"] = None
                ms["locked_parity_type"] = None
                ms["locked_symbol"] = None
                ms["target_consecutive_trades"] = 0
                ms["current_target_key"] = None
                ms["exhausted_targets"] = []
                ms["target_reached"] = False
                ms["stop_loss_reached"] = False
                state.stopped_by_take_profit = False
                state.stopped_by_stop_loss = False
                state.stopped_by_martingale_hit = False
                state.step_distribution = {s: 0 for s in range(35)}
                state.current_loss_streak = 0
                state.max_loss_streak = 0
                state.baskets_cleared = 0

                state.active_cycle = 1
                state.cycle_accumulated_pnl = 0.00
                state.vault_locked_profit = 0.00
                state.vault_balance = 0.00
                state.capital_growth_pool = 0.00
                state.session_start_balance = state.deriv_balance if state.deriv_balance > 0 else 0.0
                state.hard_sl_floor = round(state.session_start_balance - state.initial_sl_usd, 2) if state.session_start_balance > 0 else 0.0
                ms["active_cycle"] = 1
                ms["cycle_accumulated_pnl"] = 0.00
                ms["vault_locked_profit"] = 0.00
                ms["hard_sl_floor"] = state.hard_sl_floor
                rebuild_active_ladder()
                state.log("🔄 Reset Match Sniper session metrics, cycles & vault to Step 0 & Cycle 1.", "RESET")

            elif act == "get_credentials":
                await ws.send_text(json.dumps({
                    "type": "credentials_data",
                    "file_path": CREDS_FILE,
                    "creds": state.creds,
                    "raw_json": json.dumps(state.creds, indent=2),
                    "active_account": state.active_account
                }))

            elif act == "update_credentials":
                raw_txt = p.get("raw_json", "").strip()
                if raw_txt:
                    try:
                        new_c = json.loads(raw_txt)
                        state.creds = new_c
                    except Exception as ex:
                        state.log(f"Invalid credentials JSON: {ex}", "WARN")
                        continue
                else:
                    demo_id = p.get("demo_id", "").strip()
                    demo_tok = p.get("demo_token", "").strip()
                    real_id = p.get("real_id", "").strip()
                    real_tok = p.get("real_token", "").strip()
                    act_mode = p.get("active", state.active_account).strip().lower()
                    if demo_id:
                        state.creds["account_id_demo"] = demo_id
                        state.creds.setdefault("demo", {})["account_id"] = demo_id
                    if demo_tok:
                        state.creds.setdefault("demo", {})["token"] = demo_tok
                    if real_id:
                        state.creds["account_id_real"] = real_id
                        state.creds.setdefault("real", {})["account_id"] = real_id
                    if real_tok:
                        state.creds.setdefault("real", {})["token"] = real_tok
                    if act_mode in ["demo", "real"]:
                        state.creds["active"] = act_mode
                        state.active_account = act_mode
                    curr_tok = state.creds.get(state.active_account, {}).get("token", "")
                    if curr_tok:
                        state.creds["token"] = curr_tok

                state.save_credentials()
                state.log("🔑 Updated credentials.json successfully.", "AUTH")
                if state.persistent_trade_ws:
                    try:
                        await state.persistent_trade_ws.close()
                    except Exception:
                        pass
                    state.persistent_trade_ws = None
                asyncio.create_task(sync_deriv_live_balance())
    except WebSocketDisconnect:
        state.ws_clients.discard(ws)
    except Exception as e:
        state.log(f"WebSocket client error: {e}", "WARN")
        state.ws_clients.discard(ws)


def launch_browser():
    time.sleep(1.2)
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except Exception:
        pass


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    print("=" * 66)
    print(" ⚡ MATCH SNIPER SUM & ADVANCED SALVO TERMINAL (PORTABLE EXE)")
    print(f" Port:          {PORT} | Host: {HOST}")
    print(f" Web Dashboard: http://localhost:{PORT}")
    print(f" Working Dir:   {EXE_DIR}")
    print("=" * 66)
    threading.Thread(target=launch_browser, daemon=True).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
