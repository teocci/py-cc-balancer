# Security Practices

## Secrets Management

- Never hardcode or commit: API keys, credentials, tokens, passwords, private keys, connection strings
- Load secrets from environment variables using `os.getenv()` with a helper that raises on missing required values
- Use `.env` files locally with `python-dotenv`; never commit `.env` files
- `.gitignore` must include: `.env`, `.env.*`, `*.pem`, `*.key`, `*_key.json`, `secrets/`, `credentials/`
- Production: use secret management services (AWS Secrets Manager, Vault, Azure Key Vault)
- Never log or print secrets; mask them in logs (`key[:4]...key[-4:]`)

## Secure Coding

- **SQL injection:** Always use parameterized queries (`?` or `:name` placeholders), never f-strings/string interpolation
- **Path traversal:** Resolve paths and verify target is within base directory before file operations
- **Input validation:** Validate all external input (format, length, range) before processing
- **Command injection:** Never use `os.system()` or `shell=True`; use `subprocess.run()` with list arguments
- **Logging:** Sanitize dicts before logging by redacting keys like `password`, `api_key`, `token`, `secret`

## Dependencies

- Pin exact versions in `requirements.txt` or `pyproject.toml`
- Audit regularly with `pip-audit` or `safety check`
- Prefer stdlib over external packages when reasonable

## File Permissions

- Set restrictive permissions (600/700) on files containing sensitive data
