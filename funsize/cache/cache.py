"""
funsize.database.cache
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is currently a stub file that contains function prototypes for the
caching layer core

"""

import os
import shutil
import logging

import funsize.utils.oddity as oddity
import funsize.utils.csum as csum


class Cache(object):
    """ Class that provides access to cache
        Assumes all keys are hex-encoded SHA512s
        Internally converts  hex to base64 encoding
    """

    # FIXME: Typically caches are given Key-Value pairs, our cache generates
    # the key on it's own, this is not how it should be

    def __init__(self, cache_uri):
        """ cache_uri : URI of the cache for init.
                        Just a filepath for the time being
        """

        logging.info('Creating cache interface for cache %s', cache_uri)
        self.cache_dir = cache_uri
        self.cache_complete_dir = os.path.join(self.cache_dir, 'complete')
        self.cache_diffs_dir = os.path.join(self.cache_dir, 'diff')
        self.cache_partials_dir = os.path.join(self.cache_dir, 'partial')

        for directory in (self.cache_dir, self.cache_complete_dir,
                          self.cache_diffs_dir, self.cache_partials_dir):
            try:
                os.makedirs(directory)
            except OSError:
                if not os.path.isdir(directory):
                    logging.warning('Could not initalize cache')
                    logging.info('Could not create required dir %s', directory)
                    raise oddity.CacheError('Could not initalize Cache')

    def _generate_identifier(self, key):
        """ Identifier to convert (SHA512-SHA512) 16-base to i
            (SHA512-SHA512) 64-base (because of OS boundaries)
        """

        return '-'.join(csum.hexto64(x) if len(x) == 128
                        else x for x in key.split('-'))

    def _get_cache_internals(self, key, category):
        """ Method to return cache identifier and file_cache_path based on key
        """

        identifier = self._generate_identifier(key)
        id_path = os.path.join(*[d for d in identifier[:5]] + [identifier[5:]])

        if category is None:
            file_cache_path = os.path.join(self.cache_dir, id_path)
        elif category == 'complete':
            file_cache_path = os.path.join(self.cache_complete_dir, id_path)
        elif category == 'diff':
            file_cache_path = os.path.join(self.cache_diffs_dir, id_path)
        elif category == 'partial':
            file_cache_path = os.path.join(self.cache_partials_dir, id_path)

        return (identifier, file_cache_path)

    def save(self, string, key, category, isfile=False):
        """ Saves given file to cache, treats string as a local filepath if
            isfile is true. returns hash of file.
        """
        # FIXME: How do we deal with the race condition where the file is still
        # being written to cache, but since it exists is returned as is (most
        # likely corrupted).

        # FIXME: What should the behaviour be when we try to save to a
        # pre-existing key?

        if not key:
            raise oddity.CacheError('Tried to save object to cache without key')

        if isfile:
            try:
                # TODO ROUGHEDGE read in chunks of 1MB?
                with open(string, 'rb') as fobj:
                    data = fobj.read()
            except:
                logging.warning('Could not read file src %s to insert to cache',
                                string)
                raise oddity.CacheError('Error reading input %s' % string)
        else:
            data = string

        _, file_cache_path = self._get_cache_internals(key, category)

        logging.info('Writing to cache in dir %s', file_cache_path)
        try:
            os.makedirs(os.path.dirname(file_cache_path))
        except OSError:
            if not os.path.isdir(os.path.dirname(file_cache_path)):
                raise oddity.CacheError('Could not insert in Cache')

        tmp_location = file_cache_path + str(os.getpid())
        try:
            with open(tmp_location, 'wb') as fobj:
                fobj.write(data)
        except:
            raise oddity.CacheError('Error saving input %s to cache', string)
        else:
            try:
                shutil.copyfile(tmp_location, file_cache_path)
                logging.info('Worker won race. File %s copied',
                             file_cache_path)
            except OSError:
                logging.info('OSError raised while copying contents')
            else:
                os.unlink(tmp_location)

    def save_blank_file(self, key, category):
        """ Method to save a blank file to show a partial has been triggered and
            it is being in progress
        """

        if not key:
            raise oddity.CacheError('Tried to save object to cache without key')

        _, file_cache_path = self._get_cache_internals(key, category)

        logging.info('Saving blank file in the dir: %s', file_cache_path)
        try:
            os.makedirs(os.path.dirname(file_cache_path))
        except OSError:
            if not os.path.isdir(os.path.dirname(file_cache_path)):
                raise oddity.CacheError('Could not save to Cache')

        try:
            open(file_cache_path, 'a').close()
        except:
            raise oddity.CacheError('Error saving blank file to to cache')

    def is_blank_file(self, key, category):
        """ Function to check if the file is empty or not. To be used to ensure
        no second triggering is done for the same partial
        Returns True is file exists and is blank, False otherwise
        """

        if not self.find(key, category):
            return False

        _, file_cache_path = self._get_cache_internals(key, category)
        return os.stat(file_cache_path).st_size == 0

    def find(self, key, category):
        """ Checks if file with specified key is in cache
            returns True or False depending on whether the file exists

        """

        _, file_cache_path = self._get_cache_internals(key, category)
        return os.path.isfile(file_cache_path)

    def retrieve(self, key, category, output_file=None):
        """ Retrieve file with the given key
            writes the file to the path specified by output_file if present
            otherwise returns the file as a binary string/file object
        """

        identifier, file_cache_path = self._get_cache_internals(key, category)

        if output_file:
            try:
                shutil.copyfile(file_cache_path, output_file)
            except:
                logging.warning('Could not retrieve file from cache')
                raise oddity.CacheMissError('File with id %s not found',
                                            identifier)
            else:
                return
        else:
            try:
                # TODO ROUGHEDGE read in chunk 1Mb
                with open(file_cache_path, 'rb') as fobj:
                    data = fobj.read()
            except:
                logging.warning('Could not retrieve file from cache')
                raise oddity.CacheMissError('File with identifier %s not found',
                                            identifier)
            else:
                return data

    def delete_from_cache(self, key, category):
        """ Method to remove a file from cache
        """

        if not self.find(key, category):
            return

        _, file_cache_path = self._get_cache_internals(key, category)
        os.unlink(file_cache_path)
