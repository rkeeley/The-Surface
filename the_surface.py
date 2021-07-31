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
        # TODO: Create it, or at least offer to create it
        raise KeyError(
            f'Could not find a playlist called "{managed_pl_name}" for user {sp.current_user()["name"]}'
        )

    for pl in playlists['items']:
        if pl['name'] == managed_pl_name:
            managed_pl = pl
            break

    offset += limit

# Go from least- to most-recently saved tracks in the library, storing the first-seen per artist
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

# Remove tracks from the playlist by artists which no longer have songs in the library
if pl_tracks:
    sp.playlist_remove_all_occurrences_of_items(managed_pl['id'],
            [pl_tracks[a] for a in pl_tracks if pl_tracks[a] is not None])  # TODO: fix local files

# Add songs from artists with saved library tracks which aren't in the playlist
# TODO: I'm not sure what the limit is for adding songs. I assumed the library would paginate these
#       or break them up, but it doesn't, so it has to be done here
def chunk(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]

for tracks in chunk(new_tracks, 50):
    sp.playlist_add_items(managed_pl['id'], tracks)
