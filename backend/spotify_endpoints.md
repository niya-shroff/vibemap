# Spotify Web API v1 — Full Endpoint Reference

Base URL:
https://api.spotify.com/v1

All requests require:
Authorization: Bearer {access_token}

---

# 1. ALBUMS

## Get Album
GET /albums/{id}
Query:
- market (optional)

## Get Several Albums
GET /albums?ids={ids}
Query:
- ids (required, comma-separated)
- market (optional)

## Get Album Tracks
GET /albums/{id}/tracks
Query:
- limit (optional)
- offset (optional)
- market (optional)

## Get New Releases
GET /browse/new-releases
Query:
- country (optional)
- limit (optional)
- offset (optional)

## Save Albums
PUT /me/albums
Body:
{
  "ids": ["album_id"]
}
Scope: user-library-modify

## Remove Albums
DELETE /me/albums
Query:
- ids

## Check Saved Albums
GET /me/albums/contains
Query:
- ids

---

# 2. ARTISTS

## Get Artist
GET /artists/{id}

## Get Several Artists
GET /artists?ids={ids}

## Get Artist Albums
GET /artists/{id}/albums
Query:
- include_groups
- market
- limit
- offset

## Get Top Tracks
GET /artists/{id}/top-tracks
Query:
- market (required)

## Get Related Artists
GET /artists/{id}/related-artists

---

# 3. TRACKS

## Get Track
GET /tracks/{id}
Query:
- market

## Get Several Tracks
GET /tracks?ids={ids}

## Get Audio Features (single)
GET /audio-features/{id}

## Get Audio Features (multiple)
GET /audio-features?ids={ids}

## Get Audio Analysis
GET /audio-analysis/{id}

---

# 4. SEARCH

## Search
GET /search
Query:
- q (required)
- type (album, artist, track, playlist, show, episode, audiobook)
- market
- limit
- offset
- include_external=audio

---

# 5. PLAYLISTS

## Get Playlist
GET /playlists/{playlist_id}

## Get Playlist Items
GET /playlists/{playlist_id}/tracks
Query:
- limit
- offset
- market
- fields

## Create Playlist
POST /users/{user_id}/playlists
Body:
{
  "name": "",
  "public": true,
  "collaborative": false,
  "description": ""
}

## Add Items
POST /playlists/{playlist_id}/tracks
Body:
{
  "uris": ["spotify:track:xxx"]
}

## Remove Items
DELETE /playlists/{playlist_id}/tracks
Body:
{
  "tracks": [
    { "uri": "spotify:track:xxx" }
  ]
}

## Update Playlist Details
PUT /playlists/{playlist_id}

## Change Cover Image
PUT /playlists/{playlist_id}/images
Body:
- base64 image string

## Get User Playlists
GET /users/{user_id}/playlists

## Get Current User Playlists
GET /me/playlists

---

# 6. USER PROFILE

## Get Current User
GET /me
Scope: user-read-private

## Get User Profile
GET /users/{user_id}

---

# 7. USER LIBRARY

## Tracks
GET    /me/tracks
PUT    /me/tracks
DELETE /me/tracks
GET    /me/tracks/contains?ids=

## Albums
GET    /me/albums
PUT    /me/albums
DELETE /me/albums
GET    /me/albums/contains

## Shows
GET    /me/shows
PUT    /me/shows
DELETE /me/shows
GET    /me/shows/contains

## Episodes
GET    /me/episodes
PUT    /me/episodes
DELETE /me/episodes
GET    /me/episodes/contains

## Audiobooks
GET    /me/audiobooks
PUT    /me/audiobooks
DELETE /me/audiobooks
GET    /me/audiobooks/contains

---

# 8. FOLLOW

## Follow Artists/Users
PUT /me/following?type=artist|user&ids=

## Unfollow
DELETE /me/following?type=artist|user&ids=

## Check Following
GET /me/following/contains?type=artist|user&ids=

## Get Followed Artists
GET /me/following?type=artist

---

# 9. PLAYER (Premium required)

## Get Playback State
GET /me/player

## Get Devices
GET /me/player/devices

## Get Currently Playing
GET /me/player/currently-playing

## Start Playback
PUT /me/player/play
Body:
{
  "context_uri": "",
  "uris": [],
  "position_ms": 0
}

## Pause Playback
PUT /me/player/pause

## Next Track
POST /me/player/next

## Previous Track
POST /me/player/previous

## Seek
PUT /me/player/seek?position_ms={ms}

## Volume
PUT /me/player/volume?volume_percent={0-100}

## Shuffle
PUT /me/player/shuffle?state=true|false

## Repeat
PUT /me/player/repeat?state=track|context|off

## Queue
GET /me/player/queue
POST /me/player/queue?uri=

---

# 10. RECOMMENDATIONS

## Get Recommendations
GET /recommendations
Query:
- seed_artists
- seed_tracks
- seed_genres
- limit
- min/max audio filters (energy, valence, etc.)

## Genre Seeds
GET /recommendations/available-genre-seeds

---

# 11. BROWSE

## New Releases
GET /browse/new-releases

## Featured Playlists
GET /browse/featured-playlists

## Categories
GET /browse/categories

## Category Playlists
GET /browse/categories/{category_id}/playlists

---

# 12. MARKETS

GET /markets

---

# 13. SHOWS / EPISODES

## Show
GET /shows/{id}

## Show Episodes
GET /shows/{id}/episodes

## Episode
GET /episodes/{id}

---

# 14. AUDIOBOOKS

GET /audiobooks/{id}
GET /audiobooks
GET /audiobooks/{id}/chapters

---

# 15. CHAPTERS

GET /chapters/{id}
GET /chapters?ids={ids}

---

# NOTES

- All endpoints are under https://api.spotify.com/v1
- OAuth required for most endpoints
- Many endpoints require specific scopes
- Playback endpoints require Spotify Premium
- Rate limit: HTTP 429