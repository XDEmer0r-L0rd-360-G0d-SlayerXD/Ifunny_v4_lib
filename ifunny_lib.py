# This is the library that will deal with interfacing with the Ifunny servers to pull info
import os
import hashlib
import base64
import requests
import json
from lxml import html
from pprint import pprint
import logging
import datetime
import time
import pickle
import copy

"""
I am trying to avoid putting too many parameters in functions. As such I have tried to take a more init object and then
load parts approach. I also put effort to avoid spamming the servers with requests. Also some of the recursive things 
could be slow and may be reworked, but unlikely unless it is crippling.
Made by Nam. Discord: that_dude#1313, Github: XDEmer0r-L0rd-360-G0d-SlayerXD
"""

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# basic token needs to be set for most commands, bearer is for things that need a login
# these need to be changed. Use load_auths() to do so
# Things will go wrong if you don't.
BASIC_TOKEN = ""
BEARER_TOKEN = ""


class MissingAuthToken(Exception):
    """
    Exists only to tell the user that load_auths() has not been run.
    """


class ExpiredBasicToken(Exception):
    """
    Exists only to say that the basic token used to gen the bearer can't
    """
    pass


class NoContent(Exception):
    """
    There was an error when searching for the content and the api returned an error.
    """


class Queue:
    """
    This is to store queues such as post a user has, replies a post has, etc.
    not all list functions are implemented. If not, use it on Queue.stored_content as that is the basis.
    """

    def __init__(self, stored_class_type: type = None, source_url: str = None, tag_only_mode: str = None):
        """
        The init method which prepares the class. The auth needs to be changed from outside if it doesn't use basic.
        :param stored_class_type: What Type of object that is going to be stored such as User, Post, Comment.
        :param source_url: What endpoint is going to be used.
        :param tag_only_mode: If given, it will only store that attribute from the data in the list
        :param force_load: force load from id to ensure consistency of content. May lose or gain data.
        """
        # todo maybe make this inheret from list to give more functionality via __*__

        logger.info("Queue object created")

        if source_url is None:
            raise ValueError("Missing arg")
        self.stored_class_type = stored_class_type
        self.source_url = source_url
        self.tag_only_mode = tag_only_mode  # setting this to false before loading anything will may decrease server load and avoid making mare object
        self.stored_content = []  # this is just a list of the objects Queue just makes loading them easier
        self.page_next = None
        self.has_next = True
        self.chunks = 100  # this can be changed as an option but is set to max size for max speed
        self.auth_token = BASIC_TOKEN

    def __iter__(self):
        return (t for t in self.stored_content)

    def __getitem__(self, item):
        return self.stored_content[item]

    def __len__(self):
        return len(self.stored_content)

    def __str__(self):
        return str(self.stored_content)

    def store(self, thing):
        """
        A single word way to store a piece of data.
        """
        self.stored_content.append(thing)
        return self

    def clear(self):
        """
        This resets the stored content if called for any reason.
        """
        self.stored_content = []
        self.page_next = None
        self.has_next = True
        return self

    def queue_data_cleaner(self, var):
        """
        Hopefully a universal data cleaner that strips unwanted data.
        """
        # this returns a cleaned dict after striping the output it deems unneeded and should return a list
        # this one was made for posts nad needs to be calibrated
        if type(var) == list:
            if len(var) > 0 and "guest" in var[0]:
                return [a['guest'] for a in var]
            return var
        elif type(var) == dict:
            if "items" in var:
                return self.queue_data_cleaner(var["items"])
            elif "comments" in var:
                return self.queue_data_cleaner(var["comments"])
            elif "replies" in var:
                return self.queue_data_cleaner(var["replies"])
            elif "content" in var:
                return self.queue_data_cleaner(var["content"])
            elif "data" in var:
                return self.queue_data_cleaner(var["data"])
            elif "id" in var:
                return [var]
            elif "users" in var:
                return self.queue_data_cleaner(var["users"])
            elif "guests" in var:
                return self.queue_data_cleaner(var['guests'])
        pprint(var)
        pprint(self.source_url)
        raise KeyError("failed to find key")

    def page_info(self, var):
        if type(var) != dict:
            return
        if "paging" in var:
            return var["paging"]
        else:
            for k in var.keys():
                found = self.page_info(var[k])
                if found:
                    return found
        raise KeyError("No 'paging' key found")

    def load(self, limit: int = None, paging_start: str = None):
        """
        I want to do this in chunks of 100 so we get data as fast as possible. When limit == None we load until no more
        if limit == 0 then we return a clean Queue object.
        force_load does nothing right now, am considering giving the option to recall all obects by id to ensure all data is stored
        :param limit: How many to load
        :param paging_start: Changes the loading start point
        :return: self
        """
        if limit == 0:
            # dumb shit may possible here without the check
            return

        if self.source_url == "https://api.ifunny.mobi/v4/users/my/guests":
            limit += 1

        while self.has_next:
            if not limit or limit > self.chunks:
                response = api_call(self.source_url, auth=self.auth_token, params={'next': paging_start, 'limit': self.chunks}, method="GET" if self.source_url != "https://api.ifunny.mobi/v4/feeds/collective" else "POST")
            #     do parse and store
            else:
                response = api_call(self.source_url, auth=self.auth_token, params={'next': paging_start, 'limit': limit})
            # pprint(response)
            pure_list = self.queue_data_cleaner(response)
            if self.tag_only_mode:
                for a in pure_list:
                    self.store(a[self.tag_only_mode])
            elif self.stored_class_type is None:
                for a in pure_list:
                    self.store(a)
            elif self.stored_class_type == Post:
                for a in pure_list:
                    self.store(Post(data=a))
            elif self.stored_class_type == Comment:
                for a in pure_list:
                    self.store(Comment(data=a))
            elif self.stored_class_type == Reply:
                for a in pure_list:
                    self.store(Reply(data=a))
            elif self.stored_class_type == User:
                for a in pure_list:
                    self.store(User(data=a))
            else:
                raise TypeError("type was not found")
            page_info = self.page_info(response)
            self.has_next = page_info['hasNext']
            # print(page_info)
            if self.has_next:
                paging_start = self.page_next = page_info["cursors"]['next']
            if limit:
                limit -= self.chunks
                if limit <= 0:
                    return self

    def load_next(self, limit: int = 1):
        """
        load the next posts after the current loaded ones
        limit == None will load until end,
        :param limit:
        :return: self
        """
        self.load(limit, self.page_next)
        return self

    def load_until(self, ids: tuple = (), needed_matches: int = 1, include_matches: bool = True, emergency_limit: int = -1, clean_overflow: bool = True):
        """
        This will load objects until enough matching id's are found. Ideally for loading until old content in found.
        """
        pointer = 0  # shows what we are looking at in stored_content
        while needed_matches > 0 and emergency_limit != 0:
            self.load_next(limit=self.chunks)
            for a in self.stored_content[pointer:]:
                if a.id in ids:
                    needed_matches -= 1
                    if not include_matches:
                        self.stored_content.remove(pointer)
                        pointer -= 1
                pointer += 1
            emergency_limit -= 1
        if clean_overflow:
            self.stored_content = self.stored_content[:min(pointer + 1, len(self.stored_content))]
        return self

    def save_to_file(self, file_name: str = None):
        if not file_name:
            file_name = str(self.stored_class_type).replace("'", '').replace('class', '').replace(' ', '').replace('ifunny_lib.', '').replace('<', '').replace('>', '') + "_queue"
        if '.txt' not in file_name:
            file_name += '.txt'
        with open(file_name, 'w') as f:
            for a in self.stored_content:
                if type(a) == str:
                    f.write(a + '\n')
                else:
                    f.write(str(a.cdata) + '\n')

    def load_from_file(self, file_name: str):
        with open(file_name, 'r') as f:
            for a in f.readlines():
                self.store(self.stored_class_type(data=eval(a.strip())))


