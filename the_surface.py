from datetime import date

import spotipy

from decouple import config
from spotipy.oauth2 import SpotifyOAuth


def get_playlist(sp, name: str,
                 must_be_owner: bool = config('SURFACE_OWNED_PLAYLIST', default=False, cast=bool)):
    """Search Spotify for the playlist called `name` owned by the authenticated user and return it
    if found.

    This is a quick first attempt at getting the `SURFACE_PLAYLIST_NAME` playlist using the Spotify
    Search API.

    Because the search is on playlist name and not ID, it's possible for an undesired or unexpected
    playlist to be returned from the API. For example:

        - if the expected playlist has not been updated recently and a playlist with a similar name
          has, that similarly-named playlist might be the first result, even if it is not a popular
          playlist and the user has never seen it before.
        - if the logged-in user is not the playlist owner for the expected playlist and does not
          follow it, it's less likely for the playlist to appear first in the search response unless
          it has a unique name.

    These are both limitations of the Spotify Search API, and why this function is a hopeful first
    attempt. To guarantee that the current user's playlists will be found, use
    `get_playlist_thorough`.

    :param name: The name of the playlist to find
    :param must_be_owner: True if the current user must be the owner of the playlist.
        This can be useful to ensure that the correct playlist has been found, but won't work if the
        `SURFACE_PLAYLIST_NAME` playlist is collaborative and owned by another user.
    :return: None on error, or the `SURFACE_PLAYLIST_NAME` playlist object on success.
    """
    managed_pl = sp.search(q=f'"{name}"', type='playlist', limit=1)
    if not managed_pl:
        return None

    managed_pl = managed_pl['playlists']['items']
    if not managed_pl:
        return None

    if must_be_owner and managed_pl[0]['owner']['id'] != sp.current_user()['id']:
        return None

    return managed_pl[0]


def get_playlist_thorough(sp, name: str):
    """Search through the current user's playlists to find the one called :param name:, and return
    it if found.

    This will take longer than `get_playlist`, but it's more guaranteed to work (for playlists owned
    by the current user).
    """
    limit = 50
    offset = 0
    managed_pl = None
    playlists = sp.current_user_playlists(limit=limit, offset=offset)

    while not managed_pl and playlists:
        for pl in playlists['items']:
            if pl['name'] == name:
                managed_pl = pl
                break

        playlists = sp.next(playlists)

    return managed_pl


def get_or_create_playlist(sp, managed_pl_name: str):
    """Get the playlist called :param managed_pl_name:, asking to create it if not found"""

    managed_pl = get_playlist(sp, managed_pl_name)
    if not managed_pl:
        managed_pl = get_playlist_thorough(sp, managed_pl_name)

    if not managed_pl:
        answer = input(f'No playlist named "{managed_pl_name}" found. Create one? [(y)/n] ')
        if not answer or answer.lower()[0] == 'y':
            managed_pl = sp.user_playlist_create(
                sp.current_user()['id'], managed_pl_name, public=False,
                description=f"Created by the_surface.py on {date.today()}")
            print(f'\tPlaylist "{managed_pl_name}" has been created.')
        else:
            raise SystemExit(f'No playlist called {managed_pl_name} found. Nothing to do.')

    return managed_pl


def get_playlist_tracks(sp, pl: dict):
    """Return a dict of artist_id:track_id for each track in the playlist `pl`

    :param pl: The actual playlist dict from the Spotify API
    """
    limit = 100
    pl_tracks = {}
    results = sp.user_playlist_tracks(playlist_id=pl['id'], limit=limit)

    if not results['items']:
        return None

    while results:
        for track in results['items']:
            if track['track']['is_local']:
                # Local tracks are not supported because there's no way to add them to playlists via
                # the Spotify Web API.
                continue

            artist = track['track']['artists'][0]['id']
            pl_tracks[artist] = track['track']['id']

        if not results['next']:
            # No more tracks in the playlist.
            break

        results = sp.next(results)

    return pl_tracks


