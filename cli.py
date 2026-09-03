"""Dependency-free command line interface for LogAgent.

Lets an operator check the install and environment configuration WITHOUT
pulling in any of the heavy runtime dependencies (MySQL connector, Kafka,
scikit-learn, Gemini SDK). Useful for triaging the classic "dashboard won't
start" cases caused by a missing/invalid config.
"""

import argparse
import os
import sys
from typing import Dict, List, Optional

__version__ = '1.0.0'

# Optional runtime knobs and the env vars that configure them.
REQUIRED_CONFIG = [
    'MYSQL_HOST', 'MYSQL_USER', 'MYSQL_DATABASE',
]
OPTIONAL_CONFIG = [
    'MYSQL_PASSWORD', 'MYSQL_PORT', 'MYSQL_ROOT_PASSWORD',
    'KAFKA_BOOTSTRAP_SERVERS', 'GEMINI_API_KEY', 'GEMINI_MODEL',
    'GEMINI_TEMPERATURE', 'FLASK_PORT',
]


def _check_config(env: Dict[str, str]) -> Dict[str, str]:
    """Return {var: status} for each required/optional config knob.

    Status is one of 'set', 'missing' (required) or 'unset' (optional).
    """
    status: Dict[str, str] = {}
    for var in REQUIRED_CONFIG:
        status[var] = 'set' if env.get(var) else 'missing'
    for var in OPTIONAL_CONFIG:
        status[var] = 'set' if env.get(var) else 'unset'
    return status


def _render_config(status: Dict[str, str]) -> List[str]:
    lines = []
    for var in REQUIRED_CONFIG:
        lines.append(f'  {var:<28} {status[var]}')
    for var in OPTIONAL_CONFIG:
        lines.append(f'  {var:<28} {status[var]}')
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='logagent',
        description='LogAgent runtime management tool (dependency-free).',
    )
    parser.add_argument(
        '--version', action='store_true',
        help='print the LogAgent version and exit',
    )
    parser.add_argument(
        '--check-config', action='store_true',
        help='report which runtime configuration is present/absent',
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f'logagent {__version__}')
        return 0

    if args.check_config:
        print(f'logagent {__version__} configuration check:')
        status = _check_config(dict(os.environ))
        required = REQUIRED_CONFIG
        missing = [v for v in required if status[v] == 'missing']
        print('\n'.join(_render_config(status)))
        print()
        if missing:
            print(f'{len(missing)} required variable(s) unset: {", ".join(missing)}')
            print('Set them (e.g. via .env) or the dashboard/database '
                  'components will not start.')
            return 1
        print('All required configuration present.')
        return 0

    parser.print_help()
    return 0


if __name__ == '__main__':
    sys.exit(main())