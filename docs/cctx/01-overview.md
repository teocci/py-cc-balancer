# Overview

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 31 lines · ~505 tokens · 2,021 chars
> **See also**: [Index](./README.md)

---

The ccxt library is a collection of available crypto *exchanges* or exchange classes. Each class implements the public and private API for a particular crypto exchange. All exchanges are derived from the base Exchange class and share a set of common methods. To access a particular exchange from ccxt library you need to create an instance of corresponding exchange class. Supported exchanges are updated frequently and new exchanges are added regularly.

The structure of the library can be outlined as follows:


Full public and private HTTP REST APIs for all exchanges are implemented in JavaScript, Python, PHP, C#, Go and Java. WebSocket implementations are available in [CCXT Pro](https://ccxt.pro), with support for WebSocket streams.

- [**Exchanges**](#exchanges)
- [**Markets**](#markets)
- [**Implicit API**](#implicit-api)
- [**Unified API**](#unified-api)
- [**Public API**](#public-api)
- [**Private API**](#private-api)
- [**Error Handling**](#error-handling)
- [**Troubleshooting**](#troubleshooting)
- [**CCXT Pro**](#ccxt-pro)

## Social

- <sub>[![Twitter](https://img.shields.io/twitter/follow/ccxt_official?style=social)](https://twitter.com/ccxt_official)</sub> Follow us on Twitter
- <sub>[![Medium](https://img.shields.io/badge/read-our%20blog-black?logo=medium)](https://medium.com/@ccxt)</sub> Read our blog on Medium
- <sub>[![Discord](https://img.shields.io/discord/690203284119617602?logo=discord&logoColor=white)](https://discord.gg/dhzSKYU)</sub> Join our Discord
- <sub>[![Telegram Chat](https://img.shields.io/badge/CCXT-Chat-blue?logo=telegram)](https://t.me/ccxt_chat)</sub> CCXT Chat on Telegram (technical support)
<a name="announcements" id="announcements"></a>
- Announcement channels:
- - <sub>[![Telegram](https://img.shields.io/badge/CCXT-Channel-blue?logo=telegram)](https://t.me/ccxt_announcements)</sub>
- - <sub>[![Discord](https://img.shields.io/badge/CCXT-Channel-blue?logo=discord)](https://discord.com/channels/690203284119617602/1057748769690619984)</sub>