def get_artist_first_saved_tracks(sp):
    """Return {artist_id:track_id} for the longest-saved track of each artist in the Library"""

    # Get the total tracks to search from old to new in the Library
    total_tracks = sp.current_user_saved_tracks(limit=1)['total']
    limit = 50 if total_tracks > 50 else total_tracks
    offset = total_tracks - limit
    artist_tracks = {}
    results = sp.current_user_saved_tracks(limit=limit, offset=offset)

    if not results['items']:
        return None

    while results:
        for r in results['items'][::-1]:
            artist = r['track']['artists'][0]['id']
            if artist not in artist_tracks:
                artist_tracks[artist] = r['track']['id']

        offset -= limit
        if offset < 0:
            if limit != 50:
                # limit != 50 only when there are fewer than 50 tracks to be analyzed, i.e. the
                # previous loop was the last
                break

            limit = -offset
            offset = 0

        results = sp.previous(results)

    return artist_tracks


def get_artist_difference(lib_artist_tracks, pl_artist_tracks, clean_pl_artist_tracks=True):
    """Return a list of track ids for artists that are in `lib_artist_tracks`, but not in
    `pl_artist_tracks`, and removes tracks """
    # Might want to make this a wrapper function that calls the other functions
    new_tracks = []
    for artist in lib_artist_tracks:
        if artist in pl_artist_tracks:  # TODO: Should probably improve this
            # Don't care about this artist since they're already in the playlist
            if clean_pl_artist_tracks:
                del pl_artist_tracks[artist]
        else:
            # Store the associated track so it can be added in bulk later
            new_tracks.append(lib_artist_tracks[artist])

    return new_tracks


def main():
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=[
        'playlist-modify-public',
        'playlist-modify-private',
        'playlist-read-private',
        'user-library-read',
    ]))

    managed_pl_name = config('SURFACE_PLAYLIST_NAME', default='The Surface', cast=str)
    add_new_artists = config('SURFACE_ADD_NEW_ARTISTS', default=True, cast=bool)
    remove_missing_artists = config('SURFACE_REMOVE_MISSING_ARTISTS', default=True, cast=bool)

    if not add_new_artists and not remove_missing_artists:
        raise SystemExit(
            'The SURFACE_ADD_NEW_ARTISTS and SURFACE_REMOVE_MISSING_ARTISTS environment variables are both False. Nothing to do.'
        )

    print(f'Getting managed playlist "{managed_pl_name}"')
    managed_pl = get_or_create_playlist(sp, managed_pl_name)

    print(f'Collecting tracks from "{managed_pl_name}"... ')
    pl_tracks = get_playlist_tracks(sp, managed_pl) or []
    print(f'\tFound {len(pl_tracks)} tracks.')

    print('Gathering Library artist tracks... ')
    lib_artist_tracks = get_artist_first_saved_tracks(sp)
    print(f'\tFound {len(lib_artist_tracks)} tracks.')

    print(f'Finding the difference between Library and "{managed_pl_name}" artists')
    new_tracks = get_artist_difference(lib_artist_tracks, pl_tracks)

    if pl_tracks and remove_missing_artists:
        print(f'Removing tracks from "{managed_pl_name}" for artists that are not in the Library')
        sp.playlist_remove_all_occurrences_of_items(
            managed_pl['id'],
            [pl_tracks[a] for a in pl_tracks])

    if add_new_artists:
        print(f'Adding tracks from new artists to "{managed_pl_name}"')
        for chunk in range(0, len(new_tracks), 100):  # API limit is 100 additions per call
            sp.playlist_add_items(managed_pl['id'], new_tracks[chunk:chunk + 100])

    print(f'\nPlaylist management is complete! Listen to {managed_pl_name} at {managed_pl["external_urls"]["spotify"]}')


if __name__ == '__main__':
    main()
