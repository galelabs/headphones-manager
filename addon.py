#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Tristan Fischer (sphere@dersphere.de)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os

from xbmcswift2 import Plugin, xbmcgui
from resources.lib.api import \
    HeadphonesApi, AuthenticationError, ConnectionError

STRINGS = {
    # Root menu
    'all_movies': 30000,
    'add_new_wanted': 30001,
    'wanted_movies': 30002,
    'done_movies': 30003,
    # Context menu
    'addon_settings': 30100,
    'refresh_releases': 30101,
    'delete_movie': 30102,
    'delete_release': 30103,
    'download_release': 30104,
    'ignore_release': 30105,
    'youtube_trailer': 30106,
    'full_refresh': 30107,
    # Dialogs
    'enter_movie_title': 30110,
    'select_movie': 30111,
    'select_profile': 30112,
    'delete_movie_head': 30113,
    'delete_movie_l1': 30114,
    'select_default_profile': 30115,
    # Error dialogs
    'connection_error': 30120,
    'wrong_credentials': 30121,
    'wrong_network': 30122,
    'want_set_now': 30123,
    # Noticications
    'wanted_added': 30130,
    'no_movie_found': 30131,
    'success': 30132,
    # Help Dialog
    'release_help_head': 30140,
    'release_help_l1': 30141,
    'release_help_l2': 30142,
    'release_help_l3': 30143,
    # Labels in Plot:
    'type': 30150,
    'provider': 30151,
    'provider_extra': 30152,
    'age': 30153,
    'seed_leech': 30154,
    'size_mb': 30155,
    'description': 30156,
}

YT_TRAILER_URL = (
    'plugin://plugin.video.youtube/'
    '?path=/root/search&feed=search&search=%s+Trailer'
)


plugin = Plugin()


@plugin.route('/')
def main_menu():
    items = [ 
        { 'label' : 'Add Artist', 'path' : plugin.url_for('search_artist'), },
        { 'label' : 'Browse Artists', 'path' : plugin.url_for('show_artists'), },
        { 'label' : 'Wanted', 'path' : plugin.url_for('show_wanted', update = True), },
        { 'label' : 'Snatched', 'path' : plugin.url_for('show_snatched'), },
    ]

    return items

@plugin.route('/search_artist/')
def search_artist():

    instr = xbmcgui.Dialog().input('Search for Artist:')
    
    if instr != '':
        plugin.set_content('artists')
        search_results = api.find_artist(instr)
        #for result in search_results:
        #    print result

        items = [ { 'label' : result.get('name'), 
            'path' : plugin.url_for('add_artist', 
                artist_id = result.get('id') ),
            #'artist' : result.get('name'),
            } for result in search_results 
        ]
        sort_methods = ['artist', ]
        return plugin.finish(items, sort_methods = sort_methods)
    else:
        raise Exception # FIXME

@plugin.route('/add_artist/<artist_id>/')
def add_artist(artist_id):
    api.add_artist(artist_id)


# the update parameter allows us to not have to hit the database every time
@plugin.route('/wanted/<update>/')
def show_wanted(update=True):
    items = []
    wanted_albums = []
    plugin.set_content('albums')

    wanted = plugin.get_storage('wanted')
    if update:
        # if we're updating through the API, clear the storage
        wanted.clear()
        # and populate wanted_albums via the API
        wanted_albums = api.get_wanted() 
    else:
        # otherwise, populate wanted_albums from storage
        wanted_albums[ value for value in wanted.values() ]

    for wanted_album in wanted_albums:
        album_title = wanted_album['AlbumTitle'].encode('utf-8')
        artist_name = wanted_album['ArtistName'].encode('utf-8')
        album_id = wanted_album['AlbumID'].encode('utf-8')

        if update:
            wanted[album_id] = wanted_album

        print('Processing album: %s' % album_title)

        # while it would be nice to have this functionality, the performance
        # decrease from the repeated DB hits isn't worth it
        #
        #havetracks = 0
        #album = api.get_album(wanted_album.get('AlbumID')) # API hit
        #totaltracks = len(album.get('tracks'))

        #for track in album.get('tracks'):
        #    if track.get('Location') != None:
        #        havetracks += 1

        #label = '%s - %s (%d / %d)' % (artist_name, album_title, havetracks,
        #        totaltracks)
        label = '%s - %s' % (artist_name, album_title)

        items.append( {
            'label' : label,
            'path' : plugin.url_for('remove_wanted_album_dialog', 
                artist_name = artist_name, album_title = album_title, 
                album_id = album_id),
            'is_playable' : False,
            'info' : {
                'artist' : [artist_name,],
                'album' : album_title,
                },
            'replace_context_menu' : True,
            'context_menu' : [
                ( 'Remove from Wanted', 'XBMC.RunPlugin(%s)' % plugin.url_for(
                    'remove_wanted_album_dialog', artist_name = artist_name,
                    album_title = album_title, album_id = album_id) ),
                ],
            'properties' : { 
                'album_id' : album_id,
                }
            }, 
            )
    if update:
        wanted.sync()
    return plugin.finish(items, sort_methods = ['artist', 'album',])

