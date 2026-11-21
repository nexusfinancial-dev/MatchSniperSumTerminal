@echo off
title MATCH SNIPER SUM & SALVO TERMINAL (PORT 8565)
color 0A
cd /d "%~dp0"

echo ===============================================================================
echo       MATCH SNIPER SUM & SALVO TERMINAL - BASKET MATRIX & DROUGHT CITADEL
echo       - Portfolio: Multi-R (R_100, R_75, R_50, R_25, R_10)
echo       - Sub-Modes:
echo           1. Solo Match Sniper (+734.0%% • +1 Step Drought Expansion)
echo           2. Twin-Match Drought Bracketing (+317.0%% • Basket Sum & Min)
echo           3. Cluster Sniper: Under 3 / Over 6 (+213.0%% • Basket Sum & Min)
echo           4. Duo Wing: Under 2 / Over 7 (+354.5%% • Basket Sum & Min)
echo           5. Penta Salvo (+66.8%% • Min 3+ Simultaneous Trades Filter)
echo       - Interface: Cyber Bento Grid (/ or /dashboard)
echo       - Command Center: http://localhost:8565
echo ===============================================================================
echo.
echo Launching Match Sniper Sum Standalone Engine on Port 8565...
echo.

start "" "http://localhost:8565"
python app.py

pause
