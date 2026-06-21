# Troubleshooting

> **Source**: [ccxt Manual.md](https://github.com/ccxt/ccxt/blob/master/wiki/Manual.md) (Python-only excerpt)
> **Stats**: 46 lines · ~1,079 tokens · 4,316 chars
> **See also**: [Index](./README.md)

---

In case you experience any difficulty connecting to a particular exchange, do the following in order of precedence:

- Make sure that you have the most recent version of ccxt.
  Never trust your package installer (whether it is `npm`, `pip` or `composer`), instead always check your **actual (real) runtime version number** by running this code in your environment:
  ```python
  print('CCXT version:', ccxt.__version__)  # Python
  ```
- Check the [Issues](https://github.com/ccxt/ccxt/issues) or [Announcements](#announcements) for recent updates.
- Make sure you have not turned off [rate-limiter with `enableRateLimit: false`](#rate-limit) (If anyone has custom rate-limit solution built, ensure it does not misbehave).
- If you use ccxt's proxy functionality, ensure it does not misbehave.
- Turn `verbose = true` to get more detail about it!
  ```
  exchange = ccxt.binance()
  exchange.load_markets()
  exchange.verbose = True  # for less noise, you can set that after `load_markets`, but if the error happens during `load_markets` then place this line before it
  # ... your codes here ...
  ```
  Your [code to reproduce the issue + verbose output is required](https://github.com/ccxt/ccxt/wiki/FAQ#what-is-required-to-get-help) in order to get help.
- Python people can turn on DEBUG logging level with a standard pythonic logger, by adding these two lines to the beginning of their code:
  ```python
  import logging
  logging.basicConfig(level=logging.DEBUG)
  ```
- Use verbose mode to make sure that the used API credentials correspond to the keys you intend to use. Make sure there's no confusion of keypairs.
- **Try a fresh new keypair if possible.**
- Read the answers to Frequently Asked Questions: https://github.com/ccxt/ccxt/wiki/FAQ
- Check the permissions on the keypair with the exchange website!
- Check your nonce. If you used your API keys with other software, you most likely should [override your nonce function](#overriding-the-nonce) to match your previous nonce value. A nonce usually can be easily reset by generating a new unused keypair. If you are getting nonce errors with an existing key, try with a new API key that hasn't been used yet.
- Check your request rate if you are getting nonce errors. Your private requests should not follow one another quickly. You should not send them one after another in a split second or in short time. The exchange will most likely ban you if you don't make a delay before sending each new request. In other words, you should not hit their rate limit by sending unlimited private requests too frequently. Add a delay to your subsequent requests or enable the built-in rate-limiter, like shown in the long-poller [examples](https://github.com/ccxt/ccxt/tree/master/examples), also [here](#order-book--market-depth).
- Read the [docs for your exchange](https://github.com/ccxt/ccxt/wiki/Exchanges) and compare your verbose output to the docs.
- Check your connectivity with the exchange by accessing it with your browser.
- Check your connection with the exchange through a [proxy](#proxy).
- Try accesing the exchange from a different computer or a remote server, to see if this is a local or global issue with the exchange.
- Check if there were any news from the exchange recently regarding downtime for maintenance. Some exchanges go offline for updates regularly (like once a week).
- Make sure that your system time in sync with the rest of the world's clocks since otherwise you may get invalid nonce errors.

**Further Notes:**

- Use the `verbose = true` option or instantiate your troublesome exchange with `new ccxt.exchange ({ 'verbose': true })` to see the HTTP requests and responses in details. The verbose output will also be of use for us to debug it if you submit an issue on GitHub.
- Use DEBUG logging in Python!
- Some exchanges are not available in certain countries, using a [proxy](#proxy) might be the solution in such cases.
- If you are getting authentication errors or *'invalid keys'* errors, those are most likely due to a nonce issue.
- Some exchanges do not state it clearly if they fail to authenticate your request. In those circumstances they might respond with an exotic error code, like HTTP 502 Bad Gateway Error or something that's even less related to the actual cause of the error.
