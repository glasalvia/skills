#!/usr/bin/env python3
"""
Build payload for adding a movie/series to *arr services.
Reads JSON lookup result from stdin, outputs JSON payload to stdout.

Usage: build_payload.py <service> <tmdb_or_tvdb_id> <quality_profile_id> <root_folder> <monitored> <search>

Service: radarr | sonarr
"""
import sys
import json

def main():
    if len(sys.argv) != 7:
        print(json.dumps({'error': 'Usage: build_payload.py <service> <id> <quality> <root> <mon> <search>', 'code': 'INVALID_ARGS'}))
        sys.exit(1)

    service = sys.argv[1].lower()
    media_id = int(sys.argv[2])
    quality_profile = int(sys.argv[3])
    root_folder = sys.argv[4]
    monitored = sys.argv[5].lower() == 'true'
    search = sys.argv[6].lower() == 'true'

    try:
        results = json.load(sys.stdin)
    except Exception as e:
        print(json.dumps({'error': f'Error reading JSON: {e}', 'code': 'JSON_PARSE_ERROR'}))
        sys.exit(1)

    if not results:
        print(json.dumps({'error': f'Media not found with ID: {media_id}', 'code': 'NOT_FOUND'}))
        sys.exit(1)

    item = results[0]

    if service == 'radarr':
        payload = {
            'tmdbId': item.get('tmdbId', media_id),
            'title': item.get('title', ''),
            'titleSlug': item.get('titleSlug', ''),
            'images': item.get('images', []),
            'year': item.get('year', 0),
            'qualityProfileId': quality_profile,
            'rootFolderPath': root_folder,
            'monitored': monitored,
            'minimumAvailability': 'announced',
            'addOptions': {
                'searchForMovie': search
            }
        }
    elif service == 'sonarr':
        payload = {
            'tvdbId': item.get('tvdbId', media_id),
            'title': item.get('title', ''),
            'titleSlug': item.get('titleSlug', ''),
            'images': item.get('images', []),
            'seasons': item.get('seasons', []),
            'year': item.get('year', 0),
            'qualityProfileId': quality_profile,
            'languageProfileId': 1,
            'rootFolderPath': root_folder,
            'monitored': monitored,
            'addOptions': {
                'searchForMissingEpisodes': search
            }
        }
    else:
        print(json.dumps({'error': f'Unknown service: {service}', 'code': 'INVALID_SERVICE'}))
        sys.exit(1)

    print(json.dumps(payload))


if __name__ == '__main__':
    main()