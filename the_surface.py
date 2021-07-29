import spotipy
from spotipy.oauth2 import SpotifyOAuth

scope = [
    'playlist-modify-public',
    'playlist-modify-private',
    'playlist-read-private',
    'user-library-read',
]

managed_pl_name = 'The Surface'  # TODO: Parameterize

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))


# Get the managed playlist
limit = 50  # TODO: It seems like the allowed limit is different for different requests
offset = 0
managed_pl = None

while not managed_pl:
    playlists = sp.current_user_playlists(limit=limit, offset=offset)
    
    if not playlists['items']:
        raise KeyError(
            f'Could not find a playlist called "{managed_pl_name}" for user {sp.current_user()["name"]}'
        )

    for pl in playlists['items']:
        if pl['name'] == managed_pl_name:
            managed_pl = pl
            break

    offset += limit


# Get the oldest tracks from all artists in library
limit = 50
offset = 0
artist_tracks = {}
results = sp.current_user_saved_tracks(limit=limit, offset=offset)

while results['items']:
    # TODO: This is very inefficient, but I'm not sure how else to get artists/sorted library tracks
    # TODO: How does this work for local files?
    for r in results['items']:
        artist = r['track']['artists'][0]['id']
        artist_tracks[artist] = r['track']['id']

    offset += limit
    results = sp.current_user_saved_tracks(limit=limit, offset=offset)


# Get tracks in managed playlist
limit = 100
offset = 0
pl_tracks = {}
results = sp.user_playlist_tracks(playlist_id=managed_pl['id'], limit=limit, offset=offset)

while results['items']:
    for t in results['items']:
        artist = t['track']['artists'][0]['id']
        if artist is None or t['track']['id'] is None:  # Ignore local files (TODO?)
            continue
        pl_tracks[artist] = t['track']['id']

    offset += limit
    results = sp.user_playlist_tracks(playlist_id=managed_pl['id'], limit=limit, offset=offset)


# For each artist in library, if artist not in playlist, add the first-saved song to playlist
new_tracks = []
for artist in artist_tracks:
    if artist in pl_tracks:
        # Don't care about this artist since they're already in the playlist
        del pl_tracks[artist]
    else:
        # Store the associated track so it can be added in bulk later
        new_tracks.append(artist_tracks[artist])

# Remove the tracks from pl_tracks that are not in the library
if pl_tracks:
    sp.playlist_remove_all_occurrences_of_items(managed_pl['id'],
            [pl_tracks[a] for a in pl_tracks if pl_tracks[a] is not None])  # TODO: fix local files

# Add new songs from the library into the playlist
sp.playlist_add_items(managed_pl['id'], new_tracks)




# Think about multiple songs from saved artists in the playlist. I guess I don't care since either
#   the user created the pl themselves to their liking or it will have been created by this program,
#   which will have used the oldest song in the lib by default.
