"""Business objects for nuglet photos."""

class Photo(object):
    """Photo object"""
    def __init__(self, nsid, owner, title, format_, date, url, favorites):  # pylint: disable=too-many-arguments
        self.nsid = nsid
        self.owner = owner
        self.title = title
        self.format = format_
        self.date = date
        self.url = url
        self.favorites = favorites

    @classmethod
    def from_api(cls, photo, favs_for_photo):
        """
        Create a Photo object as a composite of flickr responses:

            photo -- getPhoto response
            favs_for_photo -- getFavorites response
        """
        return cls(
            nsid=photo['id'],
            owner=photo['owner'],
            title=photo['title'],
            format_=photo['originalformat'],
            date=photo['datetaken'],
            url=photo['url_o'],
            favorites=len(favs_for_photo['photo']['person']),
        )

    def __repr__(self):
        return '{}'.format(self.to_dict())

    def to_dict(self):
        """Return a serializable representation"""
        return self.__dict__
