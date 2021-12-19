__all__ = ['FlickrCache', 'loadConfig']

from .models import Base, Owner, Photo, Size

from pathlib import Path
import flickrapi
import configparser
import logging
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

_flickr = None


class FlickrCache:

    def __init__(self, cache='sqlite:///flickr.cache'):
        global _Session

        if _flickr is None:
            loadConfig()
        _engine = create_engine(cache)
        Base.metadata.create_all(_engine)
        Session = scoped_session(sessionmaker(bind=_engine))
        Base.query = Session.query_property()
        self._session = Session()

    def __del__(self):
        logging.debug('closing cache')
        self._session.close()

    def getOwner(self, nsid):
        owner = self._session.query(Owner).filter_by(
            nsid=nsid).one_or_none()
        if owner is None:
            # add the owner
            info = _flickr.people_getInfo(user_id=nsid)
            o = info['person']
            owner = Owner(nsid=nsid,
                          username=o['username']['_content'],
                          realname=o['realname']['_content'],
                          path_alias=o['path_alias'])
            self._session.add(owner)
            self._session.commit()
        return owner

    def _getPhoto(self, p):
        photo = Photo.query.filter_by(id=p['id']).one_or_none()
        if photo is None:
            _p = {}
            for f in ['id', 'secret', 'server', 'farm']:
                _p[f] = p[f]
            for f in ['title', 'description']:
                _p[f] = p[f]['_content']
            _p['date'] = datetime.datetime.fromtimestamp(
                int(p['dateuploaded']))
            _p['owner'] = self.getOwner(p['owner']['nsid'])
            if 'location' in p:
                for f in ['latitude', 'longitude']:
                    _p[f] = float(p['location'][f])
            photo = Photo(**_p)
            self._session.add(photo)
            # get the sizes
            sizes = _flickr.photos_getSizes(photo_id=photo.id)
            if sizes['stat'] != 'ok':
                raise RuntimeError('could not get sizes')
            for s in sizes['sizes']['size']:
                size = Size(label=s['label'], width=s['width'],
                            height=s['height'], photo=photo, url=s['source'])
                self._session.add(size)
        return photo

    def getPhoto(self, photo_id):
        photo = self._session.query(Photo).filter_by(id=photo_id).one_or_none()
        if photo is None:
            info = _flickr.photos_getInfo(photo_id=photo_id)
            if info['stat'] != 'ok':
                raise RuntimeError
            photo = self._getPhoto(info['photo'])
            self._session.commit()
        return photo

    def getPhotoURL(self, photo_id, width=None, height=None):
        return self.getPhoto(photo_id).get_url(width=width, height=height)


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
    for o in ['api_key', 'api_secret']:
        if not config.has_option('flickr', o):
            raise ValueError(f"no '{o}' option in 'flickr' section of {fname}")

    _flickr = flickrapi.FlickrAPI(config.get('flickr', 'api_key'),
                                  config.get('flickr', 'api_secret'),
                                  format='parsed-json')


if __name__ == '__main__':
    from pprint import pprint

    logging.basicConfig(level=logging.DEBUG)

    flickr = FlickrCache()

    pprint(flickr.getPhoto(17214949923).as_dict())
    photo = flickr.getPhoto(51348573568)
    pprint(photo.as_dict())

    print(flickr.getPhotoURL(51348573568, width=1000).as_dict())
    print(photo.get_url(width=1000).as_dict())
