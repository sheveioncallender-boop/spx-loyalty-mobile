#!/usr/bin/env python3
"""Publisher-side Android build. Connection details never appear in customer UI."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request


def validate_config(config):
    if not isinstance(config, dict):
        raise ValueError('The connection file must contain a JSON object.')
    origin = config.get('JENNYS_API_URL', '')
    database = config.get('JENNYS_DATABASE', '')
    if not isinstance(origin, str) or not isinstance(database, str):
        raise ValueError('Address and database must be text.')
    origin, database = origin.strip(), database.strip()
    parsed = urllib.parse.urlsplit(origin)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment
            or '\\' in origin or any(c.isspace() or ord(c) < 32 for c in origin)
            or parsed.port == 0):
        raise ValueError('Use an HTTPS origin without /odoo, a path, query, or credentials.')
    if not database or len(database) > 128 or any(c.isspace() or ord(c) < 32 for c in database):
        raise ValueError('Copy the exact database name from the App connection screen.')
    return {'JENNYS_API_URL': origin.rstrip('/'), 'JENNYS_DATABASE': database}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def check_connection(config):
    payload = {'jsonrpc': '2.0', 'method': 'call', 'id': 1,
               'params': {'database': config['JENNYS_DATABASE']}}
    request = urllib.request.Request(
        config['JENNYS_API_URL'] + '/spx/mobile/v1/connection',
        data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'},
    )
    with urllib.request.build_opener(NoRedirect).open(request, timeout=25) as response:
        result = json.loads(response.read(8192)).get('result', {})
    if not isinstance(result, dict) or result.get('service') != 'spx_loyalty_mobile' or result.get('api_version') != 1:
        raise ValueError('This address does not expose the expected Jenny’s connector.')
    if not result.get('database_matches'):
        raise ValueError('The database name does not match this Odoo address.')
    if not result.get('enabled'):
        raise ValueError('Enable the customer app on the selected Odoo website first.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path, help='JSON downloaded from Odoo App connection')
    parser.add_argument('--flutter', default='flutter', help='Flutter executable')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    try:
        config = validate_config(json.loads(args.config.read_text()))
        check_connection(config)
    except (ValueError, OSError, urllib.error.URLError) as error:
        parser.exit(1, f'Connection check failed: {error}\n')
    print('Connector, website and database verified. No customer records changed.')
    if args.check_only:
        return
    app = Path(__file__).resolve().parents[1] / 'app'
    with tempfile.TemporaryDirectory(prefix='jennys-build-') as temporary:
        config_file = Path(temporary) / 'connection.json'
        config_file.write_text(json.dumps(config))
        environment = dict(os.environ, CI='true', TAR_OPTIONS='--no-same-owner')
        subprocess.run([
            args.flutter, 'build', 'apk', '--release', '--target-platform', 'android-arm64',
            f'--dart-define-from-file={config_file}',
        ], cwd=app, env=environment, check=True)
    print(app / 'build/app/outputs/flutter-apk/app-release.apk')


if __name__ == '__main__':
    main()
