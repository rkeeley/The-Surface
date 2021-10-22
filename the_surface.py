from datetime import date

import spotipy

from decouple import config
from spotipy.oauth2 import SpotifyOAuth


def get_playlist(sp, name):
    """Search Spotify for the playlist called `name` owned by the authenticated user and return it
    if found.

    This /should/ return `sp.current_user()`'s playlists before any public ones, even if `name` is a
    private playlist, but the Spotify Web API doesn't guarantee that. It actually says, "Only
    popular public playlists are returned," and, "You cannot search for playlists within a user's
    library," but those both seem to be false.

    I have seen playlists I've never opened before be returned before playlists I'm following when
    those new playlists have been updated more recently than the followed playlists, but I don't
    know how that works with playlists I own.
    """
    managed_pl = sp.search(q=name, type='playlist', limit=1)['playlists']['items']
    if not managed_pl or managed_pl[0]['owner']['id'] != sp.current_user()['id']:
        return None

    return managed_pl[0]


def get_playlist_thorough(sp, name):
    """Search through sp.current_user()'s playlists to find the one called `name`.

    This will take longer than `get_playlist`, but it's more guaranteed to work according to the
    API.
    """
    limit = 50
    offset = 0
    managed_pl = None

    while not managed_pl:
        playlists = sp.current_user_playlists(limit=limit, offset=offset)

        if not playlists['items']:
            # None of the user's playlists matched. Time to stop looking
            return None

        for pl in playlists['items']:
            if pl['name'] == name:
                managed_pl = pl
                break

        offset += limit

    return managed_pl


def get_playlist_tracks(sp, pl):
    """Return a dict of artist_id:track_id for each track in the playlist `pl`"""
    limit = 100
    offset = 0
    pl_tracks = {}
    results = sp.user_playlist_tracks(playlist_id=managed_pl['id'], limit=limit, offset=offset)

    while results['items']:
        for t in results['items']:
            if t['track']['is_local']:
                # Local tracks are not supported for now. Maybe log something for the user.
                continue

            artist = t['track']['artists'][0]['id']
            pl_tracks[artist] = t['track']['id']

        offset += limit
        results = sp.user_playlist_tracks(playlist_id=managed_pl['id'], limit=limit, offset=offset)

    return pl_tracks


def get_artist_first_saved_tracks(sp):
    """Returns a dict of artist_id:track_id for the least-recently saved track of each artist in the Library"""

    # Get the total tracks to search from old to new in the Library
    total_tracks = sp.current_user_saved_tracks(limit=1)['total']
    limit = 50 if total_tracks > 50 else total_tracks
    offset = total_tracks - limit
    artist_tracks = {}
    results = sp.current_user_saved_tracks(limit=limit, offset=offset)

    while results['items']:
        for r in results['items'][::-1]:
            artist = r['track']['artists'][0]['id']
            if artist not in artist_tracks:
                artist_tracks[artist] = r['track']['id']

        offset -= limit
        if offset < 0:
            if limit != 50:
                # limit != 50 only when there are fewer than 50 tracks to be analyzed, i.e. the previous
                # loop was the last
                break

            limit = -offset
            offset = 0

        results = sp.current_user_saved_tracks(limit=limit, offset=offset)

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


if __name__ == '__main__':
    scope = [
        'playlist-modify-public',
        'playlist-modify-private',
        'playlist-read-private',
        'user-library-read',
    ]

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    managed_pl_name = config('SURFACE_PLAYLIST_NAME', default='The Surface', cast=str)
    add_new_artists = config('SURFACE_ADD_NEW_ARTISTS', default=True, cast=bool)
    remove_missing_artists = config('SURFACE_REMOVE_MISSING_ARTISTS', default=True, cast=bool)

    if not add_new_artists and not remove_missing_artists:
        raise SystemExit(
            'The SURFACE_ADD_NEW_ARTISTS and SURFACE_REMOVE_MISSING_ARTISTS environment variables are both False. Nothing to do.'
        )

    print(f'Attempting to get the "{managed_pl_name}" playlist')
    managed_pl = get_playlist(sp, managed_pl_name)
    if not managed_pl:
        answer = input(f'No playlist named "{managed_pl_name}" found. Create one? [(y)/n] ')
        if not answer or answer.lower()[0] == 'y':
            managed_pl = sp.user_playlist_create(
                sp.current_user()['id'], managed_pl_name,
                description=f"Created by the_surface.py on {date.today()}")
            print(f'\tPlaylist "{managed_pl_name}" has been created.')
        else:
            raise SystemExit(f'No playlist called {managed_pl_name} found. Nothing to do.')

    print(f'Collecting tracks from "{managed_pl_name}"... ')
    pl_tracks = get_playlist_tracks(sp, managed_pl)
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
