# No Hardcoding

## Configuration Values

- Never hardcode file paths, URLs, credentials, magic numbers, or environment-specific values
- Configuration sources (in order): environment variables → config files (YAML/TOML/JSON) → dataclass defaults
- Use `@dataclass` with `field(default_factory=lambda: os.getenv(...))` for config classes

## Magic Numbers & Strings

- Define constants at module level with descriptive names
- Use `Enum` or `IntEnum` for sets of related values
- Group project-wide constants in `constants.py`
