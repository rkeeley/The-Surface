# The Surface

Create and manage Spotify playlists with one song per artist in your library.


### Limitations

The Spotify web API [does not support adding local files to playlists](https://developer.spotify.com/documentation/general/guides/local-files-spotify-playlists). This script will ignore local files when deciding what to add to the Surface playlist.

Local files can be removed from playlists, so if an artist is found to be in the Surface playlist but not in the library, and the track in the playlist is a local one, the script will remove it.

### TODO

- I should host this somewhere
- change the code to use user logins instead of requiring so many tokens/keys
- make public on github when enough of this stuff is done
- Exiting by raising exceptions looks kind of awkward, even when the exception makes sense. Maybe exit with a bad
  return code, but more gracefully?
- documentation
- logging
    - Don't know if it would be worth logging all the changes made since it would slow down the script
    - but also it's python, so who maybe who cares
- parameterization
    - in .env file as `$ENV` variables (how Spotipy does it) or with something like `python-decouple`, as well as actual script parameters
    - toggles for removing tracks from the maintained playlist, adding new ones, etc.
    - sorting order? Sorting might be a bit of a pain with the API
    - more?
- Need to make sure local files work as expected both in the library and in the playlist

- sort the songs in the playlist by artist name
    - right now they're sorted by first-saved because of how the code works

- It's possible to search for playlists explicitly instead of looping through a user's playlists to find one in particular, but I don't know if it will always return the user's playlists first. For example, the following code sets `managed_pl` to my copy of "The Surface", but the Spotify API docs don't say if that will always happen. Nine additional playlists were returned with this query.

        results = sp.search(q='playlist:' + 'The Surface', type='playlist')
        managed_pl = results['playlists']['items'][0]