# FIXME: need a way to update the listing to remove the one we just removed
# without going back to the top of the list or adding to the navigation 
# history.
@plugin.route('/wanted/<artist_name>/<album_title>/<album_id>/')
def remove_wanted_album_dialog(artist_name, album_title, album_id):
    if xbmcgui.Dialog().yesno('Headphones Manager',
            'Remove this album from wanted albums?', '\'%s\' by \'%s\'' % (album_title, artist_name)):
        api.unqueue_album(album_id)
        wanted = plugin.get_storage('wanted')
        wanted.pop(album_id)
        wanted.sync()
        plugin.redirect(plugin.url_for('show_wanted', update = False))


@plugin.route('/queue/')
def show_snatched():
    # TODO: Implement this
    pass

@plugin.route('/artist/<artist_id>/')
def show_artist_albums(artist_id):
    items = []

    plugin.set_content('albums')

    artist = api.get_artist(artist_id)

    for album in artist.get('albums'):
        artist_name = album.get('ArtistName')
        album_title = album.get('AlbumTitle')
        album_id = album.get('AlbumID')

        album_info = api.get_album(album_id)

        havetracks = 0

        tracks = album_info.get('tracks')
        totaltracks = len(tracks)

        for track in tracks:
            if track.get('Location') != None:
                havetracks += 1

        label = album.get('AlbumTitle') + ' (%d / %d) [ %s ]' % \
                (havetracks, totaltracks, album.get('Status'))

        #thumbnail = '/opt/headphones/' + api.get_album_art(album_id)
        thumbnail = '/media/Media/Music_beets/' + artist_name + '/' + album_title + '/cover.jpg'
        print album_title.encode('unicode-escape') + ': ' + thumbnail.encode('unicode-escape')
        if not os.access(thumbnail, os.F_OK):
            print ' DOES NOT EXIST'
        elif not os.access(thumbnail, os.R_OK):
            print ' READ ONLY'

        items.append( 
                { 'label' : label, 
                    'thumbnail' : thumbnail, 
                    'path' : plugin.url_for('add_album_to_wanted', album_id = album_id)
            }
        )

    return items


@plugin.route('/add_wanted/<album_id>/')
def add_album_to_wanted(album_id):
    pass
    

@plugin.route('/artists/')
def show_artists():
    items = []
    plugin.set_content('artists')
    artists = api.get_index()
    print '%d artists: ' % len(artists)

    i = 0
    for i, artist in enumerate(artists):
        print ' > ' + artist['ArtistName'].encode('unicode-escape')
        artist_id = str(artist['ArtistID'])
        have_tracks = int(artist['HaveTracks'])
        total_tracks = int(artist['TotalTracks'])
        artist_name = artist['ArtistName'].encode('unicode-escape')

        try:
            thumb = api.get_artist_art(artist_id).encode('unicode-escape')
            thumbnail = '/opt/headphones/' + thumb
            print 'Artist: ' + artist_name + ', thumbnail: ' + thumbnail
        except:
            thumbnail = None

        label = '%s (%d / %d)' % (artist_name, have_tracks, total_tracks)
        #info = api.get_artist_info(artist_id)

        items.append( {
            'label' : label,
            #'replace_context_menu' : True,
            #'context_menu' : context_menu_artist(artist_id, label),

            'info' : {
                'count' : i,
                #'summary' : info['Summary'],
                #'content' : info['Content'],
            },

            'path' : plugin.url_for('show_artist_albums', artist_id = artist_id),
            'thumbnail' : None,
        })
    return plugin.finish(items, sort_methods=None)




