# ⚡ Match Sniper Sum & Advanced Salvo Terminal

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%26%20Uvicorn-009688.svg)](https://fastapi.tiangolo.com/)
[![Support on Giveth](https://img.shields.io/badge/Giveth-Support%20Research-blueviolet?style=flat&logo=ethereum)](https://www.giveth.io/project/fuse-terminal-quant-research-and-algorithmic-engine)

An open-source, institutional-grade quantitative execution engine and reactive web dashboard designed for synthetic volatility derivatives (Deriv platform). Built from independent empirical mathematical research, **Match Sniper Sum Terminal** delivers ultra-low latency execution via persistent WebSockets, paired with disciplined non-linear risk containment.

---

## 🎯 Core Features & System Architecture

### 1. Ultra-Low Latency WebSocket Architecture
- **Persistent Connection Pool:** Bypasses per-trade handshake overhead using persistent TCP sockets with `TCP_NODELAY` optimization.
- **Dynamic OTP Authentication:** Seamlessly integrates with Deriv's One-Time-Password authorization endpoints.
- **Real-Time Reactive UI:** Full duplex WebSocket telemetry streaming microsecond tick states, barrier pricing, and execution metrics to the local web dashboard.

### 2. Algorithmic Risk Management Mechanics
- **1-1-2 Ratchet Compounding:** Systematic progression engine designed to lock in net fractional gains without exponential liquidation exposure.
- **3-Strike Dynamic Rotation:** Multi-symbol target rotation that detects signal degradation and automatically pivots asset focus upon consecutive target misses.
- **Empirical Capital Protection:** Bounded loss mechanics enforcing maximum deficit thresholds per session.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10 or higher
- Modern web browser (Chrome, Edge, Firefox, Brave)
- Deriv account (Demo or Real) with API Token

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/nexusfinancial-dev/MatchSniperSumTerminal.git
cd MatchSniperSumTerminal
pip install -r requirements.txt
```

### 2. Configure Credentials
Copy the example configuration file to create your local `credentials.json`:
```bash
cp credentials.example.json credentials.json
```
Edit `credentials.json` with your Deriv API token and account ID:
```json
{
  "token": "YOUR_API_TOKEN",
  "account_id_demo": "VRTC12345678",
  "account_id_real": "CR12345678",
  "active": "demo"
}
```
> **Security Notice:** `credentials.json` is automatically excluded by `.gitignore`. Your private tokens and account credentials never leave your local machine.

### 3. Launch the Terminal
```bash
python app.py
```
Or simply double-click `START_MATCH_SNIPER_SUM.bat` on Windows.

The terminal will automatically launch on port `8565` and open the reactive dashboard:
👉 **`http://localhost:8565`**

---

## 📊 Scientific & Mathematical Proof
Explore the interactive mathematical proof and capital degradation models included in:
- `Match_Sniper_Capital_Proof.html` — Interactive statistical expectancy and total loss bounding proofs.
- `Match_Sniper_User_Manual.html` — Detailed operational documentation and strike management mechanics.

---

## 🛡️ Public Good & Research Disclaimer
This software is provided as an open-source educational and quantitative research tool under the MIT License. Trading synthetic volatility indices involves financial risk. The mathematical models are designed to enforce structural risk discipline, but no algorithmic system can guarantee profit. Always thoroughly test on Demo accounts first.

### Support Open Research
If this open-source tool and research adds value to your algorithmic development, consider supporting our ongoing quantitative modeling on Giveth:  
👉 **[Support Fuse Terminal on Giveth](https://www.giveth.io/project/fuse-terminal-quant-research-and-algorithmic-engine)**

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.
