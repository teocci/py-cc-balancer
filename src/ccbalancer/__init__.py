'''ccbalancer — an agent-driven crypto portfolio rebalancer CLI.

Keeps a target volatile/stablecoin ratio per trading pair on a CEX (via ccxt),
rebalancing with limit orders when drift exceeds a configurable no-trade band.
Designed to be invoked by an AI agent: token-efficient JSON output, a read-only
``plan`` path, and an explicit ``rebalance`` execution path.
'''

__all__ = ['__version__']

__version__ = '0.1.1'
