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

import base64
import json
from urllib import urlencode
from urllib2 import urlopen, Request, HTTPError, URLError
from hashlib import md5


class AuthenticationError(Exception):
    pass


class ConnectionError(Exception):
    pass


class HeadphonesApi():

    def __init__(self, *args, **kwargs):
        self._reset_connection()
        if args or kwargs:
            self.connect(*args, **kwargs)

    def _reset_connection(self):
        self.connected = False
        self.hostname = None
        self.port = None
        self.url_base = None
        self.use_https = None
        self.api_key = None

    def connect(self, hostname, port, api_key, use_https=False,
            url_base=None):
        self.log(
            'connect: hostname="%s" port="%s" use_https="%s" '
            'api_key="%s" url_base="%s"'
            % (hostname, port, use_https, 
               api_key is not None, url_base)
        )
        self.hostname = hostname
        self.port = port
        self.url_base = url_base
        self.use_https = use_https
        self.api_key = api_key
        if self.api_key:
            '''
            self.log('trying api_key...')
            try:
                json_data = self._api_call('app.available')
            except AuthenticationError:
                self.log('trying api_key: failed')
            else:
                self.log('trying api_key: success')
                '''
            self.connected = True
        else:
            raise AuthenticationError
        if not self.connected:
            self._reset_connection()
            raise AuthenticationError
        return self.api_key


###############################################################################
# API methods
    def get_index(self):
        return self._api_call('getIndex')

    def get_artist(self, artistID):
        return self._api_call('getArtist', { 'id' : artistID, })

    def get_album(self, albumID):
        return self._api_call('getAlbum', { 'id' : albumID, })

    def get_upcoming(self):
        return self._api_call('getUpcoming')

    def get_wanted(self):
        return self._api_call('getWanted')

    def get_similar(self):
        return self._api_call('getSimilar') # TODO: does this need a parameter?

    def get_history(self):
        return self._api_call('getHistory') # TODO: does this need a parameter?

    def get_logs(self):
        pass # not working in API yet

    def find_artist(self, name, limit=0):
        if limit > 0:
            params = { 'name' : name, 'limit' : limit, }
        else:
            params = { 'name' : name, }
        return self._api_call('findArtist', params)

    def find_album(self, name, limit=0):
        return self._api_call('findArtist', { 'name' : name, 'limit' : limit, })

    def add_artist(self, artistid):
        return self._api_call('addArtist', { 'id' : artistid })

    def add_album(self, releaseid):
        return self._api_call('addAlbum', { 'id' : releaseid })

    def del_artist(self, artistid):
        return self._api_call('delArtist', { 'id' : artistid })

    def pause_artist(self, artistid):
        return self._api_call('pauseArtist', { 'id' : artistid })

    def resume_artist(self, artistid):
        return self._api_call('resumeAtist', { 'id' : artistid })

    def refresh_artist(self, artistid):
        return self._api_call('refreshArtist', { 'id' : artistid })

    def queue_album(self, albumid, new=True, lossless=True):
        return self._api_call('queueAlbum', { 'id' : albumid, 'new' : new,
            'lossless' : lossless })

    def unqueue_album(self, albumid):
        return self._api_call('unqueueAlbum', { 'id' : albumid,})

    def force_search(self):
        return self._api_call('forceSearch')

    def force_process(self):
        return self._api_call('forceProcess')

    def force_active_artists_update(self):
        return self._api_call('forceActiveArtistsUpdate')

    def get_version(self):
        return self._api_call('getVersion')

    def check_github(self):
        return self._api_call('checkGithub')

    def shutdown(self):
        return self._api_call('shutdown')

    def restart(self):
        return self._api_call('restart')

    def update(self):
        return self._api_call('update')

    def get_artist_art(self, artistid):
        return self._api_call('getArtistArt', { 'id' : artistid, })

    def get_album_art(self, albumid):
        return self._api_call('getAlbumArt', { 'id' : albumid, })

    def get_artist_info(self, artistid):
        return self._api_call('getArtistInfo', { 'id' : artistid, })

    def get_album_info(self, albumid):
        return self._api_call('getAlbumInfo', { 'id' : albumid, })

    def get_artist_thumb(self, artistid):
        return self._api_call('getArtistThumb', { 'id' : artistid, })

    def get_album_thumb(self, albumid):
        return self._api_call('getAlbumThumb', { 'id' : albumid, })

    def choose_specific_download(self, albumid):
        return self._api_call('choose_specific_download', { 'id' : albumid, })

    def download_specific_release(self, params):
        return self._api_call('download_specific_release', params )


###############################################################################

    def _api_call(self, endpoint, params=None):
        #self.log('_api_call started with endpoint=%s, params=%s'
        #         % (endpoint, params))
        url = '%s/api?apikey=%s&cmd=%s' % (self._api_url, self.api_key, endpoint)
        if params:
            url += '&%s' % urlencode(params)
        #self.log('_api_call using url: %s' % url)
        raw = urlopen(self._request(url)).read()
        if raw != 'OK':
            try:
                json_data = json.loads(raw)
            except HTTPError, error:
                self.log('__urlopen HTTPError: %s' % error)
                if error.fp.read() == 'Wrong API key used':
                    raise AuthenticationError
                else:
                    raise ConnectionError
            except URLError, error:
                self.log('__urlopen URLError: %s' % error)
                raise ConnectionError
        #self.log('_api_call response: %s' % repr(json_data))
            return json_data
        else:
            return raw

    def _request(self, url):
        request = Request(url)
        '''
        if self.ba_username and self.ba_password:
            request.add_header(
                'Authorization',
                'Basic %s' % base64.encodestring('%s:%s' % (
                    self.ba_username,
                    self.ba_password)
                ).replace('\n', '')
            )
            '''
        return request

    @property
    def _api_url(self):
        proto = 'https' if self.use_https else 'http'
        url_base = '/%s' % self.url_base if self.url_base else ''
        return '%s://%s:%s%s' % (proto, self.hostname, self.port, url_base)

    def log(self, text):
        print u'[%s]: %s' % (self.__class__.__name__, repr(text))
