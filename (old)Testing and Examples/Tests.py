# this program will be the front end and do tests
import ifunny_lib as ifl
from pprint import pprint
import logging
from timeit import default_timer as timer

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

iflib_logger = logging.getLogger("ifunny_lib")
iflib_logger.setLevel(logging.WARNING)


def time(func):
    start = timer()
    func()
    end = timer()
    print(end - start, 's')


def auth_test():
    """
    Test if auth works, specifically caching
    :return: nothing, it will error if something goes wrong
    :rtype: None
    """
    logging.info("Running auth_test()")
    ifl.load_auths()
    # tokens were removed for security
    assert ifl.BASIC_TOKEN != "Basic something"
    assert ifl.BEARER_TOKEN != "Bearer something else"

    print("Auths_test works")


def post_test():
    """
    Test if getting post data works
    :return: nothing, it will error if something goes wrong
    :rtype: None
    """
    logger.info("Running post_test()")
    example_post = ifl.Post("KDI1pd1g7")
    # does it pull info correctly
    # print(example_post.raw_data)
    # pprint(example_post.cdata)
    assert example_post.cdata['publish_at'] == 1590010680
    assert example_post.creator_name == 'I_love_weed_'
    # print(example_post.raw_data["data"]["fixed_title"])

    # does it work with a url
    example_post = ifl.post_from_url(
        "https://ifunny.co/picture/if-wendys-doesn-t-like-this-tweet-within-1-hour-KDI1pd1g7")
    assert example_post.cdata['publish_at'] == 1590010680

    # does it work with an id
    example_post = ifl.post_from_id("KDI1pd1g7")
    assert example_post.cdata['publish_at'] == 1590010680
    # print(example_post.stats)

    print("post_test works")


def comment_comaprison():
    """
    testing testing path to comment and direct comment look up to be identical
    """
    logger.info("Running comment_comparison()")
    response = ifl.post_from_url(
        'https://ifunny.co/video/this-could-have-been-sub-50-AU9c9Rbi7?gallery=user&query=namisboss')
    comment = ifl.api_call(f"https://api.ifunny.mobi/v4/content/{response.id}/comments", auth=ifl.BASIC_TOKEN)['data'][
        'comments']['items'][0]
    comment_two = ifl.Comment('AU9c9Rbi7', '5edbbfcfe6abce6b205106ec')
    # print(comment_two.raw_data['data']['comment'])
    # print(comment)
    assert comment_two.cdata == comment
    print('Post comments and comment lookup are identical')


def comment_test():
    logger.info("Running comment_test()")

    # test loading from a post
    example_post = ifl.Post('NSRM3Edh7')
    # print(example_post.raw_data)
    example_post.load_comment_tree(comments=20, reply_limit=300)
    # logger.info("loaded comment tree")
    # ifl.recursive_id_print(example_post, example_post.comment_id_tree())
    assert len(example_post.comments) >= 1

    # test loading from a comment
    example_comment = ifl.Comment(post_id="NSRM3Edh7", comment_id='5ed3d6beec57403d3d034ce7')
    # print(example_comment.replies)
    did_load = example_comment.replies.load(limit=10)
    # print('Loaded replies:', did_load)
    # ifl.recursive_id_print(example_comment, example_comment.id_tree())
    # print(example_comment.replies)
    assert did_load
    assert len(example_comment.replies) >= 1
    print("seems to find, populate, and parse comments correctly")
    # pprint(example_comment.tree())
    # view = example_comment.has_id_object('5ed5dedad00afe765e3b68fc')
    # print(view.text)


def get_post_info_and_comments():
    logger.info("Runing get_post_info_and_comments()")
    # to try to demonstrate what how to use api
    # ifl.load_auths() already ran
    # print(ifl.post_from_url('https://ifunny.co/picture/me-when-i-see-animals-hurting-people-see-people-aro-GXxybkXN7?gallery=featured').post_id) returned GXxybkXN7
    example_post = ifl.post_from_id('GXxybkXN7')
    example_post.load_comment_tree(comments=2, reply_limit=1)
    # id_tree = example_post.comment_id_tree()
    # print(id_tree)
    # print(example_post)
    # ifl.recursive_id_print(example_post, id_tree)
    assert example_post.comments[0].cdata['state'] == 'top'
    print("properly loads comments from post id start with the first one being a top comment")


def get_author_id():
    logger.info("Running get_author_id()")
    link_id = ifl.get_author_id('https://ifunny.co/user/Scum')
    # print(link_id)
    temp_post = ifl.post_from_url(
        'https://ifunny.co/picture/dorit-girlfriend-ordering-my-starbucks-drink-XW5wI8bt7?gallery=user&query=Scum')
    print(temp_post.creator_id)
    searched = ifl.get_author_id("scum", search_limit=3)
    assert link_id == temp_post.creator_id == searched[0][0]
    print("All three methods to get author id give the same id")


