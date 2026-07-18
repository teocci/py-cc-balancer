# Meta: Crypto Trading Timeframes Context
# Format: AI Agent Optimized (Markdown)

## 1. Macro / Global Context (High Timeframe - HTF)
### 1W (1-Week)
- **Primary Function**: Global trend identification, macro support/resistance (S/R), market cycle phase detection.
- **Agent Action**: Map structural boundaries and liquidity pools.
- **Common Practice**: Establishing "global levels" on the 1W timeframe is a highly standard and recommended practice in technical analysis. Higher timeframes filter out intraday noise and algorithmic stop-hunts, providing high-probability structural anchors where major capital reacts.
- **Example (Ref: image_d2dee9.jpg)**: Mapping key macro boundaries over a multi-year span:
  - ATH (All-Time High): $126,300
  - Range High (RH): $76,000
  - Range Mid (RM): $68,000
  - Range Low (RL): $60,000

### 1D (1-Day)
- **Primary Function**: Directional bias establishment, swing trade setups, validation of 1W levels.
- **Agent Action**: Determine daily momentum (bullish/bearish/neutral) and daily close validation.
- **Example**: Checking if a daily candle closes above the 1W Range Mid ($68k) to confirm a continuation toward the Range High ($76k), rather than just wicking above it.

## 2. Intermediate / Swing Context (Medium Timeframe - MTF)
### 4H (4-Hour)
- **Primary Function**: Swing trade execution, intermediate structural shifts, pattern formation.
- **Agent Action**: Identify local S/R, draw trendlines, detect chart patterns (e.g., bull flags, head and shoulders, wedges).
- **Example**: Price rejects the 1W $76k RH level; the 4H timeframe shows a breakdown of an intermediate rising wedge, triggering a swing short entry.

### 1H (1-Hour)
- **Primary Function**: Intraday trend determination, momentum tracking, refining 4H zones.
- **Agent Action**: Establish day trading bias, track moving average crossovers.
- **Example**: Utilizing the 1H 200 EMA to determine intraday trend direction while price consolidates between 4H structural zones.

## 3. Micro / Execution Context (Low Timeframe - LTF)
### 15Min (15-Minute)
- **Primary Function**: Day trading execution, local structure breaks (BOS/CHOCH), precise entry/exit points.
- **Agent Action**: Execute trades based on HTF/MTF bias upon confirmation.
- **Example**: Waiting for a 15M Change of Character (CHOCH) to the upside after price taps the 1W $60k Range Low (RL) to confidently enter a long position with a tight stop loss.

### 5Min (5-Minute)
- **Primary Function**: Scalping, sniper entries, momentum bursts, high-frequency stop-loss management.
- **Agent Action**: High-frequency execution, micro-trend tracking, volume spike analysis.
- **Example**: Scalping the immediate volatility following a macro news release or refining a 15M entry to minimize stop-loss distance to fractions of a percent.

## 4. Multi-Timeframe Analysis (MTFA) Alignment Matrix
Agents should be programmed to check cascading alignments rather than trading single timeframes in isolation:
- **Swing Trade Logic**: 1W (Global Levels) -> 1D (Directional Bias) -> 4H (Execution Trigger)
- **Day Trade Logic**: 1D (Key Levels) -> 1H (Intraday Bias) -> 15Min (Execution Trigger)
- **Scalp Trade Logic**: 4H (Local Levels) -> 15Min (Micro Bias) -> 5Min (Execution Trigger)