﻿# -*- coding: utf-8 -*-
import json
import os
import re
import logging
import yaml
import requests
import fnmatch



home = os.path.expanduser("~") + "/crowdin.yaml"
if os.path.isfile(home):
    LOCATION_TO_CONFIGURATION_FILE = home
else:
    LOCATION_TO_CONFIGURATION_FILE = 'crowdin.yaml'

logger = logging.getLogger('crowdin')


class CliException(Exception):
    pass


class Configuration(object):
    def __init__(self):

        # reading configuration file
        try:
            fh = open(LOCATION_TO_CONFIGURATION_FILE, "r")
            config = yaml.load(fh)
        except(OSError, IOError) as e:
            print e, "\n Please check your config file"
            exit()

        else:

            fh.close()

            # assigning configuration values
            # print "Reading configuration from the file was successful"
            if config['project_identifier']:
                self.project_identifier = config['project_identifier']
            else:
                print "project_identifier is required in config file."
                exit()
            if config['api_key']:
                self.api_key = config['api_key']
            else:
                print "api_key is required in config file."
                exit()

            self.base_url = 'https://api.crowdin.com'
            if config['base_path']:
                #print config['base_path']
                self.base_path = config['base_path']
            else:
                self.base_path = os.getcwd()
            # self.files_source = config['files'][0]['source']
            if config['files']:
                self.files_source = config['files']
            else:
                print "You didn't set any files in your config. It's very sad."



    def get_project_identifier(self):
        return self.project_identifier

    def get_api_key(self):
        return self.api_key

    def get_base_url(self):
        return self.base_url

    def get_base_path(self):
        return self.base_path

    def get_doubled_asterisk(self, f_sources):
        root = self.base_path.replace("\\", r'/')
        if '**' in f_sources:
            items = root + f_sources[:f_sources.rfind("**")]
        else: items = root + f_sources[:f_sources.rfind('/')]
        dirs_after = f_sources[2:][f_sources.rfind("**"):]
        fg = dirs_after[:dirs_after.rfind("/")][1:]
        return root, items, fg

    def get_files_source(self):
        sources = []
        parametrs_list = []
        for f in self.files_source:
            ignore_list = []
            parametrs = {}
            root, items, fg = self.get_doubled_asterisk(f['source'])
            file_name = f['source'][1:][f['source'].rfind("/"):]
            if 'ignore' in f:
                for ign in f['ignore']:
                    root, items, fg = self.get_doubled_asterisk(ign)
                    for dp, dn, filenames in os.walk(items):
                        for ff in filenames:
                            if fnmatch.fnmatch(ff, ign[ign.rfind('/'):][1:]):
                                ignore_list.append('/' + os.path.join(dp.lstrip(root), ff).replace("\\", r'/'))

            if '*' in file_name:
                    if '**' in f['source']:
                        #sources = [os.path.join(dp.strip(root), ff).replace("\\", r'/') for dp, dn, filenames in os.walk(items)
                        #          for ff in filenames if os.path.splitext(ff)[1] == os.path.splitext(f['source'])[1]]

                        for dp, dn, filenames in os.walk(items):
                            for ff in filenames:
                                if fnmatch.fnmatch(ff, f['source'][f['source'].rfind('/'):][1:]):
                                    if fg in dp.replace("\\", r'/'):
                                        fgg=''
                                        if fg:fgg = '/'+fg
                                        value = '/' + os.path.join(dp.lstrip(root), ff).replace("\\", r'/')
                                        if not value in ignore_list:
                                            sources.append(value)
                                            sources.append(f['translation'].replace(fgg, '').replace('**', dp.replace(items, '').replace("\\", r'/')))

                    else:
                        #print items
                        for dp, dn, filenames in os.walk(items):
                            for ff in filenames:
                                #if os.path.splitext(ff)[1] == os.path.splitext(f['source'])[1]:
                                if fnmatch.fnmatch(ff, f['source'][f['source'].rfind('/'):][1:]):
                                    value = '/' + os.path.join(dp.lstrip(root), ff).replace("\\", r'/')
                                    if not value in ignore_list:
                                        sources.append(value)
                                        sources.append(f['translation'])

            elif '**' in f['source']:
                for dp, dn, filenames in os.walk(items):
                    for ff in filenames:
                        if ff == f['source'][f['source'].rfind('/'):][1:]:
                            if fg in dp.replace("\\", r'/'):
                                fgg=''
                                if fg:fgg = '/'+fg
                                value = '/' + os.path.join(dp.lstrip(root), ff).replace("\\", r'/')
                                if not value in ignore_list:
                                    sources.append(value)
                                    sources.append(f['translation'].replace(fgg, '').replace('**', dp.replace(items, '').replace("\\", r'/')))

            else:
                sources.append(f['source'])
                sources.append(f['translation'])

            if 'first_line_contains_header' in f:
                parametrs['first_line_contains_header'] = f['first_line_contains_header']
            if 'scheme' in f:
                parametrs['scheme'] = f['scheme']
            if 'multilingual_spreadsheet' in f:
                parametrs['multilingual_spreadsheet'] = f['multilingual_spreadsheet']

            parametrs_list.append(parametrs)
        return sources, parametrs_list

    def android_locale_code(self, locale_code):
        if locale_code == "he-IL":
            locale_code = "iw-IL"
        elif locale_code == "yi-DE":
            locale_code = "ji-DE"
        elif locale_code == "id-ID":
            locale_code = "in-ID"
        return locale_code.replace('-', '-r')

    def osx_language_code(self, locale_code):
        if locale_code == "zh-TW":
            locale_code = "zh-Hant"
        elif locale_code == "zh-CN":
            locale_code = "zh-Hans"
        return locale_code.replace('-', '_')

    def export_pattern_to_path(self, lang):
        #translation = {}
        lang_info = []
        get_sources_translations, params = self.get_files_source()
        for value_source, value_translation in zip(get_sources_translations[::2], get_sources_translations[1::2]):
            translation = {}
            for l in lang:
                path = value_source
                if '/' in path:
                    original_file_name = path[1:][path.rfind("/"):]
                    file_name = path[1:][path.rfind("/"):].split(".")[0]
                    original_path = path[:path.rfind("/")]
                else:
                    original_file_name = path
                    original_path = ''
                    file_name = path.split(".")[0]

                file_extension = path.split(".")[-1]

                pattern = {
                    '%original_file_name%': original_file_name,
                    '%original_path%': original_path,
                    '%file_extension%': file_extension,
                    '%file_name%': file_name,
                    '%language%': l['name'],
                    '%two_letters_code%': l['iso_639_1'],
                    '%three_letters_code%': l['iso_639_3'],
                    '%locale%': l['locale'],
                    '%crowdin_code%': l['crowdin_code'],
                    '%locale_with_underscore%': l['locale'].replace('-', '_'),
                    '%android_code%': self.android_locale_code(l['locale']),
                    '%osx_code%': self.osx_language_code(l['crowdin_code']) + '.lproj',
                }

                path_lang = value_translation
                rep = dict((re.escape(k), v) for k, v in pattern.iteritems())
                patter = re.compile("|".join(rep.keys()))
                text = patter.sub(lambda m: rep[re.escape(m.group(0))], path_lang)
                if not text in translation:
                    translation[l['crowdin_code']] = text

                if not path in lang_info:
                    lang_info.append(path)
                    lang_info.append(translation)
        return lang_info


class Connection(Configuration):
    def __init__(self, url, params, api_files=None):
        super(Connection, self).__init__()
        self.url = url
        self.params = params
        self.files = api_files

    def connect(self):
        valid_url = self.base_url + self.url['url_par1']
        if self.url['url_par2']: valid_url += self.get_project_identifier()
        valid_url += self.url['url_par3']
        if self.url['url_par4']: valid_url += '?key=' + self.get_api_key()

        response = requests.request(self.url['post'], valid_url, data=self.params, files=self.files)
        if response.status_code != 200:
            return result_handling(response.text)
        # raise CliException(response.text)
        else:
            # logger.info("Operation was successful")
            return response.content
            #return response.text


def result_handling(self):
    data = json.loads(self)
    # msg = "Operation was {0}".format()
    if data["success"] is False:
        # raise CliException(self)
        logger.info("Operation was unsuccessful")
        print "Error code: {0}. Error message: {1}".format(data["error"]["code"], data["error"]["message"])


#print Configuration().get_files_source()