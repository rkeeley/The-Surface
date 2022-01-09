# The Surface

Create and maintain Spotify playlists with one song for each artist in your library.

The Surface gives you a breadth-first look into your musical taste according to the songs you've saved.


## Usage Instructions

Running this code on your own requires a registered Spotify developer application with a client ID, client secret, and redirect URL. Check out the [Spotify App Settings Development Guide][1] for instructions on creating a developer application. The script expects that you have environment variables set for the Spotify application details, e.g.

```bash
export SPOTIPY_CLIENT_ID="<id>"
export SPOTIPY_CLIENT_SECRET="<secret>"
export SPOTIPY_REDIRECT_URI="<URI defined in the Spotify application>"
```

A python [virtual environment][2] is recommended, but not required. The pip modules in the [requirements.txt][3] file must be installed before the script can be run:

```bash
python -m pip install -r requirements.txt
```

At this point the script is ready to run. There are optional configuration options defined below, but for the
default experience, run `the_surface.py` as you would any other python program.


### Limitations

The Spotify web API [does not support adding local files to playlists][4]. This script will ignore local files when deciding what to add to the Surface playlist.

Local files can be removed from playlists, so if an artist is found to be in the Surface playlist but not in the library, and the track in the playlist is a local one, the script will remove it.


## Future Plans

- Currently this script scans your entire Library every time it runs. For cases in which only new song additions are
  desired, it could start from the Tracks that were saved more recently than the newest Track in the managed
  playlist.

- Documentation

- Local file handling
    - Document around them/improve the documentation above
    - Test more removal use cases

- Host this somewhere

- Sort the songs in the playlist by artist name
    - right now they're sorted by first-saved because of how the code works
    - way easier when creating a new playlist because you can sort in python before pushing to Spotify. In
      practice the playlist will already exist, so you'll need to figure out where in alphabetical order each new
      artist is, move the new song to that track number, then keep track of how many additions you've done while
      adding new songs so you can put more songs in the list afterwards without having to query for the track
      listing again


[1]: https://developer.spotify.com/documentation/general/guides/app-settings/#register-your-app
[2]: https://docs.python.org/3/tutorial/venv.html
[3]: https://github.com/rkeeley/The-Surface/blob/master/requirements.txt
[4]: https://developer.spotify.com/documentation/general/guides/local-files-spotify-playlists