def ask_profile():
    if not plugin.get_setting('default_profile', str):
        profiles = api.get_profiles()
        items = [profile['label'] for profile in profiles]
        selected = xbmcgui.Dialog().select(
            _('select_profile'), items
        )
        if selected == -1:
            return
        selected_profile = profiles[selected]
        profile_id = selected_profile['_id']
    else:
        profile_id = plugin.get_setting('default_profile', str)
    return profile_id



@plugin.route('/movies/all/refresh')
def do_full_refresh():
    success = api.do_full_refresh()
    if success:
        plugin.notify(msg=_('success'))


@plugin.route('/movies/<library_id>/refresh')
def refresh_releases(library_id):
    success = api.refresh_releases(library_id)
    if success:
        plugin.notify(msg=_('success'))


@plugin.route('/movies/<library_id>/delete')
def delete_movie(library_id):
    confirmed = xbmcgui.Dialog().yesno(
        _('delete_movie_head'),
        _('delete_movie_l1')
    )
    if confirmed:
        success = api.delete_movie(library_id)
        if success:
            plugin.notify(msg=_('success'))


@plugin.route('/release/<release_id>/delete')
def delete_release(release_id):
    success = api.delete_release(release_id)
    if success:
        plugin.notify(msg=_('success'))


@plugin.route('/release/<release_id>/download')
def download_release(release_id):
    success = api.download_release(release_id)
    if success:
        plugin.notify(msg=_('success'))


@plugin.route('/release/<release_id>/ignore')
def ignore_release(release_id):
    success = api.ignore_release(release_id)
    if success:
        plugin.notify(msg=_('success'))


@plugin.route('/release/help')
def show_release_help():
    xbmcgui.Dialog().ok(
        _('release_help_head'),
        _('release_help_l1'),
        _('release_help_l2'),
        _('release_help_l3'),
    )


@plugin.route('/settings/default_profile')
def set_default_profile():
    profiles = api.get_profiles()
    items = [profile['label'] for profile in profiles]
    selected = xbmcgui.Dialog().select( 
        _('select_default_profile'), items
    )
    if selected >= 0:
        selected_profile = profiles[selected]
        plugin.set_setting('default_profile', str(selected_profile['_id']))
    elif selected == -1:
        plugin.set_setting('default_profile', '')


@plugin.route('/settings')
def open_settings():
    plugin.open_settings()


def get_api():
    logged_in = False
    while not logged_in:
        hp_api = HeadphonesApi()
        try:
            new_api_key = hp_api.connect(
                hostname=plugin.get_setting('hostname', unicode),
                port=plugin.get_setting('port', int),
                use_https=plugin.get_setting('use_https', bool),
                #username=plugin.get_setting('username', unicode),
                #password=plugin.get_setting('password', unicode),
                api_key=plugin.get_setting('api_key', str),
                url_base=plugin.get_setting('url_base', str),
                #ba_username=plugin.get_setting('ba_username', unicode),
                #ba_password=plugin.get_setting('ba_password', unicode),
            )
        except AuthenticationError:
            try_again = xbmcgui.Dialog().yesno(
                _('connection_error'),
                _('wrong_credentials'),
                _('want_set_now')
            )
            if not try_again:
                return
            plugin.open_settings()
            continue
        except ConnectionError:
            try_again = xbmcgui.Dialog().yesno(
                _('connection_error'),
                _('wrong_network'),
                _('want_set_now')
            )
            if not try_again:
                return
            plugin.open_settings()
            continue
        else:
            logged_in = True
            if plugin.get_setting('api_key', str) != new_api_key:
                plugin.set_setting('api_key', new_api_key)
    return hp_api


def log(text):
    plugin.log.info(text)


def _(string_id):
    if string_id in STRINGS:
        return plugin.get_string(STRINGS[string_id]).encode('utf-8')
    else:
        log('String is missing: %s' % string_id)
        return string_id

if __name__ == '__main__':
    api = get_api()
    if api:
        plugin.run()