def auth_info():
    logger.info("Running auth_info()")
    id = ifl.get_author_id("GodDammitJim_2016")
    author = ifl.User(id)
    # print(type(User.raw_data))
    author.posts.load(2)
    assert len(author.posts) == 2
    author.posts.chunks = 100  # by setting chunks to 100, we reach ~100 posts/s
    author.posts.load(limit=2)
    assert len(author.posts) > 3
    # print(len(author.posts))
    # pprint(author.posts[0].cdata)
    print('Gets author info and loads the first visible posts (incomplete test)')


def basic_queue_loading():
    logger.info('Running basic_queue_loading()')
    # first need to replace important code, and then test new Queue functionality
    author_id = ifl.get_author_id("timebomb69882timebomb6988")
    author_obj = ifl.User(author_id)
    post_queue = ifl.Queue(ifl.Post, author_obj.endpoints['posts'])
    post_queue.load()
    # print(len(post_queue.stored_content))
    for a in post_queue:
        # print(a)
        pass


def get_subscriptions():
    logger.info("Running get_subscriptoins()")

    # this code was used to visually compare user data from subscriptions list and user object
    #
    author_id = ifl.get_author_id("namisboss")
    user = ifl.User(creator_id=author_id)
    user.subscriptions.load(2)
    response = ifl.api_call(url=f"https://api.ifunny.mobi/v4/users/{author_id}/subscriptions", auth=ifl.BASIC_TOKEN,
                            params={"limit": 1})
    # sub_author_id = ifl.get_author_id("PoliticallyincorrectAPOI")
    sub_author_id = "51cb699bc573a4904eb0a0be"
    sub_author = ifl.User(sub_author_id)
    # pprint(response["data"]["users"]["items"])
    # pprint(sub_author.cdata)
    # pprint(user.subscriptions[0].cdata)
    assert sub_author.cdata == user.subscriptions[0].cdata
    print("Correctly gets my first subscription")


def user_vs_account():
    logger.info("Running user_vs_account()")

    author_id = ifl.get_author_id("namisboss")
    response = ifl.api_call(
        url=f"https://api.ifunny.mobi/v4/users/{author_id}",
        auth=ifl.BEARER_TOKEN,
        params={"limit": 1})
    # pprint(author_id)

    # todo see if there is any more info to be gotten for indirectly blocked users, ask for it on devs
    # Faicial id: 579c41d36d9c4dc9188b4591
    # Scrum id: 5468586e4c4fd0d9688b456a
    # auth_response = ifl.api_call(url="https://api.ifunny.mobi/v4/map", auth=ifl.BEARER_TOKEN, params={'lat1': -90, 'lat2': 90, "lon1": -180, "lon2": 180, 'limit': 2})
    auth_response = ifl.api_call(url=f"https://api.ifunny.mobi/v4/account",
                                 auth=ifl.BEARER_TOKEN, params={'limit': 100})
    # pprint(auth_response)
    assert response == auth_response
    print('User call returns the same data as account info')


def deleted_comment():
    com = ifl.Comment('fN8fdWnz7', '5f68130432cf2f798314db6e')
    pprint(com.cdata)


def kill_bearer_func():
    print(ifl.kill_bearer("c00b9bdc7d3fc37bc313b98c3396ac2dc91a78d93f80a1d6f486532c3e29cd2d"))


def denester():
    example_post = ifl.post_from_id('GXxybkXN7')
    example_post.load_comment_tree(limit=2, reply_limit=1)


def endpoint_test():
    post = ifl.post_from_id("GXxybkXN7")
    post.comments.load(5)
    comment = post.comments[0]
    # pprint(comment.url_api)
    # pprint(post.cdata)
    # todo: throw these urls into gobuster
    # I care about users/my/ comments, subscriptions, guests, subscribers, blocked?
    response = ifl.api_call(
        url=f"https://api.ifunny.mobi/v4/content/NSRM3Edh7/comments/5ed40dcef4638846d3662a2b",
        auth=ifl.BEARER_TOKEN,
        params={"limit": 3})
    pprint(response)

    response2 = ifl.api_call(
        url=f"https://api.ifunny.mobi/v4/feeds/self",
        auth=ifl.BASIC_TOKEN,
        params={"limit": 1})
    # pprint(response2)
    # print(ifl.get_collective(1))
    # assert response == response2
    # post.repubs.id_only_mode = True
    # post.load_repubs(50)
    # print(post.repubs)


def main():
    # ifl.load_auths(email="email", password="pass")  # only needed when auth_test() is not run

    auth_test()
    post_test()
    comment_comaprison()
    comment_test()
    get_post_info_and_comments()
    get_author_id()
    auth_info()
    # time(auth_info)
    basic_queue_loading()
    get_subscriptions()
    user_vs_account()
    deleted_comment()
    kill_bearer_func()
    denester()
    endpoint_test()
    print(ifl.BEARER_TOKEN)
    print(ifl.BASIC_TOKEN)


if __name__ == '__main__':
    main()
