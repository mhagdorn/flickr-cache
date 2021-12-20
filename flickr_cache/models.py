__all__ = ['Base', 'Owner', 'Photo', 'Size', 'Tag', 'Tags', 'Album']


from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy


Base = declarative_base()


album_association = sqlalchemy.Table(
    'albums', Base.metadata,
    sqlalchemy.Column('albumid', sqlalchemy.Integer,
                      sqlalchemy.ForeignKey('album.id'),
                      primary_key=True),
    sqlalchemy.Column('photoid', sqlalchemy.Text,
                      sqlalchemy.ForeignKey('photo.id'),
                      primary_key=True))


class Owner(Base):
    __tablename__ = 'owner'

    nsid = sqlalchemy.Column(sqlalchemy.Text, primary_key=True)
    username = sqlalchemy.Column(sqlalchemy.Text)
    realname = sqlalchemy.Column(sqlalchemy.Text)
    path_alias = sqlalchemy.Column(sqlalchemy.Text)

    photos = relationship("Photo", back_populates="owner")
    tags = relationship("Tag", back_populates="owner")
    albums = relationship("Album", back_populates="owner")

    def as_dict(self):
        d = {}
        for k in ['nsid', 'username', 'realname', 'path_alias']:
            d[k] = getattr(self, k)
        return d


class Photo(Base):
    __tablename__ = 'photo'

    id = sqlalchemy.Column(sqlalchemy.Text, primary_key=True)
    secret = sqlalchemy.Column(sqlalchemy.Text)
    server = sqlalchemy.Column(sqlalchemy.Text)
    farm = sqlalchemy.Column(sqlalchemy.Text)
    date = sqlalchemy.Column(sqlalchemy.DateTime)
    owner_id = sqlalchemy.Column(
        sqlalchemy.Text, sqlalchemy.ForeignKey('owner.nsid'))
    title = sqlalchemy.Column(sqlalchemy.Text)
    description = sqlalchemy.Column(sqlalchemy.Text)
    latitude = sqlalchemy.Column(sqlalchemy.Float)
    longitude = sqlalchemy.Column(sqlalchemy.Float)

    owner = relationship("Owner", back_populates="photos")
    sizes = relationship("Size", back_populates="photo")
    tags = relationship("Tags", back_populates="photo")
    albums = relationship("Album", secondary=album_association,
                          back_populates="photos")

    def get_url(self, width=None, height=None):
        query = [Size.photoid == self.id]
        if width is not None:
            query.append(Size.width > width)
        if height is not None:
            query.append(Size.height > height)
        if width is None and height is None:
            query.append(Size.label == 'Medium')
        return Size.query.filter(*query).order_by(
            Size.width, Size.label).limit(1).one_or_none()

    def as_dict(self):
        d = {}
        for k in ['id', 'secret', 'farm', 'date', 'title', 'description',
                  'latitude', 'longitude']:
            d[k] = getattr(self, k)
        d['owner'] = self.owner.as_dict()
        d['sizes'] = []
        for s in self.sizes:
            d['sizes'].append(s.as_dict())
        return d


class Size(Base):
    __tablename__ = 'sizes'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    label = sqlalchemy.Column(sqlalchemy.Text)
    width = sqlalchemy.Column(sqlalchemy.Integer)
    height = sqlalchemy.Column(sqlalchemy.Integer)
    photoid = sqlalchemy.Column(
        sqlalchemy.Text, sqlalchemy.ForeignKey('photo.id'))
    url = sqlalchemy.Column(sqlalchemy.Integer)

    photo = relationship("Photo", back_populates="sizes")

    def as_dict(self):
        d = {}
        for k in ['label', 'width', 'height', 'url']:
            d[k] = getattr(self, k)
        return d


class Tag(Base):
    __tablename__ = 'tag'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    tag = sqlalchemy.Column(sqlalchemy.Text, unique=True)
    last_visited = sqlalchemy.Column(sqlalchemy.DateTime)
    owner_id = sqlalchemy.Column(
        sqlalchemy.Text, sqlalchemy.ForeignKey('owner.nsid'))

    tags = relationship("Tags", back_populates="tag")
    owner = relationship("Owner", back_populates="tags")


class Tags(Base):
    __tablename__ = 'tags'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    tagid = sqlalchemy.Column(sqlalchemy.Integer,
                              sqlalchemy.ForeignKey('tag.id'))
    photoid = sqlalchemy.Column(
        sqlalchemy.Text, sqlalchemy.ForeignKey('photo.id'))

    tag = relationship("Tag", back_populates="tags")
    photo = relationship("Photo", back_populates="tags")


class Album(Base):
    __tablename__ = 'album'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    album = sqlalchemy.Column(sqlalchemy.Text, unique=True)
    last_visited = sqlalchemy.Column(sqlalchemy.DateTime)
    owner_id = sqlalchemy.Column(
        sqlalchemy.Text, sqlalchemy.ForeignKey('owner.nsid'))

    photos = relationship("Photo", secondary=album_association,
                          back_populates="albums",
                          order_by="Photo.date.desc()")
    owner = relationship("Owner", back_populates="albums")
