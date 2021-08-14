__all__ = ['FlickrCache','loadConfig']

from pathlib import Path
import flickrapi
import configparser
import sqlite3
import logging
import datetime

_flickr = None

class FlickrCache:

    def __init__(self, cache='flickr.cache'):

        if _flickr is None:
            loadConfig()
        
        self._cache = sqlite3.connect(cache, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

        cur = self.cache.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS owner 
                       (nsid text PRIMARY KEY, username text, realname text, path_alias text)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS photo
                       (id text PRIMARY KEY, secret text, server text, farm text, date timestamp, 
                        owner text, title text, description text, latitude text, longitude text, 
                        FOREIGN KEY (owner) REFERENCES owner (nsid))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS sizes
                       (label text, width int, height int, photoid text, url text, 
                        FOREIGN KEY (photoid) REFERENCES photo (id))""")
       
    def __del__(self):
        logging.debug('closing cache')
        self.cache.close()
        
    @property
    def cache(self):
        return self._cache

    def _set_owner(self,fowner):
        cur = self.cache.cursor()
        cur.execute("select * from owner where nsid=?",(fowner['nsid'],))
        res = cur.fetchone()
        if res is None:
            logging.debug('caching owner {}'.format(fowner['nsid']))
            cur.execute("insert into owner values (:nsid, :username, :realname, :path_alias)", fowner)
            self.cache.commit()

    def _set_photo(self,fphoto):
        self._set_owner(fphoto['owner'])
        cur = self.cache.cursor()
        
        logging.debug('caching photo {}'.format(fphoto['id']))
        if 'location' in fphoto:
            latitude = fphoto['location']['latitude']
            longitutde = fphoto['location']['longitude']
        else:
            latitude = ''
            longitutde = ''

        data = (
            fphoto['id'], fphoto['secret'], fphoto['server'], fphoto['farm'],
            datetime.datetime.strptime(fphoto['dates']['taken'],'%Y-%m-%d %H:%M:%S'),
            fphoto['owner']['nsid'],fphoto['title']['_content'], fphoto['description']['_content'],
            latitude, longitutde)
        cur.execute("insert into photo values (?, ?, ?, ?, ?,?, ?, ?, ?, ?)", data)

        # get the sizes
        sizes = _flickr.photos_getSizes(photo_id=fphoto['id'])
        if sizes['stat'] != 'ok':
            raise RuntimeError('could not get sizes')
        for s in sizes['sizes']['size']:
            cur.execute("insert into sizes values (?, ?, ?, ?, ?)", (s['label'], s['width'], s['height'],
                                                                     fphoto['id'], s['source']))
        self.cache.commit()
        
        return data
        
    
    def getOwner(self,nsid):
        cur = self.cache.cursor()
        cur.execute("select * from owner where nsid=?",(nsid,))
        res = cur.fetchone()
        if res is None:
            raise ValueError(f'no such owner {nsid}')
        owner = {}
        for i,k in enumerate(['nsid','username','realname','path_alias']):
            owner[k] = res[i]
        return owner
    
    def getPhoto(self, photo_id):
        cur = self.cache.cursor()
        cur.execute("select * from photo where id=?",(photo_id,))
        data = cur.fetchone()
        if data is None:
            info = _flickr.photos_getInfo(photo_id=photo_id)
            if info['stat'] != 'ok':
                raise RuntimeError
            data = self._set_photo(info['photo'])

        photo = {}
        for i,k in enumerate(['id','secret','server','farm','date','owner','title','description','latitude','longitude']):
            photo[k] = data[i]
        photo['owner'] = self.getOwner(photo['owner'])

        return photo
        
    def getPhotoURL(self,photo_id, width=None, height=None):
        cur = self.cache.cursor()
        photo = self.getPhoto(photo_id)
        params = [photo_id]
        query = "select min(width), url from sizes where photoid=?"
        if width is not None:
            query += ' and width>?'
            params.append(width)
        if height is not None:
            query += ' and height>?'
            params.append(height)
        if width is None and height is None:
            query += 'and label = "Medium"'
        
        cur.execute(query,params)
        data = cur.fetchone()
        if data[1] is None:
            raise RuntimeError(f'query failed for image {photo_id}')
        return data[1]
    

def loadConfig(fname=Path('~/.flickr.cfg').expanduser()):
    """load flickr API key and secret from config file"""

    global _flickr

    if _flickr is not None:
        logging.debug('flickr API already initialised')
        return

    logging.debug(f'initialising flickr cache with config file {fname}')
    
    config = configparser.ConfigParser()
    config.read(fname)

    if not config.has_section('flickr'):
        raise ValueError(f"no 'flickr' section in configuration file {fname}")
    for o in ['api_key','api_secret']:
        if not config.has_option('flickr',o):
            raise ValueError(f"no '{o}' option in 'flickr' section of {fname}")

    _flickr = flickrapi.FlickrAPI(config.get('flickr','api_key'),
                                  config.get('flickr','api_secret'),
                                  format='parsed-json')
    
if __name__ == '__main__':
    from pprint import pprint

    logging.basicConfig(level=logging.DEBUG)
    
    flickr = FlickrCache()

    pprint(flickr.getPhoto(17214949923))
    pprint(flickr.getPhoto(51348573568))

    print(flickr.getPhotoURL(51348573568,width=1000))