class IfBase:

    def __init__(self, file_name: str = None):
        try:
            self.cdata = self.__getattribute__("cdata")
        except AttributeError:
            self.cdata = {}

        self.errored_attributes = set()
        self.data_attributes = ["cdata", 'errored_attributes']
        if not file_name:
            self.file_name = str(datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        else:
            self.file_name = str(file_name)
        # print(type(str(self.file_name)))

    def store_file_full(self, name: str = None):
        """Uses alternative method to store all of object data. Maybe works a panic option.
        :param name: File name/path to open
        """
        if not name:
            name = self.file_name
        with open(name, 'wb') as f:
            pickle.dump(self, f)
        logger.debug("Full store")

    def load_file_full(self, name: str):
        """Uses alternative method to store all of object data. Maybe works a panic option.
        :param name: File name/path to open
        """
        if not name:
            name = self.file_name
        with open(name, 'rb') as f:
            data = pickle.load(f)
            print(data.__dict__['smiles'])
            self.__dict__ = copy.deepcopy(data.__dict__)
        logger.debug("Full load")

    def store_file(self, name: str = None):
        if not name:
            name = self.file_name
        with open(name, 'wb') as f:
            data = [self.__getattribute__(a) for a in self.data_attributes]
            pickle.dump(data, f)

    def load_file(self, name: str):
        if not name:
            name = self.file_name
        with open(name, "rb") as f:
            data = pickle.load(f)
            for num_a, a in enumerate(data):
                if type(a) == Queue:
                    logger.debug(num_a, self.data_attributes[num_a], a.stored_content)
                self.__setattr__(self.data_attributes[num_a], a)

    def load_data(self, data: dict):
        """
        Probably unnecessary
        """
        self.cdata = data

    def try_store_attribute(self, name: str, val: str):
        """
        Try to clean up the constant try-excepting
        """
        try:
            self.__setattr__(name, self.cdata[val])
        except KeyError:
            self.errored_attributes.add(name)


class Comment(IfBase):
    """
    This is a single comment for easier parsing
    """

    def __init__(self, post_id: str = None, comment_id: str = None, data: dict = None, file_name: str = None):
        """
        Args are only used to find comment, internal vars are updated on their own.
        post_id and comment_id are used to directly pull comment info
        raw_data is the entire json that holds the comment data
        cdata (cleaned data) is raw_data but stripped of the ['data']['comment'] keys
        only need post_id & comment_id or raw_data or cdata. The 'text' tag will contain the text or link to picture
        comment, but defaults to only text if both are present.
        :param post_id: post id string
        :param comment_id: comment id string
        """

        logger.info("Comment/Reply object created")

        super().__init__(file_name)
        self.data_attributes.extend(("smiles", 'replies'))

        if file_name:
            pass
        else:
            self.load_file(file_name)
        if post_id and comment_id:
            data = api_call(f'https://api.ifunny.mobi/v4/content/{post_id}/comments/{comment_id}',
                            auth=BASIC_TOKEN)
            self.cdata = self._data_cleaner(data)
        elif data:
            self.cdata = self._data_cleaner(data)
        elif not any((post_id, comment_id, data, file_name)):
            raise ValueError("need args")

        self.update_attributes()

        if not file_name and "id" not in self.errored_attributes:
            self.file_name = self.id + "_" + self.file_name

    def update_attributes(self, data=None):
        """
        Use the current self.cdata to update all the current atrributes
        :return:
        """

        if not data:
            cdata = self.cdata
        else:
            cdata = self._data_cleaner(data)
            self.cdata = data
        self.errored_attributes = []
        self.try_store_attribute("post_id", "cid")
        self.try_store_attribute("id", "id")
        self.try_store_attribute("stats", "num")
        self.try_store_attribute("text", "text")
        try:
            self.creator_id = cdata['user']['id']
            self.creator_name = cdata['user']['original_nick']
        except KeyError:
            self.errored_attributes.append("creator_id")
            self.errored_attributes.append("creator_name")
        try:
            self.endpoints = {'main': f'https://api.ifunny.mobi/v4/content/{self.post_id}/comments/{self.id}',
                              'replies': f'https://api.ifunny.mobi/v4/content/{self.post_id}/comments/{self.id}/replies',
                              'smiles': f'https://api.ifunny.mobi/v4/content/{self.post_id}/comments/{self.id}/smiles'}
            self.replies = Queue(Reply, self.endpoints['replies'])
            self.smiles = Queue(User, self.endpoints['smiles'])
            self.smiles.auth_token = BEARER_TOKEN  # getting who smiled comment/reply requires bearer for what ever reason
        except AttributeError:
            self.errored_attributes.append("endpoints")
            self.errored_attributes.append("replies")
            self.errored_attributes.append("smiles")

    def _data_cleaner(self, var):
        # this returns a cleaned dict after striping the output it deems unneeded
        # this one was made for posts and needs to be calibrated
        if type(var) == dict:
            if "error" in var and "not_found" == var['error']:
                raise NoContent()
            if "id" in var:
                return var
            elif "data" in var:
                return var["data"]["comment"]
        elif type(var) == list:
            return var[0]
        pprint(var)
        print("cleaner failed to find key")
        raise KeyError
    
    def reload(self):
        self.__init__(self.post_id, self.id)

    def add_reply(self, thing):
        """
        Simple way to add a direct reply
        :param thing: reply object
        :return: None
        """
        self.replies.store(thing)
        return self

    def get_id_object(self, id_to_check: str):
        """
        Will return the reply object with the id.
        :param id_to_check: the id of the object
        :return: Reply object if found, else None
        """
        if id_to_check == self.id:
            return self
        else:
            for a in self.replies:
                check_in = a.get_id_object(id_to_check=id_to_check)
                if check_in is not None:
                    return check_in
            return None

    def nest_replies(self):
        """
        Take the replies stared in self.replies and properly nest them.
        :return: self
        """

        temp_stored_content = []
        for a in self.replies.stored_content:
            found = False
            for b in temp_stored_content:
                target = b.get_id_object(a.parent_comment_id)
                if target is None:
                    continue
                target.add_reply(a)
                found = True
            if not found:
                temp_stored_content.append(a)
        self.replies.stored_content = temp_stored_content
        return self

    def tree_cdata(self) -> tuple:
        """
        Like id_tree, but this one returns all the cdata instead of only ids
        :return: cdata in nested form
        """

        reply_list = []
        for a in self.replies:
            # todo remove this limiter
            sanity = a.tree()
            if "last_reply" in sanity[0]:
                del sanity[0]["last_reply"]
            reply_list.append(sanity)
        return self.cdata, reply_list


class Reply(Comment):
    """
    While very simmilar to the comment object, there are a few new pieces of data that a reply has that needs te be stored
    """

    def __init__(self, post_id: str = None, comment_id: str = None, data: dict = None, file_name: str = None):
        """
        Works in the same way as the Comment class, this is just a special case
        """
        super().__init__(post_id, comment_id, data, file_name)  # this should also auto clean the data being passed and stored

        if not file_name:
            self.update_attributes()

    def update_attributes(self, data: dict = None):

        if data:
            self.cdata = self._data_cleaner(data)

        super().update_attributes()
        self.try_store_attribute("depth", "depth")
        self.try_store_attribute("parent_comment_id", "parent_comm_id")
        self.try_store_attribute("root_comment_id", "root_comm_id")


class Post(IfBase):
    """
    This holds a single post, and parses the data for more easy use.
    """

    def __init__(self, post_id: str = None, data: dict = None, file_name: str = None):
        """
        post_id is the direct way to call post json info
        :param post_id: post id string
        """
        logger.info("Post object created")

        super().__init__(file_name)
        self.data_attributes.extend(('comments', 'repubs', 'smiles'))

        if file_name:
            self.load_file(file_name)
        else:
            if post_id:
                data = api_call("https://api.ifunny.mobi/v4/content/" + post_id, auth=BASIC_TOKEN)
                # print(data)
                self.cdata = self._data_cleaner(data)
                # print(self.cdata)
            elif data:
                self.cdata = self._data_cleaner(data)
            elif not any((post_id, data, file_name)):
                raise ValueError("need args")

            self.update_attributes()

            if "id" not in self.errored_attributes:
                self.file_name = self.id + "_" + self.file_name


    def update_attributes(self, data: dict = None):

        if not data:
            cdata = self.cdata
        else:
            cdata = data
            self.cdata = cdata

        self.errored_attributes = []
        try:
            self.creator_id = cdata["creator"]["id"]
            self.creator_name = cdata["creator"]["original_nick"]  # uses original name for consistency over time hopefully
        except KeyError:
            self.errored_attributes.append("creator_id")
            self.errored_attributes.append("creator_name")
        self.try_store_attribute("id", "id")
        self.try_store_attribute("link", "link")
        self.try_store_attribute("url", "url")
        self.try_store_attribute("stats", "num")
        self.try_store_attribute("type", "type")
        # if self.endpoints fails, so will all the queues
        try:
            self.endpoints = {'main': "https://api.ifunny.mobi/v4/content/" + self.id,
                              'comments': f'https://api.ifunny.mobi/v4/content/{self.id}/comments',
                              'repubs': f'https://api.ifunny.mobi/v4/content/{self.id}/republished',
                              'smiles': f'https://api.ifunny.mobi/v4/content/{self.id}/smiles'}
            self.comments = Queue(Comment, self.endpoints['comments'])
            self.repubs = Queue(User, self.endpoints['repubs'])
            self.smiles = Queue(User, self.endpoints['smiles'])
        except AttributeError:
            self.errored_attributes.append("endpoints")
            self.errored_attributes.append("comments")
            self.errored_attributes.append("repubs")
            self.errored_attributes.append("smiles")

    def _data_cleaner(self, var):
        # this returns a cleaned dict after striping the output it deems unneeded. Also only returns first object if given a list

        # print(var)
        if type(var) == dict:
            if "error" in var and "not_found" == var['error']:
                raise NoContent
            if "id" in var:
                return var
            elif "data" in var:
                if "id" in var["data"]:
                    logger.info(var)
                    return var["data"]
                return var["data"]['content']['items'][0]
        elif type(var) == list:
            return self._data_cleaner(var[0])

        print(var)
        print("cleaner failed to find key")
        raise KeyError
    
    def reload(self):
        self.__init__(self.id)

    def add_comment(self, thing):
        self.comments.store(thing)
        return self

    def load_comment_tree(self, comments: int = None, reply_limit: int = None):
        """
        I don't want load functions, but this one is more complex so it gets to stay.
        :param comments: How many comments to try to load
        :param reply_limit: How many relpies to each comment loaded
        :return: None
        """
        self.comments.load(limit=comments)
        for a in self.comments:
            a.replies.load(reply_limit)
            a.nest_replies()
        return self

    def comment_tree(self) -> list:
        reply_list = []
        for a in self.comments:
            reply_list.append(a.tree())
        return reply_list

    def get_id_object(self, id_to_check: str):
        """
        Searches for id within the nested comments.
        :param id_to_check: Doesn't care about the class will just get its id.
        :return:
        """
        # pprint(self.cdata)
        if id_to_check == self.id:
            return self
        else:
            for a in self.comments:
                check_in = a.get_id_object(id_to_check=id_to_check)
                if check_in is not None:
                    return check_in
            return None


class User(IfBase):
    """
    This holds the user data and gets called at various different times. Just because data exists, it doesn't mean all data get loaded. May need to reload() to have all info
    """
    def __init__(self, creator_id: str = None, data: dict = None, file_name: str = None):
        logger.info("Creator object created")

        super().__init__(file_name)
        self.data_attributes.extend(('posts', 'subscriptions', 'subscribers'))

        if file_name:
            self.load_file(file_name)
        else:
            if creator_id:
                data = api_call(f"https://api.ifunny.mobi/v4/users/" + creator_id, auth=BASIC_TOKEN)
                cdata = self._data_cleaner(data)
                self.cdata = cdata
            if data:
                cdata = self._data_cleaner(data)
                self.cdata = cdata
            elif not any((creator_id, data, file_name)):
                raise ValueError("need args")

            self.update_attributes()

            if not file_name and "id" not in self.errored_attributes:
                self.file_name = self.id + "_" + self.file_name

    def update_attributes(self, data: dict = None):

        if not data:
            cdata = self.cdata
        else:
            cdata = self._data_cleaner(data)
            self.cdata = cdata

        self.errored_attributes = []

        try:
            self.days = cdata["meme_experience"]["days"]
        except KeyError:
            self.errored_attributes.append("days")

        self.try_store_attribute("web_url", "web_url")
        self.try_store_attribute("about", "about")
        self.try_store_attribute("id", "id")
        self.try_store_attribute("name", "nick")
        self.try_store_attribute("stats", "num")
        self.try_store_attribute("total_posts", "total_posts")
        try:
            self.endpoints = {"main": f"https://api.ifunny.mobi/v4/account",
                              'posts': f'https://api.ifunny.mobi/v4/timelines/users/' + self.id,
                              'subscriptions': f"https://api.ifunny.mobi/v4/users/{self.id}/subscriptions",
                              'subscribers': f"https://api.ifunny.mobi/v4/users/{self.id}/subscribers"}
            self.posts = Queue(Post, self.endpoints['posts'])
            self.subscriptions = Queue(User, self.endpoints['subscriptions'])
            self.subscribers = Queue(User, self.endpoints['subscribers'])
        except AttributeError:
            self.errored_attributes.append("endpoints")
            self.errored_attributes.append("posts")
            self.errored_attributes.append("subscriptions")
            self.errored_attributes.append("subscribers")

    def _data_cleaner(self, var):
        """
        Cleans given data to make it uniform for the
        :param var:
        :return:
        """
        # this returns a cleaned dict after striping the output it deems unneeded. Also only returns first object if given a list

        if type(var) == dict:
            if "error" in var and "not_found" == var['error']:
                raise NoContent()
            if "id" in var:
                return var
            elif "data" in var:
                if "id" in var["data"]:
                    return var["data"]
                return var["data"]['content']['items'][0]
        elif type(var) == list:
            return var[0]

        print(var)
        print(self.cdata)
        print("cleaner failed to find key")
        raise KeyError
    
    def reload(self):
        self.__init__(self.id)

    def add_post(self, thing):
        self.posts.store(thing)


# uses bearer to login and get info
class Account(IfBase):
    """
    By using the bearer token, get user info. This is just a more advanced User class.
    """

    def __init__(self, data: dict = None, file_name: str = None):

        super().__init__(file_name)
        self.data_attributes.extend(('posts', 'subscriptions', 'subscribers', 'comments', 'guests', 'blocked', 'smiles', 'sub_feed'))

        if file_name:
            self.load_file(file_name)
        else:
            if data:
                self.cdata = data
            else:
                self.cdata = api_call(url=f"https://api.ifunny.mobi/v4/account", auth=BEARER_TOKEN, params={"limit": 1})['data']

            self.update_attributes()

            if not file_name and "id" not in self.errored_attributes:
                self.file_name = self.id + "_" + self.file_name

    def update_attributes(self, data: dict = None):

        if not data:
            cdata = self.cdata
        else:
            cdata = data
            self.cdata = cdata
        self.try_store_attribute("about", "about")
        self.try_store_attribute("id", "id")
        self.try_store_attribute("name", "nick")
        self.try_store_attribute('stats', "num")
        self.try_store_attribute("web_url", "web_url")
        try:
            self.days = cdata['meme_experience']['days']
        except KeyError:
            self.errored_attributes.append("days")
        try:
            self.endpoints = {"main": f"https://api.ifunny.mobi/v4/account",
                              'posts': f'https://api.ifunny.mobi/v4/timelines/users/' + self.id,
                              'subscriptions': f"https://api.ifunny.mobi/v4/users/{self.id}/subscriptions",
                              'subscribers': f"https://api.ifunny.mobi/v4/users/{self.id}/subscribers",
                              'comments': f"https://api.ifunny.mobi/v4/users/my/comments",  # Comment objects
                              'guests': f"https://api.ifunny.mobi/v4/users/my/guests",  # User objects
                              'blocked': f"https://api.ifunny.mobi/v4/users/my/blocked",  # User objects
                              'smiles': f"https://api.ifunny.mobi/v4/users/my/content_smiles",  # Post objects
                              'sub_feed': f"https://api.ifunny.mobi/v4/timelines/home"}  # current sub feed
            self.posts = Queue(Post, self.endpoints['posts'])
            self.subscriptions = Queue(User, self.endpoints['subscriptions'])
            self.subscribers = Queue(User, self.endpoints['subscribers'])
            self.comments = Queue(Comment, self.endpoints['comments'])
            self.guests = Queue(User, self.endpoints['guests'])  # will load 1 less than specified fixme
            self.blocked = Queue(User, self.endpoints['blocked'])
            self.smiles = Queue(Post, self.endpoints['smiles'])
            self.sub_feed = Queue(Post, self.endpoints['sub_feed'])
            # these need the bearer auth to work
            self.comments.auth_token = BEARER_TOKEN
            self.guests.auth_token = BEARER_TOKEN
            self.blocked.auth_token = BEARER_TOKEN
            self.smiles.auth_token = BEARER_TOKEN
            self.sub_feed.auth_token = BEARER_TOKEN
        except AttributeError:
            self.errored_attributes.append("endpoints")
            self.errored_attributes.extend(("posts", "subscriptions", "subscribers", 'comments', 'guests', 'blocked',
                                            'smiles', 'sub_feed'))
        
    def reload(self):
        self.__init__()


def get_basic(identifier: str = None) -> str:
    """
    This is used to get a working Basic token. This should be used to set the global BASIC_TOKEN var if one is needed.
    Basic token can only gen one bearer
    :param identifier: If not set, identifier will be a random 32 len string? It should work no matter what it is.
    :return: A prepared Basic token which can now directly be used in headers.
    """
    if identifier is None:
        hex_string = os.urandom(32).hex().upper()
    else:
        hex_string = identifier
    client_id = """MsOIJ39Q28"""
    client_secret = """PTDc3H8a)Vi=UYap"""
    hex_id = hex_string + '_' + client_id
    hash_decoded = hex_string + ':' + client_id + ':' + client_secret
    hash_encoded = hashlib.sha1(hash_decoded.encode('utf-8')).hexdigest()
    return "Basic " + base64.b64encode(bytes(hex_id + ':' + hash_encoded, 'utf-8')).decode()


def get_bearer(basic_token: str, email: str, password: str) -> str:
    """
    Basically logs in to generate a Bearer token. As this is equivalent to a login, it is recommended to save token to
    avoid calling this many times. It is recommended to call load_auths() instead.
    It is assumed that this only gets called when a new one is needed
    :param basic_token: an identification Basic token, use get_basic() to get one
    :type basic_token: str
    :param email: Ifunny account email
    :type email: str
    :param password: Ifunny account password
    :type password: str
    :return: This will return a prepared Bearer token that is ready to use in headers
    :rtype: str
    """
    headers = {"Authorization": basic_token}
    data = {"username": email, "password": password, "grant_type": "password"}
    # print(headers, data)
    response = requests.post("https://api.ifunny.mobi/v4/oauth2/token", headers=headers, data=data)
    thing = response.json()
    try:
        if 'error' in thing:
            if thing['error_description'] == 'Forbidden':
                logger.warning("New bearer, 10s login delay")
                time.sleep(10)
                response = requests.post("https://api.ifunny.mobi/v4/oauth2/token", headers=headers, data=data)
                thing = response.json()
            elif thing['error_description'] == 'Your installation was banned':
                raise ExpiredBasicToken
        return "Bearer " + thing["access_token"]
    except KeyError:
        print("Something went wrong")
        print(response.content)
        raise KeyError


def load_auths(identifier: str = None, email: str = None, password: str = None, new_login: bool = False, file: str = 'auth_data') -> None:
    """
    This will set Basic and Bearer global vars by generating them and then saving them to file, or reading from file.
    If read from file, no prams are needed
    notes:
    After basic is used to make bearer, it can't be used again
    Basic token needs to be used once first by nothing but the same get bearer
    I assume that email and pass are correct. I cannot properly check for bad login
    :param identifier: Used by servers to identify device, useful if consistency is needed. Always optional.
    :type identifier: str
    :param email: Ifunny account login email
    :type email: str
    :param password: Ifunny account login password
    :type password: str
    :param force: forcibly get new auths and overwrite saved ones (use if bearer got killed)
    :type force: bool
    :return: No return, but global vars are now set. Will error if something goes wrong.
    :rtype: None
    """
    logger.info("running login function")
    global BASIC_TOKEN, BEARER_TOKEN
    if os.path.isfile(file) and not new_login:
        # todo change this to json?
        # load tokens from file
        with open(file, "r") as f:
            thing = eval(f.read())
        BASIC_TOKEN = thing["Basic"]
        BEARER_TOKEN = thing["Bearer"]
        return
    # file not found
    if None in (email, password):
        # no file and missing needed params
        print("need email and/or password")
        os.system("pause")
        exit()
    BASIC_TOKEN = get_basic(identifier=identifier)
    BEARER_TOKEN = get_bearer(BASIC_TOKEN, email=email, password=password)
    with open(file, "w") as f:
        f.write(str({"Basic": BASIC_TOKEN, "Bearer": BEARER_TOKEN}))
    return


def kill_bearer(bearer: str = BEARER_TOKEN):
    """
    Untested but should kill the bearer token
    :param bearer:
    :return:
    """
    if "Bearer " in bearer:
        bearer = bearer[7:]
    headers = {"Authorization": BASIC_TOKEN}
    response = requests.post(url='https://api.ifunny.mobi/v4/oauth2/revoke', headers=headers, data={'token': bearer})
    return response


def api_call(url: str, auth: str = None, params: dict = None, method="GET") -> dict:
    """
    To simplify the api calls and hopefully clean up code
    :param url: The link that gets sent to, id will have to be embeded
    :type url: str
    :param auth: The needed auth token as a string
    :type auth: str
    :param params: extra things like limit
    :type params: dict
    :param method:
    :return: The parsed response
    :rtype: dict
    """
    logger.debug("making api call")
    if auth is None or auth == "":
        raise MissingAuthToken()
    header_thing = {'Authorization': auth}
    # print(params)
    try:
        response = requests.request(method, url, headers=header_thing, params=params)
        parsed = json.loads(response.content)
        if 'error' in parsed:
            raise KeyError
    except:
        logger.warning('error/exception in api_call')
        try:
            response = requests.request(method, url, headers=header_thing, params=params)
            parsed = json.loads(response.content)
            if 'error' in parsed:
                raise KeyError
        except:
            time.sleep(5)
            logger.warning('error/exception in api_call (2nd/delayed call)')
            try:
                response = requests.request(method, url, headers=header_thing, params=params)
                parsed = json.loads(response.content)
                if 'error' in parsed:
                    raise KeyError
            except:
                print('Something errored')
                print(url)
                if response:
                    print(response.content)
                raise NoContent
    return parsed


def dl_from_link(url: str, file_name: str = None):
    """
    Does as name implies.
    :param url: file source
    :param file_name: where to put it, and what to name it untested if other paths work, I just use same dir.
    :return: None
    """
    if not file_name:
        name = url.split('/')[-1]
    else:
        name = file_name
    print(f'dl: {name}')
    with open(name, 'wb') as f:
        f.write(requests.get(url).content)


def post_from_url(url: str) -> Post:
    """
    Uses the real post url and finds the id within the page.
    :param url: Link to ifunny site
    :type url: str
    :return: The post itself as the Post object. Post.id will return the id
    :rtype: Post
    """
    request = requests.get(url)
    tree = html.fromstring(request.content)
    # this might break
    post_id = tree.xpath("//li[@class='stream__item ']/div[@class='post']/@data-id")[0]  # this can break
    # print(post_id)
    return Post(post_id=post_id)


def post_from_id(post_id: str) -> Post:
    """
    Not needed as Post() exists, but here to parallel with post_from_url()
    :param post_id: id of the post
    :type post_id: str
    :return: Post object
    :rtype: Post
    """
    return Post(post_id=post_id)


def recursive_id_print(base_comment, target: tuple, indent_scale: int = 3, current_indent: int = 0) -> None:
    """
    A function used to try to cleanly print all replies in the correct nested way
    :param base_comment: The anchor comment for this branch
    :param target: What gets attached
    :param indent_scale: How big is the indent
    :param current_indent: How much is it indented
    :return: None, it just prints
    """
    if isinstance(base_comment, Post):
        # pprint(base_comment.cdata)
        print(" " * current_indent + base_comment.id)
        for a in target:
            recursive_id_print(base_comment.get_id_object(a[0]), a, current_indent=current_indent + indent_scale)
    else:
        print(" " * (current_indent - 0) + base_comment.get_id_object(target[0]).text)
        for a in target[1]:
            recursive_id_print(base_comment, a, current_indent=current_indent + indent_scale)


def get_author_id(text: str, search_limit: int = 1):
    # from a post url
    if text.__contains__("ifunny."):
        """
        When using a url to profile, find author_id in page
        """
        request = requests.get(text)
        # print(text)
        # print(request.text)
        tree = html.fromstring(request.content)
        # this might break
        # print(tree.xpath('//script')[0].text)
        potential_id = tree.xpath('//script')
        for a in potential_id:
            if "__INITIAL_STATE__" in a.text:
                found = a.text
                # print(found)
                json_object = json.loads(found.split(' = ')[1][:-1])
                author_id = json_object["user"]["data"]["id"]
                # print(author_id)
                return author_id
    else:
        """
        When searching by name and using ifunny's searching (can't find shadowbanned/nonexistent names)
        """
        requst = api_call(url=f'https://api.ifunny.mobi/v4/search/users_for_mentions', auth=BEARER_TOKEN, params={"q": text, 'limit': search_limit})
        preped = requst['data']['users']['items']
        if search_limit == 1:
            try:
                return preped[0]["id"]
            except IndexError:
                print(preped)
        return [(a["id"], a['original_nick']) for a in preped]


def get_features(limit: int = 0) -> Queue:
    """
    Get the current features
    :param limit: How many to grab
    :return: Queue object with the current features
    """
    feats = Queue(Post, "https://api.ifunny.mobi/v4/feeds/featured")
    feats.load(limit=limit)
    return feats


def get_popular(limit: int = 0) -> Queue:
    """
    Get random featured posts
    :param limit: How many to load
    :return: The Queue object
    """
    pop = Queue(Post, "https://api.ifunny.mobi/v4/feeds/popular")
    pop.load(limit=limit)
    return pop


def get_collective(limit: int = 0) -> Queue:
    """
    This one almost destroys anything I had organized because it needs post instead of get.
    If limit == None then it will return a clean Queue object for use.
    :param limit: How many to load
    :return: The current collective
    """
    collective = Queue(Post, "https://api.ifunny.mobi/v4/feeds/collective")
    if limit is None:
        collective.load(limit=0)
    else:
        collective.load(limit=limit)
    return collective

"""
Made by Nam. Discord: that_dude#1313, Github: XDEmer0r-L0rd-360-G0d-SlayerXD
"""
