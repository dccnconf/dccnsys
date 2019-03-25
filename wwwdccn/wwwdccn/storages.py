from storages.backends.sftpstorage import SFTPStorage
from storages.utils import setting


class StaticSFTPStorage(SFTPStorage):

    def __init__(self, host=None, params=None, root_path=None, base_url=None):
        _host = host or setting('STATIC_SFTP_STORAGE_HOST')
        _params = params or setting('STATIC_SFTP_STORAGE_PARAMS', {})
        _root_path = setting('STATIC_SFTP_STORAGE_ROOT', '') \
            if root_path is None else root_path
        _base_url = setting('STATIC_URL') if base_url is None else base_url
        super().__init__(host=_host, params=_params, interactive=False,
                         root_path=_root_path, base_url=_base_url)
